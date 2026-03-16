import pytest

from docbuild.config.merge import deep_merge


@pytest.mark.parametrize(
    "thedicts,expected",
    [
        #
        pytest.param([], {}, id="empty"),
        #
        pytest.param([{"a": 1}, {"a": 2}], {"a": 2}, id="overwrite_scalar"),
        #
        pytest.param(
            [{"a": 1, "b": 2}, {"a": 2}],
            {"a": 2, "b": 2},
            id="merge_keys_overwrite_scalar",
        ),
        #
        pytest.param(
            [{"db": {"host": "localhost", "port": 1234}}, {"db": {"port": 5432}}],
            {"db": {"host": "localhost", "port": 5432}},
            id="nested_dicts_recursive",
        ),
        #
        pytest.param(
            [{"a": [1, 2]}, {"a": [3, 4]}],
            {"a": [1, 2, 3, 4]},
            id="list_concatenation",
        ),
        #
        pytest.param(
            [{"t": (1, 2)}, {"t": (3, 4)}],
            {"t": (1, 2, 3, 4)},
            id="tuple_concatenation",
        ),
        #
        pytest.param(
            [{"a": [1, 2]}, {"a": 3}],
            {"a": 3},
            id="overwrite_list_with_scalar",
        ),
        #
        pytest.param(
            [{"a": 1}, {"a": [2, 3]}],
            {"a": [2, 3]},
            id="overwrite_scalar_with_list",
        ),
        #
        pytest.param(
            [{"x": {"l": ["a"]}}, {"x": {"l": ["b"]}}],
            {"x": {"l": ["a", "b"]}},
            id="nested_list_concatenation",
        ),
        #
        pytest.param(
            [{"a": [{"x": 1}]}, {"a": [{"y": 2}]}],
            {"a": [{"x": 1}, {"y": 2}]},
            id="list_of_dicts_concatenation",
        ),
        #
        pytest.param(
            [{"s": {1, 2}}, {"s": {3, 4}}],
            {"s": {1, 2, 3, 4}},
            id="set_union",
        ),
        #
        pytest.param(
            [{"s": {1, 2}}, {"s": {2, 3}}],
            {"s": {1, 2, 3}},
            id="set_union_overlap",
        ),
    ],
)
def test_deep_merge(thedicts, expected):
    assert deep_merge(*thedicts) == expected


def test_deep_merge_is_truly_deep():
    d1 = {"nested": [1, 2], "deep": {"a": 1}}
    d2 = {}
    merged = deep_merge(d1, d2)

    # Modify result
    merged["nested"].append(3)
    merged["deep"]["b"] = 2

    # Assert original is untouched
    assert d1["nested"] == [1, 2]
    assert "b" not in d1["deep"]


def test_three_way_merge():
    d1 = {"a": 1}
    d2 = {"b": 2}
    d3 = {"c": 3}
    assert deep_merge(d1, d2, d3) == {"a": 1, "b": 2, "c": 3}


def test_deep_merge_inputs_remain_independent():
    # Verify that subsequent dictionaries (not just the first) are also treated as immutable sources
    d1 = {}
    d2 = {"a": [1, 2], "b": {"x": 1}}
    merged = deep_merge(d1, d2)

    # Modify result
    merged["a"].append(3)
    merged["b"]["y"] = 2

    # Assert input d2 is untouched
    assert d2["a"] == [1, 2]
    assert "y" not in d2["b"]


def test_deep_merge_return_type():
    class MyMap(dict):
        pass

    m1 = MyMap({"a": 1})
    m2 = {"b": 2}
    result = deep_merge(m1, m2)

    assert isinstance(result, dict)
    assert not isinstance(result, MyMap)
    assert result == {"a": 1, "b": 2}


def test_deep_merge_converts_nested_custom_mapping_to_dict():
    class MyMap(dict):
        pass

    # MyMap instance nested inside a standard dict
    d1 = {"nested": MyMap({"a": 1})}
    d2 = {"nested": {"b": 2}}

    result = deep_merge(d1, d2)

    # Check that merge happened correctly
    assert result == {"nested": {"a": 1, "b": 2}}

    # Check that the nested dictionary is a plain dict, not MyMap
    # This verifies that the line `existing = dict(existing)` was executed
    # and the result contains the converted dict.
    assert type(result["nested"]) is dict
    assert not isinstance(result["nested"], MyMap)

    # Verify original d1 is untouched
    assert isinstance(d1["nested"], MyMap)
    assert d1["nested"] == {"a": 1}
