"""Deliverable model facade.

.. warning::

    The deliverable model assumes that the XML node has already been successfully
    validated against the schema. As such, the model does NOT have defensive checks
    for missing or malformed XML data.
    If the XML is invalid, behavior is undefined and may raise exceptions.
"""

from dataclasses import dataclass, field
from functools import cached_property
from typing import ClassVar, Literal

from lxml import etree

from ...utils.convert import convert2bool
from ..metadata import Metadata
from ..repo import Repo
from .paths import DeliverablePaths
from .view import DeliverableXMLView


@dataclass
class Deliverable:
    """Deliverable model class operated on a validated config.

    * DeliverableXMLView owns facts you can derive from the XML node alone.
    * DeliverablePaths owns path construction.
    * Deliverable owns orchestration and non-XML domain objects.
    """

    # -- Class variables
    _DEFAULT_LANGUAGE: ClassVar[str] = "en-us"

    # -- Instance variables
    _node: etree._Element = field(repr=False)
    _metafile: str | None = field(repr=False, default=None)
    # TODO: Is that still needed?
    _meta: Metadata | None = None

    # -- "Private" methods for internal use in properties
    #def _base_format_path(self, fmt: str) -> str:
    #    """Return the base path for a specific output format."""
    #    return self.paths.base_format_path(fmt)

    def _append_dcfile(self, identifier: str) -> str:
        """Append the DC filename suffix to an identifier when present."""
        dcfile = self.xml.dcfile
        if dcfile:
            return f"{identifier}:{dcfile}"
        return f"{identifier}:"

    # -- XML-derived properties
    @cached_property
    def xml(self) -> DeliverableXMLView:
        """Return the XML view of this deliverable."""
        return DeliverableXMLView(self._node)

    @cached_property
    def paths(self) -> DeliverablePaths:
        """Return the path helper for this deliverable."""
        return DeliverablePaths(self.xml, self.meta)

    @cached_property
    def pdlang(self) -> str:
        """Return product/docset/language identifier."""
        return f"{self.xml.product_docset}/{self.xml.lang}"

    @cached_property
    def pdlangdc(self) -> str:
        """Return product/docset/language plus DC filename identifier."""
        # TODO: what to do for a pre-built deliverable?
        return self._append_dcfile(self.pdlang)

    @cached_property
    def full_id(self) -> str:
        """Return the canonical unique identifier for this deliverable."""
        branch = self.make_safe_name(self.branch)
        identifier = f"{self.xml.product_docset}/{branch}/{self.xml.lang}"
        return self._append_dcfile(identifier)

    @cached_property
    def docsuite(self) -> str:
        """Return docsuite identifier in ``product/docset/lang:dc`` format."""
        # TODO: what to do for a pre-built deliverable?
        return self._append_dcfile(self.pdlang)

    @cached_property
    def lang_is_default(self) -> bool:
        """Return ``True`` when the language node is marked as default."""
        content: str = self._node.getparent().attrib.get("lang", "")
        return content == type(self)._DEFAULT_LANGUAGE

    @cached_property
    def branch(self) -> str:
        """Return the branch for this deliverable, with fallback lookup."""
        if branch := self.xml.branch():
            return branch
        if fallback_branch := self.xml.branch_from_fallback_locale():
            return fallback_branch
        # This shouldn't happen if the XML is valid,
        # but we want to be sure to fail loudly if it does
        raise ValueError(f"No branch found for this deliverable {self.pdlangdc}")

    @cached_property
    def subdir(self) -> str:
        """Return configured subdirectory or an empty string."""
        return self.xml.subdir()

    @cached_property
    def git(self) -> Repo:
        """Return the Git repository configuration for this deliverable."""
        if repo := self.xml.git_remote():
            return repo
        raise ValueError(
            f"No git remote found for {self!s}"
            # f"{self.xml.productid}/{self.xml.docsetid}/{self.xml.lang}/{self.xml.dcfile}"
        )

    @cached_property
    def format(self) -> dict[Literal["html", "single-html", "pdf", "epub"], bool]:
        """Return enabled output formats normalized to booleans."""
        attrs = self.xml.format_attrs()
        #if attrs is None:
        #    raise ValueError(
        #        f"No format found for {self!s}"
        #        # f"{self.productid}/{self.docsetid}/{self.lang}/{self.dcfile}"
        #    )

        expected: tuple[Literal["html", "single-html", "pdf", "epub"], ...] = (
            "html",
            "single-html",
            "pdf",
            "epub",
        )
        return {fmt: convert2bool(attrs[fmt]) for fmt in expected if fmt in attrs}

    @property
    def metafile(self) -> str | None:
        """Return the metadata file path."""
        # TODO: Is that still needed?
        return self._metafile

    @metafile.setter
    def metafile(self, value: str) -> None:
        """Set the metadata file path."""
        # TODO: Is that still needed?
        self._metafile = value

    @property
    def meta(self) -> Metadata | None:
        """Return parsed metadata for this deliverable."""
        # TODO: Is that still needed?
        return self._meta

    @meta.setter
    def meta(self, value: Metadata) -> None:
        """Set parsed metadata for this deliverable."""
        # TODO: Is that still needed?
        if not isinstance(value, Metadata):
            raise TypeError(f"Expected Metadata, got {type(value)}")
        self._meta = value

    def __hash__(self) -> int:
        """Return a hash based on the stable full identifier."""
        return hash(self.full_id)

    def __repr__(self) -> str:
        """Return a concise debug representation of this deliverable."""
        # return (
        #     f"{self.__class__.__name__}(productid={self.productid!r}, "
        #     f"docsetid={self.docsetid!r}, lang={self.lang!r}, "
        #     f"branch={self.branch!r}, dcfile={self.dcfile!r})"
        # )
        return f"{self.__class__.__name__}({self.xml!s})"

    @staticmethod
    def make_safe_name(name: str) -> str:
        """Normalize a string for safe use in filenames and path fragments."""
        table = str.maketrans(
            {"/": "_", ":": "-", "*": "_", "?": "_", "<": "", ">": "", "\\": ""}
        )
        return name.translate(table)
