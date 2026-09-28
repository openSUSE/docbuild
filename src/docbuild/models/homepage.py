"""Pydantic models for the Portal Homepage JSON."""

from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from ..config.xml.portal import PortalConfig


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

    product_families: list[ProductFamily] = Field(
        default_factory=list, serialization_alias="productFamilies"
    )
    products_list: list[ProductItem] = Field(
        default_factory=list, serialization_alias="productsList"
    )
    sbp_category_list: list[CategoryItem] = Field(
        default_factory=list, serialization_alias="sbpCategoryList"
    )
    trd_partner_list: list[CategoryItem] = Field(
        default_factory=list, serialization_alias="trdPartnerList"
    )
    smart_doc_category_list: list[CategoryItem] = Field(
        default_factory=list, serialization_alias="smartDocCategoryList"
    )
    spotlight_text: str = Field(default="", serialization_alias="spotlightText")
    spotlight_link: str = Field(default="", serialization_alias="spotlightLink")

    @classmethod
    def from_portal(cls, portal_config: PortalConfig) -> Self:
        """Extract homepage data from the PortalConfig."""
        hp = cls()

        # Load standard properties mapping dictionary lists to Pydantic objects
        hp.product_families = [
            ProductFamily(**pf) for pf in portal_config.productfamilies
        ]

        hp.sbp_category_list = [
            CategoryItem(**c) for c in portal_config.get_categories("sbp", "/sbp/")
        ]
        hp.trd_partner_list = [
            CategoryItem(**c) for c in portal_config.get_categories("trd", "/trd/")
        ]
        hp.smart_doc_category_list = [
            CategoryItem(**c) for c in portal_config.get_categories("smart", "/smart/")
        ]

        hp.products_list = [ProductItem(**p) for p in portal_config.products]

        spotlight = portal_config.spotlight
        hp.spotlight_text = spotlight["spotlightText"]
        hp.spotlight_link = spotlight["spotlightLink"]

        return hp

    def save(self, filepath: str | Path) -> None:
        """Serialize and save the model to a JSON file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(by_alias=True, indent=2))
