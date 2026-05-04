"""XML facade for deliverable node access."""

from collections.abc import Generator
from dataclasses import dataclass, field
from functools import cached_property
from typing import Literal, cast

from lxml import etree

from ...models.language import LanguageCode
from ...utils.convert import convert2bool
from ..repo import Repo


@dataclass
class DeliverableXMLView:
    """Common Portal/XML facade for a deliverable node."""

    node: etree._Element = field(repr=False)

    # -- Ancestor nodes
    @cached_property
    def product_node(self) -> etree._Element:
        """Return the ancestor ``<product>`` element."""
        return self.node.getparent().getparent().getparent().getparent()

    @cached_property
    def docset_node(self) -> etree._Element:
        """Return the ancestor ``<docset>`` element."""
        return cast(etree._Element, self.node.getparent().getparent().getparent())

    # -- Identity fields
    @cached_property
    def productid(self) -> str:
        """Return the product ID (``<product id=…>``) or None if absent.."""
        return self.product_node.attrib.get("id")

    @cached_property
    def product_docset(self) -> str:
        """Return the product/docset ID (``<product id=…>/<docset id=…>``)."""
        productid = self.productid
        docsetid = self.docsetid
        return f"{productid}/{docsetid}"

    @cached_property
    def productname(self) -> str | None:
        """Return the product name from ``<product><name>`` or None if absent."""
        return self.product_node.findtext("name", default=None, namespaces=None)

    @cached_property
    def acronym(self) -> str:
        """Return the product acronym, or an empty string if absent."""
        node = self.product_node.findtext("acronym", default=None, namespaces=None)
        return node.strip() if node is not None else ""

    @cached_property
    def docsetrealid(self) -> str | None:
        """Return the docset real ID (``<docset id=…>``) or None if absent."""
        return self.docset_node.attrib.get("id", None)

    @cached_property
    def docsetid(self) -> str | None:
        """Return the docset path/name (``<docset path=…>``), NOT the real ID."""
        return self.docset_node.attrib.get("path", None)

    @cached_property
    def lang(self) -> LanguageCode:
        """Return the language and country code (e.g. ``'en-us'``)."""
        return LanguageCode(language=self.node.getparent().attrib.get("lang").strip())

    @cached_property
    def dcfile(self) -> str | None:
        """Return the DC filename, or ``None`` if absent."""
        if (dcnode := self.node.find("dc")) is not None:
            return dcnode.attrib.get("file")
        return None

    @cached_property
    def basefile(self) -> str | None:
        """Return :attr:`dcfile` stripped of its ``DC-`` prefix."""
        return self.dcfile and self.dcfile.lstrip("DC-")

    # -- Deliverable kind (type)
    @cached_property
    def kind(self) -> str | None:
        """Return the deliverable type from ``@type`` or ``None`` if absent."""
        return self.node.attrib.get("type")

    @cached_property
    def is_prebuilt(self) -> bool:
        """Return True if the deliverable is marked as prebuilt."""
        if self.kind is not None:
            return self._is_kind("prebuilt")
        # Fallback: if no type is specified, we can infer prebuilt from the
        # presence of a <prebuilt> child node
        return self.node[0].tag == "prebuilt"

    @cached_property
    def is_dc(self) -> bool:
        """Return True if the deliverable is marked as DC."""
        if self.kind is not None:
            return self._is_kind("dc")
        # Fallback: if no type is specified, we can infer DC from the
        # presence of a DC file
        return self.dcfile is not None

    @cached_property
    def is_ref(self) -> bool:
        """Return True if the deliverable is marked as a reference."""
        if self.kind is not None:
            return self._is_kind("ref")
        # Fallback: if no type is specified, we can infer ref from the
        # presence of a <ref> child node
        return self.node[0].tag == "ref"

    def _is_kind(self, expected: str) -> bool:
        """Return ``True`` when the deliverable type matches ``expected``."""
        return self.kind == expected

    # -- Content and categories
    # Categories can be defined per product and at the document root.
    def categories(self) -> Generator[etree._Element, None, None]:
        """Yield all ``<category>`` elements under the product node."""
        yield from self.product_node.xpath("categories/category")

    def categories_from_root(self) -> Generator[etree._Element, None, None]:
        """Yield all ``<category>`` elements under the root node ."""
        root = self.node.getroottree().getroot()
        yield from root.xpath("categories/category")

    @cached_property
    def all_categories(self) -> Generator[etree._Element, None, None]:
        """Return product and root-level category elements."""
        yield from self.categories()
        yield from self.categories_from_root()

    def desc(self) -> Generator[etree._Element, None, None]:
        """Yield product ``<desc>`` elements."""
        yield from self.product_node.xpath("descriptions/desc")

    # -- Location and repository
    def branch(self) -> str | None:
        """Return branch from current language or ``None`` if missing."""
        node = self.node.getparent().findtext("branch", default=None)
        return node.strip() if node is not None else None

    def branch_from_fallback_locale(self) -> str | None:
        """Return branch from fallback locale lookup or ``None`` if missing."""
        node = self.node.getparent().xpath(
            "ancestor::resources/locale[@lang!='en-us']/branch",
        )
        if len(node) > 0:
            return node[0].text.strip()
        return None

    def subdir(self) -> str:
        """Return subdirectory or empty string."""
        node = self.node.getparent().findtext("subdir", default=None)
        return node.strip() if node is not None else ""

    def git_remote(self) -> Repo | None:
        """Return git remote URL from sibling ``<git>`` node."""
        # TODO: Use Repo as return object?
        node = self.node.getparent().getparent().find("git")
        if node is not None:
            return Repo(node.attrib.get("remote"))
        return None

    # -- Output formats
    def _ref_format_attrs(self) -> dict[str, str] | None:
        """Return raw format attributes from the linked English DC deliverable."""
        linkend = self.node[0].attrib.get("linkend")
        other_deli = self.node.xpath(
            f"../../locale[@lang='en-us']/deliverable[@id={linkend!r}]"
        )
        #if not other_deli:
        #    raise ValueError(f"English deliverable not found for linkend={linkend!r}")

        return self._dc_format_attrs(other_deli[0])

    def _dc_format_attrs(self, source_node: etree._Element | None = None) -> dict[str, str] | None:
        """Return raw format attributes from ``dc/format`` in the given node."""
        node = (source_node if source_node is not None else self.node).find("dc/format")
        return node.attrib if node is not None else None

    def _prebuilt_format_attrs(self, expected_formats: tuple[str, ...]) -> dict[str, str]:
        """Return raw format attributes from prebuilt URL nodes."""
        # For validated prebuilt deliverables, each <url> uses a single
        # format attribute (e.g. format="html").
        url_nodes = self.node.xpath("prebuilt/url")
        attrs = {fmt: "0" for fmt in expected_formats}  # default all formats to False
        for url_node in url_nodes:
            if (url_format := url_node.attrib["format"]) in expected_formats:
                attrs[url_format] = "1"
        return attrs

    def format_attrs(self) -> dict[
            Literal["epub", "html", "pdf", "single-html"], bool
        ] | None:
        """Return deliverable output formats as a boolean dict.

        Extracts format attributes from the XML element, converts their
        values to booleans, and returns a complete dict with all expected
        formats (defaulting missing keys to False). Returns None if no
        format element is found.
        """
        expected_formats = ("epub", "html", "pdf", "single-html")
        # _ = dcfile
        raw_attrs = None

        if self.is_ref:
            raw_attrs = self._ref_format_attrs()
        elif self.is_dc:
            raw_attrs = self._dc_format_attrs()
        elif self.is_prebuilt:
            raw_attrs = self._prebuilt_format_attrs(expected_formats)
        #else:
        #    raw_attrs = None

        # Return None if no format attributes found
        if raw_attrs is None:
            return None

        # Convert attribute values to booleans, defaulting missing keys to False
        return {
            fmt: convert2bool(raw_attrs.get(fmt, "0"))
            for fmt in expected_formats
        }

    # -- Dunder methods
    def __str__(self) -> str:
        """Return a human-readable string representation of the deliverable."""
        return (
            f"productid={self.productid!r}, "
            f"docsetid={self.docsetid!r}, lang={self.lang!r}, "
            f"branch={self.branch()!r}, dcfile={self.dcfile!r}"
        )

    def __repr__(self) -> str:
        """Return a concise string representation of the deliverable."""
        return f"{self.__class__.__name__}({self!s})"
