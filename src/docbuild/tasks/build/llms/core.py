"""Core orchestration for HTML to Markdown conversion."""

from html import escape
from typing import Final

from justhtml import JustHTML
from justhtml.dom import Element

from docbuild.tasks.build.llms.cleaners import (
    AntoraHTMLCleaner,
    DocBookHTMLCleaner,
    HTMLCleaner,
)
from docbuild.tasks.build.llms.dom import get_attrs
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


def clean_and_convert(html_content: str) -> str:
    """Parse HTML into a DOM tree, clean it, and convert to Markdown."""
    doc = JustHTML(html_content, sanitize=False)
    cleaner = get_cleaner(doc)

    # Mutate the DOM tree in place
    cleaner.clean(doc.root)
    placeholders = replace_tables_and_images(doc.root)

    md: str = doc.to_markdown()
    for key, val in placeholders.items():
        md = md.replace(key, val)
    return md


def inject_llms_links(
    html_content: str, md_rel_path: str, llmstxt_rel_path: str
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

    safe_md_path = escape(md_rel_path, quote=True)
    safe_llms_path = escape(llmstxt_rel_path, quote=True)

    md_markup = f'<link rel="alternate" type="text/markdown" href="{safe_md_path}">'
    llms_markup = f'<link rel="alternate" type="text/markdown" href="{safe_llms_path}">'

    parsed_md = JustHTML(md_markup, fragment=True, sanitize=False).root
    parsed_llms = JustHTML(llms_markup, fragment=True, sanitize=False).root

    if parsed_md.children and parsed_llms.children:
        head.append_child(parsed_md.children[0])
        head.append_child(parsed_llms.children[0])

    return doc.to_html()
