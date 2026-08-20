"""Synchronization utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import subprocess

from .shell import run_command


@dataclass(frozen=True, slots=True)
class RsyncOptions:
    """Configuration options for rsync execution."""

    archive: bool = True
    compress: bool = False
    delete: bool = False
    dry_run: bool = False
    verbose: bool = False
    partial: bool = False

    # Acts as an escape hatch for the 100+ rsync options not explicitly modeled here.
    # Users can pass arbitrary flags (e.g., ["--exclude=*.tmp", "--bwlimit=1000"]).
    extra_args: list[str] = field(default_factory=list)

    def to_args(self) -> list[str]:
        """Convert the configured options into a list of command-line arguments.

        :return: A list of string arguments formatted for the rsync command.
        """
        args: list[str] = []

        if self.archive:
            args.append("-a")
        if self.compress:
            args.append("-z")
        if self.delete:
            args.append("--delete")
        if self.dry_run:
            args.append("--dry-run")
        if self.verbose:
            args.append("-v")
        if self.partial:
            args.append("--partial")

        args.extend(self.extra_args)

        return args


async def rsync(
    source: str | os.PathLike[str],
    target: str | os.PathLike[str],
    *,
    content_only: bool | None = None,
    options: RsyncOptions | None = None,
) -> subprocess.CompletedProcess[str]:
    """Asynchronously execute the rsync command.

    :param source: Path to the source file or directory.
    :param target: Path to the target destination.
    :param content_only: If True, appends a trailing slash to the source to sync contents.
                         If None, infers the intent from the raw source string.
    :param options: Configuration object containing the rsync flags.
    :return: Process execution results containing stdout, stderr, and exit code.
    """
    options = options or RsyncOptions()

    # Inspect the raw string for a trailing slash before pathlib normalizes it
    source_str = str(source)
    has_trailing_slash = source_str.endswith(("/", "\\"))

    source_path = Path(source).expanduser()
    target_path = Path(target).expanduser()

    source_arg = str(source_path)
    if content_only is True or (content_only is None and has_trailing_slash):
        source_arg += "/"

    command = [
        "rsync",
        *options.to_args(),
        source_arg,
        str(target_path),
    ]

    return await run_command(command)
