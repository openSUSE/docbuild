"""Extractor for prebuilt (Antora) deliverable metadata."""

import datetime
import json
import logging
from pathlib import Path
import re
from typing import Any

from pydantic import BaseModel, ValidationError

from docbuild.models.deliverable import Deliverable
from docbuild.models.json_ld import JsonLD, JsonLDEntity, unknown_json_ld_fields
from docbuild.models.language import LanguageCode

log = logging.getLogger(__name__)


def find_html_path(prebuilt_dir: Path, deliverable: Deliverable, html_url: str) -> Path | None:
    """Attempt to find the prebuilt HTML file in multiple candidate paths."""
    if not html_url:
        return None

    clean_url = html_url.lstrip("/")

    # Use LanguageCode object and wrap in str() - Pylance type-checking
    lang_str: str = deliverable.xml.lang.language
    short_lang: str = deliverable.xml.lang.lang

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


def read_json_ld(
    html_source: Path | str | None, *, source_path: Path | None = None
) -> dict[str, Any]:
    """Read and parse the JSON-LD block from an HTML file path or raw HTML string."""
    if not html_source:
        return {}

    source = html_source if isinstance(html_source, Path) else source_path or "HTML content"
    try:
        if isinstance(html_source, Path):
            with open(html_source, encoding="utf-8") as f:
                content = f.read(5000)
        else:
            content = html_source[:5000]

        match = re.search(
            r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            content,
            re.IGNORECASE | re.DOTALL,
        )

        if match:
            return json.loads(match.group(1))
        log.debug("No JSON-LD block found in %s", source)

    except Exception as e:
        log.debug("Failed to parse JSON-LD from %s: %s", source, e)

    return {}


def extract_entities(json_ld: dict[str, Any] | None, prod_title: str) -> tuple[list[str], list[dict[str, Any]]]:
    """Extract tasks and products from the JSON-LD entities."""
    if not json_ld or not isinstance(json_ld, dict):
        entities = []
    else:
        entities = json_ld.get("about") or json_ld.get("mentions") or []

    if isinstance(entities, dict):
        entities = [entities]

    tasks = []
    versions = []
    for entity in entities:
        if isinstance(entity, dict):
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


def _valid_fields(
    model: type[BaseModel], data: dict[str, Any], names: tuple[str, ...]
) -> dict[str, Any]:
    valid: dict[str, Any] = {}
    for name in names:
        field = model.model_fields[name]
        for key in {name, field.alias or name}:
            if key not in data:
                continue
            try:
                model.model_validate({key: data[key]})
            except ValidationError:
                continue
            valid[key] = data[key]
    return valid


def _prebuilt_projection(data: dict[str, Any]) -> JsonLD:
    fields = _valid_fields(JsonLD, data, ("headline", "in_language", "date_modified"))
    names = ("about",) if data.get("about") else ("mentions",)
    for name in names:
        value = data.get(name)
        if isinstance(value, dict):
            fields[name] = _valid_fields(JsonLDEntity, value, ("name", "software_version"))
        elif isinstance(value, list):
            fields[name] = [
                _valid_fields(JsonLDEntity, item, ("name", "software_version"))
                for item in value if isinstance(item, dict)
            ]
    return JsonLD.model_validate(fields)


def extract_prebuilt_metadata(deliverable: Deliverable, prebuilt_dir: Path) -> dict[str, Any]:
    """Extract metadata for a prebuilt (Antora) deliverable."""
    html_url = deliverable.xml.prebuilt_html_url

    # Pass deliverable so it can search translated directories
    html_path = find_html_path(prebuilt_dir, deliverable, html_url)
    raw_json_ld = read_json_ld(html_path)
    if not isinstance(raw_json_ld, dict):
        raw_json_ld = {}
    try:
        json_ld = JsonLD.model_validate(raw_json_ld)
    except ValidationError as exc:
        for error in exc.errors():
            location = error["loc"]
            if location and location[0] in {"dateModified", "date_modified"}:
                log.warning(
                    "Invalid date format '%s' in JSON-LD for %s. Falling back to None.",
                    raw_json_ld.get(location[0]),
                    html_url,
                )
            else:
                path = ".".join(str(part) for part in location)
                log.warning(
                    "Invalid JSON-LD field %s in %s: %s",
                    path, html_path, error["msg"],
                )
        json_ld = _prebuilt_projection(raw_json_ld)
    unknown_fields = unknown_json_ld_fields(raw_json_ld)
    if unknown_fields:
        log.warning(
            "Unknown JSON-LD field(s) %s in %s",
            ", ".join(unknown_fields),
            html_path,
        )

    in_language = json_ld.in_language or str(deliverable.xml.lang)
    lang_code = LanguageCode(language=in_language).language
    is_default = (lang_code == "en-us")

    date_modified_raw = json_ld.date_modified
    date_modified = date_modified_raw.strip() if date_modified_raw else None

    if date_modified:
        if "T" in date_modified:
            date_modified = date_modified.split("T")[0]

        try:
            # Strictly validate that it matches YYYY-MM-DD
            datetime.date.fromisoformat(date_modified)
        except ValueError:
            log.warning(
                "Invalid date format '%s' in JSON-LD for %s. Falling back to None.",
                date_modified,
                html_url
            )
            date_modified = None

    headline = json_ld.headline
    tasks, products = extract_entities(
        json_ld.model_dump(by_alias=True, exclude_none=True),
        deliverable.xml.prebuilt_title,
    )

    # Extract text from the first valid local description
    desc_text = next(
        (' '.join(node.xpath("string()").split()) for node in deliverable.xml.local_desc()),
        ""
    )

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
                "title": headline or deliverable.xml.prebuilt_title,
                "subtitle": "",
                "description": desc_text,
                "dcfile": deliverable.xml.dcfile or deliverable.xml.target_id or "",
                "rootid": deliverable.xml.target_id or "",
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
