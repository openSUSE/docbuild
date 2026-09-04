"""Extractor for prebuilt (Antora) deliverable metadata."""

import json
import logging
from pathlib import Path
import re
from typing import Any

from lxml import etree  # type: ignore

from docbuild.models.deliverable import Deliverable
from docbuild.models.language import LanguageCode

log = logging.getLogger(__name__)


def _extract_xml_properties(node: etree._Element) -> tuple[str, str, str, str, bool, str]:
    """Extract properties directly from the XML node."""
    desc = ""
    if desc_nodes := node.xpath("./description/text()"):
        desc = desc_nodes[0].strip()

    prod_title = ""
    if title_nodes := node.xpath("./prebuilt/title/text()"):
        prod_title = title_nodes[0].strip()

    html_url = ""
    pdf_url = ""
    for url_node in node.xpath("./prebuilt/url"):
        fmt = url_node.get("format", "html").lower()
        href = url_node.get("href", "")
        if fmt == "html":
            html_url = href
        elif fmt == "pdf":
            pdf_url = href

    is_gated = str(node.get("gated", "false")).lower() == "true"
    category = node.get("category", "")

    return desc, prod_title, html_url, pdf_url, is_gated, category


def _read_json_ld(html_path: Path) -> dict[str, Any]:
    """Read and parse the JSON-LD block from the given HTML file path."""
    if not html_path.exists():
        log.warning("Prebuilt HTML file not found at %s", html_path)
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


def extract_prebuilt_metadata(deliverable: Deliverable, prebuilt_dir: Path) -> dict[str, Any]:
    """Extract metadata for a prebuilt (Antora) deliverable.

    Parses its JSON-LD and combines it with XML properties.
    """
    node = deliverable._node

    desc, prod_title, html_url, pdf_url, is_gated, category = _extract_xml_properties(node)

    json_ld: dict[str, Any] = {}
    if html_url:
        html_path = prebuilt_dir / str(deliverable.xml.lang) / html_url.lstrip("/")
        json_ld = _read_json_ld(html_path)

    in_language = json_ld.get("inLanguage", str(deliverable.xml.lang))
    lang_code = LanguageCode(language=in_language).language
    is_default = (lang_code == "en-us")

    date_modified = json_ld.get("dateModified", "")
    if "T" in date_modified:
        date_modified = date_modified.split("T")[0]

    headline = json_ld.get("headline", "")

    entities = json_ld.get("about", json_ld.get("mentions", []))
    if isinstance(entities, dict):
        entities = [entities]  # Normalize to list

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

    return {
        "docs": [
            {
                "lang": lang_code,
                "default": is_default,
                "title": headline,
                "subtitle": "",
                "description": desc,
                "dcfile": "",
                "rootid": "",
                "format": {
                    "html": html_url,
                    "pdf": pdf_url
                },
                "dateModified": date_modified
            }
        ],
        "tasks": tasks,
        "products": products,
        "docTypes": [],
        "isGated": is_gated,
        "rank": "",
        "category": category
    }
