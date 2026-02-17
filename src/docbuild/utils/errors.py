"""Utilities for handling and formatting application errors."""

from pydantic import BaseModel, ValidationError
from rich.console import Console
from rich.text import Text


def format_pydantic_error(
    error: ValidationError,
    model_class: type[BaseModel],
    config_file: str,
    verbose: int = 0
) -> None:
    """Centralized formatter for Pydantic ValidationErrors using Rich.

    :param error: The caught ValidationError object.
    :param model_class: The Pydantic model class that failed validation.
    :param config_file: The name/path of the config file being processed.
    :param verbose: Verbosity level to control error detail.
    """
    console = Console(stderr=True)
    errors = error.errors()
    error_count = len(errors)

    # Header
    header = Text.assemble(
        (f"{error_count} Validation error{'s' if error_count > 1 else ''} ", "bold red"),
        ("in config file ", "white"),
        (f"'{config_file}'", "bold cyan"),
        (":", "white")
    )
    console.print(header)
    console.print()

    # Smart Truncation: Show only first 5 unless verbose
    max_display = 5 if verbose < 2 else error_count
    display_errors = errors[:max_display]

    for i, err in enumerate(display_errors, 1):
        # 1. Resolve Location and Field Info
        loc_path = ".".join(str(v) for v in err["loc"])
        err_type = err["type"]
        msg = err["msg"]

        # 2. Extract Field Metadata from the Model Class
        field_info = None
        current_model = model_class

        for part in err["loc"]:
            # Check if current_model is a Pydantic class and contains the field
            if (isinstance(current_model, type) and
                issubclass(current_model, BaseModel) and
                part in current_model.model_fields):

                field_info = current_model.model_fields[part]

                # Move deeper into the tree if the annotation is another model
                annotation = field_info.annotation
                if (isinstance(annotation, type) and
                    issubclass(annotation, BaseModel)):
                    current_model = annotation
                else:
                    # We have reached a leaf node or a complex type (List, etc.)
                    # Stop traversing but keep the field_info
                    current_model = None
            else:
                field_info = None
                break

        # 3. Build the Display
        error_panel = Text()
        error_panel.append(f"({i}) In '", style="white")
        error_panel.append(loc_path, style="bold yellow")
        error_panel.append("':\n", style="white")

        # Error detail
        error_panel.append(f"    {msg}\n", style="red")

        # Helpful context from Field metadata
        if field_info:
            if field_info.title:
                error_panel.append("    Expected: ", style="dim")
                error_panel.append(f"{field_info.title}\n", style="italic green")
            if verbose > 0 and field_info.description:
                error_panel.append("    Description: ", style="dim")
                error_panel.append(f"{field_info.description}\n", style="dim italic")

        # Documentation Link
        error_panel.append("    See: ", style="dim")
        error_panel.append(
            f"https://opensuse.github.io/docbuild/latest/errors/{err_type}.html",
            style="link underline blue"
        )

        console.print(error_panel)
        console.print()

    # Footer for Truncation
    if error_count > max_display:
        console.print(
            f"[dim]... and {error_count - max_display} more errors. "
            "Use '-vv' to see all errors.[/dim]\n"
        )
