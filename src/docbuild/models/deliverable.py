"""Module for defining the Deliverable model."""

from collections.abc import Generator
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
import re
from typing import Literal, cast

from lxml import etree

from ..utils.convert import convert2bool
from .metadata import Metadata
from .repo import Repo


@dataclass
class Deliverable:
    """A class to represent a deliverable.

    Usually called with a ``<deliverable>`` node from the XML
    configuration file. It contains information about the product,
    docset, language, branch, and other metadata related to the
    deliverable.
    """

    _node: etree._Element = field(repr=False)  # deliverable node
    _metafile: str | None = field(repr=False, default=None)
    _product_node: etree._Element | None = field(repr=False, default=None)
    _meta: Metadata | None = None

    @cached_property
    def all_categories(self) -> Generator[etree._Element, None, None]:
        """Return the groups (formerly categories) of the deliverable.

        Yield all elements from the product and root node.

        :yield: The elements categories/category and category.
        """
        yield from self.categories
        yield from self.categories_from_root

    @cached_property
    def categories(self) -> Generator[etree._Element, None, None]:
        """Return the groups (formerly categories) from the product node.

        Yield all elements under the product were this deliverable belongs to.

        :yield: The elements categories/category and category.
        """
        yield from self.product_node.xpath("categories/category|category")

    @cached_property
    def categories_from_root(self) -> Generator[etree._Element, None, None]:
        """Return the groups (formerly categories) from the root node.

        Yield all elements under the root node.

        :yield: The elements categories/category and category.
        """
        root = self.product_node.getroottree().getroot()
        yield from root.xpath("categories/category|category")

    @cached_property
    def desc(self) -> Generator[etree._Element, None, None]:
        """Return the <desc> from the product node."""
        yield from self.product_node.xpath("desc")

    @cached_property
    def productid(self) -> str | None:
        """Return the product ID."""
        # ancestor::product/@productid
        return self.product_node.attrib.get("productid", None)

    @cached_property
    def productname(self) -> str | None:
        """Return the product name."""
        # ancestor::product/name
        return self.product_node.findtext("name", default=None, namespaces=None)

    @cached_property
    def docsetid(self) -> str:
        """Return the docset ID."""
        # ancestor::docset/@setid
        return next(self._node.iterancestors("docset")).attrib.get("setid")

    @cached_property
    def lang(self) -> str:
        """Returns the language and country code (e.g., 'en-us')."""
        # ../../builddocs/language/@lang
        return self._node.getparent().attrib.get("lang").strip()

    @cached_property
    def language(self) -> str:
        """Returns only the language (e.g., 'en')."""
        return re.split(r"[_-]", self.lang)[0]

    @cached_property
    def product_docset(self) -> str:
        """Returns product and docset."""
        return f"{self.productid}/{self.docsetid}"

    @cached_property
    def pdlang(self) -> str:
        """Return product, docset, and language."""
        return f"{self.product_docset}/{self.lang}"

    @cached_property
    def pdlangdc(self) -> str:
        """Return product, docset, language and DC filename."""
        return f"{self.pdlang}:{self.dcfile}"

    @cached_property
    def full_id(self) -> str:
        """Return the full ID of the deliverable."""
        branch = self.make_safe_name(self.branch)
        return f"{self.product_docset}/{branch}/{self.lang}:{self.dcfile}"

    @cached_property
    def lang_is_default(self) -> bool:
        """Check if the language is the default language."""
        # ../language/@default
        # If the attribute default does not exist we get None.
        # As a fall back we return "0" => False
        content: str = self._node.getparent().attrib.get("default", "0")

        mapping = {
            "1": True,
            "0": False,
            "on": True,
            "off": False,
            "true": True,
            "false": False,
        }
        return mapping.get(content.strip(), False)

    @cached_property
    def docsuite(self) -> str:
        """Return the product, docset, language and the DC filename."""
        return f"{self.pdlang}:{self.dcfile}"

    @cached_property
    def branch(self) -> str:
        """Return the branch where to find the deliverable.

        Searches for the branch in the English language node first,
        then in the current language node.

        :return: The branch name as a string.
        :raises ValueError: If no branch is found
        """
        node = self._node.getparent().findtext("branch", default=None)
        if node is not None:
            return node.strip()

        # If we cannot find the branch in the current language node,
        # we look in the English language and use this branch
        node = self._node.getparent().xpath(
            "ancestor::builddocs/language"
            "[@lang!='en-us' or @default!='1' or @default!='true']/branch",
        )
        if node:
            return node[0].text.strip()

        raise ValueError(f"No branch found for this deliverable {self.pdlangdc}")

    @cached_property
    def subdir(self) -> str:
        """Return subdirectory or an empty string if not found."""
        node = self._node.getparent().findtext("subdir", default=None)
        if node is not None:
            return node.strip()
        else:
            return ""

    @cached_property
    def git(self) -> Repo:
        """Return the git repository.

        :return: The git remote URL as a string.
        :raises ValueError: If no git remote is found for the deliverable.
        """
        # ../preceding-sibling::git/@remote
        node = self._node.getparent().getparent().find("git")
        if node is not None:
            return Repo(node.attrib.get("remote"))
        raise ValueError(
            "No git remote found for "
            f"{self.productid}/{self.docsetid}/{self.lang}/{self.dcfile}"
        )

    @cached_property
    def dcfile(self) -> str:
        """Return the DC filename or None if not found."""
        # ./dc
        return self._node.findtext("dc", default=None, namespaces=None)

    @cached_property
    def basefile(self) -> str:
        """Return the DC filename without the DC prefix."""
        return self.dcfile.lstrip("DC-")

    @cached_property
    def format(self) -> dict[Literal["html", "single-html", "pdf", "epub"], bool]:
        """Return the formats of the deliverable.

        Normalize the format attributes to boolean values.

        :return: A dictionary with format names as keys and boolean values.
        :raises ValueError: If no format is found for the deliverable.
        """
        # ./format
        dc = self.dcfile
        # We need to look inside English deliverables for formats
        node = self._node.xpath(
            f"(format|../../language[@lang='en-us']/"
            f"deliverable[dc[{dc!r} = .]]/format)[last()]"
        )
        if not node:
            raise ValueError(
                "No format found for "
                f"{self.productid}/{self.docsetid}/{self.lang}/{self.dcfile}"
            )

        return {key: convert2bool(value) for key, value in node[0].attrib.items()}

    @cached_property
    def node(self) -> etree._Element:
        """Return the node of the deliverable."""
        return self._node

    @cached_property
    def acronym(self) -> str:
        """Return the product acronym or None if not found."""
        # ancestor::product/acronym
        node = self.product_node.findtext("acronym", default=None, namespaces=None)
        if node is not None:
            return node.strip()
        return ""

    @cached_property
    def version(self) -> str:
        """Return the version of the docset or None if not found."""
        # ancestor::docset/version
        return self.docset_node.findtext("version", default=None, namespaces=None)

    @cached_property
    def lifecycle(self) -> str:
        # TODO: Return Lifecycle object?
        """Return the lifecycle of the docset."""
        # ancestor::docset/@lifecycle
        return self.docset_node.attrib.get("lifecycle")

    # --- Path properties
    @cached_property
    def relpath(self) -> str:
        """Return the relative path of the deliverable."""
        return f"{self.lang}/{self.product_docset}"

    @cached_property
    def repo_path(self) -> Path:
        """Return the "slug" path of the repository."""
        return Path(self.git.slug)

    @cached_property
    def zip_path(self) -> str:
        """Return the path to the ZIP file."""
        return (
            f"{self.lang}/{self.productid}/{self.docsetid}/"
            f"{self.productid}-{self.docsetid}-{self.lang}.zip"
        )

    def _base_format_path(self, fmt: str) -> str:
        """Return the base path for a given format."""
        path = "/"
        fallback_rootid = self.dcfile.lstrip("DC-")
        if self.meta is not None:
            rootid = self.meta.rootid
            if rootid is None:
                # Derive rootid from the DC file
                rootid = fallback_rootid
        else:
            rootid = fallback_rootid

        # Suppress English
        if self.lang != "en-us":
            path += f"{self.lang}/"

        path += f"{self.productid}/{self.docsetid}/{fmt}/{rootid}/"
        return path

    @cached_property
    def html_path(self) -> str:
        """Return the path to the HTML directory."""
        return self._base_format_path("html")

    @cached_property
    def singlehtml_path(self) -> str:
        """Return the path to the single HTML directory."""
        return self._base_format_path("single-html")

    @cached_property
    def pdf_path(self) -> str:
        """Return the path to the PDF file."""
        path = "/"
        draft = ""  # TODO
        name = self.dcfile.lstrip("DC-")
        if self.lang != "en-us":
            path += f"{self.lang}/"

        path += f"{self.product_docset}/pdf/{name}{draft}_{self.language}.pdf"
        return path

    # --- Node handling
    @cached_property
    def product_node(self) -> etree._Element:
        """Return the product node of the deliverable."""
        # There is always a <product> node
        return self._node.getparent().getparent().getparent().getparent()

    @cached_property
    def docset_node(self) -> etree._Element:
        """Return the docset node of the deliverable."""
        # There is always a <docset> node
        return cast(etree._Element, self._node.getparent().getparent().getparent())

    @property
    def metafile(self) -> str | None:
        """Return the metadata file."""
        return self._metafile

    @metafile.setter
    def metafile(self, value: str) -> None:
        """Set the metadata file."""
        self._metafile = value

    @property
    def meta(self) -> Metadata | None:
        """Return the metadata object of the deliverable."""
        return self._meta

    @meta.setter
    def meta(self, value: Metadata) -> None:
        """Set the metadata content of the deliverable."""
        if not isinstance(value, Metadata):
            raise TypeError(f"Expected type Metadata, but got {type(value)}")
        self._meta = value

    def __hash__(self) -> int:
        """Implement hash(self)."""
        return hash(self.full_id)

    def __repr__(self) -> str:
        """Implement repr(self)."""
        return (
            f"{self.__class__.__name__}(productid={self.productid!r}, "
            f"docsetid={self.docsetid!r}, "
            f"lang={self.lang!r}, "
            f"branch={self.branch!r}, "
            f"dcfile={self.dcfile!r})"
        )

    def to_dict(self) -> dict:
        """Return the deliverable as a JSON object."""
        raise NotImplementedError("Not yet implemented")

    @staticmethod
    def make_safe_name(name: str) -> str:
        """Make a name safe for use in a filename or directory."""
        table = str.maketrans(
            {
                "/": "_",
                ":": "-",
                "*": "_",
                "?": "_",
                "<": "",
                ">": "",
                "\\": "",
            }
        )
        return name.translate(table)
