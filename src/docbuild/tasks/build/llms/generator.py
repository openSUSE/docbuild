"""Orchestrator for generating LLMs Markdown from HTML builds."""

import fnmatch
import json
import logging
from pathlib import Path

from aiostream import pipe, stream
from justhtml import JustHTML
from pydantic import ValidationError
from rich.markup import escape
import yaml

from docbuild.cli.console import console_err
from docbuild.cli.message import WARNING
from docbuild.models.deliverable import Deliverable
from docbuild.models.json_ld import JsonLD
from docbuild.models.product import Product
from docbuild.tasks.build.llms.core import clean_and_convert, inject_llms_links
from docbuild.utils.merge import merge_and_deduplicate_lists

log = logging.getLogger(__name__)


EXPECTED_LD_FIELDS = tuple(
    field.alias or field_name
    for field_name, field in JsonLD.model_fields.items()
)


def warn_metadata(msg: str) -> None:
    """Log a metadata warning and print it with a Rich WARNING label."""
    log.warning(msg)
    console_err.print(WARNING.render(console=console_err), escape(msg))


def extract_json_ld(html_content: str, html_file: Path) -> JsonLD | None:
    """Extract and validate JSON-LD metadata from an HTML document."""
    doc = JustHTML(html_content, sanitize=False)
    ld_script = doc.query_one('script[type="application/ld+json"]')
    raw_json = ld_script.to_text(strip=True) if ld_script else ""
    if not raw_json:
        warn_metadata(f"No JSON-LD block found in {html_file}")
        return None

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        warn_metadata(f"Invalid JSON-LD in {html_file}: {exc}")
        return None

    if not isinstance(parsed, dict):
        warn_metadata(f"JSON-LD block in {html_file} is not a JSON object.")
        return None

    try:
        metadata = JsonLD.model_validate(parsed)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        )
        warn_metadata(f"Invalid JSON-LD fields in {html_file}: {details}")
        return None

    dumped = metadata.model_dump(by_alias=True)
    missing_fields = [field for field in EXPECTED_LD_FIELDS if not dumped.get(field)]
    if missing_fields:
        warn_metadata(
            f"Missing JSON-LD field(s) {', '.join(missing_fields)} in {html_file}"
        )

    return metadata


def resolve_product_name(acronym: str) -> str:
    """Resolve a product acronym (e.g. 'sles') to its full display name."""
    try:
        return str(Product(acronym))
    except ValueError:
        return acronym


async def process_single_html_file(
    html_file: Path,
    html_dir: Path,
    llms_dest: Path,
    llms_route_prefix: str,
    deliverable_route: str,
    static_title: str,
    categories: list[str] | None = None,
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
    ld_data = extract_json_ld(html_content, html_file)

    frontmatter = {"title": static_title, "description": ""}
    if categories:
        frontmatter["categories"] = categories

    # Dynamically extract product and version from the logical file path
    # (Format: en-us/sles/16.1/html/...)
    path_parts = full_rel_path.parts
    if len(path_parts) > 3 and path_parts[3] == "html":
        frontmatter["product"] = resolve_product_name(path_parts[1])
        frontmatter["version"] = path_parts[2]

    if ld_data:
        frontmatter["title"] = ld_data.name or frontmatter["title"]
        frontmatter["description"] = ld_data.description or ""
        for key, value in (
            ("dateCreated", ld_data.date_created),
            ("dateModified", ld_data.date_modified),
            ("datePublished", ld_data.date_published),
        ):
            if value:
                frontmatter[key] = value

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

    # Resolve actual HTML directory (html_dir overrides deliverable.paths.html, which overrides fallback)
    fallback_route = f"{language}/{d_xml.product_id}/{d_xml.docset_version}/html/{subdir}".strip("/")
    deliv_paths = getattr(deliverable, "paths", None)

    scan_dir = Path(html_dir or getattr(deliv_paths, "html", Path(target_base_dir) / fallback_route))

    # Dynamically deduce the route directly from the filesystem path, with a direct string fallback
    deliverable_route = str(scan_dir.relative_to(target_base_dir)) if scan_dir.is_relative_to(target_base_dir) else fallback_route

    if not scan_dir.exists():
        log.warning("HTML directory %s does not exist, skipping.", scan_dir)
        return

    # Extract categories safely
    categories = (getattr(d_xml, "categoryid", "") or "").split()

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
                categories=categories,
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
