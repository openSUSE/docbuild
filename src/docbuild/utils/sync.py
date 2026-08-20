"""Synchronization utilities."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
import os
from pathlib import Path
import subprocess

from .shell import run_command


@dataclass(frozen=True, slots=True)
class RsyncOptions:
    """Configuration options for rsync execution."""

    # Store the CLI flag directly in the field's metadata
    archive: bool = field(default=True, metadata={"flag": "-a"})
    compress: bool = field(default=False, metadata={"flag": "-z"})
    delete: bool = field(default=False, metadata={"flag": "--delete"})
    dry_run: bool = field(default=False, metadata={"flag": "--dry-run"})
    verbose: bool = field(default=False, metadata={"flag": "-v"})
    partial: bool = field(default=False, metadata={"flag": "--partial"})

    exclude: list[str] | tuple[str, ...] = field(
        default_factory=list, metadata={"flag": "--exclude"}
    )

    # Acts as an escape hatch for the 100+ rsync options not explicitly modeled here.
    # Users can pass arbitrary flags (e.g., ["--exclude=*.tmp", "--bwlimit=1000"]).
    extra_args: list[str] = field(default_factory=list)

    def to_args(self) -> list[str]:
        """Convert the configured options into a list of command-line arguments.

        :return: A list of string arguments formatted for the rsync command.
        """
        args: list[str] = []

        for f in fields(self):
            # Retrieve the flag string from metadata (returns None if not present)
            flag = f.metadata.get("flag")
            if not flag:
                continue

            # Get the actual value the user provided for this instance
            value = getattr(self, f.name)

            match value:
                # Append the flag if the boolean is True (e.g., archive=True -> "-a")
                case True:
                    args.append(flag)

                # Skip the flag entirely if it is False or explicitly set to None
                case False | None:
                    pass

                # Expand lists or tuples by repeating the flag for each item
                # (e.g., ["*.tmp", ".git"] -> "--exclude", "*.tmp", "--exclude", ".git")
                case list() | tuple():
                    for item in value:
                        args.extend([flag, str(item)])

                # Catch-all for single configuration values like strings or integers
                # (e.g., timeout=60 -> "--timeout", "60")
                case _:
                    args.extend([flag, str(value)])

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
