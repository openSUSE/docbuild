"""Pydantic models for the Portal Homepage JSON."""

from pathlib import Path
from typing import Self, cast

from lxml import etree  # type: ignore
from pydantic import BaseModel, ConfigDict, Field

from docbuild.models.deliverable import Deliverable


class ProductFamily(BaseModel):
    """Represents a product family on the homepage."""

    name: str
    rank: str
    path: str = ""


class ProductDescription(BaseModel):
    """Represents a localized description for a product."""

    lang: str
    default: bool = False
    description: str


class DocsetLink(BaseModel):
    """Represents a link to a docset."""

    name: str
    path: str


class ProductItem(BaseModel):
    """Represents an individual product listing on the homepage."""

    name: str
    acronym: str = Field(default="", serialization_alias="acronym")
    product_family: str = Field(serialization_alias="productFamily")
    description: list[ProductDescription] = Field(default_factory=list)
    rank: str
    supported: list[DocsetLink] = Field(default_factory=list)
    unsupported: list[DocsetLink] = Field(default_factory=list)


class CategoryItem(BaseModel):
    """Represents an item in SBP, TRD, or SmartDocs lists."""

    name: str
    path: str


class Homepage(BaseModel):
    """The root model for homepage.json."""

    model_config = ConfigDict(populate_by_name=True)

    product_families: list[ProductFamily] = Field(default_factory=list, serialization_alias="productFamilies")
    products_list: list[ProductItem] = Field(default_factory=list, serialization_alias="productsList")
    sbp_category_list: list[CategoryItem] = Field(default_factory=list, serialization_alias="sbpCategoryList")
    trd_partner_list: list[CategoryItem] = Field(default_factory=list, serialization_alias="trdPartnerList")
    smart_doc_category_list: list[CategoryItem] = Field(default_factory=list, serialization_alias="smartDocCategoryList")
    spotlight_text: str = Field(default="", serialization_alias="spotlightText")
    spotlight_link: str = Field(default="", serialization_alias="spotlightLink")

    @classmethod
    def _extract_categories(cls, root: etree._Element | etree._ElementTree, prod_id: str, prefix: str) -> list[CategoryItem]:
        """Extract specialized docset categories."""
        items = []
        for ds in root.xpath(f"/portal/product[@id='{prod_id}']/docset"):
            name = ds.xpath("string(./version)").strip()
            if name.startswith("Smart Docs: "):
                name = name.replace("Smart Docs: ", "")
            path = ds.get("path", "").lstrip("/")
            items.append(CategoryItem(name=name, path=f"{prefix}{path}"))
        return items

    @classmethod
    def _extract_products(cls, root: etree._Element | etree._ElementTree, family_map: dict[str, str]) -> list[ProductItem]:
        """Extract the main product list."""
        items = []
        special_ids = {"sbp", "trd", "smart"}
        for prod in root.xpath("/portal/product"):
            prod_id = prod.get("id", "")
            if prod_id in special_ids:
                continue

            name = prod.xpath("string(name)").strip()

            # Map the ID back to the human-readable string using our map
            family_id = str(prod.get("family") or "").strip()
            family = str(family_map.get(family_id, family_id) or "")

            rank = prod.get("rank", "").strip()

            descriptions = []
            for d in prod.xpath("descriptions/desc"):
                lang = d.get("lang", "en-us")
                # Extract ONLY the title, as requested
                desc_text = " ".join(d.xpath("string(./title)").split())
                if desc_text:
                    descriptions.append(ProductDescription(
                        lang=lang,
                        default=(lang == "en-us"),
                        description=desc_text
                    ))

            supported, unsupported = [], []
            for ds in prod.xpath("docset"):
                # Ensure we only grab the immediate <version> tag, not nested ones!
                ds_name = ds.xpath("string(./version)").strip() or ds.get("id", "")

                ds_path = ds.get("path", "")
                if not ds_path.startswith("/"):
                    ds_path = f"/{prod_id}/{ds_path}"
                if not ds_path.endswith("/"):
                    ds_path += "/"

                link = DocsetLink(name=ds_name, path=ds_path)

                if ds.get("lifecycle", "supported") in ("supported", "beta"):
                    supported.append(link)
                else:
                    unsupported.append(link)

            items.append(ProductItem(
                name=name,
                acronym=prod_id,
                product_family=family,
                description=descriptions,
                rank=rank,
                supported=supported,
                unsupported=unsupported
            ))
        return items

    @classmethod
    def _resolve_spotlight_target(cls, target: etree._Element, linkend: str, text: str) -> tuple[str, str]:
        """Resolve the tag-specific logic for a spotlight target."""
        if target.tag == "product":
            link = f"/{target.get('id', '')}/"
            if not text:
                text = target.xpath("string(name)").strip()
            return text, link

        if target.tag == "docset":
            prod_node = target.getparent()
            prod_id = prod_node.get("id", "") if prod_node is not None else ""
            ds_path = target.get("path", "")

            link = f"/{prod_id}/{ds_path}".replace("//", "/")
            if not link.endswith("/"):
                link += "/"

            if not text:
                prod_name = prod_node.xpath("string(name)").strip() if prod_node is not None else ""
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
                    ds_version = ds_node.xpath("string(./version)").strip() if ds_node is not None else ""
                    text = f"{prod_name} {ds_version}".strip()
                return text, link
            except Exception:
                pass

        return text, f"/{linkend}/"

    @classmethod
    def _extract_spotlight(cls, root: etree._Element | etree._ElementTree) -> tuple[str, str]:
        """Extract spotlight text and link from the Portal configuration."""
        spotlights = root.xpath("/portal/spotlight")
        if not spotlights:
            return "", ""

        s_node = spotlights[0]
        linkend = s_node.get("linkend", "")
        text = " ".join(s_node.xpath("string()").split())

        if not linkend:
            return text, ""

        target_nodes = root.xpath(f"//*[@id='{linkend}']")
        if not target_nodes:
            return text, linkend

        return cls._resolve_spotlight_target(target_nodes[0], linkend, text)

    @classmethod
    def from_portal(cls, portal: object) -> Self:
        """Extract homepage data from the Portal configuration."""
        root = cast(etree._Element, getattr(portal, "node", portal))
        hp = cls()

        family_map = {}
        for rank_idx, pf in enumerate(root.xpath("/portal/productfamilies/item"), start=1):
            item_id = pf.get("id", "")
            item_text = pf.xpath("string()").strip()
            if item_id:
                family_map[item_id] = item_text

            hp.product_families.append(ProductFamily(
                name=item_text,
                rank=pf.get("rank", "").strip() or str(rank_idx),
                path=pf.get("path", "")
            ))

        hp.sbp_category_list = cls._extract_categories(root, "sbp", "/sbp/")
        hp.trd_partner_list = cls._extract_categories(root, "trd", "/trd/")
        hp.smart_doc_category_list = cls._extract_categories(root, "smart", "/smart/")
        hp.products_list = cls._extract_products(root, family_map)

        hp.spotlight_text, hp.spotlight_link = cls._extract_spotlight(root)

        return hp

    def save(self, filepath: str | Path) -> None:
        """Serialize and save the model to a JSON file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(by_alias=True, indent=2))
