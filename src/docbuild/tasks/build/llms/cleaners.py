"""HTML cleaner classes for stripping unwanted DOM nodes."""

from typing import Final

from justhtml.dom import Node, NodeType

from docbuild.tasks.build.llms.dom import get_attrs, is_empty_removable, normalize_node


class HTMLCleaner:
    """Base class to strip specific tags, IDs, and classes using DOM traversal."""

    VOID_ELEMENTS: Final[frozenset[str]] = frozenset(
        {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }
    )

    def __init__(
        self,
        tags_to_strip: list[str] | None,
        ids_to_strip: list[str] | None,
        classes_to_strip: list[str] | None,
    ) -> None:
        """Initialize the HTML stripper with target elements to remove."""
        base_tags = {"script", "style", "noscript", "button", "svg", "shared-header"}
        self.tags_to_strip = frozenset(base_tags | set(tags_to_strip or []))
        self.ids_to_strip = frozenset(ids_to_strip or [])
        self.classes_to_strip = frozenset(classes_to_strip or [])

    def should_strip(self, node: NodeType) -> bool:
        """Determine if a DOM node should be stripped."""
        if not isinstance(node, Node):
            return False

        tag = node.name.lower()
        attrs = get_attrs(node)
        node_id = attrs.get("id", "")
        node_classes = attrs.get("class", "").split()

        return (
            tag in self.tags_to_strip
            or node_id in self.ids_to_strip
            or any(cls in self.classes_to_strip for cls in node_classes)
        )

    def clean(self, node: NodeType) -> None:
        """Recursively clean and normalize the DOM tree in place."""
        children = getattr(node, "children", None)
        if children:
            for i in range(len(children) - 1, -1, -1):
                child = children[i]
                if self.should_strip(child):
                    children.pop(i)
                    child.parent = None
                else:
                    self.clean(child)
                    if is_empty_removable(child):
                        children.pop(i)
                        child.parent = None

        normalize_node(node)


class DocBookHTMLCleaner(HTMLCleaner):
    """HTML Cleaner tailored for DAPS/DocBook output."""

    def __init__(self) -> None:
        """Initialize cleaner with DAPS/DocBook specific rules."""
        super().__init__(
            tags_to_strip=["nav", "header", "footer", "aside"],
            ids_to_strip=[
                "_bypass-block",
                "_header",
                "_header-wrap",
                "_logo",
                "_fixed-header-wrap",
                "_fixed-header",
                "_toc-bubble-wrap",
                "_toc-area",
                "_nav-area",
                "_toolbar",
                "_find-area",
                "_footer",
                "_footer-wrap",
                "_bottom-pagination",
                "_side-toc-overall",
                "_side-toc-page",
                "_document-overview",
                "_open-document-overview",
                "navbar",
                "toc",
                "_mainnav",
                "_unfold-side-toc-page",
                "_open-side-toc-overall",
                "_print-button",
                "_share-mail",
                "_share-print",
                "searchUnifyChatbot",
                "qualtrics_container",
            ],
            classes_to_strip=[
                "navbar",
                "toc",
                "table-of-contents",
                "bypass-block",
                "crumbs",
                "bottom-pagination",
                "side-toc",
                "side-title",
                "bubble-container",
                "bubble-title",
                "book-title",
                "big-version-info",
                "version-info",
                "permalink",
                "icon-editsource",
                "icon-reportbug",
                "icons",
                "symbol",
                "date",
                "titlepage-revhistory",
                "share",
                "docsurvey-wrapper",
            ],
        )

    def clean(self, node: NodeType) -> None:
        """Scope body to #_content when present and clean the DOM tree."""
        if isinstance(node, Node) and node.name.lower() == "body":
            content = node.query_one("#_content")
            if content is not None:
                node.children = [content]
                content.parent = node
        super().clean(node)


class AntoraHTMLCleaner(HTMLCleaner):
    """HTML Cleaner tailored for Antora output."""

    def __init__(self) -> None:
        """Initialize cleaner with Antora specific rules."""
        super().__init__(
            tags_to_strip=["nav", "header", "footer", "aside"],
            ids_to_strip=["topbar-nav"],
            classes_to_strip=[
                "nav-panel-menu",
                "nav-panel-explore",
                "toc",
                "nav-container",
                "footer",
                "toolbar",
                "nav-wrapper",
                "breadcrumbs",
                "anchor",
            ],
        )
