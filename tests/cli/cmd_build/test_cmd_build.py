from types import SimpleNamespace

import click
from click import Abort, Command, Context
from pydantic import Field, ValidationError
import pytest

from docbuild.cli import callback as callback_module
from docbuild.cli.callback import validate_doctypes


def test_validate_doctypes_with_empty_doctypes():
    cmd = Command("dummy_build")
    ctx = Context(cmd)
    ctx.obj = SimpleNamespace()

    result = validate_doctypes(ctx, None, tuple())
    assert not result
    # No ctx.obj.doctypes as this doesn't exist


def test_validate_doctypes_abort(monkeypatch):
    ctx = Context(Command("dummy_build"))
    ctx.obj = SimpleNamespace()

    def raise_for_invalid(s: str) -> DummyDoctype:
        if s.startswith("wrong"):
            raise Abort("is not a valid Product")
        return DummyDoctype(s)

    monkeypatch.setattr(
        callback_module.Doctype,
        "from_str",
        staticmethod(raise_for_invalid),
    )

    with pytest.raises(Abort, match="is not a valid Product"):
        validate_doctypes(ctx, None, ("wrong/1/en-us",))


class DummyDoctype:
    def __init__(self, value):
        self.value = value
        parts = value.split("/")
        self.product = parts[0]
        self.version = parts[1]

    def __eq__(self, other):
        return isinstance(other, DummyDoctype) and self.value == other.value

    def __str__(self):
        return self.value


@pytest.fixture(autouse=True)
def patch_doctype(monkeypatch):
    # Patch Doctype.from_str to return a DummyDoctype for testing
    monkeypatch.setattr(
        callback_module,
        "Doctype",
        type(
            "Doctype",
            (),
            {
                "from_str": staticmethod(lambda s: DummyDoctype(s)),
                "model_fields": {
                    "field": type(
                        "Field",
                        (),
                        {"description": "desc", "examples": ["ex"]},
                    )(),
                },
            },
        ),
    )
    # Patch merge_doctypes to just return the list for simplicity
    monkeypatch.setattr(callback_module, "merge_doctypes", lambda *args: list(args))


def test_validate_doctypes_empty(ctx):
    context = ctx(SimpleNamespace())
    result = validate_doctypes(context, None, ())
    assert result == []
    assert not hasattr(context.obj, "doctypes") or context.obj.doctypes == []


def test_validate_doctypes_valid(ctx):
    context = ctx(SimpleNamespace())
    doctypes = ("foo/1/en-us", "bar/2/de-de")
    result = validate_doctypes(context, None, doctypes)
    assert result == [DummyDoctype("foo/1/en-us"), DummyDoctype("bar/2/de-de")]
    assert context.obj.doctypes == result


def test_validate_doctypes_invalid(monkeypatch, ctx):
    context = ctx(SimpleNamespace())

    # Patch Doctype.from_str to raise ValidationError
    class DummyValidationError(Exception):
        def errors(self):
            return [{"loc": ["field"], "msg": "bad", "type": "value_error"}]

    monkeypatch.setattr(
        callback_module,
        "Doctype",
        type(
            "Doctype",
            (),
            {
                "from_str": staticmethod(
                    lambda s: (_ for _ in ()).throw(Abort()),
                ),
                "model_fields": {
                    "field": type(
                        "Field",
                        (),
                        {"description": "desc", "examples": ["ex"]},
                    )(),
                },
            },
        ),
    )
    with pytest.raises(click.Abort):
        validate_doctypes(context, None, ("bad/doctype",))


@pytest.mark.parametrize(
    "doctypes,expected",
    [
        (tuple(), []),
        (("sles/15-SP6/en-us",), [DummyDoctype("sles/15-SP6/en-us")]),
        (
            ("sles/15-SP6/en-us", "suma/4.3/de-de"),
            [DummyDoctype("sles/15-SP6/en-us"), DummyDoctype("suma/4.3/de-de")],
        ),
    ],
)
def test_validate_doctypes_with_doctypes(ctx, doctypes, expected):
    """Test validate_doctypes with different doctype inputs."""
    context = ctx(SimpleNamespace(doctypes=[]))

    result = validate_doctypes(context, None, doctypes)
    assert result == expected
    assert context.obj.doctypes == expected


def test_validate_doctypes_validation_error(monkeypatch, ctx, capsys):
    """Test that validation errors are properly formatted and displayed."""
    context = ctx(SimpleNamespace(doctypes=[]))

    # Create a mock ValidationError with the structure expected in validate_doctypes
    class MockValidationError(Exception):
        def errors(self):
            return [
                {
                    "loc": ["product"],
                    "msg": "Invalid product name",
                    "type": "value_error",
                },
            ]

    def mock_from_str(s: str):
        if s.startswith("invalid"):
            raise MockValidationError()
        return DummyDoctype(s)

    # Patch necessary methods
    monkeypatch.setattr(callback_module, "ValidationError", MockValidationError)
    monkeypatch.setattr(
        callback_module.Doctype, "from_str", staticmethod(mock_from_str)
    )
    monkeypatch.setattr(
        callback_module.Doctype,
        "model_fields",
        {
            "product": type(
                "Field",
                (),
                {
                    "description": "Product name must be alphanumeric",
                    "examples": ["sles", "suma"],
                },
            )(),
        },
    )

    # Test that the function properly aborts and formats error messages
    with pytest.raises(click.Abort):
        validate_doctypes(context, None, ("invalid/product/en-us",))

    captured = capsys.readouterr()
    assert "ERROR in 'product': Invalid product name" in captured.err
    assert "Hint: Product name must be alphanumeric" in captured.out
    assert "Examples: sles, suma" in captured.out


