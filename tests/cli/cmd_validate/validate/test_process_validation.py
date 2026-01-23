from pathlib import Path
import shutil
from subprocess import CompletedProcess
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

import docbuild.cli.cmd_validate.process as process_mod
from docbuild.cli.context import DocBuildContext


def is_jing_installed():
    return shutil.which("jing") is not None


async def test_run_command():
    """Test the run_command function."""
    command = ["echo", "Hello, World!"]

    process = await process_mod.run_command(command)

    assert process.returncode == 0, \
        f"Expected return code 0, got {process.returncode}"
    assert process.stdout.strip() == "Hello, World!", \
        f"Unexpected stdout: {process.stdout}"
    assert process.stderr == "", f"Unexpected stderr: {process.stderr}"


@pytest.mark.skipif(not is_jing_installed(), reason="jing command not found")
async def test_validate_rng_with_rng_suffix(tmp_path: Path):
    """Test validate_rng with a schema file having a .rng suffix."""
    xmlfile = tmp_path / Path("file.xml")
    xmlfile.write_text("""<root/>""")

    rng_schema = tmp_path / Path("schema.rng")
    rng_schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
  <start><element name="root"><text/></element></start>
</grammar>""")

    proc = await process_mod.validate_rng(xmlfile, rng_schema)

    assert proc.returncode == 0, f"Expected return code 0, got {proc.returncode}"


@pytest.mark.skipif(not is_jing_installed(), reason="jing command not found")
async def test_validate_rng_with_invalid_xml(tmp_path: Path):
    """Test validate_rng with an invalid XML file."""
    xmlfile = tmp_path / Path("file.xml")
    xmlfile.write_text("""<wrong_root/>""")

    rng_schema = tmp_path / Path("schema.rng")
    rng_schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start><element name="root"><text/></element></start>
</grammar>""")

    proc = await process_mod.validate_rng(xmlfile, rng_schema)
    assert proc.returncode != 0, f"Expected non-zero return code, got {proc.returncode}"
    assert 'error: element "wrong_root"' in (proc.stdout + proc.stderr)


@pytest.mark.skipif(not is_jing_installed(), reason="jing command not found")
async def test_validate_rng_without_xinclude(tmp_path: Path):
    """Test validate_rng with xinclude set to False."""
    xmlfile = tmp_path / Path("file.xml")
    xmlfile.write_text("""<root/>""")

    rng_schema = tmp_path / Path("schema.rng")
    rng_schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start><element name="root"><text/></element></start>
</grammar>""")

    proc = await process_mod.validate_rng(xmlfile, rng_schema, xinclude=False)

    assert proc.returncode == 0, f"Expected return code 0, got {proc.returncode}"


@pytest.mark.skipif(not is_jing_installed(), reason="jing command not found")
async def test_validate_rng_with_invalid_xml_without_xinclude(tmp_path: Path):
    """Test validate_rng with xinclude set to False."""
    xmlfile = tmp_path / Path("file.xml")
    xmlfile.write_text("""<wrong_root/>""")

    rng_schema = tmp_path / Path("schema.rng")
    rng_schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start><element name="root"><text/></element></start>
</grammar>""")

    proc = await process_mod.validate_rng(xmlfile, rng_schema, xinclude=False)

    assert proc.returncode != 0, f"Expected non-zero return code, got {proc.returncode}"
    assert 'element "wrong_root" not allowed anywhere' in (proc.stdout + proc.stderr)


async def test_validate_rng_jing_failure():
    """Test validate_rng when jing fails."""
    xmlfile = MagicMock(spec=Path)
    rng_schema = MagicMock(spec=Path)
    xmlfile.__str__.return_value = "/mocked/path/to/file.xml"
    rng_schema.__str__.return_value = "/mocked/path/to/schema.rng"

    with patch.object(
        process_mod,
        "run_command",
        new=AsyncMock(
            return_value=CompletedProcess(
                args=["jing", xmlfile, rng_schema],
                returncode=1,
                stdout="Error in jing",
                stderr="",
            )
        ),
    ) as mock_run_command:
        proc = await process_mod.validate_rng(
            xmlfile, rng_schema_path=rng_schema, xinclude=False, idcheck=False
        )

        assert proc.returncode != 0, "Expected validation to fail."
        assert proc.stdout == "Error in jing", f"Unexpected stdout: {proc.stdout}"

        mock_run_command.assert_called_once_with(
            ["jing", str(rng_schema), str(xmlfile)]
        )


async def test_validate_rng_command_not_found():
    """Test validate_rng when a command is not found and has a filename."""
    xmlfile = MagicMock(spec=Path)
    rng_schema = MagicMock(spec=Path)
    xmlfile.__str__.return_value = "/mocked/path/to/file.xml"
    rng_schema.__str__.return_value = "/mocked/path/to/schema.rng"

    error = FileNotFoundError(2, "No such file or directory")
    error.filename = "jing"

    with patch.object(
        process_mod, "run_command", new_callable=AsyncMock, side_effect=error
    ):
        proc = await process_mod.validate_rng(
            xmlfile, rng_schema_path=rng_schema, xinclude=False
        )

    assert proc.returncode != 0, "Expected validation to fail."
    assert proc.stderr == "jing command not found. Please install it to run validation."


