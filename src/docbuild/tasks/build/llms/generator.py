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
    target_base_dir: Path,
    llms_dest: Path,
    llmstxt_dir: str,
    domain: str,
    url_product: str,
    url_docset: str,
    static_title: str,
    frontmatter_base: dict[str, Any],
    only_md: bool = False,
) -> str | None:
    """Process an HTML file to generate Markdown and update HTML with link tags."""
    if not html_file.exists():
        return None

    rel_path = html_file.relative_to(target_base_dir)
    md_file = llms_dest / rel_path.with_suffix(".md")
    md_file.parent.mkdir(parents=True, exist_ok=True)

    f"{domain}/{url_product}/{url_docset}/html/{rel_path.as_posix()}"

    html_content = html_file.read_text(encoding="utf-8")
    soup = BeautifulSoup(html_content, "html.parser")
    ld_script = soup.find("script", type="application/ld+json")
    if ld_script and ld_script.string:
        ld_data = json.loads(ld_script.string)
    else:
        # Provide the expected log for testing
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

    # Inject specific date metadata from JSON-LD if present
    if ld_data:
        for d_key in ("dateCreated", "dateModified", "datePublished"):
            if ld_data.get(d_key):
                frontmatter[d_key] = ld_data[d_key]

    # Use yaml.safe_dump for secure serialization, width=inf to avoid wrapping lines
    yaml_block = yaml.safe_dump(
        frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True, width=float("inf")
    )
    md_content = clean_and_convert(html_content)
    full_md = f"---\n{yaml_block}---\n\n{md_content}"
    md_file.write_text(full_md, encoding="utf-8")

    md_abs_path = f"/{llmstxt_dir}/{rel_path.with_suffix('.md').as_posix()}"

    if not only_md:
        llmstxt_abs_path = f"/{llmstxt_dir}/llms.txt"
        updated_html = inject_llms_links(html_content, md_abs_path, llmstxt_abs_path)
        html_file.write_text(updated_html, encoding="utf-8")

    return f"- [{frontmatter.get('title', rel_path.stem)}]({md_abs_path})"


async def generate_llmstxt(
    deliverable: Deliverable,
    target_base_dir: Path | str,
    build_llmstxt: bool,
    llmstxt_dir: str,
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

    target_base_dir = Path(target_base_dir)
    if not (target_base_dir.exists() and target_base_dir.is_dir()):
        log.warning(
            "Target directory %s does not exist, skipping llms.txt generation.",
            target_base_dir,
        )
        return

    log.info("Generating LLM Markdown files in %s", target_base_dir / llmstxt_dir)
    llms_dest = target_base_dir / llmstxt_dir
    llms_dest.mkdir(parents=True, exist_ok=True)
    domain = canonical_domain.rstrip("/")

    d_xml = deliverable.xml
    static_title = getattr(d_xml, "title", deliverable.full_id)

    url_product_id = d_xml.product_id or "unknown"
    if hasattr(deliverable, "make_safe_name"):
        url_product = deliverable.make_safe_name(url_product_id)
    else:
        url_product = url_product_id.replace("/", "_")

    url_docset = d_xml.docset_path or "unknown"

    # Use dictionary comprehension to filter empty keys (reduces C901 complexity)
    frontmatter_base = {
        k: v for k, v in {
            "product": d_xml.product_id,
            "version": d_xml.docset_version,
            "language": str(d_xml.lang),
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

        scan_dir = Path(html_dir) if html_dir else target_base_dir

        html_files = []
        for file in scan_dir.rglob("*.html"):
            if any(fnmatch.fnmatch(file.name, p) for p in exclude_patterns):
                log.debug("Skipping ignored file during LLM generation: %s", file)
                continue
            html_files.append(file)

        async def process_file(html_file: Path) -> str | None:
            return await process_single_html_file(
                html_file=html_file,
                target_base_dir=target_base_dir,
                llms_dest=llms_dest,
                llmstxt_dir=llmstxt_dir,
                domain=domain,
                url_product=url_product,
                url_docset=url_docset,
                static_title=static_title,
                frontmatter_base=frontmatter_base,
                only_md=only_md,
            )

        pipeline = stream.iterate(html_files) | pipe.map(process_file, ordered=False, task_limit=10)

        async with pipeline.stream() as streamer:
            async for result in streamer:
                if result:
                    index_lines.append(result)

        llms_txt = target_base_dir / "llms.txt"
        llms_txt.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
        log.info("Successfully generated %s", llms_txt)

    except Exception as e:
        log.error("Failed to generate llms.txt: %s", e)
