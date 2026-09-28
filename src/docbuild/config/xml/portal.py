"""Abstraction layer for Portal XML configuration."""

from collections.abc import Generator
from pathlib import Path
from typing import Any

from lxml import etree  # type: ignore

from ...constants import XML_NS
from ...models.deliverable import Deliverable
from .xinclude import parse_xml_with_xinclude_base


class PortalConfig:
    """Wrapper class for parsing and extracting data from the Portal XML.

    This class handles all XPath evaluations and XML traversal, acting as a clean
    abstraction layer for Pydantic models and CLI commands.
    """

    def __init__(
        self,
        filepath: Path | str | None = None,
        tree: etree._ElementTree | None = None,
    ) -> None:
        """Initialize with either a filepath to parse or an existing etree."""
        if tree is not None:
            self.tree = tree
        elif filepath is not None:
            self.tree = parse_xml_with_xinclude_base(filepath)
        else:
            msg = "Must provide either filepath or tree"
            raise ValueError(msg)

        self.root = self.tree.getroot() if hasattr(self.tree, "getroot") else self.tree

    def _resolve_spotlight_target(
        self, target: etree._Element, linkend: str, text: str
    ) -> tuple[str, str]:
        """Resolve the tag-specific logic for a spotlight target."""
        if target.tag == "product":
            prod_id = target.get(f"{{{XML_NS}}}id") or ""
            link = f"/{prod_id}/"
            if not text:
                text = target.xpath("string(name)").strip()
            return text, link

        if target.tag == "docset":
            prod_node = target.getparent()
            prod_id = (
                prod_node.get(f"{{{XML_NS}}}id") or "" if prod_node is not None else ""
            )
            ds_path = target.get("path", "")

            link = f"/{prod_id}/{ds_path}".replace("//", "/")
            if not link.endswith("/"):
                link += "/"

            if not text:
                prod_name = (
                    prod_node.xpath("string(name)").strip()
                    if prod_node is not None
                    else ""
                )
                ds_version = target.xpath("string(./version)").strip()
                text = f"{prod_name} {ds_version}".strip()
            return text, link

        if target.tag == "deliverable":
            try:
                target_d = Deliverable(target)
                link = f"/{target_d.xml.product_docset}/"
                if not text:
                    prod_name = target_d.xml.productname or ""
                    ds_node = target_d.xml.docset_node
                    ds_version = (
                        ds_node.xpath("string(./version)").strip()
                        if ds_node is not None
                        else ""
                    )
                    text = f"{prod_name} {ds_version}".strip()
                return text, link
            except Exception:
                pass

        return text, f"/{linkend}/"

    @property
    def spotlight(self) -> dict[str, str]:
        """Extract spotlight text and link.

        :return: A dictionary containing 'spotlightText' and 'spotlightLink'.
        """
        spotlights = self.root.xpath("/portal/spotlight")
        if not spotlights:
            return {"spotlightText": "", "spotlightLink": ""}

        s_node = spotlights[0]
        linkend = s_node.get("linkend", "")
        text = " ".join(s_node.xpath("string()").split())

        if not linkend:
            return {"spotlightText": text, "spotlightLink": ""}

        target_nodes = self.root.xpath("id($linkend)", linkend=linkend)
        if not target_nodes:
            return {"spotlightText": text, "spotlightLink": linkend}

        final_text, final_link = self._resolve_spotlight_target(
            target_nodes[0], linkend, text
        )
        return {"spotlightText": final_text, "spotlightLink": final_link}

    @property
    def productfamilies(self) -> list[dict[str, str]]:
        """Extract product families.

        :return: A list of dictionaries representing product families.
        """
        families = []
        for rank_idx, pf in enumerate(
            self.root.xpath("/portal/productfamilies/item"), start=1
        ):
            item_id = pf.get(f"{{{XML_NS}}}id") or ""
            item_text = pf.xpath("string()").strip()
            families.append(
                {
                    "id": item_id,
                    "name": item_text,
                    "rank": pf.get("rank", "").strip() or str(rank_idx),
                    "path": pf.get("path", ""),
                }
            )
        return families

    def get_categories(self, prod_id: str, prefix: str) -> list[dict[str, str]]:
        """Extract specialized docset categories (sbp, trd, smart).

        :param prod_id: The ID of the product containing the docsets.
        :param prefix: The path prefix to prepend to the docset path.
        """
        items = []
        for ds in self.root.xpath("id($prod_id)/docset", prod_id=prod_id):
            name = ds.xpath("string(./version)").strip()
            if name.startswith("Smart Docs: "):
                name = name.replace("Smart Docs: ", "")
            path = ds.get("path", "").lstrip("/")
            items.append({"name": name, "path": f"{prefix}{path}"})
        return items

    @property
    def products(self) -> list[dict[str, Any]]:
        """Extract the main product list.

        :return: A list of dictionaries representing individual products.
        """
        # Create a mapping of family IDs to their names
        family_map = {f["id"]: f["name"] for f in self.productfamilies if f["id"]}

        items = []
        special_ids = {"sbp", "trd", "smart"}
        for prod in self.root.xpath("/portal/product"):
            prod_id = prod.get(f"{{{XML_NS}}}id") or ""
            if prod_id in special_ids:
                continue

            name = prod.xpath("string(name)").strip()

            # Map the ID back to the human-readable string
            family_id = str(prod.get("family") or "").strip()
            family = str(family_map.get(family_id, family_id) or "")

            rank = prod.get("rank", "").strip()

            descriptions = []
            for d in prod.xpath("descriptions/desc"):
                lang = d.get("lang", "en-us")
                desc_text = " ".join(d.xpath("string(./title)").split())
                if desc_text:
                    descriptions.append(
                        {
                            "lang": lang,
                            "default": (lang == "en-us"),
                            "description": desc_text,
                        }
                    )

            supported, unsupported = [], []
            for ds in prod.xpath("docset"):
                ds_name = (
                    ds.xpath("string(./version)").strip()
                    or ds.get(f"{{{XML_NS}}}id")
                    or ""
                )
                ds_path = ds.get("path", "")

                if not ds_path.startswith("/"):
                    ds_path = f"/{prod_id}/{ds_path}"
                if not ds_path.endswith("/"):
                    ds_path += "/"

                link = {"name": ds_name, "path": ds_path}

                if ds.get("lifecycle", "supported") in ("supported", "beta"):
                    supported.append(link)
                else:
                    unsupported.append(link)

            items.append(
                {
                    "name": name,
                    "acronym": prod_id,
                    "product_family": family,
                    "productFamily": family,
                    "description": descriptions,
                    "rank": rank,
                    "supported": supported,
                    "unsupported": unsupported,
                }
            )
        return items

    def iter_deliverables(self) -> Generator[Deliverable, None, None]:
        """Yield all deliverables defined in the portal XML."""
        for deliv_node in self.root.xpath("//deliverable"):
            yield Deliverable(deliv_node)
