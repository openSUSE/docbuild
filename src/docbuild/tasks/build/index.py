"""Task for generating index HTML pages from metadata using Jinja2."""

from datetime import datetime
import json
import logging
from pathlib import Path
import re
from typing import Any

import jinja2

from ...cli.console import console, console_err
from ...models.doctype import Doctype

log = logging.getLogger(__name__)


def resolve_dynamic_path(template_str: str, mapping: dict[str, str]) -> str:
    """Replace all placeholder variations including single/double braces and quotes."""
    result = str(template_str)
    for key, val in mapping.items():
        pattern = re.compile(rf"[\{{\"']*{re.escape(key)}[\}}\"']*", re.IGNORECASE)
        result = pattern.sub(val, result)

    return re.sub(r"[\{\}\"']", "", result)


def _get_search_patterns(doctypes: list[Doctype]) -> list[str]:
    """Build list of JSON search glob patterns from requested doctypes."""
    if not doctypes:
        return ["*.json"]

    patterns: list[str] = []
    for dt in doctypes:
        docsets = getattr(dt, "docset", ["*"])
        if not docsets:
            docsets = ["*"]
        elif isinstance(docsets, str):
            docsets = [docsets]

        for ds in docsets:
            patterns.append("*.json" if ds == "*" else f"{ds}.json")

    return patterns


def _extract_render_context(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str], str]:
    """Extract template context variables, path mappings, and language code from raw metadata."""
    category = str(data.get("category", "product")).lower()
    docset_id = data.get("version", "unknown")
    product = data.get("productname", "").lower().replace(" ", "-") or "unknown"
    version = data.get("version", "unknown")

    lang = "en-us"
    if "docs" in data and isinstance(data["docs"], list) and len(data["docs"]) > 0:
        lang = data["docs"][0].get("lang", "en-us")

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

    return render_context, format_dict, lang


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
        old_html = out_dir / "index_old.html"
        index_html.rename(old_html)
        console.print(f"Backed up existing {index_html.name} -> {old_html.name}")

    try:
        rendered = template.render(**render_context)
        index_html.write_text(rendered, encoding="utf-8")
        console.print(f"[green]✔ Rendered index page[/] for {docset_id} ({lang}) -> {index_html}")
        return True
    except Exception as e:
        console_err.print(f"[error]Failed to render template for {docset_id}:[/] {e}")
        return False


async def process(
    main_portal_config: Path,
    jinja_dir: Path,
    json_cache_dir: Path,
    target_base_dir: Path,
    target_dir_dyn: str,
    doctypes: list[Doctype],
    keep_index: bool,
) -> int:
    """Render index pages from JSON metadata using Jinja2."""
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

    search_names = _get_search_patterns(doctypes)
    json_files: set[Path] = set()
    for name in search_names:
        json_files.update(json_cache_dir.rglob(name))

    if not json_files:
        console_err.print(
            f"[yellow]⚠ No JSON metadata files found in {json_cache_dir} matching {search_names}[/]"
        )
        return 0

    processed = 0
    errors = 0

    for json_file in json_files:
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            console_err.print(f"[error]Failed to read JSON {json_file.name}:[/] {e}")
            errors += 1
            continue

        docset_id = json_file.stem
        render_context, format_dict, lang = _extract_render_context(data)
        out_dir_rel = resolve_dynamic_path(target_dir_dyn, format_dict)
        out_dir = target_base_dir / out_dir_rel

        success = _render_and_write_index(
            template, render_context, out_dir, docset_id, lang, keep_index
        )
        if success:
            processed += 1
        else:
            errors += 1

    console.print(
        f"\n[bold]Index Generation Summary:[/] {processed} files rendered, {errors} errors."
    )
    return 1 if errors > 0 else 0
