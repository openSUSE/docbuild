"""Tests for the Pydantic error formatting utility."""

from typing import Any

from pydantic import BaseModel, Field, IPvAnyAddress, ValidationError, create_model
from rich.console import Console

from docbuild.constants import DEFAULT_ERROR_LIMIT
from docbuild.utils.errors import format_pydantic_error


class SubModel(BaseModel):
    """A sub-model for testing nested validation."""

    name: str = Field(title="Sub Name", description="A sub description")


class MockModel(BaseModel):
    """A mock model for testing top-level validation."""

    age: int = Field(title="User Age")
    sub: SubModel


def test_format_pydantic_error_smoke(capsys):
    """Smoke test to ensure the formatter runs without crashing with injected console."""
    invalid_data: dict[str, Any] = {"age": "not-an-int", "sub": {"name": 123}}
    # Create a specific console to test dependency injection
    test_console = Console(stderr=True, force_terminal=False)

    try:
        MockModel(**invalid_data)
    except ValidationError as e:
        format_pydantic_error(
            e, MockModel, "test.toml", verbose=1, console=test_console
        )

    captured = capsys.readouterr()

    assert "Validation error" in captured.err
    assert "User Age" in captured.err
    assert "A sub description" in captured.err


def test_format_pydantic_error_truncation(capsys):
    """Verify truncation message appears based on DEFAULT_ERROR_LIMIT."""

    # Define a dictionary of fields: { 'a': (int, ...), 'b': (int, ...), ... }
    # This creates exactly one more field than the allowed display limit.
    field_definitions: dict[str, Any] = {
        chr(97 + i): (int, ...)
        for i in range(DEFAULT_ERROR_LIMIT + 1)
    }

    # Use create_model with explicit __base__ to satisfy type checkers.
    # Renamed to dynamic_model (lowercase) to satisfy Ruff N806.
    dynamic_model = create_model(
        "DynamicModel",
        __base__=BaseModel,
        **field_definitions
    )

    # Create invalid input for all fields
    invalid_input = {k: "not-an-int" for k in field_definitions.keys()}

    try:
        dynamic_model(**invalid_input)
    except ValidationError as e:
        format_pydantic_error(e, dynamic_model, "test.toml", verbose=0)

    captured = capsys.readouterr()
    # Check that the footer correctly identifies the hidden error
    assert "... and 1 more errors" in captured.err


def test_format_pydantic_error_path_cleaning(capsys):
    """Verify that internal Pydantic tags like [..] are stripped from the path."""

    class UnionModel(BaseModel):
        # A union often causes Pydantic to add tags like 'function-plain[...]'
        host: IPvAnyAddress | str = Field(pattern=r"^[a-z]+$")

    # This will fail both IPvAnyAddress and the string regex
    invalid_data: dict[str, Any] = {"host": "123-invalid-host"}

    try:
        UnionModel(**invalid_data)
    except ValidationError as e:
        format_pydantic_error(e, UnionModel, "test.toml")

    captured = capsys.readouterr()

    # We want to see 'In 'host'', NOT 'In 'host.function-plain...''
    assert "In 'host':" in captured.err
    # Verify no bracketed pydantic internals leaked in the path part
    assert "[" not in captured.err.split("In '")[1].split("':")[0]
