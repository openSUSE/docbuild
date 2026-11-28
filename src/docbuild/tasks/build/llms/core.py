"""Core orchestration for HTML to Markdown conversion."""

from html import escape
from pathlib import Path
import posixpath
import re
from typing import Final
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

from justhtml import JustHTML
from justhtml.dom import Element, Node, NodeType

from docbuild.tasks.build.llms.cleaners import (
    AntoraHTMLCleaner,
    DocBookHTMLCleaner,
    HTMLCleaner,
)
from docbuild.tasks.build.llms.dom import (
    get_attrs,
    preserve_id_anchors,
    replace_node,
)
from docbuild.tasks.build.llms.markdown import replace_tables_and_images


def detect_generator(doc: JustHTML) -> str | None:
    """Detect the HTML type from the <meta name="generator"> tag."""
    target_generators: Final[tuple[str, ...]] = ("daps", "docbook", "antora")

    for meta in doc.query("meta"):
        attrs = get_attrs(meta)
        name = attrs.get("name", "").lower()

        if name == "generator":
            content = attrs.get("content", "").lower()
            for gen in target_generators:
                if gen in content:
                    return gen
    return None


def get_cleaner(doc: JustHTML) -> HTMLCleaner:
    """Return the appropriate HTMLCleaner instance based on the document type."""
    generator = detect_generator(doc)

    match generator:
        case "antora":
            return AntoraHTMLCleaner()
        case "daps" | "docbook":
            return DocBookHTMLCleaner()
        case None if doc.query_one("main#_content article.documentation") is not None:
            return DocBookHTMLCleaner()
        case _:
            return HTMLCleaner(None, None, None)


def rewrite_html_links(
    root: NodeType,
    source_html: Path,
    html_dir: Path,
    generated_html_files: set[Path],
    canonical_domain: str,
    deliverable_route: str,
) -> None:
    """Rewrite relative HTML links to generated Markdown or canonical HTML."""
    if not isinstance(root, Node):
        return

    html_root = html_dir.resolve()
    source_path = source_html.resolve()
    try:
        source_rel_path = source_path.relative_to(html_root)
    except ValueError:
        return

    source_md_path = source_rel_path.with_suffix(".md")
    canonical_source = urljoin(
        canonical_domain.rstrip("/") + "/",
        quote(f"{deliverable_route}/{source_rel_path.as_posix()}", safe="/-._~"),
    )

    for link in root.query("a"):
        attrs = get_attrs(link)
        href = attrs.get("href", "")
        parsed = urlsplit(href)
        if (
            not href
            or parsed.scheme
            or parsed.netloc
            or parsed.path.startswith("/")
            or not parsed.path.lower().endswith(".html")
        ):
            continue

        target_path = (source_path.parent / unquote(parsed.path)).resolve()
        try:
            target_rel_path = target_path.relative_to(html_root)
        except ValueError:
            target_rel_path = None

        if target_rel_path is not None and target_path in generated_html_files:
            target_md_path = target_rel_path.with_suffix(".md")
            relative_md_path = posixpath.relpath(
                target_md_path.as_posix(), start=source_md_path.parent.as_posix()
            )
            rewritten_href = urlunsplit(
                (
                    "",
                    "",
                    quote(relative_md_path, safe="/-._~"),
                    parsed.query,
                    parsed.fragment,
                )
            )
        else:
            rewritten_href = urljoin(canonical_source, href)

        if isinstance(link, Node) and link.attrs is not None:
            link.attrs["href"] = rewritten_href


