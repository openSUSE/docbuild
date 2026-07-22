"""System dependency validation and version checking."""

from collections.abc import Callable
from functools import wraps
import re
import shutil
import subprocess
from typing import ParamSpec, TypedDict, TypeVar

import click
import semver

from ..constants import SYSTEM_DEPENDENCIES

P = ParamSpec("P")
T = TypeVar("T")


class DependencyStatus(TypedDict):
    """Data structure for returning the status of a dependency."""

    name: str
    required: str | None
    found: str | None
    is_installed: bool
    is_valid: bool
    message: str


def get_binary_version(name: str) -> str | None:
    """Run a tool and attempt to extract its version string using regex."""
    try:
        # Most tools respond to --version on either stdout or stderr
        result = subprocess.run(
            [name, "--version"], capture_output=True, text=True, check=False
        )
        output = result.stdout.strip() or result.stderr.strip()

        # Extract the first sequence of numbers and dots (e.g., "1.2.3" or "20220510")
        match = re.search(r"(\d+(?:\.\d+)*)", output)
        if match:
            return match.group(1)
    except Exception:
        pass

    return None


def _coerce_semver(version_str: str) -> semver.Version:
    """Convert loose version strings to strict SemVer objects."""
    # Handle pure integers (e.g., "4") via the native class constructor
    if version_str.isdigit():
        return semver.Version(int(version_str))

    # Pad incomplete versions (like "3.4") with zeros so they parse strictly
    parts = version_str.split(".")
    while len(parts) < 3:
        parts.append("0")

    # Strictly take the first 3 parts (in case of weird 4-part OS versions)
    return semver.Version.parse(".".join(parts[:3]))


def check_dependencies() -> list[DependencyStatus]:
    """Check all defined system dependencies and return their status."""
    results: list[DependencyStatus] = []

    for name, requirement in SYSTEM_DEPENDENCIES.items():
        is_installed = shutil.which(name) is not None

        if not is_installed:
            results.append({
                "name": name,
                "required": requirement,
                "found": None,
                "is_installed": False,
                "is_valid": False,
                "message": "Not found in PATH",
            })
            continue

        found_version = get_binary_version(name)

        if requirement is None:
            # Tool exists, and any version is fine
            results.append({
                "name": name,
                "required": "Any",
                "found": found_version or "Unknown",
                "is_installed": True,
                "is_valid": True,
                "message": "OK",
            })
            continue

        # Parse requirement (e.g. ">=20220510")
        req_match = re.match(r"^\s*(>=|==|>)\s*([\d\.]+)", requirement)
        if not req_match:
            results.append({
                "name": name,
                "required": requirement,
                "found": found_version,
                "is_installed": True,
                "is_valid": True,  # Cannot parse req, assume OK but warn
                "message": f"Cannot parse requirement: {requirement}",
            })
            continue

        op, min_v = req_match.groups()

        if found_version is None:
             results.append({
                "name": name,
                "required": requirement,
                "found": "Unknown",
                "is_installed": True,
                "is_valid": True,
                "message": "Warning: Could not determine version",
            })
             continue

        # Compare semantic versions using semver's match expression
        try:
            v_found = _coerce_semver(found_version)

            # The right side of the expression also needs to be strictly formatted
            v_min_strict = str(_coerce_semver(min_v))

            # Evaluate using semver's match engine (e.g., v_found.match(">=4.0.0"))
            is_valid = v_found.match(f"{op}{v_min_strict}")

            results.append({
                "name": name,
                "required": requirement,
                "found": found_version,
                "is_installed": True,
                "is_valid": is_valid,
                "message": "OK" if is_valid else "Version too old",
            })
        except Exception:
             results.append({
                "name": name,
                "required": requirement,
                "found": found_version,
                "is_installed": True,
                "is_valid": True,
                "message": "Warning: Version comparison failed",
            })

    return results


def requires_system_tools(tools: list[str] | None = None) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Enforce system dependencies on specific CLI commands.

    :param tools: A list of tool names. Defaults to all SYSTEM_DEPENDENCIES.
    """
    if tools is None:
        tools = list(SYSTEM_DEPENDENCIES.keys())

    def decorator(f: Callable[P, T]) -> Callable[P, T]:
        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            missing_tools = []

            # Use our central checking engine instead of duplicating complex logic
            statuses = check_dependencies()

            for status in statuses:
                if status["name"] in tools:
                    if not status["is_installed"]:
                        missing_tools.append(f"'{status['name']}' (missing)")
                    elif not status["is_valid"]:
                        missing_tools.append(
                            f"'{status['name']}' (needs {status['required']}, found {status['found']})"
                        )

            if missing_tools:
                click.secho(
                    "Error: This command requires system dependencies that are missing or outdated:\n  " +
                    "\n  ".join(missing_tools) +
                    "\n\nRun 'docbuild doctor' for a complete system check.",
                    fg="red", err=True
                )
                click.get_current_context().exit(1)

            return f(*args, **kwargs)
        return wrapper
    return decorator
