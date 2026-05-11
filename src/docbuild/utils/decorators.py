"""Useful decorators for XML checks."""

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, TypeVar

from lxml import etree

if TYPE_CHECKING:
    from ..config.xml.checks import CheckResult


CheckFunc = Callable[
    [etree._Element | etree._ElementTree],
    Iterator["CheckResult"],
]
"""Concrete callable type for registered XML checks."""

F = TypeVar(
    "F",
    bound=CheckFunc,
)
"""A type variable representing a callable that takes an XML element or tree"""


class RegistryDecorator:
    """A class to register functions in a registry for XML checks."""

    def __init__(self) -> None:
        """Initialize the registry."""
        self.registry: list[CheckFunc] = []

    def __call__(self, func: F) -> F:
        """Register a function as a check.

        The method wraps the function unchanged, allowing it to be called
        with XML elements or trees.

        :param func: The function to register.
        :return: The wrapped function.
        """
        if not callable(func):
            raise TypeError("Only callable objects can be registered as checks.")
        self.registry.append(func)
        return func


def factory_registry() -> RegistryDecorator:
    """Create a decorator that registers functions in its own registry.

    Example usage:

    >>> register_check = factory_registry()
    >>> @register_check
    ... def check_example(
    ...     tree: etree._Element | etree._ElementTree,
    ... ) -> Iterator[CheckResult]:
    ...     if False:
    ...         yield CheckResult(message="example")
    >>> register_check.registry[0].__name__
    'check_example'

    :return: A decorator that registers functions in a registry,
       see :class:`~docbuild.utils.decorators.RegistryDecorator`.
    """
    return RegistryDecorator()
