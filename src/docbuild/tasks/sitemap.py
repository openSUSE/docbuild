"""Task module for generating a sitemap.xml."""

import asyncio
from datetime import UTC, datetime
from functools import partial
import logging
from pathlib import Path

from lxml import etree

from docbuild.constants import DEFAULT_LANG

log = logging.getLogger(__name__)

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
NSMAP = {None: SITEMAP_NS}
QMap = partial(etree.QName, SITEMAP_NS)


def _is_ignored(path: Path) -> bool:
    """Check if a file should be ignored from the sitemap."""
    if path.name in ("404.html", "500.html"):
        log.debug("Sitemap: Ignoring error page %s", path)
        return True
    return False


def build_sitemap_tree(target_dir: Path, base_url: str) -> etree._ElementTree:
    """Traverse directory and build the XML tree synchronously."""
    urlset = etree.Element(QMap("urlset"), nsmap=NSMAP)

    if not base_url.endswith("/"):
        base_url += "/"

    for html_file in target_dir.rglob("*.html"):
        parts = html_file.parts
        if DEFAULT_LANG not in parts:
            log.debug("Sitemap: Skipping non-default lang file %s", html_file)
            continue

        if _is_ignored(html_file):
            continue

        try:
            rel_path = html_file.relative_to(target_dir)
        except ValueError:
            continue

        # Convert to POSIX path for URLs
        url_path = rel_path.as_posix()

        # Remove the default lang (e.g. 'en-us') from the URL path
        lang_prefix = f"{DEFAULT_LANG}/"
        if url_path.startswith(lang_prefix):
            url_path = url_path[len(lang_prefix):]
        url_path = url_path.replace(f"/{lang_prefix}", "/")

        mtime = html_file.stat().st_mtime
        lastmod = datetime.fromtimestamp(mtime, tz=UTC).strftime("%Y-%m-%d")

        url_node = etree.SubElement(urlset, QMap("url"))
        loc_node = etree.SubElement(url_node, QMap("loc"))
        loc_node.text = f"{base_url}{url_path}"

        lastmod_node = etree.SubElement(url_node, QMap("lastmod"))
        lastmod_node.text = lastmod

    return etree.ElementTree(urlset)


async def generate_sitemap(target_dir: Path, base_url: str) -> Path:
    """Generate a sitemap.xml in the root of the target directory."""
    # Target directories are normally created by Pydantic during real runs.
    # This graceful exit is purely for mocked unit tests where the filesystem isn't touched.
    if not target_dir.exists():
        log.warning("Target directory %s does not exist. Skipping sitemap.", target_dir)
        return target_dir / "sitemap.xml"

    log.info("Generating sitemap.xml in %s", target_dir)

    tree = await asyncio.to_thread(build_sitemap_tree, target_dir, base_url)

    sitemap_path = target_dir / "sitemap.xml"

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
