from lxml import etree  # type: ignore
import pytest

# from docbuild.constants import ALLOWED_LIFECYCLES
from docbuild.models.doctype import Doctype
from docbuild.models.language import LanguageCode
from docbuild.models.lifecycle import LifecycleFlag
from docbuild.models.product import Product


def test_valid_doctype():
    doctype = Doctype(
        product="sles", docset="15-SP6", lifecycle="supported", langs=["en-us"]
    )
    assert doctype.product == Product.sles
    assert doctype.docset == ["15-SP6"]
    assert doctype.lifecycle == LifecycleFlag.supported
    assert doctype.langs == [LanguageCode(language="en-us")]


def test_str_in_doctype():
    doctype = Doctype(
        product="sles",
        docset="15-SP6",
        lifecycle="supported",
        langs=["en-us"],
    )
    assert str(doctype) == "sles/15-SP6@supported/en-us"


def test_repr_in_doctype():
    doctype = Doctype(
        product="sles",
        docset="15-SP6",
        lifecycle="supported",
        langs=["en-us"],
    )
    assert repr(doctype) == (
        "Doctype(product='sles', docset=[15-SP6], lifecycle='supported', langs=[en-us])"
    )


@pytest.mark.parametrize("langs,expected",
    [
        ({}, [LanguageCode(language="en-us")]),
        ({"langs": "de-de"}, [LanguageCode(language="de-de")]),
        ({"langs": "en-us,de-de"}, [LanguageCode(language="de-de"), LanguageCode(language="en-us")]),
    ]
)
def test_string_langs_in_doctype(langs, expected):
    doctype = Doctype(
        product="sles",
        docset="15-SP6",
        lifecycle="supported",
        **langs,
    )
    assert doctype.langs == expected


def test_multiplestrings_langs_in_doctype():
    doctype = Doctype(
        product="sles",
        docset="15-SP6",
        lifecycle="supported",
        langs="en-us,de-de",
    )
    assert doctype.langs == [
        LanguageCode(language="de-de"),
        LanguageCode(language="en-us"),
    ]


@pytest.mark.parametrize("lifecycle,expected", [
    # 1 optional lifecycle, default to unknown
    ({}, LifecycleFlag.unknown),
    # 2
    ({"lifecycle": "supported"}, LifecycleFlag.supported),
])
def test_lifecycle_in_doctype(lifecycle, expected):
    doctype = Doctype(
        product="sles",
        docset="15-SP6",
        **lifecycle,
        langs="en-us",
    )
    assert doctype.lifecycle == expected


@pytest.mark.parametrize(
    "string,expected",
    [
        (
            "sles/15-SP6/en-us",
            (
                Product.sles,
                ["15-SP6"],
                LifecycleFlag.unknown,
                [LanguageCode(language="en-us")],
            ),
        ),
        (
            "sles/15-SP5,15-SP6/en-us",
            (
                Product.sles,
                ["15-SP5", "15-SP6"],
                LifecycleFlag.unknown,
                [LanguageCode(language="en-us")],
            ),
        ),
        (
            "//en-us",
            (
                Product.ALL,
                ["*"],
                LifecycleFlag.unknown,
                [LanguageCode(language="en-us")],
            ),
        ),
        (
            "/*/*/en-us",
            (
                Product.ALL,
                ["*"],
                LifecycleFlag.unknown,
                [LanguageCode(language="en-us")],
            ),
        ),
        (
            "*//en-us",
            (
                Product.ALL,
                ["*"],
                LifecycleFlag.unknown,
                [LanguageCode(language="en-us")],
            ),
        ),
        (
            "*/*/en-us",
            (
                Product.ALL,
                ["*"],
                LifecycleFlag.unknown,
                [LanguageCode(language="en-us")],
            ),
        ),
        (
            "*/@beta/en-us",
            (Product.ALL, ["*"], LifecycleFlag.beta, [LanguageCode(language="en-us")]),
        ),
        (
            "*/*@beta/en-us",
            (Product.ALL, ["*"], LifecycleFlag.beta, [LanguageCode(language="en-us")]),
        ),
        (
            "sles/*@beta/en-us",
            (Product.sles, ["*"], LifecycleFlag.beta, [LanguageCode(language="en-us")]),
        ),
        (
            "/sles/*@beta/en-us",
            (Product.sles, ["*"], LifecycleFlag.beta, [LanguageCode(language="en-us")]),
        ),
        (
            "/*/*@supported/*",
            (Product.ALL, ["*"], LifecycleFlag.supported, [LanguageCode(language="*")]),
        ),
        (
            "/*/*/*",
            (Product.ALL, ["*"], LifecycleFlag.unknown, [LanguageCode(language="*")]),
        ),
    ],
)
def test_valid_string_from_string(string, expected):
    doctype = Doctype.from_str(string)
    product, docset, lifecycle, langs = expected
    assert doctype.product == product
    assert doctype.docset == docset
    assert doctype.lifecycle == lifecycle
    assert doctype.langs == langs


def test_invalid_string_from_string():
    with pytest.raises(ValueError):
        Doctype.from_str("nonsense")


