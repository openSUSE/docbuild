"""Task module for generating a sitemap.xml."""

import asyncio
from datetime import UTC, datetime
import logging
from pathlib import Path

from lxml import etree

log = logging.getLogger(__name__)

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
NSMAP = {None: SITEMAP_NS}


def _build_sitemap_tree(target_dir: Path, base_url: str) -> etree._ElementTree:
    """Traverse directory and build the XML tree synchronously."""
    urlset = etree.Element(f"{{{SITEMAP_NS}}}urlset", nsmap=NSMAP)

    # Ensure base_url ends with a slash for clean concatenation
    if not base_url.endswith("/"):
        base_url += "/"

    # Traverse target directory for html files
    # The issue specifies excluding languages other than English.
    # We look for files containing '/en-us/' in their path.
    for html_file in target_dir.rglob("*.html"):
        # Basic filtering: ensure it's in the en-us tree and skip common error pages
        parts = html_file.parts
        if "en-us" not in parts:
            continue
        if html_file.name in ("404.html", "500.html"):
            continue

        # Calculate relative path to form the URL
        try:
            rel_path = html_file.relative_to(target_dir)
        except ValueError:
            continue

        # Get file modification time
        mtime = html_file.stat().st_mtime
        lastmod = datetime.fromtimestamp(mtime, tz=UTC).strftime("%Y-%m-%d")

        # Create <url> node
        url_node = etree.SubElement(urlset, f"{{{SITEMAP_NS}}}url")

        loc_node = etree.SubElement(url_node, f"{{{SITEMAP_NS}}}loc")
        # Replace Windows backslashes if any, and append to base URL
        loc_node.text = f"{base_url}{rel_path.as_posix()}"

        lastmod_node = etree.SubElement(url_node, f"{{{SITEMAP_NS}}}lastmod")
        lastmod_node.text = lastmod

    return etree.ElementTree(urlset)


async def generate_sitemap(target_dir: Path, base_url: str) -> Path:
    """Generate a sitemap.xml in the root of the target directory.

    :param target_dir: The root distribution directory (target_base_dir).
    :param base_url: The base website URL (e.g. 'https://documentation.suse.com').
    :return: Path to the generated sitemap.xml.
    """
    log.info("Generating sitemap.xml in %s", target_dir)

    # Offload the blocking filesystem traversal to a thread
    tree = await asyncio.to_thread(_build_sitemap_tree, target_dir, base_url)

    sitemap_path = target_dir / "sitemap.xml"

    # Write to disk
    def _write() -> None:
        tree.write(
            str(sitemap_path),
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=True
        )

    await asyncio.to_thread(_write)
    log.info("Successfully wrote sitemap with base URL: %s", base_url)

    return sitemap_path
