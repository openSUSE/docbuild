"""Path calculation helper for deliverables."""

from dataclasses import dataclass
from functools import cached_property

from .view import DeliverableXMLView
from ..language import LanguageCode


@dataclass
class DeliverablePaths:
    """Path-related properties for a deliverable."""

    xml: DeliverableXMLView
    # git: Repo
    rootid: str | None = None
    lang: LanguageCode | None = None

    def _lang(self) -> LanguageCode:
        """Return the language override or XML-derived language."""
        return self.lang if self.lang is not None else self.xml.lang

    @cached_property
    def product_docset(self) -> str:
        """Return product and docset joined by a slash."""
        return f"{self.xml.productid}/{self.xml.docsetid}"

    @cached_property
    def relpath(self) -> str:
        """Return the relative path of the deliverable."""
        lang = self._lang()
        return f"{lang}/{self.product_docset}"

    @cached_property
    def zip_path(self) -> str:
        """Return the path to the ZIP file."""
        lang = self._lang()
        productid = self.xml.productid
        docsetid = self.xml.docsetid
        return f"{lang}/{productid}/{docsetid}/{productid}-{docsetid}-{lang}.zip"

    def base_format_path(self, fmt: str) -> str:
        """Return the base path for a given format."""
        path = "/"
        lang = self._lang()
        dcfile = self.xml.dcfile
        if dcfile is None:
            raise ValueError("No DC filename found for path generation")

        fallback_rootid = dcfile.lstrip("DC-")
        rootid = self.rootid or fallback_rootid

        # Suppress English
        if lang != "en-us":
            path += f"{lang}/"

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
        lang = self._lang()
        dcfile = self.xml.dcfile
        if dcfile is None:
            raise ValueError("No DC filename found for PDF path generation")
        name = dcfile.lstrip("DC-")
        if lang != "en-us":
            path += f"{lang}/"

        # We are only interested in the language, not the country code.
        path += f"{self.product_docset}/pdf/{name}{draft}_{lang.lang}.pdf"
        return path

    def __repr__(self) -> str:
        """Return a string representation of the deliverable paths."""
        return f"{self.__class__.__name__}(xml=({self.xml!s}), rootid={self.rootid!s})"
