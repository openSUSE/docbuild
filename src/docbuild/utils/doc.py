"""Utility decorators for docbuild."""

from collections.abc import Callable
import functools
from typing import Any, ParamSpec, TypeVar

T = TypeVar("T", bound=Callable[..., object])
P = ParamSpec("P")
R = TypeVar("R")
FormatValue = str | int | bool


class SafeDict(dict):
    """A 'safe' dictionary."""

    def __missing__(self, key: str) -> str:
        """Let missing keys stay as keys."""
        return "{" + key + "}"


def docstring(
    template: str | None = None,
    **kwargs: Any,  # noqa: ANN401
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Replace placeholders in docstring.

    This decorator formats the docstring of the decorated function
    (or an explicit template string) by replacing placeholders
    with the provided keyword arguments. If a placeholder does not
    have a corresponding keyword argument, it will remain unchanged
    in the docstring.

    If `template` is None, the decorated function's existing docstring is used.
    Placeholders in the form `{key}` are replaced by corresponding keyword arguments.
    Missing keys remain unchanged in the docstring.

    :param template: Optional string template with placeholders.
        Defaults to the function's docstring if None.
    :param kwargs: Keyword arguments mapping placeholder names to their
        replacement values.
    :return: Decorated function with the updated docstring.

    :example:

    .. code-block:: python

        @docstring("Hello {name}, welcome to {place}", name="Alice")
        def greet():
            pass

        print(greet.__doc__)
        # Output: "Hello Alice, welcome to {place}"
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        base_template = template if template is not None else func.__doc__ or ""
        formatted_doc = base_template.format_map(SafeDict(kwargs))

        @functools.wraps(func)
        def wrapped(*args: P.args, **fkwargs: P.kwargs) -> R:
            return func(*args, **fkwargs)

        wrapped.__doc__ = formatted_doc
        return wrapped

    return decorator
