import pytest

from docbuild.config.merge import deep_merge


@pytest.mark.parametrize(
    "thedicts,expected",
    [
        # 1
        ([{"a": 1}, {"a": 2}], {"a": 2}),
        # 2
        ([{"a": 1, "b": 2}, {"a": 2}], {"a": 2, "b": 2}),
        # 3
        (
            [{"db": {"host": "localhost", "port": 1234}}, {"db": {"port": 5432}}],
            {"db": {"host": "localhost", "port": 5432}},
        ),
        #
    ],
)
def test_deep_merge(thedicts, expected):
    assert deep_merge(*thedicts) == expected
