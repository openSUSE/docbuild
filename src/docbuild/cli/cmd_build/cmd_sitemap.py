"""CLI command to generate a sitemap."""

import asyncio
from contextlib import suppress
from pathlib import Path
from threading import Lock

import click
from rich.text import Text

from ...tasks.sitemap import generate_sitemap
from ..console import console, console_err
from ..context import DocBuildContext


async def generate_sitemap_with_progress(
    target_dir: Path, base_url: str, *, verbose: int = 0
) -> Path:
    """Generate a sitemap with transient status on interactive terminals.

    :param target_dir: Root of the published documentation.
    :param base_url: Canonical URL prefix for sitemap entries.
    :param verbose: Disable animation when verbose logs are enabled.
    :returns: Path returned by sitemap generation.
    """
    if verbose or not console_err.is_terminal or console_err.is_dumb_terminal:
        return await asyncio.create_task(
            generate_sitemap(target_dir, base_url), name="build:sitemap"
        )

    lock = Lock()
    latest = ("Scanning HTML files", target_dir)

    def report_progress(description: str, directory: Path) -> None:
        # Coalesce updates so a fast traversal cannot build a display backlog.
        nonlocal latest
        with lock:
            latest = (description, directory)

    with console_err.status(Text("Scanning HTML files: .")) as status:

        async def update_display() -> None:
            while True:
                with lock:
                    description, directory = latest
                relative_dir = directory.relative_to(target_dir).as_posix()
                status.update(Text(f"{description}: {relative_dir}"))
                await asyncio.sleep(0.1)

        display_task = asyncio.create_task(
            update_display(), name="build:sitemap:display"
        )
        try:
            return await asyncio.create_task(
                generate_sitemap(target_dir, base_url, on_progress=report_progress),
                name="build:sitemap",
            )
        finally:
            display_task.cancel()
            with suppress(asyncio.CancelledError):
                await display_task


@click.command(
    name="sitemap",
    help="Generate a sitemap.xml in the target distribution directory."
)
@click.pass_context
def sitemap(ctx: click.Context) -> None:
    """Generate a sitemap.xml in the target distribution directory."""
    ctx.ensure_object(DocBuildContext)
    context: DocBuildContext = ctx.obj
    env = context.envconfig

    assert env is not None, "Environment configuration is missing."

    target_base_dir = Path(env.paths.target.target_base_dir)
    base_url = str(env.general.canonical_url_domain)

    async def main() -> int:
        """Generate the sitemap."""
        await generate_sitemap_with_progress(
            target_base_dir, base_url, verbose=context.verbose
        )
        console.print(f"Generated sitemap at \'{target_base_dir}/sitemap.xml\'", style="success")
        return 0

    result = asyncio.run(main())
    ctx.exit(result)
