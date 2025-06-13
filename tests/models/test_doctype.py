import pytest

# from docbuild.constants import ALLOWED_LIFECYCLES
from docbuild.models.doctype import Doctype
from docbuild.models.language import LanguageCode
from docbuild.models.lifecycle import LifecycleFlag
from docbuild.models.product import Product


def test_valid_doctype():
    doctype = Doctype(
        product='sles', docset='15-SP6', lifecycle='supported', langs=['en-us']
    )
    assert doctype.product == Product.sles
    assert doctype.docset == ['15-SP6']
    assert doctype.lifecycle == LifecycleFlag.supported
    assert doctype.langs == [LanguageCode('en-us')]


def test_str_in_doctype():
    doctype = Doctype(
        product='sles',
        docset='15-SP6',
        lifecycle='supported',
        langs=['en-us'],
    )
    assert str(doctype) == 'sles/15-SP6@supported/en-us'


def test_repr_in_doctype():
    doctype = Doctype(
        product='sles',
        docset='15-SP6',
        lifecycle='supported',
        langs=['en-us'],
    )
    assert repr(doctype) == (
        "Doctype(product='sles', docset=[15-SP6], lifecycle='supported', langs=[en-us])"
    )


def test_string_langs_in_doctype():
    doctype = Doctype(
        product='sles',
        docset='15-SP6',
        lifecycle='supported',
        langs='en-us',
    )
    assert doctype.langs == [LanguageCode('en-us')]


def test_multiplestrings_langs_in_doctype():
    doctype = Doctype(
        product='sles',
        docset='15-SP6',
        lifecycle='supported',
        langs='en-us,de-de',
    )
    assert doctype.langs == [LanguageCode('de-de'), LanguageCode('en-us')]


@pytest.mark.parametrize(
    'string,expected',
    [
        (
            'sles/15-SP6/en-us',
            (
                Product.sles,
                ['15-SP6'],
                LifecycleFlag.unknown,
                [LanguageCode('en-us')],
            ),
        ),
        (
            'sles/15-SP5,15-SP6/en-us',
            (
                Product.sles,
                ['15-SP5', '15-SP6'],
                LifecycleFlag.unknown,
                [LanguageCode('en-us')],
            ),
        ),
        (
            '//en-us',
            (Product.ALL, ['*'], LifecycleFlag.unknown, [LanguageCode('en-us')]),
        ),
        (
            '*//en-us',
            (Product.ALL, ['*'], LifecycleFlag.unknown, [LanguageCode('en-us')]),
        ),
        (
            '/*/en-us',
            (Product.ALL, ['*'], LifecycleFlag.unknown, [LanguageCode('en-us')]),
        ),
        (
            '*/*/en-us',
            (Product.ALL, ['*'], LifecycleFlag.unknown, [LanguageCode('en-us')]),
        ),
        (
            '*/@beta/en-us',
            (Product.ALL, ['*'], LifecycleFlag.beta, [LanguageCode('en-us')]),
        ),
        (
            '*/*@beta/en-us',
            (Product.ALL, ['*'], LifecycleFlag.beta, [LanguageCode('en-us')]),
        ),
        (
            'sles/*@beta/en-us',
            (Product.sles, ['*'], LifecycleFlag.beta, [LanguageCode('en-us')]),
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
        Doctype.from_str('nonsense')


def test_contains_with_doctypes():
    dt1 = Doctype.from_str('sles/15-SP6/en-us')
    dt2 = Doctype.from_str('sles/*/en-us')
    assert dt1 in dt2


def test_eq_with_doctypes():
    dt1 = Doctype.from_str('sles/15-SP6/en-us')
    dt2 = Doctype.from_str('sles/15-SP6/en-us')
    assert dt1 == dt2


def test_lt_with_doctypes():
    dt1 = Doctype.from_str('sles/15-SP6/en-us')
    dt2 = Doctype.from_str('sles/15-SP7/en-us')
    assert dt1 < dt2


def test_compare_with_doctype_and_invalid_type():
    dt = Doctype.from_str('sles/15-SP6/en-us')
    result = dt.__contains__('not-a-doctype')  # type: ignore
    assert result is NotImplemented


def test_eq_with_doctype_and_invalid_type():
    dt = Doctype.from_str('sles/15-SP6/en-us')
    result = dt.__eq__('not-a-doctype')  # type: ignore
    assert result == NotImplemented


def test_lt_with_doctype_and_invalid_type():
    dt = Doctype.from_str('sles/15-SP6/en-us')
    result = dt.__lt__('not-a-doctype')  # type: ignore
    assert result == NotImplemented


def test_hash_with_doctype():
    dt1 = Doctype.from_str('sles/15-SP6/en-us')
    dt2 = Doctype.from_str('sles/15-SP6/en-us')
    assert hash(dt1) == hash(dt2)


def test_coerce_lifecycle_to_doctype():
    dt1 = Doctype(
        product='sles',
        docset='15-SP5',
        lifecycle=LifecycleFlag.supported,
        langs='en-us',
    )
    assert dt1.lifecycle == LifecycleFlag.supported


def test_sorted_docsets_in_doctype():
    dt1 = Doctype.from_str('sles/15-SP6,15-SP2,16-SP0/en-us')
    assert dt1.docset == ['15-SP2', '15-SP6', '16-SP0']


def test_sorted_langs_in_doctype():
    dt1 = Doctype.from_str('sles/15-SP6/en-us,zh-cn,de-de')
    assert dt1.langs == [
        'de-de',
        'en-us',
        'zh-cn',
    ]


def test_sorted_docsets_in_doctype_instantiation():
    dt1 = Doctype(
        product='sles',
        docset=['16-SP0', '15-SP7'],
        lifecycle=LifecycleFlag.supported,
        langs='en-us',
    )
    assert dt1.docset == ['15-SP7', '16-SP0']


def test_sorted_langs_in_doctype_instantiation():
    langs = ['en-us', 'de-de']
    dt1 = Doctype(
        product='sles',
        docset='15-SP6',
        lifecycle=LifecycleFlag.supported,
        langs=langs,
    )
    assert dt1.langs == sorted([LanguageCode(lang) for lang in langs])
