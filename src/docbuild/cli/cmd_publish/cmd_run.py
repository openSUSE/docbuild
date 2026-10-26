"""Publish documentation deliverables to a remote server."""

import asyncio
from pathlib import Path

import click

from ...models.doctype import Doctype
from ...tasks.publish import (
    collect_publish_paths,
    publish_deliverables,
    stage_server_root_files,
)
from ...utils.sync import RsyncOptions
from ...utils.sysdeps import requires_system_tools
from ..callback import validate_doctypes
from ..completion import complete_doctypes
from ..console import console, console_err
from ..context import DocBuildContext


@click.command(
    name="run",
    help="""Publish built documentation deliverables to a remote destination.

    A document (or "doctype") consists of the following syntax:

        [PRODUCT]/[DOCSET][@LIFECYCLES]/LANGS
    """,
)
@click.argument(
    "doctypes",
    nargs=-1,
    shell_complete=complete_doctypes,
    callback=validate_doctypes,
)
@click.option(
    "--with-server-files/--without-server-files",
    "with_server_files",
    default=True,
    help="Stage and publish server root files (assets, robots.txt, etc.). Enabled by default.",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm publishing without prompting.",
)
@requires_system_tools(["rsync"])
@click.pass_obj
def run(
    context: DocBuildContext,
    doctypes: tuple[Doctype, ...] | list[Doctype],
    *,
    with_server_files: bool,
    yes: bool,
) -> None:
    """Run the publish command."""
    envconfig = context.envconfig
    if not envconfig.remote or not envconfig.remote.server or not envconfig.remote.path:
        console_err.print(
            r"[bold red]Error:[/bold red] The \[remote] section is not configured in your environment config. "
            "Publish requires both 'server' and 'path'."
        )
        raise click.exceptions.Exit(1)

    remote_server = str(envconfig.remote.server)
    remote_path = str(envconfig.remote.path)
    target_base_dir = Path(envconfig.paths.target.target_base_dir)
    target_dir_dyn = envconfig.paths.target.target_dir_dyn
    server_rootfiles_dir = (
        Path(envconfig.paths.server_rootfiles_dir) if envconfig.paths.server_rootfiles_dir else None
    )

    rsync_opts = RsyncOptions(exclude=list(envconfig.rsync.exclude))

    # 1. Optionally stage server root files
    if with_server_files and server_rootfiles_dir:
        staged = asyncio.run(
            stage_server_root_files(server_rootfiles_dir, target_base_dir, rsync_options=rsync_opts)
        )
        if not staged and not server_rootfiles_dir.is_dir():
            console.print(
                f"[yellow]Warning: Server root files directory '{server_rootfiles_dir}' not found. Continuing without it.[/yellow]"
            )

    # 2. Collect files to sync
    portal_config = context.main_portal_config
    paths_to_sync = asyncio.run(
        collect_publish_paths(
            portal_config=portal_config,
            doctypes=doctypes,
            target_base_dir=target_base_dir,
            target_dir_dyn=target_dir_dyn,
            include_server_files=with_server_files,
            server_rootfiles_dir=server_rootfiles_dir,
        )
    )

    if not paths_to_sync:
        console.print("[yellow]No deliverables or files found to publish.[/yellow]")
        raise click.exceptions.Exit(0)

    console.print(
        f"Ready to publish [bold cyan]{len(paths_to_sync)}[/bold cyan] item(s) from "
        f"[bold]{target_base_dir}[/bold] to [bold green]{remote_server}:{remote_path}[/bold green]:"
    )
    for p in paths_to_sync[:10]:
        console.print(f"  • {p}")
    if len(paths_to_sync) > 10:
        console.print(f"  [dim]... and {len(paths_to_sync) - 10} more[/dim]")

    # 3. Confirmation prompt
    if not yes:
        click.confirm("Do you want to continue?", abort=True)

    # 4. Perform remote rsync
    ret = asyncio.run(
        publish_deliverables(
            target_base_dir=target_base_dir,
            remote_server=remote_server,
            remote_path=remote_path,
            paths_to_sync=paths_to_sync,
            rsync_options=rsync_opts,
        )
    )

    if ret != 0:
        console_err.print(f"[bold red]Publish failed with returncode {ret}.[/bold red]")
        raise click.exceptions.Exit(ret)

    console.print("[bold green]Publish completed successfully![/bold green]")
