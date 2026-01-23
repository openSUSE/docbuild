"""Click callback to validate doctype strings."""

import logging

import click
from pydantic import Field, ValidationError

from ..models.doctype import Doctype
from ..utils.merge import merge_doctypes

log = logging.getLogger(__name__)


def validate_doctypes(
    ctx: click.Context,
    param: click.Parameter | None,
    doctypes: tuple[str, ...],
) -> list[Doctype]:
    """Click callback function to validate a list of doctype strings.

    Each string must conform to the format: PRODUCT/DOCSET@LIFECYCLE/LANGS
    LANGS can be a single language code, a comma-separated list (no spaces),
    or '*' for all.
    Defaults and wildcards (*) are handled.

    :param param: The click parameter that triggered this callback.
    :param doctypes: A tuple of doctype strings to validate.
    :return: A list of validated Doctype objects.
    :raises click.Abort: If any doctype string is invalid, the command is aborted.
    """
    processed_data = []  # Store successfully parsed/validated data

    if not doctypes:
        return []

    # click.echo(f"Our doctypes: {doctypes=}")
    for doctype_str in doctypes:
        try:
            doctype = Doctype.from_str(doctype_str)
            processed_data.append(doctype)

        except ValueError as err:
            click.secho(
                f"ERROR: Invalid doctype string '{doctype_str}': {err}",
                fg="red",
                err=True,
            )
            raise click.Abort(err) from err

        except ValidationError as err:
            for error in err.errors():
                field = error["loc"][0]
                # Convert to string to ensure it works as dictionary key
                field_name = str(field)
                msg = error["msg"]
                # Make accessing of .description and .examples safe(r) if
                # the definition in Doctype is not present
                safe_field = Field(description=None, examples=None)
                hint = getattr(
                    Doctype.model_fields.get(field_name, safe_field),
                    "description",
                    None,
                )
                examples = getattr(
                    Doctype.model_fields.get(field_name, safe_field),
                    "examples",
                    None,
                )
                click.secho(
                    f"ERROR in '{field}': {msg}",
                    fg="red",
                    err=True,
                )
                if hint:
                    click.echo(f"  → Hint: {hint}")
                if examples:
                    click.echo(f"  → Examples: {', '.join(examples)}")
                click.echo()
            raise click.Abort(err) from err

    # --- Optional: Post-validation checks across all inputs ---
    # This part becomes more complex if you need to merge/check '*' against lists.
    # For now, we'll just validate each argument independently.
    # You might handle the combination logic in the main command.

    processed_data = merge_doctypes(*processed_data)
    ctx.obj.doctypes = processed_data
    return processed_data
