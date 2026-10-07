"""Utilities for handling and formatting application errors."""


import tomllib

from pydantic import BaseModel, ValidationError
from rich.console import Console
from rich.text import Text

from ..cli.console import console_err
from ..constants import DEFAULT_ERROR_LIMIT


def format_pydantic_error(
    error: ValidationError,
    model_class: type[BaseModel],
    config_file: str,
    verbose: int = 0,
    console: Console | None = None,
) -> None:
    """Centralized formatter for Pydantic ValidationErrors using Rich.

    :param error: The caught ValidationError object.
    :param model_class: The Pydantic model class that failed validation.
    :param config_file: The name/path of the config file being processed.
    :param verbose: Verbosity level to control error detail.
    :param console: Optional Rich console object. If None, creates a stderr console.
    """
    # Use provided console or fall back to default (Dependency Injection)
    con = console or console_err

    errors = error.errors()
    error_count = len(errors)

    # Header
    header = Text.assemble(
        (f"{error_count} Validation error{'s' if error_count > 1 else ''} ", "error"),
        ("in config file ", "white"),
        (f"'{config_file}'", "bold cyan"),
        (":", "white")
    )
    con.print(header)
    con.print()

    # Smart Truncation: Use the constant from constants.py
    max_display = DEFAULT_ERROR_LIMIT if verbose < 2 else error_count
    display_errors = errors[:max_display]

    for i, err in enumerate(display_errors, 1):
        # 1. Resolve Location and Field Info
        # Filter out internal Pydantic tags (strings with '[' or '-')
        # to keep the path clean for end users.
        clean_loc = [
            str(v) for v in err["loc"]
            if not (isinstance(v, str) and ("[" in v or "-" in v))
            and not isinstance(v, int)
        ]
        loc_path = ".".join(clean_loc)

        err_type = err["type"]
        msg = err["msg"]

        # 2. Extract Field Metadata from the Model Class
        field_info = None
        current_model = model_class

        for part in err["loc"]:
            if (isinstance(current_model, type) and
                issubclass(current_model, BaseModel) and
                part in current_model.model_fields):

                field_info = current_model.model_fields[part]

                annotation = field_info.annotation
                if (isinstance(annotation, type) and
                    issubclass(annotation, BaseModel)):
                    current_model = annotation
                else:
                    current_model = None
            else:
                field_info = None
                break

        # 3. Build the Display
        error_panel = Text()
        error_panel.append(f"({i}) In '", style="white")
        error_panel.append(loc_path, style="warning")
        error_panel.append("':\n", style="white")

        # Error detail
        error_panel.append(f"    {msg}\n", style="error")

        # Helpful context from Field metadata
        if field_info:
            if field_info.title:
                error_panel.append("    Expected: ", style="muted")
                error_panel.append(f"{field_info.title}\n", style="italic green")
            if verbose > 0 and field_info.description:
                error_panel.append("    Description: ", style="muted")
                error_panel.append(f"{field_info.description}\n", style="dim italic")

        # Documentation Link
        error_panel.append("    See: ", style="muted")
        error_panel.append(
            f"https://opensuse.github.io/docbuild/latest/errors/{err_type}.html",
            style="link underline blue"
        )

        con.print(error_panel)
        con.print()

    # Footer for Truncation
    if error_count > max_display:
        con.print(
            f"[muted]... and {error_count - max_display} more errors. "
            "Use '-vv' to see all errors.[/]\n"
        )

def format_toml_error(
    error: tomllib.TOMLDecodeError,
    config_file: str,
    console: Console | None = None,
) -> None:
    """Format TOML syntax errors using Rich.

    :param error: The caught TOMLDecodeError object.
    :param config_file: The name/path of the config file with the syntax error.
    :param console: Optional Rich console object.
    """
    con = console or console_err

    header = Text.assemble(
        ("Syntax error ", "error"),
        ("in config file ", "white"),
        (f"'{config_file}'", "bold cyan"),
        (":", "white")
    )
    con.print(header)

    # tomllib error messages include the line and column info naturally
    con.print(f"    [error]{error}[/]")
    con.print()
    con.print("    [muted]Please verify that the file is a valid TOML file.[/]")
    con.print("    [muted]Note: Booleans must be lowercase (true/false) in TOML.[/]")
