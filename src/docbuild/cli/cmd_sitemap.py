"""CLI command to generate a sitemap."""

import asyncio
from pathlib import Path

import click

from ..tasks.sitemap import generate_sitemap
from .context import DocBuildContext


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

    if not env:
        click.secho("Environment configuration is missing.", fg="red")
        ctx.exit(1)

    target_base_dir = Path(env.paths.target.target_base_dir)
    base_url = str(getattr(env, "canonical_url_domain", "https://documentation.suse.com/"))

    async def main() -> int:
        click.secho(f"Generating sitemap.xml in {target_base_dir}...", fg="green")
        await generate_sitemap(target_base_dir, base_url)
        return 0

    result = asyncio.run(main())
    ctx.exit(result)
