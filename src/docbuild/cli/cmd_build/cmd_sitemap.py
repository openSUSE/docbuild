"""CLI command to generate a sitemap."""

import asyncio

import click

from ...tasks.sitemap import generate_sitemap
from ..console import console
from ..context import DocBuildContext


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

    target_base_dir = env.paths.target.target_base_dir
    base_url = str(env.canonical_url_domain)

    async def main() -> int:
        console.print(f"Generating sitemap.xml in {target_base_dir}...", style="green")
        await generate_sitemap(target_base_dir, base_url)
        return 0

    result = asyncio.run(main())
    ctx.exit(result)
