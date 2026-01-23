"""Useful decorators for XML checks."""

from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, TypeVar, cast

from lxml import etree

if TYPE_CHECKING:
    from ..config.xml.checks import CheckResult

F = TypeVar("F", bound=Callable[[etree._Element | etree._ElementTree], "CheckResult"])
"""A type variable representing a callable that takes an XML element or tree"""


class RegistryDecorator:
    """A class to register functions in a registry for XML checks."""

    def __init__(self) -> None:
        """Initialize the registry."""
        self.registry = []

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

        @wraps(func)
        def wrapper(*args: object, **kwargs: object) -> "CheckResult":
            return func(*args, **kwargs)

        return cast(F, wrapper)


def factory_registry() -> Callable[[F], F]:
    """Create a decorator that registers functions in its own registry.

    Example usage:

    >>> register_check = factory_registry()
    >>> @register_check
    ... def check_example(tree: etree._Element | etree._ElementTree) -> bool:
    ...     return True
    >>> register_check.registry[0].__name__
    'check_example'

    :return: A decorator that registers functions in a registry,
       see :class:`~docbuild.utils.decorators.RegistryDecorator`.
    """
    return RegistryDecorator()
