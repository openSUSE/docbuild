from lxml import etree
import pytest

from docbuild.utils.decorators import factory_registry


def test_register_check_registers_function():
    register_check = factory_registry()
    registry = register_check.registry  # Store reference to registry before decoration

    @register_check
    def foo(tree):
        return True

    assert foo(etree.Element("root", nsmap=None, attrib=None)) is True
    assert registry[0].__name__ == "foo"


def test_register_check_type_error():
    register_check = factory_registry()
    with pytest.raises(TypeError):
        register_check(42)  # type: ignore[call-arg]


def test_multiple_functions_registered():
    register_check = factory_registry()
    registry = register_check.registry  # Store reference to registry before decoration

    @register_check
    def foo(tree):
        return True

    @register_check
    def bar(tree):
        return False

    assert len(registry) == 2

    for func, name in zip(registry, ("foo", "bar"), strict=False):
        assert callable(func)
        assert func.__name__ == name


def test_wrapper_preserves_function_metadata():
    register_check = factory_registry()

    @register_check
    def foo(tree):
        """Docstring for foo."""
        return True

    assert foo.__name__ == "foo"
    assert foo.__doc__ == "Docstring for foo."
