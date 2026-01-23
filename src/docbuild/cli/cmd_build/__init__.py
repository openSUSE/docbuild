"""CLI interface to build a document.

A document (or "doctype") consists of ``[PRODUCT]/[DOCSET][@LIFECYCLES]/LANGS``
with the following properties:

\b

* (Optional) ``PRODUCT`` is the product. To mark "ALL" products, omit the
  product or use "*"
* (Optional) ``DOCSET`` is the docset, usually the version or release of
  a product.
  To mark "ALL" docsets, omit the docset or use ``"*"``.
* (Optional) ``LIFECYCLES`` marks a list of lifecycles separated by comma
  or pipe symbol.
  A lifecycle can be one of the values 'supported', 'unsupported', 'beta',
  or 'hidden'.
* ``LANGS`` marks a list of languages separated by comma. Every single
  language contains a LANGUAGE-COUNTRY syntax, for example 'en-us', 'de-de' etc.

Examples of the doctypes syntax:

\b

* ``"//en-us"``
  Builds all supported deliverables for English
* ``"sles/*/en-us"``
  Builds only SLES deliverables which are supported and in English
* ``"sles/*@unsupported/en-us,de-de"``
  Builds all English and German SLES releases which are unsupported
* ``"sles/@beta|supported/de-de"``
  Build all docsets that are supported and beta for German SLES.
* ``"sles/@beta,supported/de-de"``
  Same as the previous one, but with comma as the separator between
  the lifecycle states.
"""  # noqa: D301

import click

from ...models.doctype import Doctype
from ..callback import validate_doctypes
from ..context import DocBuildContext


@click.command(
    help=__doc__.replace("\b\n\n", "\b\n").replace("``", ""),  # type: ignore
)
@click.argument(
    "doctypes",
    nargs=-1,
    callback=validate_doctypes,
)
@click.pass_context
def build(ctx: click.Context, doctypes: tuple[Doctype]) -> None:
    """Subcommand build.

    :param ctx: The Click context object.
    :param doctypes: A tuple of doctype objects to build.
    """
    ctx.ensure_object(DocBuildContext)
    context: DocBuildContext = ctx.obj

    click.echo(f"[BUILD] Verbosity: {context.verbose}")
    click.echo(f"{context=}")
    click.echo(f"{context.appconfigfiles=}")
