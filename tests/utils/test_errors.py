"""Tests for the Pydantic error formatting utility."""

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from docbuild.utils.errors import format_pydantic_error


class SubModel(BaseModel):
    """A sub-model for testing nested validation."""

    name: str = Field(title="Sub Name", description="A sub description")


class MockModel(BaseModel):
    """A mock model for testing top-level validation."""

    age: int = Field(title="User Age")
    sub: SubModel


def test_format_pydantic_error_smoke(capsys):
    """Smoke test to ensure the formatter runs without crashing."""
    # Using Any to bypass static type checking for invalid data types
    invalid_data: dict[str, Any] = {"age": "not-an-int", "sub": {"name": 123}}

    try:
        # Trigger a validation error
        MockModel(**invalid_data)
    except ValidationError as e:
        # Run the formatter
        format_pydantic_error(e, MockModel, "test.toml", verbose=1)

    captured = capsys.readouterr()

    # Check for key UI elements
    assert "Validation error" in captured.err
    assert "test.toml" in captured.err
    assert "User Age" in captured.err
    assert "A sub description" in captured.err
    assert "https://opensuse.github.io/docbuild/latest/errors/" in captured.err


def test_format_pydantic_error_truncation(capsys):
    """Verify that truncation message appears when many errors exist."""

    class MultiModel(BaseModel):
        """A model with many fields to trigger truncation."""

        a: int
        b: int
        c: int
        d: int
        e: int
        f: int

    # Cast to Any to bypass static type checking for the invalid input
    invalid_input: dict[str, Any] = {
        "a": "x",
        "b": "x",
        "c": "x",
        "d": "x",
        "e": "x",
        "f": "x",
    }

    try:
        MultiModel(**invalid_input)
    except ValidationError as e:
        format_pydantic_error(e, MultiModel, "test.toml", verbose=0)

    captured = capsys.readouterr()
    assert "... and 1 more errors" in captured.err
