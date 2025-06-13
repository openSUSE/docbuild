"""Module for Path related utilities."""

from pathlib import Path


def calc_max_len(files: tuple[Path | str, ...], last_parts: int = -2) -> int:
    """Calculate the maximum length of file names.

    Shortens the filenames to the last parts of the path (last_parts)
    for display purposes, ensuring the maximum length is even.

    :param files: A tuple of file paths to calculate lengths for.
    :param last_parts: Number of parts from the end of the path to consider.
       Needs to be negative to count from the end.
       By default, it considers the last two parts.
    :return: The maximum length of the shortened file names.

    .. code-block:: python

        >>> files = (Path('/path/to/file1.xml'), Path('/another/path/to/file2.xml'))
        >>> calc_max_len(files)
        30
    """
    lengths = []

    for filepath in files:
        path = Path(filepath)
        # Shorten the filename
        if len(path.parts) >= abs(last_parts):
            shortname = '/'.join(path.parts[last_parts:])
        else:
            shortname = str(filepath)
        lengths.append(len(shortname))

    max_length = max(lengths) if lengths else 0
    if max_length % 2:
        max_length += 1

    return max_length
