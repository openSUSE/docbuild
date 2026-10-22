"""Task for generating index HTML pages from metadata using Jinja2."""

import asyncio
from collections.abc import Sequence
from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any

from aiostream import pipe, stream
import jinja2

from ...cli.console import console, console_err
from ...models.doctype import Doctype
from ...models.manifest import Manifest

log = logging.getLogger(__name__)


def _matches_doctypes(
    doctypes: Sequence[Doctype], product: str, docset: str, lang: str
) -> bool:
    """Check if the given product, docset, and language match any of the doctypes."""
    if not doctypes:
        return True

    for dt in doctypes:
        # Extract product acronym (handling Product Enum object)
        dt_prod = getattr(dt, "product", "*")
        if getattr(dt_prod, "name", "") == "ALL":
            dt_prod_str = "*"
        else:
            dt_prod_str = getattr(dt_prod, "acronym", str(dt_prod))

        # Extract docsets (list of strings)
        dt_docsets = getattr(dt, "docset", ["*"]) or ["*"]
        if not isinstance(dt_docsets, (list, tuple, set)):
            dt_docsets = [dt_docsets]

        # Extract language strings (handling LanguageCode model objects)
        dt_langs_raw = getattr(dt, "langs", getattr(dt, "lang", ["*"])) or ["*"]
        if not isinstance(dt_langs_raw, (list, tuple, set)):
            dt_langs_raw = [dt_langs_raw]
        dt_langs = [getattr(lng, "language", str(lng)) for lng in dt_langs_raw]

        match_prod = dt_prod_str == "*" or dt_prod_str.lower() == str(product).lower()
        match_ds = "*" in dt_docsets or str(docset).lower() in [str(d).lower() for d in dt_docsets]
        match_lang = "*" in dt_langs or str(lang).lower() in [str(lng).lower() for lng in dt_langs]

        if match_prod and match_ds and match_lang:
            return True

    return False


def _get_languages(data: dict[str, Any]) -> list[str]:
    """Extract all localized languages from the manifest data."""
    languages = {
        archive["lang"]
        for archive in data.get("archives", [])
        if isinstance(archive, dict) and archive.get("lang")
    }
    if not languages:
        languages = {
            doc["lang"]
            for document in data.get("documents", [])
            if isinstance(document, dict)
            for doc in document.get("docs", [])
            if isinstance(doc, dict) and doc.get("lang")
        }
    if not languages:
        languages = {
            doc["lang"]
            for doc in data.get("docs", [])
            if isinstance(doc, dict) and doc.get("lang")
        }
    if not languages:
        languages = {"en-us"}
    return sorted(languages)


def _render_and_write_index(
    template: jinja2.Template,
    render_context: dict[str, Any],
    out_dir: Path,
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
        console.print(f"Backed up existing {index_html.name} -> {old_html.name}")

    try:
        rendered = template.render(**render_context)
        index_html.write_text(rendered, encoding="utf-8")
        console.print(
            f"[success]✔ Rendered index page[/] for {docset_id} ({lang}) -> {index_html}"
        )
        return True
    except Exception as e:
        console_err.print(f"[error]Failed to render template for {docset_id} ({lang}):[/] {e}")
        return False


def process_manifest_sync(
    json_file: Path,
    template: jinja2.Template,
    doctypes: Sequence[Doctype],
    target_base_dir: Path,
    target_dir_dyn: str,
    keep_index: bool,
) -> tuple[int, int]:
    """Parse JSON, check doctypes, render and write HTML synchronously."""
    try:
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        console_err.print(f"[error]Failed to read JSON {json_file.name}:[/] {exc}")
        return 0, 1

    try:
        # Use Manifest model to extract known fields cleanly
        manifest = Manifest(**data)
        product = getattr(manifest, "acronym", None) or "unknown"
        version = getattr(manifest, "version", None) or "unknown"
    except Exception:
        # Fallback if validation fails
        product = data.get("acronym", "unknown")
        version = data.get("version", "unknown")

    docset_id = version
    category = str(data.get("category", "product")).lower()
    languages = _get_languages(data)

    processed = 0
    errors = 0

    for lang in languages:
        if not _matches_doctypes(doctypes, product, docset_id, lang):
            continue

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
            "version": version,
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

        success = _render_and_write_index(
            template, render_context, out_dir, docset_id, lang, keep_index
        )
        if success:
            processed += 1
        else:
            errors += 1

    return processed, errors


async def process_manifest(
    json_file: Path,
    template: jinja2.Template,
    doctypes: Sequence[Doctype],
    target_base_dir: Path,
    target_dir_dyn: str,
    keep_index: bool,
) -> tuple[int, int]:
    """Async wrapper to process a single manifest file in a thread."""
    task = asyncio.current_task()
    if task is not None:
        task.set_name(f"build:index:{json_file.parent.name}:{json_file.stem}")
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
    except Exception as exc:
        console_err.print(f"[error]Failed to process {json_file.name}:[/] {exc}")
        return 0, 1


async def process(
    main_portal_config: Path | str,
    jinja_dir: Path | str,
    json_cache_dir: Path | str,
    target_base_dir: Path | str,
    target_dir_dyn: str,
    doctypes: Sequence[Doctype],
    keep_index: bool,
) -> int:
    """Render index pages from JSON metadata using Jinja2 async pipelines."""
    # Ensure all path arguments are actual Path objects
    jinja_dir = Path(jinja_dir)
    json_cache_dir = Path(json_cache_dir)
    target_base_dir = Path(target_base_dir)

    if not jinja_dir.exists():
        console_err.print(f"[error]Jinja directory not found:[/] {jinja_dir}")
        return 1

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(jinja_dir),
        autoescape=jinja2.select_autoescape(["html", "xml"]),
    )

    def custom_file_exists(filepath: str | Path | None) -> bool:
        """Check if a file exists relative to the target base directory."""
        if not filepath:
            return False
        check_path = target_base_dir / str(filepath).lstrip("/")
        return check_path.exists()

    env.filters["file_exists"] = custom_file_exists

    try:
        template = env.get_template("index.html.jinja")
    except jinja2.TemplateNotFound:
        console_err.print(f"[error]Template 'index.html.jinja' not found in {jinja_dir}[/]")
        return 1

    json_files = list(json_cache_dir.rglob("*.json"))

    if not json_files:
        console_err.print(
            f"[yellow]⚠ No JSON metadata files found in {json_cache_dir}[/]"
        )
        return 0

    processed = 0
    errors = 0
    max_workers = 10

    async def _map_manifest(jf: Path) -> tuple[int, int]:
        return await process_manifest(
            jf, template, doctypes, target_base_dir, target_dir_dyn, keep_index
        )

    pipeline = stream.iterate(json_files) | pipe.map(
        _map_manifest,
        task_limit=max_workers,
        ordered=False,
    )

    async with pipeline.stream() as streamer:
        async for p, e in streamer:
            processed += p
            errors += e

    console.print(
        f"\n[info]Index Generation Summary:[/] {processed} files rendered, {errors} errors."
    )
    return 1 if errors > 0 else 0
