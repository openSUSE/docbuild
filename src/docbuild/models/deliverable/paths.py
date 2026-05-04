"""Path calculation helper for deliverables."""

from dataclasses import dataclass
from functools import cached_property

from ..metadata import Metadata
from .view import DeliverableXMLView


@dataclass
class DeliverablePaths:
    """Path-related properties for a deliverable."""

    xml: DeliverableXMLView
    # git: Repo
    meta: Metadata | None = None  # TODO: Remove it?

    @cached_property
    def product_docset(self) -> str:
        """Return product and docset joined by a slash."""
        return f"{self.xml.productid}/{self.xml.docsetid}"

    @cached_property
    def relpath(self) -> str:
        """Return the relative path of the deliverable."""
        return f"{self.xml.lang}/{self.product_docset}"

    @cached_property
    def zip_path(self) -> str:
        """Return the path to the ZIP file."""
        productid = self.xml.productid
        docsetid = self.xml.docsetid
        lang = self.xml.lang
        return f"{lang}/{productid}/{docsetid}/{productid}-{docsetid}-{lang}.zip"

    def base_format_path(self, fmt: str) -> str:
        """Return the base path for a given format."""
        path = "/"
        dcfile = self.xml.dcfile
        if dcfile is None:
            raise ValueError("No DC filename found for path generation")

        fallback_rootid = dcfile.lstrip("DC-")
        if self.meta is not None:
            if (rootid := self.meta.rootid) is None:
                # Derive rootid from the DC file
                rootid = fallback_rootid
        else:
            rootid = fallback_rootid

        # Suppress English
        if self.xml.lang != "en-us":
            path += f"{self.xml.lang}/"

        path += f"{self.xml.productid}/{self.xml.docsetid}/{fmt}/{rootid}/"
        return path

    @cached_property
    def html_path(self) -> str:
        """Return the path to the HTML directory."""
        return self.base_format_path("html")

    @cached_property
    def singlehtml_path(self) -> str:
        """Return the path to the single-HTML directory."""
        return self.base_format_path("single-html")

    @cached_property
    def pdf_path(self) -> str:
        """Return the path to the PDF file."""
        path = "/"
        draft = ""  # TODO
        dcfile = self.xml.dcfile
        if dcfile is None:
            raise ValueError("No DC filename found for PDF path generation")
        name = dcfile.lstrip("DC-")
        if self.xml.lang != "en-us":
            path += f"{self.xml.lang}/"

        # We are only interested in the language, not the country code.
        path += f"{self.product_docset}/pdf/{name}{draft}_{self.xml.lang.lang}.pdf"
        return path

    def __repr__(self) -> str:
        """Return a string representation of the deliverable paths."""
        return f"{self.__class__.__name__}(xml=({self.xml!s}), meta={self.meta!s})"
