"""CLI command to retroactively generate Markdown and llms.txt files.

Provide one or more doctypes in ``product/docset/lang`` format, or use
``--all`` to process all configured deliverables. The two modes are
mutually exclusive.

For standard DAPS builds, this command scans the target directory
configured in your environment (``paths.target.target_base_dir``). For
prebuilt deliverables, it locates the source HTML in
``paths.prebuilt_dir``, copies it to the target directory, and writes
the generated Markdown and ``llms.txt`` files there.

It also injects ``<link rel="alternate" type="text/markdown">`` tags
into the HTML files pointing to the generated Markdown counterparts and
``llms.txt`` index.
"""

import asyncio
from collections.abc import Sequence
import logging
from pathlib import Path
import sys

import click

from ..models.doctype import Doctype
from ..tasks.build.runner import process_llms
from .callback import validate_doctypes
from .console import console, console_err
from .context import DocBuildContext

log = logging.getLogger(__name__)


@click.command(name="llms", help=__doc__)
@click.argument(
    "doctypes",
    nargs=-1,
    callback=validate_doctypes,
)
@click.option(
    "--all",
    "process_all",
    is_flag=True,
    default=False,
    help="Generate LLMs files for all configured deliverables.",
)
@click.pass_obj
def llms(
    context: DocBuildContext,
    doctypes: Sequence[Doctype],
    process_all: bool,
) -> None:
    """Generate Markdown and llms.txt files for build or prebuilt deliverables.

    Validate that either specific ``doctypes`` or ``--all`` is provided,
    read paths and flags from the environment configuration, and run
    :func:`~docbuild.tasks.build.runner.process_llms`.

    :param context: (DocBuildContext) The shared CLI context containing
        the loaded environment configuration.
    :param doctypes: (Sequence[Doctype]) Doctype selectors to process,
        mutually exclusive with ``process_all``.
    :param process_all: (bool) Whether to process all configured
        deliverables instead of specific doctypes.
    :returns: (None) Exits the process with the status code from the
        LLMs generation pipeline.
    :raises click.UsageError: If both or neither of ``doctypes`` and
        ``--all`` are specified.
    """
    if process_all and doctypes:
        raise click.UsageError(
            "The --all option cannot be combined with doctypes. "
            "Use either --all or one or more doctypes."
        )

    if not process_all and not doctypes:
        raise click.UsageError(
            "Please specify one or more doctypes, or use --all to process all deliverables."
        )

    if not context.envconfig:
        msg = "Environment configuration not found."
        log.error(msg)
        console_err.print(f"[error]{msg}[/]")
        sys.exit(1)

    env = context.envconfig
    target_base_dir = Path(env.paths.target.target_base_dir)
    target_dir_dyn = env.paths.target.target_dir_dyn
    prebuilt_dir = Path(env.paths.prebuilt_dir)
    main_portal_config = Path(env.paths.main_portal_config)
    build_llmstxt = env.build.build_llmstxt
    llmstxt_dir = str(env.paths.llmstxt_dir)
    canonical_domain = str(env.general.canonical_url_domain)

    if not build_llmstxt:
        msg = "LLMs generation is disabled in configuration (build.build_llmstxt = false)."
        log.info(msg)
        console.print(f"[warning]{msg}[/]")
        console.print("[hint]To run this command, either update your env.toml or pass '-C build.build_llmstxt=true'.[/]")
        sys.exit(0)

    selected = list(doctypes) if doctypes else None

    msg = f"Starting retroactive LLMs generation in: {target_base_dir}"
    log.info(msg)
    console.print(f"[header]{msg}[/]")

    try:
        result = asyncio.run(
            process_llms(
                main_portal_config=main_portal_config,
                target_base_dir=target_base_dir,
                target_dir_dyn=target_dir_dyn,
                prebuilt_dir=prebuilt_dir,
                build_llmstxt=build_llmstxt,
                llmstxt_dir=llmstxt_dir,
                doctypes=selected,
                canonical_domain=canonical_domain,
            )
        )
        if result != 0:
            err_msg = f"Failed to execute retroactive LLMs generation in: {target_base_dir}"
            log.error(err_msg)
            console_err.print(f"[error]{err_msg}[/]")
            sys.exit(result)

        completion_msg = "Retroactive LLMs generation completed successfully."
        log.info(completion_msg)
        console.print(f"[success]{completion_msg}[/]")
    except Exception as e:
        err_msg = f"Failed to execute retroactive LLMs generation: {e}"
        log.error(err_msg)
        console_err.print(f"[error]{err_msg}[/]")
        sys.exit(1)
