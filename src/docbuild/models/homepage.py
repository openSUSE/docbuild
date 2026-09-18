"""Pydantic models for the Portal Homepage JSON."""

from pathlib import Path
from typing import Self

from lxml import etree  # type: ignore
from pydantic import BaseModel, ConfigDict, Field


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
            name = ds.xpath("string(version)").strip()
            if name.startswith("Smart Docs: "):
                name = name.replace("Smart Docs: ", "")
            path = ds.get("path", "").lstrip("/")
            items.append(CategoryItem(name=name, path=f"{prefix}{path}"))
        return items

    @classmethod
    def _extract_products(cls, root: etree._Element | etree._ElementTree) -> list[ProductItem]:
        """Extract the main product list."""
        items = []
        special_ids = {"sbp", "trd", "smart"}
        for prod in root.xpath("/portal/product"):
            prod_id = prod.get("id", "")
            if prod_id in special_ids:
                continue

            name = prod.xpath("string(name)").strip()
            family = prod.get("family", "").strip()
            rank = prod.get("rank", "").strip()

            descriptions = []
            for d in prod.xpath("descriptions/desc"):
                lang = d.get("lang", "en-us")
                desc_text = " ".join(d.xpath("string()").split())
                descriptions.append(ProductDescription(
                    lang=lang,
                    default=(lang == "en-us"),
                    description=desc_text
                ))

            supported, unsupported = [], []
            for ds in prod.xpath("docset"):
                ds_name = ds.xpath("string(version)").strip() or ds.get("id", "")

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
    def from_portal(cls, root: etree._Element | etree._ElementTree) -> Self:
        """Extract homepage data from the Portal configuration."""
        hp = cls()

        for pf in root.xpath("/portal/productfamilies/item"):
            hp.product_families.append(ProductFamily(
                name=pf.xpath("string()").strip(),
                rank=pf.get("rank", ""),
                path=pf.get("path", "")
            ))

        hp.sbp_category_list = cls._extract_categories(root, "sbp", "/sbp/")
        hp.trd_partner_list = cls._extract_categories(root, "trd", "/trd/")
        hp.smart_doc_category_list = cls._extract_categories(root, "smart", "/smart/")
        hp.products_list = cls._extract_products(root)

        spotlight = root.xpath("/portal/spotlight")
        if spotlight:
            hp.spotlight_text = " ".join(spotlight[0].xpath("string()").split())
            hp.spotlight_link = spotlight[0].get("linkend", "")

        return hp

    def save(self, filepath: str | Path) -> None:
        """Serialize and save the model to a JSON file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(by_alias=True, indent=2))
