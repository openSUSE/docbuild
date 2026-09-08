"""Extractor for prebuilt (Antora) deliverable metadata."""

import datetime
import json
import logging
from pathlib import Path
import re
from typing import Any

from docbuild.models.deliverable import Deliverable
from docbuild.models.language import LanguageCode

log = logging.getLogger(__name__)


def _find_html_path(prebuilt_dir: Path, deliverable: Deliverable, html_url: str) -> Path | None:
    """Attempt to find the prebuilt HTML file in multiple candidate paths."""
    if not html_url:
        return None

    clean_url = html_url.lstrip("/")
    lang_str = str(deliverable.xml.lang)
    short_lang = lang_str.split("-")[0]

    # Create raw list, then deduplicate while preserving order using dict.fromkeys()
    raw_candidates = [
        prebuilt_dir / clean_url,
        prebuilt_dir / lang_str / clean_url,
        prebuilt_dir / short_lang / clean_url,
        prebuilt_dir / "en" / clean_url,
        prebuilt_dir / "en-us" / clean_url,
    ]
    candidates = list(dict.fromkeys(raw_candidates))

    for candidate in candidates:
        if candidate.exists():
            return candidate

    log.warning(
        "Prebuilt HTML file not found in any candidate path for %s; tried: %s",
        html_url,
        ", ".join(str(c) for c in candidates),
    )
    return None


def _read_json_ld(html_path: Path | None) -> dict[str, Any]:
    """Read and parse the JSON-LD block from the given HTML file path."""
    if not html_path:
        return {}

    try:
        with open(html_path, encoding="utf-8") as f:
            content = f.read(5000)

        match = re.search(
            r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            content,
            re.IGNORECASE | re.DOTALL,
        )

        if match:
            return json.loads(match.group(1))
        log.warning("No JSON-LD block found in %s", html_path)
    except Exception as e:
        log.error("Failed to parse JSON-LD from %s: %s", html_path, e)

    return {}


def _extract_entities(json_ld: dict[str, Any], prod_title: str) -> tuple[list[str], list[dict[str, Any]]]:
    """Extract tasks and products from the JSON-LD entities."""
    entities = json_ld.get("about", json_ld.get("mentions", []))
    if isinstance(entities, dict):
        entities = [entities]

    tasks = []
    versions = []
    for entity in entities:
        if name := entity.get("name"):
            tasks.append(name)
        if version := entity.get("softwareVersion"):
            versions.append(version)

    products = []
    if prod_title:
        products.append({
            "name": prod_title,
            "versions": versions
        })

    return tasks, products


def extract_prebuilt_metadata(deliverable: Deliverable, prebuilt_dir: Path) -> dict[str, Any]:
    """Extract metadata for a prebuilt (Antora) deliverable.

    Parses its JSON-LD and combines it with XML properties from the view.
    """
    html_url = deliverable.xml.prebuilt_html_url

    # Pass deliverable so it can search translated directories
    html_path = _find_html_path(prebuilt_dir, deliverable, html_url)
    json_ld = _read_json_ld(html_path)

    in_language = json_ld.get("inLanguage", str(deliverable.xml.lang))
    lang_code = LanguageCode(language=in_language).language
    is_default = (lang_code == "en-us")

    date_modified = json_ld.get("dateModified", "")
    if date_modified:
        if "T" in date_modified:
            date_modified = date_modified.split("T")[0]
    else:
        # Fallback so Pydantic validation doesn't fail on empty date strings
        date_modified = datetime.date.today().isoformat()

    tasks, products = _extract_entities(json_ld, deliverable.xml.prebuilt_title)

    # Extract text from the first valid local description
    desc_text = ""
    for desc_node in deliverable.xml.local_desc():
        if desc_node.text:
            desc_text = desc_node.text.strip()
            break

    # Build format dict dynamically so we don't include empty 'pdf' keys
    fmt = {"html": html_url}
    if pdf_url := deliverable.xml.prebuilt_pdf_url:
        fmt["pdf"] = pdf_url

    raw_data = {
        "productname": deliverable.xml.productname or "SUSE Rancher Prime",
        "acronym": deliverable.xml.acronym or "",
        "version": deliverable.xml.docset_version or "",
        "docs": [
            {
                "lang": lang_code,
                "default": is_default,
                # Fallback to XML title if HTML JSON-LD is missing
                "title": json_ld.get("headline") or deliverable.xml.prebuilt_title,
                "subtitle": "",
                "description": desc_text,
                "dcfile": deliverable.xml.dcfile or "",
                "rootid": "",
                "format": fmt,
                "dateModified": date_modified
            }
        ],
        "tasks": tasks,
        "products": products,
        "docTypes": [],
        "isGated": deliverable.xml.is_gated,
        "rank": "",
        "category": deliverable.xml.categoryid or ""
    }

    return raw_data
