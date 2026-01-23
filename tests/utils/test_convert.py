import pytest

from docbuild.utils import convert


@pytest.mark.parametrize(
    "input_value,expected_output",
    [
        (True, True),
        ("yes", True),
        ("true", True),
        ("1", True),
        ("on", True),
        (False, False),
        ("no", False),
        ("false", False),
        ("0", False),
        ("off", False),
    ],
)
def test_convert2bool(input_value, expected_output):
    """Test the convert2bool function."""
    assert convert.convert2bool(input_value) is expected_output


def test_convert2bool_invalid():
    """Test the convert2bool function with invalid input."""
    with pytest.raises(ValueError, match="Invalid boolean value: invalid"):
        convert.convert2bool("invalid")