def test_validate_doctypes_merge_called(monkeypatch, ctx):
    """Test that merge_doctypes is called with the correct arguments."""
    context = ctx(SimpleNamespace())
    doctypes = ("sles/15/en-us", "suma/4.3/de-de")

    # Track merge_doctypes calls
    mock_merge_called_with = []

    def mock_merge(*args):
        nonlocal mock_merge_called_with
        mock_merge_called_with = args
        return list(args)

    monkeypatch.setattr(callback_module, "merge_doctypes", mock_merge)

    validate_doctypes(context, None, doctypes)

    # Verify merge_doctypes was called with both doctypes
    assert len(mock_merge_called_with) == 2
    assert all(isinstance(dt, DummyDoctype) for dt in mock_merge_called_with)
    assert [dt.value for dt in mock_merge_called_with] == [
        "sles/15/en-us",
        "suma/4.3/de-de",
    ]


def test_validate_doctypes_echo_outputs(ctx):
    """Test the echo statements in validate_doctypes."""
    context = ctx(SimpleNamespace(verbose=1))
    result = validate_doctypes(context, None, ("sles/15/en-us",))

    assert result[0].value == "sles/15/en-us"


def test_validate_doctypes_full_error_message(monkeypatch, capsys):
    def mock_validation_error(*args, **kwargs):
        raise ValidationError.from_exception_data(
            "Mock validation error",
            [
                {
                    "type": "string_type",
                    "loc": ("product", "foo"),
                    "input": 4,
                    "ctx": {"gt": 5},
                },
            ],
        )

    monkeypatch.setattr(
        callback_module.Doctype,
        "model_fields",
        {
            "product": Field(
                title="Product",
                description="A product name is a lowercase acronym.",
                examples=["alpha", "beta"],
            ),
        },
    )
    monkeypatch.setattr(callback_module.Doctype, "from_str", mock_validation_error)

    with pytest.raises(click.Abort, match=r"Mock validation error"):
        validate_doctypes(
            click.Context(click.Command("dummy")),
            None,
            ("foo/bar",),
        )

    # Capture output after the function call
    captured = capsys.readouterr()

    # assert exc_info.value.title == "Mock validation error"
    assert "Invalid doctype string" in captured.err
    assert "'foo/bar'" in captured.err


def test_validate_doctypes_only_hint_error_message(monkeypatch, capsys):
    def mock_validation_error(*args, **kwargs):
        raise ValidationError.from_exception_data(
            "Mock validation error",
            [
                {
                    "type": "string_type",
                    "loc": ("product", "foo"),
                    "input": 4,
                    "ctx": {"gt": 5},
                },
            ],
        )

    monkeypatch.setattr(
        callback_module.Doctype,
        "model_fields",
        {
            "product": type(
                "Field",
                (),
                {
                    "description": "A product name is a lowercase acronym.",
                    # no examples provided
                },
            )(),
        },
    )
    monkeypatch.setattr(callback_module.Doctype, "from_str", mock_validation_error)

    with pytest.raises(click.Abort, match=r"Mock validation error"):
        validate_doctypes(
            click.Context(click.Command("dummy")),
            None,
            ("foo/bar",),
        )

    # Capture output after the function call
    captured = capsys.readouterr()

    assert "Invalid doctype string" in captured.err
    assert "'foo/bar'" in captured.err


def test_validate_doctypes_only_description_error_message(monkeypatch, capsys):
    def mock_validation_error(*args, **kwargs):
        raise ValidationError.from_exception_data(
            "Mock validation error",
            [
                {
                    "type": "string_type",
                    "loc": ("product", "foo"),
                    "input": 4,
                    "ctx": {"gt": 5},
                },
            ],
        )

    monkeypatch.setattr(
        callback_module.Doctype,
        "model_fields",
        {
            "product": type(
                "Field",
                (),
                {
                    # no description provided
                    "examples": ["alpha", "beta"],
                },
            )(),
        },
    )
    monkeypatch.setattr(callback_module.Doctype, "from_str", mock_validation_error)

    with pytest.raises(click.Abort, match=r"Mock validation error"):
        validate_doctypes(
            click.Context(click.Command("dummy")),
            None,
            ("foo/bar",),
        )

    # Capture output after the function call
    captured = capsys.readouterr()

    # assert exc_info.value.title == "Mock validation error"
    assert "Invalid doctype string" in captured.err or captured.out
    assert "'foo/bar'" in captured.err
