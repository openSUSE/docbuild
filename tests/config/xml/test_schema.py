from pathlib import Path
import shutil
import subprocess

import pytest

# Configuration of paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR.parents[2] / "src/docbuild/config/xml/data"
SCHEMA = DATA_DIR / "portal-config.rnc"

# Local test case directories
CASES_DIR = BASE_DIR / "schema_cases"
VALID_DIR = CASES_DIR / "valid"
INVALID_DIR = CASES_DIR / "invalid"

def run_jing(xml_path: Path) -> tuple[int, str]:
    """Execute jing with full XInclude support enabled."""
    jing_bin = shutil.which("jing")
    if not jing_bin:
        pytest.skip("jing executable not found in PATH")

    xinclude_prop = "-Dorg.apache.xerces.xni.parser.XMLParserConfiguration=" \
                    "org.apache.xerces.parsers.XIncludeParserConfiguration"

    env = {
        "JAVA_OPTS": xinclude_prop,
        "JAVA_ARGS": xinclude_prop,
        "ADDITIONAL_FLAGS": xinclude_prop
    }

    cmd = [jing_bin]
    if SCHEMA.suffix == ".rnc":
        cmd.append("-c")

    cmd.extend([str(SCHEMA), str(xml_path)])

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    # Combine stdout and stderr for the error message
    output = (result.stdout + result.stderr).strip()
    return result.returncode, output


@pytest.mark.parametrize("xml_file", list(VALID_DIR.glob("*.xml")), ids=lambda p: p.name)
def test_portal_schema_valid(xml_file: Path) -> None:
    """Positive tests: These files must validate successfully."""
    exit_code, stderr = run_jing(xml_file)
    assert exit_code == 0, f"Valid file {xml_file.name} failed validation:\n{stderr}"


@pytest.mark.parametrize("xml_file", list(INVALID_DIR.glob("*.xml")), ids=lambda p: p.name)
def test_portal_schema_invalid(xml_file: Path) -> None:
    """Negative tests: These files must fail validation."""
    exit_code, _ = run_jing(xml_file)
    assert exit_code != 0, f"Invalid file {xml_file.name} unexpectedly passed validation!"