@pytest.mark.parametrize(
    "string, expected_langs",
    [
        ("sles/16.0", [LanguageCode(language="en-us")]),
        ("sles/16.0@supported", [LanguageCode(language="en-us")]),
        ("*/15-SP6", [LanguageCode(language="en-us")]),
    ],
    ids=["product_docset", "product_docset_lifecycle", "wildcard_product_docset"],
)
def test_missing_lang_defaults_to_en_us(string, expected_langs):
    """Omitting the language segment should default to 'en-us'."""
    doctype = Doctype.from_str(string)
    assert doctype.langs == expected_langs


def test_contains_with_doctypes():
    dt1 = Doctype.from_str("sles/15-SP6/en-us")
    dt2 = Doctype.from_str("sles/*/en-us")
    assert dt1 in dt2


def test_eq_with_doctypes():
    dt1 = Doctype.from_str("sles/15-SP6/en-us")
    dt2 = Doctype.from_str("sles/15-SP6/en-us")
    assert dt1 == dt2


def test_lt_with_doctypes():
    dt1 = Doctype.from_str("sles/15-SP6/en-us")
    dt2 = Doctype.from_str("sles/15-SP7/en-us")
    assert dt1 < dt2


def test_compare_with_doctype_and_invalid_type():
    dt = Doctype.from_str("sles/15-SP6/en-us")
    result = dt.__contains__("not-a-doctype")  # type: ignore
    assert result is NotImplemented


def test_eq_with_doctype_and_invalid_type():
    dt = Doctype.from_str("sles/15-SP6/en-us")
    result = dt.__eq__("not-a-doctype")  # type: ignore
    assert result == NotImplemented


def test_lt_with_doctype_and_invalid_type():
    dt = Doctype.from_str("sles/15-SP6/en-us")
    result = dt.__lt__("not-a-doctype")  # type: ignore
    assert result == NotImplemented


def test_hash_with_doctype():
    dt1 = Doctype.from_str("sles/15-SP6/en-us")
    dt2 = Doctype.from_str("sles/15-SP6/en-us")
    assert hash(dt1) == hash(dt2)


def test_iter_returns_doctype_items():
    doctype = Doctype.from_str("sles/15-SP6,15-SP7/en-us,de-de")

    items = list(doctype.iter_doctypes())

    assert items
    assert all(isinstance(item, Doctype) for item in items)
    assert all(item.product == doctype.product for item in items)
    assert all(item.lifecycle == doctype.lifecycle for item in items)
    assert all(len(item.docset) == 1 for item in items)
    assert all(len(item.langs) == 1 for item in items)


def test_iter_is_docset_major_order():
    doctype = Doctype.from_str("sles/15-SP6,15-SP7/en-us,de-de")

    result = [
        f"{item.product.acronym}/{item.docset[0]}/{item.langs[0].language}"
        for item in doctype.iter_doctypes()
    ]

    assert result == [
        "sles/15-SP6/de-de",
        "sles/15-SP6/en-us",
        "sles/15-SP7/de-de",
        "sles/15-SP7/en-us",
    ]


def test_iter_wildcard_docset_expands_with_portal_root():
    root = etree.fromstring(
        """
        <portal>
           <product id="sles">
              <docset path="15-SP6"><resources><locale lang="en-us"/><locale lang="de-de"/></resources></docset>
              <docset path="16.0"><resources><locale lang="en-us"/></resources></docset>
           </product>
        </portal>
        """,
    )

    doctype = Doctype.from_str("sles/*/*")
    result = [
        f"{item.product.acronym}/{item.docset[0]}/{item.langs[0].language}"
        for item in doctype.iter_doctypes(portal_root=root)
    ]

    assert result == [
        "sles/15-SP6/de-de",
        "sles/15-SP6/en-us",
        "sles/16.0/en-us",
    ]


def test_coerce_lifecycle_to_doctype():
    dt1 = Doctype(
        product="sles",
        docset=["15-SP5"],
        lifecycle=LifecycleFlag.supported,
        langs=["en-us"],
    )
    assert dt1.lifecycle == LifecycleFlag.supported


def test_sorted_docsets_in_doctype():
    dt1 = Doctype.from_str("sles/15-SP6,15-SP2,16-SP0/en-us")
    assert dt1.docset == ["15-SP2", "15-SP6", "16-SP0"]


def test_sorted_langs_in_doctype():
    dt1 = Doctype.from_str("sles/15-SP6/en-us,zh-cn,de-de")
    assert dt1.langs == [
        LanguageCode(language="de-de"),
        LanguageCode(language="en-us"),
        LanguageCode(language="zh-cn"),
    ]


def test_iter_wildcard_remains_symbolic_without_portal_root():
    doctype = Doctype.from_str("sles/*/en-us")
    result = [
        f"{item.product.acronym}/{item.docset[0]}/{item.langs[0].language}"
        for item in doctype.iter_doctypes()
    ]

    assert result == ["sles/*/en-us"]


