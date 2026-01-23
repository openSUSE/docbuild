import pytest

from docbuild.models.doctype import Doctype
from docbuild.utils.merge import _dedup_doctypes, merge_doctypes


def dt(s: str) -> Doctype:
    """Create a Doctype instance from a string."""
    # The fix: call the classmethod from_str directly, or use a keyword argument.
    return Doctype.from_str(s)


@pytest.mark.parametrize(
    "inputs,expected",
    [
        # Simple merge with wildcard
        (["sles/1,2/en-us", "sles/*/en-us"], ["sles/*/en-us"]),
        (["sles/1,2/*", "sles/1/en-us"], ["sles/1,2/*"]),
        # Non-overlapping products
        (["sles/1,2/en-us", "smart/1,2/en-us"], ["sles/1,2/en-us", "smart/1,2/en-us"]),
        # Wildcard in langs
        (["sles/1/en-us", "sles/2/*"], ["sles/1/en-us", "sles/2/*"]),
        (["sles/1/en-us,de-de", "sles/2/*"], ["sles/1/en-us,de-de", "sles/2/*"]),
        # Merging docsets and langs
        (["sles/1/en-us", "sles/2/en-us"], ["sles/1,2/en-us"]),
        (["sles/1/en-us", "sles/1/de-de"], ["sles/1/de-de,en-us"]),
        (["sles/1/en-us", "sles/1/en-us,de-de"], ["sles/1/de-de,en-us"]),
        # Wildcard absorbs specific
        (["sles/1/en-us", "sles/1/*"], ["sles/1/*"]),
        (["sles/1/*", "sles/1/en-us"], ["sles/1/*"]),
        # No merge for different lifecycle
        (["sles/1/en-us", "sles/1@beta/en-us"], ["sles/1/en-us", "sles/1@beta/en-us"]),
        # No merge for different product
        (["sles/1/en-us", "smart/1/en-us"], ["sles/1/en-us", "smart/1/en-us"]),
        # Idempotent
        (["sles/1/en-us"], ["sles/1/en-us"]),
        # Two identical doctypes
        (["sles/1/en-us", "sles/1/en-us"], ["sles/1/en-us"]),
        # Empty inputs
        ([], []),
        ## --- Some more realistic scenarios ---
        # 1
        (["sles/15-SP6/en-us", "sles/*/en-us"], ["sles/*/en-us"]),
        # 2
        (
            ["sles/15-SP5,15-SP4/*", "sles/15-SP4/en-us"],
            ["sles/15-SP4,15-SP5/*"],
        ),
        # 3
        (
            [
                "sles/15-SP6,15-SP5/en-us,de-de",
                "sles/*/en-us",
                "smart/network,container/en-us",
            ],
            [
                "sles/*/en-us",
                "sles/15-SP6,15-SP5/de-de",
                "smart/container,network/en-us",
            ],
        ),
        # 4
        (
            [
                "sles/15-SP6,15-SP5/en-us,de-de",
                "sles/15-SP4/zh-cn",
            ],
            ["sles/15-SP5,15-SP6/de-de,en-us", "sles/15-SP4/zh-cn"],
        ),
        # 5
        (
            ["sles/*/en-us", "sles/*/de-de", "sles/16-SP0/zh-cn"],
            ["sles/*/de-de,en-us", "sles/16-SP0/zh-cn"],
        ),
    ],
)
def test_merge_doctypes(inputs, expected):
    """Test merge_doctypes with various merging and wildcard scenarios."""
    real_dts = [dt(d) for d in inputs]
    results = merge_doctypes(*real_dts)
    assert results == [dt(d) for d in expected]


def test_dedup_doctypes_empty():
    assert _dedup_doctypes([]) == []


def test_dedup_doctypes_duplicates():
    d = dt("sles/1/en-us")
    result = _dedup_doctypes([d, d, d])
    assert result == [d]
    assert result != [d, d, d]


def test_dedup_doctypes_single():
    d = dt("sles/1/en-us")
    result = _dedup_doctypes([d])
    assert result == [d]


def test_dedup_doctypes_distinct():
    dt1 = dt("sles/1/en-us")
    dt2 = dt("sles/2/en-us")
    result = _dedup_doctypes([dt1, dt2])
    assert set(result) == {dt1, dt2}


def test_dedup_doctypes_order_preserved():
    """Test that _dedup_doctypes preserves the order of first occurrence."""
    dt1 = dt("sles/1/en-us")
    dt2 = dt("sles/2/en-us")
    dt3 = dt("sles/1/en-us")  # duplicate of dt1
    result = _dedup_doctypes([dt1, dt2, dt3])
    assert result == [dt1, dt2]


def test_dedup_doctypes_multiple_distinct():
    """Test _dedup_doctypes with three distinct Doctype objects."""
    dt1 = dt("sles/1/en-us")
    dt2 = dt("sles/2/en-us")
    dt3 = dt("sles/3/en-us")
    result = _dedup_doctypes([dt1, dt2, dt3])
    assert set(result) == {dt1, dt2, dt3}
