"""Orchestrator for generating LLMs Markdown from HTML builds."""

import fnmatch
import json
import logging
from pathlib import Path
from typing import Any

from aiostream import pipe, stream
from bs4 import BeautifulSoup
import yaml

from docbuild.models.deliverable import Deliverable
from docbuild.tasks.build.llms.core import clean_and_convert, inject_llms_links
from docbuild.utils.merge import merge_and_deduplicate_lists

log = logging.getLogger(__name__)


async def process_single_html_file(
    html_file: Path,
    html_dir: Path,
    llms_dest: Path,
    llms_route_prefix: str,
    deliverable_route: str,
    static_title: str,
    frontmatter_base: dict[str, Any],
    only_md: bool = False,
) -> str | None:
    """Process an HTML file to generate Markdown and update HTML with link tags."""
    if not html_file.exists():
        return None

    # Determine exact path inside the deliverable (e.g. index.html or folder/page.html)
    try:
        local_rel_path = html_file.relative_to(html_dir)
    except ValueError:
        local_rel_path = Path(html_file.name)

    # Reconstruct the absolute correct logical path (e.g. en-us/sles/16.1/html/DELIV/index.md)
    full_rel_path = Path(deliverable_route) / local_rel_path

    md_file = llms_dest / full_rel_path.with_suffix(".md")
    md_file.parent.mkdir(parents=True, exist_ok=True)

    html_content = html_file.read_text(encoding="utf-8")
    soup = BeautifulSoup(html_content, "html.parser")
    ld_script = soup.find("script", type="application/ld+json")
    if ld_script and ld_script.string:
        ld_data = json.loads(ld_script.string)
    else:
        logging.getLogger("docbuild.tasks.metadata.prebuilt").debug(
            "No JSON-LD block found in %s", html_file
        )
        ld_data = {}

    frontmatter = {"title": static_title, "description": ""}
    if ld_data and "name" in ld_data:
        frontmatter["title"] = ld_data["name"]
    if ld_data and "description" in ld_data:
        frontmatter["description"] = ld_data["description"]

    frontmatter.update(frontmatter_base)

    if ld_data:
        for d_key in ("dateCreated", "dateModified", "datePublished"):
            if ld_data.get(d_key):
                frontmatter[d_key] = ld_data[d_key]

    yaml_block = yaml.safe_dump(
        frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True, width=float("inf")
    )
    md_content = clean_and_convert(html_content)
    full_md = f"---\n{yaml_block}---\n\n{md_content}"
    md_file.write_text(full_md, encoding="utf-8")

    # The canonical web route for the hrefs
    md_abs_url = f"/{llms_route_prefix}/{full_rel_path.with_suffix('.md').as_posix()}"

    if not only_md:
        llmstxt_abs_url = f"/{llms_route_prefix}/llms.txt"
        updated_html = inject_llms_links(html_content, md_abs_url, llmstxt_abs_url)
        html_file.write_text(updated_html, encoding="utf-8")

    return f"- [{frontmatter.get('title', local_rel_path.stem)}]({md_abs_url})"


async def generate_llmstxt(
    deliverable: Deliverable,
    target_base_dir: Path | str,
    build_llmstxt: bool,
    llmstxt_dir: str | Path,
    canonical_domain: str = "https://documentation.suse.com",
    llms_exclude: list[str] | None = None,
    llms_exclude_extra: list[str] | None = None,
    only_md: bool = False,
    html_dir: Path | str | None = None,
) -> None:
    """Generate Markdown and llms.txt files from the HTML output directory."""
    if not build_llmstxt:
        log.debug("Skipping llms.txt generation, disabled by configuration.")
        return

    # Securely resolve LLMs destination (Pathlib handles absolute strings automatically)
    llms_dest = Path(target_base_dir) / str(llmstxt_dir)

    llms_route_prefix = llms_dest.name
    llms_dest.mkdir(parents=True, exist_ok=True)
    d_xml = deliverable.xml
    static_title = getattr(d_xml, "title", deliverable.full_id)
    language = str(d_xml.lang)
    subdir = deliverable.subdir or ""

    # Reconstruct exact logical path
    deliverable_route = f"{language}/{d_xml.product_id}/{d_xml.docset_version}/html/{subdir}".strip("/")

    # Resolve actual HTML directory using a single fallback chain
    default_html_path = Path(target_base_dir) / deliverable_route
    scan_dir = Path(html_dir) if html_dir else Path(
        getattr(getattr(deliverable, "paths", None), "html", default_html_path)
    )

    if not scan_dir.exists():
        log.warning("HTML directory %s does not exist, skipping.", scan_dir)
        return

    frontmatter_base = {
        k: v for k, v in {
            "product": d_xml.product_id,
            "version": d_xml.docset_version,
            "language": language,
            "categories": (d_xml.categoryid or "").split(),
        }.items() if v
    }

    try:
        index_lines = [
            f"# {static_title}",
            "",
            "> Documentation generated for LLMs.",
            "",
            "## Files",
            "",
        ]

        exclude_patterns = merge_and_deduplicate_lists(llms_exclude, llms_exclude_extra)

        html_files = []
        for file in scan_dir.rglob("*.html"):
            if any(fnmatch.fnmatch(file.name, p) for p in exclude_patterns):
                log.debug("Skipping ignored file during LLM generation: %s", file)
                continue
            html_files.append(file)

        async def process_file(html_file: Path) -> str | None:
            return await process_single_html_file(
                html_file=html_file,
                html_dir=scan_dir,
                llms_dest=llms_dest,
                llms_route_prefix=llms_route_prefix,
                deliverable_route=deliverable_route,
                static_title=static_title,
                frontmatter_base=frontmatter_base,
                only_md=only_md,
            )

        pipeline = stream.iterate(html_files) | pipe.map(process_file, ordered=False, task_limit=10)

        async with pipeline.stream() as streamer:
            async for result in streamer:
                if result:
                    index_lines.append(result)

        global_llms_txt = llms_dest / "llms.txt"
        with open(global_llms_txt, "a", encoding="utf-8") as f:
            f.write("\n".join(index_lines) + "\n")

        log.info("Successfully generated Markdown for %s", deliverable.full_id)

    except Exception as e:
        log.error("Failed to generate llms.txt: %s", e)
