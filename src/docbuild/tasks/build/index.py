"""Task for generating index HTML pages from metadata using Jinja2."""

import asyncio
from collections.abc import Iterator, Sequence
from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any

from aiostream import stream
import jinja2
from pydantic import ValidationError

from ...cli.console import console, console_err
from ...constants import DEFAULT_LIFECYCLE
from ...models.doctype import Doctype
from ...models.lifecycle import LifecycleFlag
from ...models.manifest import Manifest

log = logging.getLogger(__name__)


def get_matching_doctypes(
    doctypes: Sequence[Doctype],
    product: str,
    docset: str,
    lang: str | None,
    lifecycle: str | LifecycleFlag = LifecycleFlag.unknown,
) -> Iterator[Doctype]:
    """Yield matching constraints using the shared Doctype containment rules."""
    if not doctypes:
        return

    candidate = Doctype(
        product=product,
        docset=[docset],
        langs=[] if lang is None else [lang],
        lifecycle=lifecycle,
    )
    yield from (doctype for doctype in doctypes if candidate in doctype)


def get_languages(manifest: Manifest) -> list[str]:
    """Return sorted archive languages, falling back to documents or English."""
    languages = {str(archive.lang) for archive in manifest.archives}
    if not languages:
        languages = {
            doc.lang
            for document in manifest.documents
            for doc in document.docs
            if doc.lang
        }

    return sorted(languages) or ["en-us"]


def render_and_write_index(
    template: jinja2.Template,
    render_context: dict[str, Any],
    out_dir: Path,
    product: str,
    docset_id: str,
    lang: str,
    keep_index: bool,
) -> bool:
    """Render the Jinja template and write the index.html file to disk."""
    out_dir.mkdir(parents=True, exist_ok=True)
    index_html = out_dir / "index.html"

    if index_html.exists() and keep_index:
        old_html = out_dir / "index.html.bak"
        index_html.rename(old_html)
        log.debug("Backed up existing %s to %s", index_html.name, old_html.name)

    try:
        rendered = template.render(**render_context)
        index_html.write_text(rendered, encoding="utf-8")
        console.print(
            f"[success]✔ Rendered index page[/] for {product}/{docset_id}/{lang} -> {index_html}"
        )
        return True
    except jinja2.TemplateError as e:
        console_err.print(f"[error]Failed to render template for {product}/{docset_id}/{lang}:[/] {e}")
        return False
    except OSError as e:
        console_err.print(f"[error]Failed to write index.html for {product}/{docset_id}/{lang}:[/] {e}")
        return False


def process_manifest_sync(
    json_file: Path,
    template: jinja2.Template,
    doctypes: Sequence[Doctype],
    target_base_dir: Path,
    target_dir_dyn: str,
    keep_index: bool,
) -> tuple[int, int, list[Doctype]]:
    """Parse JSON, check doctypes, render and write HTML synchronously."""
    log.debug("Reading manifest: %s", json_file.name)
    try:
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        console_err.print(f"[error]Failed to read JSON {json_file.name}:[/] {exc}")
        return 0, 1, []

    if (
        doctypes
        and isinstance(data, dict)
        and "acronym" in data
        and "version" in data
        and not any(get_matching_doctypes(
            doctypes, data["acronym"], data["version"], None
        ))
    ):
        return 0, 0, []

    try:
        manifest = Manifest.model_validate(data)
    except ValidationError as exc:
        console_err.print(f"[error]Validation error for {json_file.name}:[/] {exc}")
        return 0, 1, []

    product = getattr(manifest, "acronym", "unknown")
    docset_id = getattr(manifest, "version", "unknown")

    cats = getattr(manifest, "categories", [])
    if cats:
        primary = cats[0]
        category = str(getattr(primary, "value", primary)).lower()
    else:
        category = "product"

    languages = get_languages(manifest)

    processed = 0
    errors = 0
    matched_doctypes = []

    for lang in languages:
        matched = list(get_matching_doctypes(
            doctypes, product, docset_id, lang, manifest.lifecycle
        ))
        if not matched and doctypes:
            continue

        matched_doctypes.extend(matched)

        render_context = {
            "data": data,
            "now": datetime.now,
            "lang": lang,
            "isProduct": category not in ["sbp", "trd", "smartdocs"],
            "isSBP": category == "sbp",
            "isTRD": category == "trd",
            "isSmartDocs": category == "smartdocs",
            "translations": data.get("translations", {}),
            "base_url": "/",
        }

        format_dict = {
            "product": product,
            "version": docset_id,
            "lang": lang,
            "docset": docset_id,
            "category": category,
        }

        try:
            path_template = jinja2.Template(target_dir_dyn)
            out_dir_rel = path_template.render(**format_dict)
        except jinja2.TemplateError as exc:
            console_err.print(
                f"[error]Failed to render target directory path for {json_file.name}:[/] {exc}"
            )
            errors += 1
            continue

        out_dir = target_base_dir / out_dir_rel.strip("/")

        success = render_and_write_index(
            template, render_context, out_dir, product, docset_id, lang, keep_index
        )
        if success:
            processed += 1
        else:
            errors += 1

    return processed, errors, matched_doctypes


