"""Build a documentation deliverables from source.

See :ref:`concept-doctype-syntax`
"""

import asyncio
import math
from pathlib import Path

import click

from ...models.doctype import Doctype
from ...tasks.build.runner import process as build_process
from ...tasks.metadata.runner import process as metadata_process
from ...tasks.sitemap import generate_sitemap
from ...utils.contextmgr import make_timer
from ...utils.sysdeps import requires_system_tools
from ..callback import validate_doctypes
from ..completion import complete_doctypes
from ..console import console, console_err
from ..context import DocBuildContext


@click.command(
    name="run",
    help="""Build a documentation deliverables from source.

    A document (or "doctype") consists of the following syntax:

       [PRODUCT]/[DOCSET][@LIFECYCLES]/LANGS

    With the following properties:

    \b
    * (Optional) 'PRODUCT' is the product. To mark "ALL" products, omit the
      product or use '*'
    * (Optional) 'DOCSET' is the docset, usually the version or release of
      a product.
      To mark "ALL" docsets, omit the docset or use '*'.
    * (Optional) ``LIFECYCLES`` marks a list of lifecycles separated by comma
      or pipe symbol.
      A lifecycle can be one of the values 'supported', 'unsupported', 'beta',
      or 'unpublished'.
    * 'LANGS' marks a list of languages separated by comma. Every single
      language contains a LANGUAGE-COUNTRY syntax, for example 'en-us', 'de-de' etc.

    \b
    Examples:
    * docbuild build run "//en-us"
      Builds all supported deliverables for English

    \b
    * docbuild build run "sles/*/en-us"
      Builds only SLES deliverables which are supported and in English

    \b
    * docbuild build run "sles/*@unsupported/en-us,de-de"
      Builds all English and German SLES releases which are unsupported

    \b
    * docbuild build run "sles/@beta,supported/de-de"
      Same as the previous one, but with comma as the separator between
      the lifecycle states.
    """
)
@click.argument(
    "doctypes", nargs=-1, callback=validate_doctypes, shell_complete=complete_doctypes
)
@click.option(
    "-S", "--skip-repo-update", is_flag=True, default=False, show_default=True,
    help="Skip updating git repositories before processing.",
)
@click.option(
    "-M", "--skip-metadata", is_flag=True, default=False, show_default=True,
    help="Skip generating metadata (runs before build by default).",
)
@click.option(
    "--sitemap/--no-sitemap", is_flag=True, default=True, show_default=True,
    help="Generate a sitemap.xml in the target root after building.",
)
@click.pass_context
@requires_system_tools()
def run(
    ctx: click.Context,
    doctypes: tuple[Doctype, ...],
    skip_repo_update: bool,
    skip_metadata: bool,
    sitemap: bool,
) -> None:
    """Run the build pipeline for deliverables.

    \f

    :param ctx: Click context holding environment and app configuration.
    :param doctypes: Tuple of parsed Doctype specifications.
    :param skip_repo_update: If True, do not pull or update git remotes.
    :param skip_metadata: If True, bypass metadata generation phase.
    :param sitemap: If True, generate sitemap.xml after build.
    """  # noqa: D301
    ctx.ensure_object(DocBuildContext)
    context: DocBuildContext = ctx.obj

    assert context.envconfig is not None
    env = context.envconfig

    timer = make_timer("build")
    result = 1  # Default exit code for interruption or error

    # Paths for Metadata & Build
    main_portal_config = env.paths.main_portal_config
    repo_dir = env.paths.repo_dir
    tmp_repo_dir = env.paths.tmp_repo_dir
    tmp_metadata_dir = env.paths.tmp.tmp_metadata_dir
    meta_cache_dir = env.paths.meta_cache_dir
    json_cache_dir = env.paths.json_cache_dir
    tmp_build_base_dir = env.paths.tmp.tmp_build_base_dir
    target_base_dir = Path(env.paths.target.target_base_dir)
    target_dir_dyn = env.paths.target.target_dir_dyn

    dapsmetatmpl = str(env.build.daps.meta)
    daps_list_srcfiles_tmpl = str(env.build.daps.list_srcfiles)
    daps_tmpls = {
        "html": getattr(env.build.daps, "html", "daps -d {{dcfile}} --builddir {{builddir}} html"),
        "pdf": getattr(env.build.daps, "pdf", "daps -d {{dcfile}} --builddir {{builddir}} pdf"),
        "single-html": getattr(env.build.daps, "single_html", "daps -d {{dcfile}} --builddir {{builddir}} single-html"),
        "epub": getattr(env.build.daps, "epub", "daps -d {{dcfile}} --builddir {{builddir}} epub"),
    }

    max_workers = context.appconfig.max_workers if context.appconfig else 1
    console.print(f"Config path: {env.paths.config_dir}")

    async def run_pipeline() -> int:
        build_skip_repo = skip_repo_update

        if not skip_metadata:
            console.print("[header]Running metadata generation (fail-fast validation)...[/]")
            meta_result = await asyncio.create_task(
                metadata_process(
                    main_portal_config=main_portal_config,
                    tmp_metadata_dir=tmp_metadata_dir,
                    repo_dir=repo_dir,
                    tmp_repo_dir=tmp_repo_dir,
                    meta_cache_dir=meta_cache_dir,
                    json_cache_dir=json_cache_dir,
                    prebuilt_dir=env.paths.prebuilt_dir,
                    dapsmetatmpl=dapsmetatmpl,
                    daps_list_srcfiles_tmpl=daps_list_srcfiles_tmpl,
                    max_workers=max_workers,
                    doctypes=list(doctypes),
                    skip_repo_update=skip_repo_update,
                ),
                name="build:metadata",
            )

            if meta_result != 0:
                console_err.print("[error]Metadata generation failed. Aborting build.[/]")
                return meta_result

            build_skip_repo = True

        console.print(f"[header]Starting async build pipeline with {max_workers} workers...[/]")
        return await asyncio.create_task(
            build_process(
                main_portal_config=main_portal_config,
                repo_dir=repo_dir,
                tmp_repo_dir=tmp_repo_dir,
                tmp_build_base_dir=tmp_build_base_dir,
                target_base_dir=target_base_dir,
                target_dir_dyn=target_dir_dyn,
                max_workers=max_workers,
                doctypes=doctypes,
                daps_tmpls=daps_tmpls,
                skip_repo_update=build_skip_repo,
                rsync_options=env.rsync.to_options(),
                build_llmstxt=env.build.build_llmstxt,
                llmstxt_dir=env.paths.llmstxt_dir,
            ),
            name="build:build",
        )

    t = None
    try:
        with timer() as t:
            async def main() -> int:
                res = await asyncio.create_task(run_pipeline(), name="build")
                if res == 0 and sitemap:
                    base_url = str(env.general.canonical_url_domain)
                    await generate_sitemap(target_base_dir, base_url)
                return res

            result = asyncio.run(main())
    finally:
        if t and not math.isnan(t.elapsed):
            console.print(f"Elapsed time {t.elapsed:0.2f}s")

    ctx.exit(result)
