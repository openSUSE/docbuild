"""System dependency validation and version checking."""

from collections.abc import Callable
from functools import wraps
import re
import shutil
import subprocess
from typing import ParamSpec, TypedDict, TypeVar

import click
from packaging.version import parse as parse_version

P = ParamSpec("P")
T = TypeVar("T")

# First-order dependencies required by docbuild
SYSTEM_DEPENDENCIES = {
    "jing": ">=20220510",
    "trang": None,  # Any version
    "daps": ">=4",
    "xmllint": None,
    "xsltproc": None,
}


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

        # Compare semantic versions
        try:
            v_found = parse_version(found_version)
            v_min = parse_version(min_v)
            is_valid = False

            if op == ">=":
                is_valid = v_found >= v_min
            elif op == "==":
                is_valid = v_found == v_min
            elif op == ">":
                is_valid = v_found > v_min

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


def requires_system_tools(tools: list[str]) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Enforce system dependencies on specific CLI commands.

    :param tools: A list of tool names (e.g., ["daps", "xmllint"]) that must be present.
    """
    def decorator(f: Callable[P, T]) -> Callable[P, T]:
        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            missing_tools = []

            # Check the requested tools against our SYSTEM_DEPENDENCIES definition
            for tool_name in tools:
                req = SYSTEM_DEPENDENCIES.get(tool_name)

                # 1. Check if it's installed at all
                if shutil.which(tool_name) is None:
                    missing_tools.append(f"'{tool_name}' (missing)")
                    continue

                # 2. Check version if a requirement exists
                if req:
                    found_v = get_binary_version(tool_name)
                    req_match = re.match(r"^\s*(>=|==|>)\s*([\d\.]+)", req)

                    if found_v and req_match:
                        op, min_v = req_match.groups()
                        try:
                            v_found = parse_version(found_v)
                            v_min = parse_version(min_v)
                            if op == ">=" and not (v_found >= v_min):
                                missing_tools.append(f"'{tool_name}' (needs {req}, found {found_v})")
                        except Exception:
                            pass # If we can't parse it, we give it a pass rather than crashing

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
