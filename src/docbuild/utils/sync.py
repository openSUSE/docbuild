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

    archive: bool = field(
        default=True,
        metadata={"flag": "-a"},
    )
    """Enable archive mode. Preserves permissions, timestamps, and ownership."""

    compress: bool = field(
        default=False,
        metadata={"flag": "-z"},
    )
    """Enable compression during transfer. Useful for slow connections but increases CPU usage."""

    delete: bool = field(
        default=False,
        metadata={"flag": "--delete"},
    )
    """Delete files on the destination that do not exist on the source."""

    dry_run: bool = field(
        default=False,
        metadata={"flag": "--dry-run"},
    )
    """Perform a trial run showing what would be transferred without actually doing it."""

    verbose: bool = field(
        default=False,
        metadata={"flag": "-v"},
    )
    """Increase verbosity to see what rsync is doing."""

    partial: bool = field(
        default=False,
        metadata={"flag": "--partial"},
    )
    """Keep partially transferred files. Useful for resuming interrupted transfers."""

    exclude: list[str] | tuple[str, ...] = field(
        default_factory=list,
        metadata={"flag": "--exclude"},
    )
    """List of patterns to exclude from transfer. Each pattern becomes a separate --exclude flag."""

    extra_args: list[str] = field(default_factory=list)
    """Additional arbitrary rsync command-line arguments not modeled as explicit fields.
    Enables use of 100+ unsupported rsync options (e.g., ["--exclude=*.tmp", "--bwlimit=1000"]).
    """

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
                # This branch enables extensibility for future fields beyond booleans/lists.
                case _:  # pragma: no cover
                    args.extend([flag, str(value)])

        args.extend(self.extra_args)
        return args


def is_remote_path(path: str | os.PathLike[str]) -> bool:
    """Determine whether a path specification refers to a remote location in rsync syntax.

    :param path: The path string or PathLike object to evaluate.
    :return: True if the path is remote; False otherwise.
    """
    path_str = os.fspath(path)

    if path_str.startswith("rsync://"):
        return True

    if ":" in path_str:
        colon_idx = path_str.find(":")
        slash_idx = path_str.find("/")
        if slash_idx == -1 or colon_idx < slash_idx:
            return True

    return False


async def rsync(
    source: str | os.PathLike[str],
    target: str | os.PathLike[str],
    *,
    content_only: bool | None = None,
    options: RsyncOptions | None = None,
) -> subprocess.CompletedProcess[str]:
    """Asynchronously execute the rsync command.

    Supports both local and remote paths. Remote paths use rsync syntax:
    SSH (``user@host:/path``), daemon (``host::module``), or URL (``rsync://host/path``).

    :param source: Path to the source file or directory (local or remote).
    :param target: Path to the target destination (local or remote).
    :param content_only: If True, appends a trailing slash to the source to sync contents.
                         If False, ensures no trailing slash on the source to sync the directory itself.
                         If None, infers the intent from the raw source string.
    :param options: Configuration object containing the rsync flags.
    :return: Process execution results containing stdout, stderr, and exit code.
    :raises ValueError: If both source and target are remote paths.

    Example:
      * Sync from remote to local::

          await rsync("user@remote:/docs", "/local/backup")

      * Sync from local to remote (contents only)::

          await rsync("/local/docs", "remote:/backups", content_only=True)

    """
    options = options or RsyncOptions()

    source_str = os.fspath(source)
    target_str = os.fspath(target)

    source_is_remote = is_remote_path(source_str)
    target_is_remote = is_remote_path(target_str)

    if source_is_remote and target_is_remote:
        msg = "Both source and target cannot be remote paths."
        raise ValueError(msg)

    # Inspect raw string for a trailing slash before normalization
    has_trailing_slash = source_str.endswith("/")
    should_have_slash = content_only is True or (
        content_only is None and has_trailing_slash
    )

    if source_is_remote:
        # Avoid stripping root slash in 'host:/' which would turn it into 'host:' ($HOME)
        if source_str.endswith(":/"):
            base_source = source_str
        else:
            base_source = source_str.rstrip("/")
    else:
        expanded = str(Path(source).expanduser())
        base_source = expanded if expanded == "/" else expanded.rstrip("/")

    if should_have_slash:
        source_arg = base_source if base_source.endswith("/") else f"{base_source}/"
    else:
        source_arg = (
            base_source.rstrip("/")
            if base_source != "/" and not base_source.endswith(":/")
            else base_source
        )

    if target_is_remote:
        target_arg = target_str
    else:
        target_arg = str(Path(target).expanduser())

    command = [
        "rsync",
        *options.to_args(),
        source_arg,
        target_arg,
    ]

    return await run_command(command)
