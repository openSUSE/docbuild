"""XML facade for deliverable node access."""

from collections.abc import Generator
from dataclasses import dataclass, field
from functools import cached_property
import logging
from typing import Literal, cast

from lxml import etree  # type: ignore

from ...constants import XML_ID
from ...models.language import LanguageCode
from ...utils.convert import convert2bool
from ..repo import Repo

log = logging.getLogger(__name__)


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
    def product_id(self) -> str:
        """Return the product ID (``<product xml:id=…>``) or None if absent.."""
        return self.product_node.get(XML_ID)

    @cached_property
    def product_path(self) -> str | None:
        """Return the product path for the deliverable.

        This corresponds to the ``path`` attribute on the ``<product>`` tag and
        is used to specify a relative directory name for the product.
        If the ``path`` attribute is not present, this property will be ``None``.

        :return: The product path string, or ``None`` if not set.
        """
        return self.product_node.attrib.get("path", None)

    @cached_property
    def product_docset(self) -> str:
        """Return the product/docset ID (``<product id=…>/<docset id=…>``)."""
        product_id = self.product_id
        docset_path = self.docset_path
        return f"{product_id}/{docset_path}"

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
    def docset_id(self) -> str:
        """Return the docset real ID (``<docset xml:id=…>``)."""
        return self.docset_node.get(XML_ID)

    @cached_property
    def docset_path(self) -> str | None:
        """Return the docset path for the deliverable.

        This corresponds to the ``path`` attribute on the ``<docset>`` tag and
        is used to specify a relative directory name for the docset.
        If the ``path`` attribute is not present, this property will be ``None``.

        :return: The product path string, or ``None`` if not set.
        """
        return self.docset_node.attrib.get("path", None)

    @cached_property
    def locale_en(self) -> etree._Element | None:
        """Return the English locale node (``<locale lang="en-us">``) or None if absent."""
        return self.docset_node.find("resources/locale[@lang='en-us']")

    @cached_property
    def lang(self) -> LanguageCode:
        """Return the language and country code (e.g. ``'en-us'``)."""
        return LanguageCode(language=self.node.getparent().attrib.get("lang").strip())

    @cached_property
    def dcfile(self) -> str | None:
        """Return the DC filename, or ``None`` if absent."""
        if (dcnode := self.node.find("dc")) is not None:
            return dcnode.attrib.get("file")

        if self.is_xref and (target := self.final_target_node) is not None and target is not self.node:
            if (dcnode := target.find("dc")) is not None:
                return dcnode.attrib.get("file")

        return None

    @cached_property
    def deliverableid(self) -> str | None:
        """Return the deliverable ID (`<deliverable xml:id=…>`) or None if absent."""
        xml_id = self.xml_id
        if xml_id:
            return xml_id
        if self.is_xref and (ref_node := self.xref_node) is not None:
            return ref_node.get("linkend")
        return None

    @property
    def identifier(self) -> str:
        """Return the fully qualified deliverable identifier string."""
        return f"{self.product_docset}/{self.lang}:{self.deliverableid}"


    @cached_property
    def target_id(self) -> str | None:
        """Return the target deliverable ID (linkend for xrefs, else deliverableid)."""
        if self.is_xref:
            ref_node = self.xref_node
            if ref_node is not None and ref_node.get("linkend"):
                return ref_node.get("linkend")
        return self.deliverableid

    @cached_property
    def resolved_prebuilt_html_url(self) -> str | None:
        """Return the prebuilt HTML URL, resolving refs to their target."""
        if self.prebuilt_html_url:
            return self.prebuilt_html_url
        if self.is_xref and (target := self.final_target_node) is not None:
            prebuilt_node = target.find("prebuilt")
            if prebuilt_node is not None:
                url_node = prebuilt_node.find("url[@format='html']")
                if url_node is not None:
                    return url_node.get("href")
        return None

    @cached_property
    def basefile(self) -> str | None:
        """Return :attr:`dcfile` stripped of its ``DC-`` prefix, or target_id as fallback."""
        if self.dcfile:
            return self.dcfile.lstrip("DC-")
        return self.target_id

    @cached_property
    def translations(self) -> set[str]:
        """Return a set of all language codes available for this deliverable."""
        d_id = self.xml_id
        if self.docset_node is None or not d_id:
            return {str(self.lang)}

        # Always include the base language
        langs = {str(self.lang)}

        for deliv_node in self.docset_node.xpath(f"resources/locale[@lang!='en-us']/deliverable[xref[@linkend='{d_id}']]"):
            # We must look at the parent <locale> to get the 'lang' attribute
            parent_loc = deliv_node.getparent()
            if loc_lang := parent_loc.get("lang"):
                langs.add(loc_lang)
        return langs

    # -- Deliverable kind (type)
    @cached_property
    def kind(self) -> str | None:
        """Return the deliverable type from ``@type`` or ``None`` if absent."""
        return self.node.attrib.get("type")

    @cached_property
    def is_prebuilt(self) -> bool:
        """Return True if the deliverable is marked as prebuilt."""
        if self.kind is not None and not self.is_xref:
            return self._is_kind("prebuilt")

        # Fallback 1: infer prebuilt from a local <prebuilt> child node
        if self.node.find("prebuilt") is not None:
            return True

        # Fallback 2: if it's a translated reference, check if the English target is prebuilt
        if self.is_xref and (target := self.final_target_node) is not None and target is not self.node:
            return target.find("prebuilt") is not None or target.get("type") == "prebuilt"

        return False

    @cached_property
    def is_dc(self) -> bool:
        """Return True if the deliverable is marked as DC."""
        return self.node.find("dc") is not None

    @cached_property
    def xref_node(self) -> etree._Element | None:
        """Return the child <xref> element if present."""
        return self.node.find("xref")

    @cached_property
    def is_xref(self) -> bool:
        """Return True if the deliverable is marked as a cross-reference."""
        if self.kind == "xref":
            return True
        if self.xref_node is not None:
            return True
        return False

    def _is_kind(self, expected: str) -> bool:
        """Return ``True`` when the deliverable type matches ``expected``."""
        return self.kind == expected

    # -- Content and categories
    @cached_property
    def categoryid(self) -> str | None:
        """Return the raw category ID from ``@category``, or ``None`` if absent."""
        if cat := self.node.get("category"):
            return cat
        if self.is_xref:
            if self.xref_node is not None and (cat := self.xref_node.get("category")):
                return cat
            if (
                target := self.final_target_node
            ) is not None and target is not self.node:
                return target.get("category")
        return None

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

    @cached_property
    def category_title(self) -> str | None:
        """Return the resolved category title, or the raw ID if not found."""
        cat_id = self.categoryid
        if not cat_id:
            return None

        for cat in self.all_categories:
            lang_nodes = cat.xpath("id($cat_id)", cat_id=cat_id)
            if lang_nodes:
                title = lang_nodes[0].findtext("title")
                if not title:
                    title = lang_nodes[0].get("title")
                if not title:
                    title = lang_nodes[0].get("name")
                return title.strip() if title else cat_id
        return cat_id

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
        if len(node) > 0 and node[0].text is not None:
            return node[0].text.strip()
        return None

    def subdir(self) -> str:
        """Return combined subdirectory (locale-level + deliverable-level) or empty string."""
        parts = self.node.xpath("parent::*/subdir/text() | subdir/text()")
        return "/".join(p.strip() for p in parts)

    def git_remote(self) -> Repo | str | None:
        """Return git remote URL from sibling ``<git>`` node."""
        # TODO: Use Repo as return object?
        node = self.node.getparent().getparent().find("git")
        if node is not None:
            remote_str = node.attrib.get("remote")
            try:
                return Repo(remote_str)
            except ValueError:
                return remote_str
        return None

    # -- Output formats
    def _xref_format_attrs(self, expected_formats: tuple[str, ...]) -> dict[str, str] | None:
        """Return raw format attributes from the linked deliverable."""
        if (target := self.final_target_node) is not None and target is not self.node:
            if target.find("dc") is not None:
                return self._dc_format_attrs(target)
            if target.find("prebuilt") is not None or target.get("type") == "prebuilt":
                return self._prebuilt_format_attrs(expected_formats, source_node=target)
        return None

    def _dc_format_attrs(self, source_node: etree._Element | None = None) -> dict[str, str] | None:
        """Return raw format attributes from ``dc/format`` in the given node."""
        node = (source_node if source_node is not None else self.node).find("dc/format")
        return node.attrib if node is not None else None

    def _prebuilt_format_attrs(
        self,
        expected_formats: tuple[str, ...],
        source_node: etree._Element | None = None,
    ) -> dict[str, str]:
        """Return raw format attributes from prebuilt URL nodes."""
        # For validated prebuilt deliverables, each <url> uses a single
        # format attribute (e.g. format="html").
        node = source_node if source_node is not None else self.node
        url_nodes = node.xpath("prebuilt/url")
        attrs = {fmt: "0" for fmt in expected_formats}  # default all formats to False
        for url_node in url_nodes:
            if (url_format := url_node.attrib.get("format")) in expected_formats:
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

        if self.is_xref:
            raw_attrs = self._xref_format_attrs(expected_formats)
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
            f"product_id={self.product_id!r}, "
            f"docset_path={self.docset_path!r}, lang={self.lang!r}, "
            f"branch={self.branch()!r}, dcfile={self.dcfile!r}"
        )

    def __repr__(self) -> str:
        """Return a concise string representation of the deliverable."""
        return f"{self.__class__.__name__}({self!s})"

    @cached_property
    def target_node(self) -> etree._Element | None:
        """Return the direct target element of a reference deliverable.

        For a ``<deliverable><xref linkend="foo">``, this will return the
        element with ``xml:id="foo"``. If the reference is broken or the
        deliverable is not a reference, it returns ``None``.

        :returns: The target ``etree._Element`` or ``None``.
        """
        if not self.is_xref:
            return None

        ref_node = self.xref_node
        if ref_node is None:
            return None

        linkend = ref_node.get("linkend")
        if not linkend:
            return None

        # Use the XPath `id()` function to find the element by its xml:id
        # Fall back to attribute search for trees constructed via XInclude where
        # libxml2's document ID hash table is not populated for inserted nodes.
        target_nodes = self.node.xpath("id($linkend)", linkend=linkend)
        if not target_nodes:
            target_nodes = self.node.xpath("//*[@xml:id=$linkend]", linkend=linkend)

        if target_nodes:
            return target_nodes[0]
        return None

    @cached_property
    def xml_id(self) -> str | None:
        """Return the xml:id of the deliverable."""
        return self.node.get(XML_ID)

    @cached_property
    def final_target_node(self) -> etree._Element | None:
        """Recursively resolve reference chains to find the terminal node.

        This property follows a chain of ``<deliverable><xref linkend="..."/>``
        until it finds a node that is not a reference deliverable.

        - If the deliverable is not a reference, it returns the node itself.
        - It detects and stops on circular dependencies, returning the first
          node that is part of the cycle.
        - It stops when it encounters a non-deliverable element (e.g., ``<product>``).
        - If a reference is broken (points to a non-existent ID), it returns ``None``.

        :returns: The terminal ``etree._Element`` in a reference chain, or ``None``.
        """
        if not self.is_xref:
            return self.node

        current_view = self
        visited_ids = {self.xml_id} if self.xml_id else set()

        while current_view is not None and current_view.is_xref:
            target_node = current_view.target_node
            if target_node is None:
                return None  # Broken reference

            # A non-deliverable is a terminal node.
            if etree.QName(target_node).localname != "deliverable":
                return target_node

            target_id = target_node.get(XML_ID)
            if not target_id:
                return target_node

            if target_id in visited_ids:
                return current_view.node  # Cycle detected

            visited_ids.add(target_id)
            current_view = DeliverableXMLView(target_node)

        return current_view.node if current_view else None

    def local_desc(self) -> Generator[etree._Element, None, None]:
        """Yield local ``<desc>`` elements, usually from prebuilts."""
        if (target := self.final_target_node) is not None:
            yield from target.xpath("./prebuilt/descriptions/desc")

    @cached_property
    def prebuilt_title(self) -> str:
        """Return the prebuilt title text if present."""
        if (target := self.final_target_node) is not None:
            return (target.findtext("./prebuilt/title") or "").strip()
        return ""

    def _get_prebuilt_url(self, fmt: str) -> str:
        """Extract local prebuilt URLs for a given format."""
        if (target := self.final_target_node) is not None:
            for node in target.xpath(f'./prebuilt/url[@format="{fmt}"]'):
                href = node.get("href", "")
                if href.startswith("/"):
                    if self.is_xref:
                        return href.replace("/en/", f"/{self.lang.lang}/")
                    return href
        return ""

    @cached_property
    def prebuilt_html_url(self) -> str:
        """Return the local prebuilt HTML URL (starts with '/')."""
        return self._get_prebuilt_url("html")

    @cached_property
    def prebuilt_pdf_url(self) -> str:
        """Return the local prebuilt PDF URL (starts with '/')."""
        return self._get_prebuilt_url("pdf")

    @cached_property
    def is_gated(self) -> bool:
        """Return True if the deliverable is marked as gated."""
        if (target := self.final_target_node) is not None:
            return str(target.get("gated", "false")).lower() == "true"
        return False

    @cached_property
    def docset_version(self) -> str:
        """Return the docset version."""
        if self.docset_node is not None:
            node = self.docset_node.findtext("version", default="")
            return node.strip() if node else ""
        return ""

    @cached_property
    def target_type(self) -> Literal["product", "docset", "deliverable"] | None:
        """Return the local element name of the target node, if this is an xref."""
        if not self.is_xref or self.final_target_node is None:
            return None
        return etree.QName(self.final_target_node).localname  # type: ignore

    @cached_property
    def target_url(self) -> str | None:
        """Return the web URL for the xref target (product, docset, or deliverable)."""
        target = self.final_target_node
        if target is None:
            return None

        tag = self.target_type
        if tag == "product":
            p_path = target.get("path") or target.get(XML_ID) or ""
            return f"/{p_path}/"

        if tag == "docset":
            prod = target.getparent()
            p_path = (prod.get("path") or prod.get(XML_ID) or "") if prod is not None else ""
            ds_path = target.get("path") or target.get(XML_ID) or ""
            return f"/{p_path}/{ds_path}/" if p_path else f"/{ds_path}/"

        return self.resolved_prebuilt_html_url

    @cached_property
    def target_title(self) -> str:
        """Return the display title of the target node."""
        target = self.final_target_node
        if target is None:
            return ""

        tag = self.target_type
        if tag == "product":
            return target.findtext("name") or target.get("path") or target.get(XML_ID) or ""
        if tag == "docset":
            return target.findtext("name") or target.findtext("version") or target.get("path") or target.get(XML_ID) or ""

        return target.findtext("title") or ""
