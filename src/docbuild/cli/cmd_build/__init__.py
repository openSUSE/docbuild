"""CLI interface to build a document."""

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
    help="Skip generating metadata (runs before build by default).",
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

    # Paths for Metadata & Build
    main_portal_config = Path(env.paths.main_portal_config)
    repo_dir = Path(env.paths.repo_dir)
    tmp_repo_dir = Path(env.paths.tmp_repo_dir)
    tmp_metadata_dir = Path(env.paths.tmp.tmp_metadata_dir)
    meta_cache_dir = Path(env.paths.meta_cache_dir)
    json_cache_dir = Path(env.paths.json_cache_dir)
    tmp_build_base_dir = Path(env.paths.tmp.tmp_build_base_dir)

    dapsmetatmpl = str(env.build.daps.meta)

    # Dynamic templates for the build runner
    # We use getattr safely until we formally add these to the EnvBuildDaps model
    daps_tmpls = {
        "html": getattr(env.build.daps, "html", "daps -d {{dcfile}} --builddir {{builddir}} html"),
        "pdf": getattr(env.build.daps, "pdf", "daps -d {{dcfile}} --builddir {{builddir}} pdf"),
        "single-html": getattr(env.build.daps, "single_html", "daps -d {{dcfile}} --builddir {{builddir}} single-html"),
        "epub": getattr(env.build.daps, "epub", "daps -d {{dcfile}} --builddir {{builddir}} epub"),
    }

    max_workers = context.appconfig.max_workers if context.appconfig else 1

    async def run_pipeline() -> int:
        build_skip_repo = skip_repo_update

        # 1. Run Metadata (Fail-Fast Validation)
        if not skip_metadata:
            click.echo("[BUILD] Running metadata generation (fail-fast validation)...")
            meta_result = await metadata_process(
                main_portal_config=main_portal_config,
                tmp_metadata_dir=tmp_metadata_dir,
                repo_dir=repo_dir,
                tmp_repo_dir=tmp_repo_dir,
                meta_cache_dir=meta_cache_dir,
                json_cache_dir=json_cache_dir,
                dapsmetatmpl=dapsmetatmpl,
                max_workers=max_workers,
                doctypes=list(doctypes),
                skip_repo_update=skip_repo_update,
            )

            if meta_result != 0:
                click.echo("[BUILD] Metadata generation failed. Aborting build.", err=True)
                return meta_result

            # Since repos were updated during metadata, skip updating them again during build
            build_skip_repo = True

        # 2. Run Build
        click.echo(f"[BUILD] Starting async build pipeline with {max_workers} workers...")
        build_result = await build_process(
            main_portal_config=main_portal_config,
            repo_dir=repo_dir,
            tmp_build_base_dir=tmp_build_base_dir,
            max_workers=max_workers,
            doctypes=doctypes,
            daps_tmpls=daps_tmpls,
            skip_repo_update=build_skip_repo,
        )

        return build_result

    result = asyncio.run(run_pipeline())
    ctx.exit(result)
