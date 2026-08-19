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

import asyncio
from pathlib import Path

import click

from ...models.doctype import Doctype
from ...tasks.build.runner import process as build_process
from ...tasks.metadata.runner import process as metadata_process
from ...utils.sysdeps import requires_system_tools
from ..callback import validate_doctypes
from ..context import DocBuildContext


@click.command(help="Subcommand to build a document.")
@click.argument("doctypes", nargs=-1, callback=validate_doctypes)
@click.option(
    "-S", "--skip-repo-update", is_flag=True, default=False, show_default=True,
    help="Skip updating git repositories before processing.",
)
@click.option(
    "-M", "--skip-metadata", is_flag=True, default=False, show_default=True,
    help="Skip generating metadata after a successful build.",
)
@click.pass_context
@requires_system_tools()
def build(
    ctx: click.Context,
    doctypes: tuple[Doctype, ...],
    skip_repo_update: bool,
    skip_metadata: bool,
) -> None:
    """Subcommand build."""
    ctx.ensure_object(DocBuildContext)
    context: DocBuildContext = ctx.obj

    if not context.envconfig:
        click.echo("Environment configuration is missing.", err=True)
        ctx.exit(1)

    assert context.envconfig is not None
    env = context.envconfig

    # Paths for Build
    main_portal_config = Path(env.paths.main_portal_config)
    repo_dir = Path(env.paths.repo_dir)
    tmp_build_dir = Path(env.paths.tmp.tmp_build_base_dir) / str(env.paths.tmp.tmp_build_dir_dyn)

    # Paths for Metadata
    tmp_metadata_dir = Path(env.paths.tmp.tmp_metadata_dir)
    tmp_repo_dir = Path(env.paths.tmp_repo_dir)
    meta_cache_dir = Path(env.paths.meta_cache_dir)
    json_cache_dir = Path(env.paths.json_cache_dir)
    dapsmetatmpl = str(env.build.daps.meta)

    max_workers = context.appconfig.max_workers if context.appconfig else 1

    async def run_pipeline() -> int:
        click.echo(f"[BUILD] Starting async build pipeline with {max_workers} workers...")
        build_result = await build_process(
            main_portal_config=main_portal_config,
            repo_dir=repo_dir,
            tmp_build_dir=tmp_build_dir,
            max_workers=max_workers,
            doctypes=doctypes,
            skip_repo_update=skip_repo_update,
        )

        if build_result == 0 and not skip_metadata:
            click.echo("[BUILD] Build successful. Chaining metadata generation...")
            return await metadata_process(
                main_portal_config=main_portal_config,
                tmp_metadata_dir=tmp_metadata_dir,
                repo_dir=repo_dir,
                tmp_repo_dir=tmp_repo_dir,
                meta_cache_dir=meta_cache_dir,
                json_cache_dir=json_cache_dir,
                dapsmetatmpl=dapsmetatmpl,
                max_workers=max_workers,
                doctypes=list(doctypes),
                skip_repo_update=True, # Repos were already updated by the build task
            )
        return build_result

    result = asyncio.run(run_pipeline())
    ctx.exit(result)