async def test_validate_rng_command_not_found_no_filename():
    """Test validate_rng when FileNotFoundError has no filename attribute."""
    xmlfile = MagicMock(spec=Path)
    rng_schema = MagicMock(spec=Path)
    error = FileNotFoundError(2, "No such file or directory")
    error.filename = None

    with patch.object(
        process_mod, "run_command", new_callable=AsyncMock, side_effect=error
    ):
        proc = await process_mod.validate_rng(xmlfile, rng_schema, xinclude=False)

    assert proc.returncode != 0, "Expected validation to fail."
    assert (
        proc.stderr
        == "xmllint/jing command not found. Please install it to run validation."
    )


async def test_process_file_with_validation_issues(capsys, tmp_path):
    with patch.object(
        process_mod,
        "validate_rng",
        new=AsyncMock(
            return_value=CompletedProcess(
                args=["jing"], returncode=1, stdout="", stderr="Validation error"
            )
        ),
    ):
        dir_path = tmp_path / "path" / "to"
        dir_path.mkdir(parents=True)
        xmlfile = dir_path / "file.xml"
        xmlfile.touch()

        mock_context = Mock(spec=DocBuildContext)
        mock_context.verbose = 2
        mock_context.validation_method = "jing"  # <-- Use 'jing' or 'lxml'

        result = await process_mod.process_file(xmlfile, mock_context, 40)

        assert result == 10  # RNG validation failure code


async def test_process_file_with_xmlsyntax_error(capsys, tmp_path):
    dir_path = tmp_path / "path" / "to"
    dir_path.mkdir(parents=True)
    xmlfile = dir_path / "file.xml"
    xmlfile.write_text("""<root><invalid></root>""")

    mock_context = Mock(spec=DocBuildContext)
    mock_context.verbose = 2
    mock_context.validation_method = "jing"

    with (
        patch.object(
            process_mod.etree,
            "parse",
            new=Mock(
                side_effect=process_mod.etree.XMLSyntaxError(
                    "XML syntax error", None, 0, 0, "fake.xml"
                )
            ),
        ),
        patch.object(
            process_mod,
            "validate_rng",
            new=AsyncMock(
                return_value=CompletedProcess(
                    args=["jing"], returncode=0, stdout="", stderr=""
                )
            ),
        ),
    ):
        result = await process_mod.process_file(xmlfile, mock_context, 40)

    assert result == 20


def test_validate_rng_lxml_success(monkeypatch):
    """When RelaxNG validates the XML, function returns (True, '')."""
    fake_xml_doc = object()

    # parse called twice: first for schema, second for xml file
    calls = {"n": 0}

    def fake_parse(path):
        calls["n"] += 1
        return object() if calls["n"] == 1 else fake_xml_doc

    monkeypatch.setattr(process_mod.etree, "parse", fake_parse)

    fake_relaxng = Mock()
    fake_relaxng.validate.return_value = True
    monkeypatch.setattr(process_mod.etree, "RelaxNG", lambda doc: fake_relaxng)

    ok, msg = process_mod.validate_rng_lxml(Path("/tmp/f.xml"), Path("/tmp/schema.rng"))
    assert ok is True
    assert msg == ""


def test_validate_rng_lxml_validation_failure(monkeypatch):
    """When RelaxNG.validate() returns False, function returns (False, error_log)."""
    monkeypatch.setattr(process_mod.etree, "parse", lambda p: object())
    fake_relaxng = Mock()
    fake_relaxng.validate.return_value = False
    fake_relaxng.error_log = "some relaxng errors"
    monkeypatch.setattr(process_mod.etree, "RelaxNG", lambda doc: fake_relaxng)

    ok, msg = process_mod.validate_rng_lxml(Path("/tmp/f.xml"), Path("/tmp/schema.rng"))
    assert ok is False
    assert "some relaxng errors" in msg


def test_validate_rng_lxml_xml_syntax_error(monkeypatch):
    """If lxml raises XMLSyntaxError, function returns a descriptive message."""

    def raise_syntax(path):
        raise process_mod.etree.XMLSyntaxError("bad xml", None, 0, 0, "file")

    monkeypatch.setattr(process_mod.etree, "parse", raise_syntax)

    ok, msg = process_mod.validate_rng_lxml(Path("/tmp/f.xml"), Path("/tmp/schema.rng"))
    assert ok is False
    assert "XML or RNG syntax error" in msg


def test_validate_rng_lxml_relaxng_parse_error(monkeypatch):
    """If RelaxNG constructor raises RelaxNGParseError, return an error message."""
    monkeypatch.setattr(process_mod.etree, "parse", lambda p: object())

    def raise_relaxng(doc):
        raise process_mod.etree.RelaxNGParseError("schema parse failure")

    monkeypatch.setattr(process_mod.etree, "RelaxNG", raise_relaxng)

    ok, msg = process_mod.validate_rng_lxml(Path("/tmp/f.xml"), Path("/tmp/schema.rng"))
    assert ok is False
    assert "RELAX NG schema parsing error" in msg


def test_validate_rng_lxml_generic_exception(monkeypatch):
    """Any other exception is caught and reported as an unexpected error."""
    monkeypatch.setattr(process_mod.etree, "parse", lambda p: object())

    def raise_generic(doc):
        raise Exception("boom")

    monkeypatch.setattr(process_mod.etree, "RelaxNG", raise_generic)

    ok, msg = process_mod.validate_rng_lxml(Path("/tmp/f.xml"), Path("/tmp/schema.rng"))
    assert ok is False
    assert "An unexpected error occurred during validation" in msg
