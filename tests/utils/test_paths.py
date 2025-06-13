from docbuild.utils.paths import calc_max_len
from pathlib import Path


def test_calc_max_len():
    """Test the calc_max_len function."""
    files = (Path('/path/to/file1.xml'), Path('/another/path/to/file2.xml'))

    # Test with default last_parts
    max_len_default = calc_max_len(files)
    assert max_len_default > 0

    # Test with specific last_parts
    max_len_last_parts = calc_max_len(files, last_parts=-1)
    assert max_len_last_parts > 0

    # Test with empty tuple
    max_len_empty = calc_max_len(())
    assert max_len_empty == 0


def test_calc_max_len_even_length():
    """Test that the maximum length returned is even."""
    files = (Path('/path/to/file1.xml'), Path('/another/path/to/file2.xml'))

    max_len = calc_max_len(files)
    assert max_len % 2 == 0, f"Expected even length, got {max_len}"


def test_calc_max_len_short_path():
    """Test calc_max_len with a path that has fewer parts than last_parts."""
    files = (Path('/file.xml'), Path('/anotherfile.xml'))

    max_len = calc_max_len(files, last_parts=-3)
    assert max_len > 0, "Expected a positive maximum length."
    assert max_len == len('/anotherfile.xml'), (
        'Expected the full path length for short paths.'
    )

