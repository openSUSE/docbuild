"""CLI command to retroactively generate Markdown and llms.txt files."""

import asyncio
import logging
from pathlib import Path
import sys

import click

from ..tasks.build.runner import generate_llmstxt
from .context import DocBuildContext

log = logging.getLogger(__name__)


@click.command(name="llms")
@click.pass_obj
def llms(context: DocBuildContext) -> None:
    """Generate Markdown and llms.txt files for an existing build directory.

    This command scans the target base directory configured in your environment
    (defined as 'paths.target' in env.toml), cleans the HTML files found within,
    converts them to Markdown, and generates the root llms.txt index file.
    """
    if not context.envconfig:
        msg = "Environment configuration not found."
        log.error(msg)
        click.echo(msg, err=True)
        sys.exit(1)

    target_dest = Path(context.envconfig.paths.target.target_base_dir)
    build_llmstxt = context.envconfig.build.build_llmstxt
    llmstxt_dir = context.envconfig.paths.llmstxt_dir

    if not build_llmstxt:
        msg = "LLMs generation is disabled in configuration (build.build_llmstxt = false)."
        log.info(msg)
        click.echo(msg)
        click.echo("To run this command, either update your env.toml or pass '-C build.build_llmstxt=true'.")
        sys.exit(0)

    if not target_dest.exists() or not target_dest.is_dir():
        msg = f"The configured target directory does not exist or is not a directory: {target_dest}"
        log.error(msg)
        click.echo(msg, err=True)
        sys.exit(1)

    msg = f"Starting retroactive LLMs generation in: {target_dest}"
    log.info(msg)
    click.echo(msg)

    # Dummy deliverable object expected by generate_llmstxt
    class DummyDeliverable:
        def __init__(self, target_dest: Path) -> None:
            self.full_id = f"retroactive_build_{target_dest.name}"

            class DummyXML:
                title = f"Documentation Index for {target_dest.name}"

            self.xml = DummyXML()

    dummy_deliverable = DummyDeliverable(target_dest)

    try:
        asyncio.run(
            generate_llmstxt(
                deliverable=dummy_deliverable,  # type: ignore
                target_dest=target_dest,
                build_llmstxt=build_llmstxt,
                llmstxt_dir=llmstxt_dir,
            )
        )
        completion_msg = "Retroactive LLMs generation completed successfully."
        log.info(completion_msg)
        click.echo(completion_msg)
    except Exception as e:
        err_msg = f"Failed to execute retroactive LLMs generation: {e}"
        log.error(err_msg)
        click.echo(err_msg, err=True)
        sys.exit(1)
