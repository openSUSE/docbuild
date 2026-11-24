"""CLI command for building index pages from metadata."""

import asyncio
from typing import TYPE_CHECKING

import click

from ...cli.callback import validate_doctypes
from ...cli.completion import complete_doctypes
from ...models.doctype import Doctype
from ...tasks.build.index import process

if TYPE_CHECKING:
    from ...cli.cmd_cli import DocBuildContext
    from ...models.config.env import EnvConfig


@click.command(name="index")
@click.argument(
    "doctypes",
    nargs=-1,
    required=True,
    callback=validate_doctypes,
    shell_complete=complete_doctypes,
)
@click.option(
    "--keep-index",
    is_flag=True,
    default=False,
    help="Rename existing index.html to index.html.bak before generating.",
)
@click.pass_context
def index(
    ctx: click.Context,
    doctypes: tuple[Doctype, ...],
    keep_index: bool,
) -> None:
    """Generate index HTML pages for deliverables using Jinja templates.

    \f

    The pages are built from the JSON metadata cache with the
    :file:`index.html.jinja` template.

    :param ctx: The Click context that holds the environment config.
    :param doctypes: Doctypes to build the index pages for.
    :param keep_index: Rename an existing :file:`index.html` to
        :file:`index.html.bak` instead of overwriting it.
    """  # noqa: D301
    context: DocBuildContext = ctx.obj
    assert context.envconfig is not None
    env_config: EnvConfig = context.envconfig

    workers = getattr(env_config, "workers", 10)

    status = asyncio.run(
        process(
            jinja_dir=env_config.paths.jinja_dir,
            json_cache_dir=env_config.paths.json_cache_dir,
            target_base_dir=env_config.paths.target.target_base_dir,
            target_dir_dyn=env_config.paths.target.target_dir_dyn,
            doctypes=doctypes,
            keep_index=keep_index,
            max_workers=workers,
        )
    )
    if status != 0:
        ctx.exit(status)
