"""Schema loader and converter for RELAX NG."""
from pathlib import Path
import shutil
import subprocess
import tempfile

from lxml import etree  # type: ignore[import-untyped]
from sphinx.errors import ExtensionError


def check_trang_availability() -> None:
    """Check if the 'trang' command is available in the environment."""
    if shutil.which("trang") is None:
        raise ExtensionError(
            "The 'trang' command is required for rnc2html extension but was not found. "
            "Please install trang (e.g., 'zypper in trang' or 'apt install trang')."
        )


def load_schema(schema_path: str | Path) -> etree._ElementTree:
    """Load a RELAX NG schema, converting from RNC if necessary.

    :param schema_path: Path to the schema file (.rnc or .rng)
    :return: The parsed ElementTree
    :raises ExtensionError: If conversion fails or format is unsupported
    :raises FileNotFoundError: If file does not exist
    """
    path = Path(schema_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {path}")

    if path.suffix.lower() == ".rnc":
        check_trang_availability()
        return _convert_and_load_rnc(path)
    elif path.suffix.lower() == ".rng":
        try:
            return etree.parse(str(path))
        except etree.XMLSyntaxError as e:
            raise ExtensionError(f"Failed to parse RNG: {e}") from e
    else:
        raise ExtensionError(f"Unsupported schema format: {path.suffix}")


def _convert_and_load_rnc(rnc_path: Path) -> etree._ElementTree:
    """Convert RNC to RNG using trang and load it."""
    with tempfile.NamedTemporaryFile(suffix=".rng", delete=False) as tmp:
        output_path = Path(tmp.name)
        # Close the file immediately so subprocess can write to it safely on all OSs
        tmp.close()

    try:
        # Run trang
        cmd = ["trang", "-I", "rnc", "-O", "rng", str(rnc_path), str(output_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            raise ExtensionError(
                f"Failed to convert RNC to RNG using 'trang':\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            )

        # Load the resulting RNG
        try:
            tree = etree.parse(str(output_path))
        except etree.XMLSyntaxError as e:
            raise ExtensionError(f"Failed to parse converted RNG: {e}") from e

        return tree

    finally:
        # Cleanup
        if output_path.exists():
            output_path.unlink()
