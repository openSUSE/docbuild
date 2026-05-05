"""Custom PEP 517 build backend to convert RNC schemas to RNG before packaging."""

from pathlib import Path
import subprocess
from typing import Any
import sys

from setuptools import build_meta as _orig  # type: ignore

# Proxy the required PEP 517 hooks to standard setuptools
prepare_metadata_for_build_wheel = _orig.prepare_metadata_for_build_wheel
get_requires_for_build_wheel = _orig.get_requires_for_build_wheel
get_requires_for_build_sdist = _orig.get_requires_for_build_sdist

# Proxy PEP 660 editable install hooks to standard setuptools
get_requires_for_build_editable = getattr(_orig, "get_requires_for_build_editable", None)
prepare_metadata_for_build_editable = getattr(_orig, "prepare_metadata_for_build_editable", None)


def run_trang() -> None:
    """Find and convert .rnc files to .rng using trang."""
    # Based on pyproject.toml, the data is in src/docbuild/config/xml/data/
    data_dir = Path("src") / "docbuild" / "config" / "xml" / "data"

    if not data_dir.exists():
        return

    # Find all .rnc files in the directory
    for rnc_path in data_dir.glob("*.rnc"):
        rng_path = rnc_path.with_suffix(".rng")

        print(f"--- Custom Build Hook: Converting {rnc_path} to {rng_path} ---")
        try:
            # Run trang command
            subprocess.run(["trang", str(rnc_path), str(rng_path)], check=True)
            print(f"Successfully converted {rnc_path} -> {rng_path}")
        except FileNotFoundError:
            print(
                "WARNING: 'trang' command not found. "
                "Ensure it is installed to generate RNG schemas.",
                file=sys.stderr
            )
        except subprocess.CalledProcessError as e:
            print(f"ERROR: trang conversion failed for {rnc_path}", file=sys.stderr)


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    """Build a wheel.

    :param wheel_directory: The directory where the wheel should be placed.
    :param config_settings: Optional configuration settings for the build.
    :param metadata_directory: Optional directory for metadata.
    """
    run_trang()
    return _orig.build_wheel(wheel_directory, config_settings, metadata_directory)


def build_sdist(
    sdist_directory: str,
    config_settings: dict[str, Any] | None = None,
) -> str:
    """Build a source distribution.

    :param sdist_directory: The directory where the source distribution should be placed.
    :param config_settings: Optional configuration settings for the build.
    """
    run_trang()
    return _orig.build_sdist(sdist_directory, config_settings)


def build_editable(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    """Build an editable wheel for local development/CI.

    :param wheel_directory: The directory where the wheel should be placed.
    :param config_settings: Optional configuration settings for the build.
    :param metadata_directory: Optional directory for metadata.
    """
    run_trang()
    return _orig.build_editable(wheel_directory, config_settings, metadata_directory)