def test_iter_wildcard_product_expands_with_portal_root():
    root = etree.fromstring(
        """
        <portal>
            <product id="sles">
            <docset path="15-SP6"><resources><locale lang="en-us"/></resources></docset>
            </product>
            <product id="smart">
            <docset path="2.0"><resources><locale lang="en-us"/></resources></docset>
            </product>
        </portal>
        """,
    )

    doctype = Doctype.from_str("*/*/en-us")
    result = [
        f"{item.product.acronym}/{item.docset[0]}/{item.langs[0].language}"
        for item in doctype.iter_doctypes(portal_root=root)
    ]

    assert result == [
        "sles/15-SP6/en-us",
        "smart/2.0/en-us",
    ]


def test_sorted_docsets_in_doctype_instantiation():
    dt1 = Doctype(
        product="sles",
        docset=["16-SP0", "15-SP7"],
        lifecycle=LifecycleFlag.supported,
        langs=["en-us"],
    )
    assert dt1.docset == ["15-SP7", "16-SP0"]


def test_sorted_langs_in_doctype_instantiation():
    langs = ["en-us", "de-de"]
    dt1 = Doctype(
        product="sles",
        docset="15-SP6",
        lifecycle=LifecycleFlag.supported,
        langs=langs,
    )
    assert dt1.langs == sorted([LanguageCode(language=lang) for lang in langs])


@pytest.mark.parametrize(
    "string_or_doctype,xpath",
    [
        # 1: product + one docset + a single language
        (
            "sles/15-SP6/en-us",
            (
                "product[@id='sles']"
                "/docset[@path='15-SP6']"
                "/resources/locale[@lang='en-us']"
            ),
        ),
        # 2: product + all docsets + a single language
        (
            "sles//en-us",
            ("product[@id='sles']/docset/resources/locale[@lang='en-us']"),
        ),
        # 3: product + one docset + one lifecycle + multiple languages
        (
            "sles/15-SP6@supported/en-us,de-de",
            (
                "product[@id='sles']"
                "/docset[@path='15-SP6'][@lifecycle='supported']"
                "/resources/locale[@lang='de-de' or @lang='en-us']"
            ),
        ),
        # 4: product + one docset + multiple lifecycles + one language
        (
            "sles/15-SP7@supported,beta/de-de",
            (
                "product[@id='sles']"
                "/docset[@path='15-SP7'][@lifecycle='supported' or @lifecycle='beta']"
                "/resources/locale[@lang='de-de']"
            ),
        ),
        # 5: product + one docset + multiple lifecycles + all languages
        (
            "sles/15-SP6@supported/*",
            (
                "product[@id='sles']"
                "/docset[@path='15-SP6'][@lifecycle='supported']"
                "/resources/locale"
            ),
        ),
        # 6: many products + many docsets + many lifecycles + English
        ("//en-us", "product/docset/resources/locale[@lang='en-us']"),
        # 7: all products, docsets, lifecycles, and languages
        ("//*", "product/docset/resources/locale"),
        # 8: fallback to English for empty language lists
        (
            Doctype(product="sles", docset=["15-SP6"], langs=[]),
            "product[@id='sles']/docset[@path='15-SP6']/resources/locale[@lang='en-us']",
        ),
        # 9: explicit language plus wildcard means all languages
        (
            Doctype(product="sles", docset=["15-SP6"], langs=["en-us", "*"]),
            "product[@id='sles']/docset[@path='15-SP6']/resources/locale",
        ),
    ],
)
def test_xpath_in_doctype(string_or_doctype, xpath):
    """Test the XPath extraction from a Doctype."""
    if isinstance(string_or_doctype, str):
        doctype = Doctype.from_str(string_or_doctype)
    else:
        doctype = string_or_doctype
    assert xpath == doctype.xpath()


def test_product_xpath_segment():
    """Test the product_xpath_segment method."""
    # Test with all products (*)
    dt_all = Doctype.from_str("*/15-SP6/en-us")
    assert dt_all.product_xpath_segment() == "product"

    # Test with a specific product
    dt_specific = Doctype.from_str("sles/15-SP6/en-us")
    assert dt_specific.product_xpath_segment() == "product[@id='sles']"


@pytest.mark.parametrize(
    "string,xpath",
    [
        # 1
        ("sles/*/en-us", "docset"),
        # 2
        ("sles/15-SP6/en-us", "docset[@path='15-SP6']"),
        # 3
        ("sles/15-SP6,15-SP7/en-us", "docset[@path='15-SP6' or @path='15-SP7']"),
    ],
)
def test_docset_xpath_segment(string, xpath):
    """Test the docset_xpath_segment method."""
    # Test with all docsets (*)
    dt_all = Doctype.from_str(string)
    assert dt_all.docset_xpath_segment() == xpath


def test_docset_xpath_segment_with_argument():
    """Test the docset_xpath_segment method with a specific argument."""
    dt = Doctype.from_str("sles/15-SP6/en-us")
    assert dt.docset_xpath_segment("16.0") == "docset[@path='16.0']"
    assert dt.docset_xpath_segment("*") == "docset"
