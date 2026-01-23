import pytest

from docbuild.constants import ALLOWED_PRODUCTS
from docbuild.models.product import Product


@pytest.mark.parametrize("product", ALLOWED_PRODUCTS)
def test_valid_product(product):
    instance = Product[product]
    assert instance.value == product


def test_access_all_productname_constants():
    instance = Product.ALL
    assert instance.name == "ALL"
    assert instance.value == "*"
    assert Product["ALL"] == Product.ALL
    assert Product("*") == Product.ALL


def test_access_valid_productname_with_underscore():
    assert Product["sle_ha"] == Product.sle_ha


def test_access_valid_productname_with_dash():
    assert Product["sle-ha"] == Product.sle_ha


def test_access_valid_productname_uppercase_key():
    # Enum names are case-sensitive, this should fail
    with pytest.raises(KeyError):
        Product["SLE-HA"]


def test_enum_productvalue_integrity():
    assert Product.sle_ha.value == "sle-ha"


def test_invalid_key_raises_keyerror_with_hint():
    with pytest.raises(KeyError) as excinfo:
        Product["not-a-product"]
    assert "not-a-product" in str(excinfo.value)


def test_invalid_values_raise_value_error():
    with pytest.raises(ValueError) as excinfo:
        Product("unknown")

    assert "unknown" in str(excinfo.value)
