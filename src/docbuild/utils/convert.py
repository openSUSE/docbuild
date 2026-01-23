"""Convert utility functions."""


def convert2bool(value: str | bool) -> bool:
    """Convert a string or bool into a boolean.

    :param value: The value to convert to a boolean. Valid values are:

        * True, "yes", "true", "1", "on" for True and
        * False, "no", "false", "0", "off" for False.
    :return: The boolean value
    :raises ValueError: If the value cannot be converted to a valid boolean
    """
    mapping = {
        "yes": True,
        "true": True,
        "1": True,
        "on": True,
        "no": False,
        "false": False,
        "0": False,
        "off": False,
    }
    value = str(value).lower()
    if value in mapping:
        return mapping[value]

    raise ValueError(f"Invalid boolean value: {value}")