async def process_manifest(
    json_file: Path,
    template: jinja2.Template,
    doctypes: Sequence[Doctype],
    target_base_dir: Path,
    target_dir_dyn: str,
    keep_index: bool,
) -> tuple[int, int, list[Doctype]]:
    """Async wrapper to process a single manifest file in a thread."""
    task = asyncio.current_task()
    if task is not None:
        task.set_name(f"build:index:{json_file.parent.name}:{json_file.stem}")
    log.debug("Reading manifest: %s", json_file)
    try:
        return await asyncio.to_thread(
            process_manifest_sync,
            json_file,
            template,
            doctypes,
            target_base_dir,
            target_dir_dyn,
            keep_index,
        )
    except (OSError, ValueError) as exc:
        console_err.print(f"[error]Failed to process {json_file.name}:[/] {exc}")
        return 0, 1, []


def load_template(jinja_dir: Path, target_base_dir: Path) -> jinja2.Template | None:
    """Initialize Jinja environment and load the index template."""
    if not jinja_dir.exists():
        console_err.print(f"[error]Jinja directory not found:[/] {jinja_dir}")
        return None

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(jinja_dir),
        autoescape=jinja2.select_autoescape(["html", "xml"]),
    )

    def custom_file_exists(filepath: str | Path | None) -> bool:
        if not filepath:
            return False
        check_path = target_base_dir / str(filepath).lstrip("/")
        return check_path.exists()

    env.filters["file_exists"] = custom_file_exists

    try:
        return env.get_template("index.html.jinja")
    except jinja2.TemplateNotFound:
        console_err.print(f"[error]Template 'index.html.jinja' not found in {jinja_dir}[/]")
        return None


async def process(
    jinja_dir: Path,
    json_cache_dir: Path,
    target_base_dir: Path,
    target_dir_dyn: str,
    doctypes: Sequence[Doctype],
    keep_index: bool,
    max_workers: int = 10,
) -> int:
    """Render index pages from JSON metadata using Jinja2 async pipelines."""
    jinja_dir = Path(jinja_dir)
    json_cache_dir = Path(json_cache_dir)
    target_base_dir = Path(target_base_dir)

    doctypes = [
        dt.model_copy(update={"lifecycle": LifecycleFlag(DEFAULT_LIFECYCLE)})
        if dt.lifecycle == LifecycleFlag.unknown else dt
        for dt in doctypes
    ]

    template = load_template(jinja_dir, target_base_dir)
    if not template:
        return 1

    json_files = [
        path for path in json_cache_dir.rglob("*.json")
        if path != json_cache_dir / "homepage.json"
        and (
            not doctypes
            or path.parent == json_cache_dir
            or any(get_matching_doctypes(
                doctypes, path.parent.name, path.stem, None
            ))
        )
    ]

    if not json_files:
        console_err.print(
            f"[yellow]⚠ No JSON metadata files found in {json_cache_dir}[/]"
        )
        return 0

    processed = 0
    errors = 0
    all_matched_doctypes = set()

    async def _map_manifest(
        jf: Path, *additional_paths: Path
    ) -> tuple[int, int, list[Doctype]]:
        return await process_manifest(
            jf, template, doctypes, target_base_dir, target_dir_dyn, keep_index
        )

    log.info("Starting index generation for %d manifest(s) with %d workers", len(json_files), max_workers)

    pipeline = stream.map(
        stream.iterate(json_files),
        _map_manifest,
        task_limit=max_workers,
        ordered=False,
    )

    async with pipeline.stream() as streamer:
        async for p, e, matched in streamer:
            processed += p
            errors += e
            all_matched_doctypes.update(matched)

    # Validate that every doctype constraint provided by the user actually matched something
    if doctypes:
        unmatched = set(doctypes) - all_matched_doctypes
        if unmatched:
            for u in unmatched:
                console_err.print(f"[error]No matches found for doctype:[/] {u}")
            errors += len(unmatched)

    console.print(
        f"\n[info]Index Generation Summary:[/] {processed} files rendered, {errors} errors."
    )
    return 1 if errors > 0 else 0
