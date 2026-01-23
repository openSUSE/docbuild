"""Module for defining the Metadata model."""

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import ClassVar, Self


@dataclass
class Metadata:
    """A class to represent the metadata of a deliverable."""

    title: str | None = field(default=None)
    """The title of the deliverable."""

    subtitle: str = field(default="")
    """The subtitle of the deliverable."""

    # SEO metadata
    seo_title: str | None = field(default=None)
    """The SEO title of the deliverable."""
    seo_description: str = field(default="")
    """The SEO description of the deliverable."""
    seo_social_descr: str = field(default="")
    """The SEO social description of the deliverable."""
    #
    dateModified: str = field(default="")  # noqa: N815
    """The date when the deliverable was last modified."""
    tasks: list[str] = field(default_factory=list)
    """A list of tasks related to the deliverable."""
    series: str | None = field(default=None)
    """The series of the deliverable, if applicable."""
    rootid: str | None = field(default=None)
    """The root ID of the deliverable, if applicable."""
    #
    # description: str | None = field(default=None)
    products: list[dict] = field(default_factory=list)
    """A list of products related to the deliverable, each represented
    as a dictionary."""
    # docTypes: list[str] | None = field(default=None)
    # archives: list[str] | None = field(default=None)
    # category: str | None = field(default=None)
    #
    _match: ClassVar[re.Pattern] = re.compile(r"\[(.*?)\](.*)")

    def read(self, metafile: Path | str) -> Self:  # noqa: C901
        """Read the metadata from a file.

        :param metafile: The path to the metadata file.
        :return: The metadata instance.
        """
        lines = Path(metafile).open().readlines()
        for line in lines:
            if line.lstrip().startswith("#"):
                continue
            key, value = map(str.strip, line.split("=", 1))

            match key:
                # case "category":
                #     if value:
                #         self.category = value
                case "title":
                    self.title = value

                case "subtitle":
                    if value:
                        self.subtitle = value

                case "seo-title":
                    if value:
                        self.seo_title = value

                case "seo-social-descr":
                    if value:
                        self.seo_social_descr = value

                case "seo-description":
                    if value:
                        self.seo_description = value

                case "date":
                    if value:
                        self.dateModified = value

                case "rootid":
                    if value:
                        self.rootid = value

                case "task":
                    self.tasks = [task.strip() for task in value.split(";")]

                case "productname":
                    # productlist = [entry["name"] for entry in self.products]
                    if mtch := self._match.match(value):
                        versions = mtch.group(1).strip().split(";")
                        product = mtch.group(2).strip()

                        dct = {
                            "name": product,
                            "versions": versions,
                        }
                        self.products.append(dct)

                case "series":
                    if value:
                        self.series = value

        return self
