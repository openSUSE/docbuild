"""Abstraction layer for Portal XML configuration."""

from collections.abc import Generator, Iterator
from pathlib import Path
from typing import Any

from lxml import etree  # type: ignore

from ...constants import XML_NS
from ...models.deliverable import Deliverable
from .xinclude import parse_xml_with_xinclude_base

XML_ID = etree.QName(XML_NS, "id")
SPECIAL_IDS = {"sbp", "trd", "smart"}


class PortalConfig:
    """Wrapper class for parsing and extracting data from the Portal XML.

    This class handles all XPath evaluations and XML traversal, acting as a clean
    abstraction layer for Pydantic models and CLI commands.
    """

    def __init__(
        self,
        source: Path | str | etree._Element | etree._ElementTree,
    ) -> None:
        """Initialize with either a filepath to parse or an existing etree."""
        tree = parse_xml_with_xinclude_base(source) if isinstance(source, (str, Path)) else source
        self.root = tree.getroot() if hasattr(tree, "getroot") else tree

    def _resolve_spotlight_target(
        self, target: etree._Element, linkend: str, text: str
    ) -> tuple[str, str]:
        """Resolve the tag-specific logic for a spotlight target."""
        match target.tag:
            case "product":
                link = f"/{target.get(XML_ID) or ''}/"
                if not text:
                    text = target.xpath("string(name)").strip()

            case "docset":
                prod = target.getparent()
                prod_id = (prod.get(XML_ID) if prod is not None else "") or ""
                ds_path = target.get("path", "").strip("/")
                link = f"/{prod_id}/{ds_path}/"
                if not text:
                    prod_name = prod.xpath("string(name)").strip() if prod is not None else ""
                    ds_version = target.xpath("string(version)").strip()
                    text = f"{prod_name} {ds_version}".strip()

            case "deliverable":
                d = Deliverable(target)
                link = f"/{d.xml.product_docset}/"
                if not text:
                    prod_name = d.xml.productname or ""
                    ds_node = d.xml.docset_node
                    ds_version = ds_node.xpath("string(version)").strip() if ds_node is not None else ""
                    text = f"{prod_name} {ds_version}".strip()

            case _:
                link = f"/{linkend}/"

        return text, link

    @property
    def spotlight(self) -> dict[str, str]:
        """Extract spotlight text and link.

        :return: A dictionary containing 'spotlightText' and 'spotlightLink'.
        """
        # Fix: use relative path "spotlight" instead of absolute "/portal/spotlight" for .find()
        if (spotlight := self.root.find("spotlight")) is None:
            return {}

        if not (linkend := spotlight.get("linkend", "")):
            text = " ".join(spotlight.xpath("string()").split())
            return {"spotlightText": text, "spotlightLink": ""}

        linkend = spotlight.attrib["linkend"]
        text = " ".join(spotlight.xpath("string()").split())
        target = self.root.xpath("id($linkend)", linkend=linkend)[0]

        final_text, final_link = self._resolve_spotlight_target(target, linkend, text)
        return {"spotlightText": final_text, "spotlightLink": final_link}

    @property
    def productfamilies(self) -> Iterator[dict[str, str]]:
        """Extract product families.

        :return: An iterator of dictionaries representing product families.
        """
        for rank, pf in enumerate(self.root.xpath("/portal/productfamilies/item"), start=1):
            item_id = pf.get(XML_ID) or ""
            item_text = pf.xpath("string()").strip()
            yield {
                "id": item_id,
                "name": item_text,
                "rank": pf.get("rank", "").strip() or str(rank),
                "path": pf.get("path", ""),
            }

    def get_categories(self, prod_id: str) -> Iterator[dict[str, str]]:
        """Extract specialized docset categories (sbp, trd, smart).

        :param prod_id: The ID of the product containing the docsets.
        """
        for ds in self.root.xpath("id($prod_id)/docset", prod_id=prod_id):
            parent = ds.getparent()
            prod_path = (
                (parent.get("path") if parent is not None else "") or prod_id
            ).strip("/")
            name = (
                ds.xpath("string(./listingversion)").strip()
                or ds.xpath("string(./version)").strip()
            )
            path = ds.get("path", "").strip("/")
            yield {"name": name, "path": f"/{prod_path}/{path}/"}

    @property
    def products(self) -> Iterator[dict[str, Any]]:
        """Yield extracted products from the Portal configuration.

        :yield: A dictionary representing an individual product.
        """
        family_map = {f["id"]: f["name"] for f in self.productfamilies if f["id"]}
        for prod in self.root.xpath("/portal/product"):
            if (prod_id := prod.get(XML_ID) or "") in SPECIAL_IDS:
                continue

            # Optimize descriptions: one-pass comprehension with walrus operator
            descriptions = [
                {
                    "lang": d.get("lang", "en-us"),
                    "default": d.get("lang", "en-us") == "en-us",
                    "description": title,
                }
                for d in prod.xpath("descriptions/desc")
                if (title := " ".join(d.xpath("string(title)").split()))
            ]

            # Optimize docsets: single-pass partition without duplicated dict creation
            supported: list[dict[str, str]] = []
            unsupported: list[dict[str, str]] = []
            for ds in prod.xpath("docset"):
                target = (
                    supported
                    if ds.get("lifecycle", "supported") in ("supported", "beta")
                    else unsupported
                )
                target.append(
                    {
                        "name": ds.xpath("string(version)").strip() or ds.get(XML_ID, ""),
                        "path": f"/{prod_id}/{ds.get('path', '').strip('/')}/",
                    }
                )

            family = family_map.get(prod.get("family", ""), prod.get("family", ""))

            yield {
                "name": prod.xpath("string(name)").strip(),
                "acronym": prod_id,
                "product_family": family,
                "description": descriptions,
                "rank": prod.get("rank", "").strip(),
                "supported": supported,
                "unsupported": unsupported,
            }

    def iter_deliverables(self) -> Generator[Deliverable, None, None]:
        """Yield all deliverables defined in the portal XML."""
        for deliv_node in self.root.xpath("//deliverable"):
            yield Deliverable(deliv_node)
