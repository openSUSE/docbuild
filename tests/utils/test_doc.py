from docbuild.utils.doc import docstring


def test_docstring_with_empty_func():
    @docstring("Hello {name}, welcome to {place}", name="Alice")
    def greet() -> str:
        return "Hello"

    assert greet() == "Hello"
    assert greet.__doc__ == "Hello Alice, welcome to {place}"


def test_docstring_with_existing_docstring():
    @docstring(name="Alice")
    def greet():
        """Hello {name}, welcome to {place}."""
        pass

    assert greet.__doc__ == "Hello Alice, welcome to {place}."
