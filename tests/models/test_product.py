from typing import cast

import pytest

from docbuild.models.product import Product


@pytest.mark.parametrize(
    "product",
    [member.acronym for member in Product if member is not Product.ALL],
)
def test_valid_product(product):
    instance = cast(Product, Product[product])
    assert instance.acronym == product


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
    assert Product.sle_ha.value == "SUSE Linux Enterprise High Availability"
    assert Product.sle_ha.acronym == "sle-ha"


def test_access_product_from_acronym_value():
    assert Product("sle-ha") == Product.sle_ha


def test_missing_wildcard_branch_returns_all():
    # Product("*") resolves directly and does not call _missing_.
    # Call _missing_ explicitly to cover its wildcard branch.
    assert Product._missing_("*") == Product.ALL


def test_missing_non_string_input_raises_value_error():
    with pytest.raises(ValueError) as excinfo:
        Product._missing_(42)

    assert "42" in str(excinfo.value)


def test_invalid_key_raises_keyerror_with_hint():
    with pytest.raises(KeyError) as excinfo:
        Product["not-a-product"]
    assert "not-a-product" in str(excinfo.value)


def test_invalid_values_raise_value_error():
    with pytest.raises(ValueError) as excinfo:
        Product("unknown")

    assert "unknown" in str(excinfo.value)
