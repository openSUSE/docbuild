"""CLI command to retroactively generate Markdown and llms.txt files."""

import asyncio
import logging
from pathlib import Path
import sys

import click

from ...config.app import normalize_runtime_placeholders
from ...models.doctype import Doctype
from ...tasks.build.runner import generate_llmstxt
from ..callback import validate_doctypes
from ..completion import complete_doctypes
from ..context import DocBuildContext

log = logging.getLogger(__name__)


def _resolve_targets(target_base: Path, target_dir_dyn: str, doctypes: tuple[Doctype, ...]) -> set[Path]:
    """Resolve specific directories to process based on doctypes or --all flag."""
    if not doctypes:
        return {target_base}

    targets_to_process: set[Path] = set()
    missing_doctypes: list[str] = []

    # Prepare the template string to correctly construct directory paths
    dyn_template = normalize_runtime_placeholders(target_dir_dyn)

    for dt in doctypes:
        prod_str = dt.product.acronym if dt.product else "*"
        docsets = dt.docset if dt.docset and "*" not in dt.docset else ["*"]
        langs = [lang.language for lang in dt.langs] if dt.langs else ["*"]

        found_match = False
        for ds in docsets:
            for lang in langs:
                # Use the dynamic template to build the expected relative path string
                search_path = dyn_template.format(lang=lang, language=lang, product=prod_str, version=ds, docset=ds)

                # Glob the target base with our dynamic path
                for match in target_base.glob(search_path):
                    if match.is_dir():
                        targets_to_process.add(match)
                        found_match = True

        if not found_match:
            missing_doctypes.append(str(dt))

    if missing_doctypes:
        msg = f"No matching directories found for: {', '.join(missing_doctypes)}"
        log.warning(msg)
        click.echo(msg)

    return targets_to_process


@click.command(name="llms")
@click.argument(
    "doctypes", nargs=-1, callback=validate_doctypes, shell_complete=complete_doctypes
)
@click.option(
    "--all", "all_docs", is_flag=True, default=False,
    help="Traverse the complete target directory regardless of doctypes."
)
@click.pass_obj
def llms(context: DocBuildContext, doctypes: tuple[Doctype, ...], all_docs: bool) -> None:
    """Generate Markdown and llms.txt files for an existing build directory.

    This command scans the target base directory configured in your environment
    (defined as 'paths.target.target_base_dir' in env.toml), cleans the HTML
    files found within, converts them to Markdown, and generates the root
    llms.txt index file.

    You can limit the conversion to specific products or docsets by passing
    doctypes (e.g., sles/15-SP3). Use --all to process the entire target directory.
    """
    if all_docs and doctypes:
        msg = "The --all flag cannot be used alongside specific doctypes."
        log.error(msg)
        click.echo(msg, err=True)
        sys.exit(1)

    if not doctypes and not all_docs:
        msg = "You must provide at least one doctype or use the --all flag to process the entire directory."
        log.error(msg)
        click.echo(msg, err=True)
        sys.exit(1)

    if not context.envconfig:
        msg = "Environment configuration not found."
        log.error(msg)
        click.echo(msg, err=True)
        sys.exit(1)

    target_base = Path(context.envconfig.paths.target.target_base_dir)
    target_dir_dyn = context.envconfig.paths.target.target_dir_dyn
    build_llmstxt = context.envconfig.build.build_llmstxt

    # Resolve llmstxt_dir: if absolute, keep it; if relative, base it on target_base
    configured_llms_dir = Path(context.envconfig.paths.llmstxt_dir)
    llmstxt_dir = configured_llms_dir if configured_llms_dir.is_absolute() else target_base / configured_llms_dir

    if not build_llmstxt:
        msg = "LLMs generation is disabled in configuration (build.build_llmstxt = false)."
        log.info(msg)
        click.echo(msg)
        click.echo("To run this command, either update your env.toml or pass '-C build.build_llmstxt=true'.")
        sys.exit(0)

    # Note: Pydantic validates target_base exists, but we ensure it's a directory here
    if not target_base.is_dir():
        msg = f"The configured target directory is not a directory: {target_base}"
        log.error(msg)
        click.echo(msg, err=True)
        sys.exit(1)

    targets_to_process = _resolve_targets(
        target_base=target_base,
        target_dir_dyn=target_dir_dyn,
        doctypes=() if all_docs else doctypes
    )

    if not targets_to_process:
        sys.exit(0)

    # Dummy deliverable object expected by generate_llmstxt
    class DummyDeliverable:
        def __init__(self, target_dest: Path) -> None:
            self.full_id = f"retroactive_build_{target_dest.name}"

            class DummyXML:
                title = f"Documentation Index for {target_dest.name}"

            self.xml = DummyXML()

    # Process all resolved targets
    try:
        for target_dest in targets_to_process:
            msg = f"Starting retroactive LLMs generation in: {target_dest}"
            log.info(msg)
            click.echo(msg)

            dummy_deliverable = DummyDeliverable(target_dest)

            asyncio.run(
                generate_llmstxt(
                    deliverable=dummy_deliverable,  # type: ignore
                    target_dest=target_dest,
                    build_llmstxt=build_llmstxt,
                    llmstxt_dir=str(llmstxt_dir),
                )
            )
            completion_msg = f"Retroactive LLMs generation completed successfully for {target_dest.name}."
            log.info(completion_msg)
            click.echo(completion_msg)

    except Exception as e:
        err_msg = f"Failed to execute retroactive LLMs generation: {e}"
        log.error(err_msg)
        click.echo(err_msg, err=True)
        sys.exit(1)