def collect_link_fragments(
    html_files: list[Path], html_dir: Path, generated_html_files: set[Path]
) -> dict[Path, set[str]]:
    """Collect fragments referenced by relative links to generated HTML pages."""
    html_root = html_dir.resolve()
    fragments: dict[Path, set[str]] = {}

    for source_html in html_files:
        source_path = source_html.resolve()
        doc = JustHTML(source_html.read_text(encoding="utf-8"), sanitize=False)
        for link in doc.query("a"):
            href = get_attrs(link).get("href", "")
            parsed = urlsplit(href)
            if (
                not parsed.fragment
                or parsed.scheme
                or parsed.netloc
                or parsed.path.startswith("/")
                or (parsed.path and not parsed.path.lower().endswith(".html"))
            ):
                continue

            target_path = (
                (source_path.parent / unquote(parsed.path)).resolve()
                if parsed.path
                else source_path
            )
            if target_path not in generated_html_files:
                continue
            try:
                target_path.relative_to(html_root)
            except ValueError:
                continue
            fragments.setdefault(target_path, set()).add(unquote(parsed.fragment))

    return fragments


def clean_and_convert(
    html_content: str,
    *,
    source_html: Path | None = None,
    html_dir: Path | None = None,
    generated_html_files: set[Path] | None = None,
    anchor_ids: set[str] | None = None,
    canonical_domain: str = "https://documentation.suse.com",
    deliverable_route: str = "",
) -> str:
    """Parse HTML into a DOM tree, clean it, and convert to Markdown."""
    doc = JustHTML(html_content, sanitize=False)
    cleaner = get_cleaner(doc)

    # Mutate the DOM tree in place
    cleaner.clean(doc.root)
    if source_html is not None and html_dir is not None:
        rewrite_html_links(
            doc.root,
            source_html,
            html_dir,
            generated_html_files or set(),
            canonical_domain,
            deliverable_route,
        )
    anchor_placeholders = preserve_id_anchors(doc.root, anchor_ids)
    placeholders = replace_tables_and_images(doc.root)

    md: str = doc.to_markdown()
    for key, value in anchor_placeholders.items():
        md = md.replace(key, value)
    for key, val in placeholders.items():
        md = md.replace(key, val)
    md = re.sub(
        r"^(>\s*)\\\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\\\](?:\n>)?\n",
        r"\1[!\2]\n",
        md,
        flags=re.MULTILINE,
    )
    return md


def inject_llms_links(
    html_content: str, md_abs_path: str, llmstxt_abs_path: str
) -> str:
    """Inject alternate markdown link tags into the <head> of an HTML document."""
    doc = JustHTML(html_content, sanitize=False)
    head = doc.query_one("head")

    if head is None:
        target_parent = doc.query_one("html") or doc.root
        head = Element("head", {}, "html")
        head.parent = target_parent
        if target_parent.children is None:
            target_parent.children = []
        target_parent.children.insert(0, head)

    # Clean existing tags to prevent duplicates
    for link in list(head.query("link")):
        attrs = get_attrs(link)
        link_type = attrs.get("type", "")
        link_href = attrs.get("href", "")

        # Remove existing text/markdown links and text/plain llms.txt fallbacks
        if link_type == "text/markdown" or (link_type == "text/plain" and "llms.txt" in link_href):
            replace_node(link, None)

    safe_md_path = escape(md_abs_path, quote=True)
    safe_llms_path = escape(llmstxt_abs_path, quote=True)

    md_markup = f'<link rel="alternate" type="text/markdown" href="{safe_md_path}">'
    llms_markup = f'<link rel="alternate" type="text/markdown" href="{safe_llms_path}">'
    fallback_markup = f'<link rel="index" type="text/plain" href="{safe_llms_path}">'

    parsed_md = JustHTML(md_markup, fragment=True, sanitize=False).root
    parsed_llms = JustHTML(llms_markup, fragment=True, sanitize=False).root
    parsed_fallback = JustHTML(fallback_markup, fragment=True, sanitize=False).root

    if parsed_md.children and parsed_llms.children and parsed_fallback.children:
        head.append_child(parsed_md.children[0])
        head.append_child(parsed_llms.children[0])
        head.append_child(parsed_fallback.children[0])

    return doc.to_html()

