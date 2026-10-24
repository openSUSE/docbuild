"""Tests for the XML validation tasks."""

from pathlib import Path
import shutil
from subprocess import CompletedProcess
import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from lxml import etree  # type: ignore
import pytest

from docbuild.config.xml.checks import CheckResult
from docbuild.tasks import portal as portal_task
from docbuild.tasks.portal import ValidationResult, validate_portal_config, validate_rng


def is_jing_installed():
    return sys.platform != "darwin" and shutil.which("jing") is not None


# --- Core Logic & Parsing Tests ---

@patch.object(portal_task, "run_validation", new_callable=AsyncMock)
@patch.object(portal_task.etree, "parse", side_effect=ValueError("Generic test error"))
async def test_validate_portal_config_generic_parsing_error(
    mock_etree_parse, mock_run_validation, tmp_path
):
    mock_run_validation.return_value = ValidationResult(True, 0, "")
    xml_file = tmp_path / "file.xml"
    xml_file.touch()
    schema = tmp_path / "schema.rnc"

    with pytest.raises(ValueError, match=str(mock_etree_parse.side_effect)):
        await validate_portal_config(xml_file, schema, verbose=3)

    mock_run_validation.assert_awaited_once()
    mock_etree_parse.assert_called_once()


@patch.object(portal_task, "display_results")
@patch.object(portal_task, "run_python_checks", new_callable=AsyncMock)
async def test_run_checks_and_display_skips_render(mock_run_python_checks, mock_display_results):
    mock_run_python_checks.return_value = []
    success = await portal_task.run_checks_and_display(MagicMock(), verbose=2)
    assert success is True
    mock_display_results.assert_not_called()


async def test_cache_resolved_portal_config_returns_none(tmp_path):
    tree = etree.ElementTree(etree.Element("portal"))
    cached_path = await portal_task.cache_resolved_portal_config(
        tree, tmp_path / "portal.xml", base_server_cache_dir=None
    )
    assert cached_path is None


async def test_cache_resolved_portal_config_writes_xml(tmp_path):
    cache_dir = tmp_path / "cache"
    tree = etree.ElementTree(etree.Element("portal"))
    main_portal_config = tmp_path / "portal.xml"

    cached_path = await portal_task.cache_resolved_portal_config(
        tree, main_portal_config, base_server_cache_dir=cache_dir
    )

    assert cached_path is not None
    assert cached_path == Path(cache_dir) / "portal.resolved.xml"
    assert cached_path.exists()


# --- Command Execution Tests ---

async def test_run_command():
    command = ["echo", "Hello, World!"]
    process = await portal_task.run_command(command)
    assert process.returncode == 0
    assert process.stdout.strip() == "Hello, World!"


# --- Jing / RELAX NG Validation Tests ---

@patch.object(portal_task, "run_command", new_callable=AsyncMock)
async def test_validate_rng_with_idcheck_success(mock_run_command, tmp_path):
    mock_run_command.return_value = CompletedProcess(
        args=["fake-command"], returncode=0, stdout="", stderr=""
    )
    xml_file = tmp_path / "valid.xml"
    rng_schema = tmp_path / "schema.rnc"

    proc = await validate_rng(xml_file, rng_schema, xinclude=False, idcheck=True)
    assert proc.returncode == 0
    assert "-i" not in mock_run_command.call_args.args[0]


@patch.object(portal_task, "run_command", new_callable=AsyncMock)
async def test_validate_rng_with_idcheck_duplicate_failure(mock_run_command, tmp_path):
    mock_run_command.return_value = CompletedProcess(
        args=["fake-command"], returncode=1, stdout="", stderr='error: duplicate ID "test-id"'
    )
    xml_file = tmp_path / "duplicate_id.xml"
    rng_schema = tmp_path / "schema.rnc"

    proc = await validate_rng(xml_file, rng_schema, xinclude=False, idcheck=True)
    assert proc.returncode != 0
    assert "duplicate ID" in proc.stderr
    assert "-i" not in mock_run_command.call_args.args[0]


@patch.object(portal_task, "run_command", new_callable=AsyncMock)
async def test_validate_rng_without_idcheck_success(mock_run_command, tmp_path):
    mock_run_command.return_value = CompletedProcess(
        args=["fake-command"], returncode=0, stdout="", stderr=""
    )
    xml_file = tmp_path / "duplicate_id.xml"
    rng_schema = tmp_path / "schema.rnc"

    proc = await validate_rng(xml_file, rng_schema, xinclude=False, idcheck=False)
    assert proc.returncode == 0
    assert "-i" in mock_run_command.call_args.args[0]


@pytest.mark.skipif(not is_jing_installed(), reason="jing not found")
async def test_validate_rng_with_rnc_suffix(tmp_path: Path):
    xmlfile = tmp_path / Path("file.xml")
    xmlfile.write_text("<root/>")
    rnc_schema = tmp_path / Path("schema.rnc")
    rnc_schema.write_text("start = element root { text }")

    proc = await portal_task.validate_rng(xmlfile, rnc_schema)
    assert proc.returncode == 0


@pytest.mark.skipif(not is_jing_installed(), reason="jing not found")
async def test_validate_rng_with_invalid_xml(tmp_path: Path):
    xmlfile = tmp_path / Path("file.xml")
    xmlfile.write_text("<wrong_root/>")
    rng_schema = tmp_path / Path("schema.rng")
    rng_schema.write_text(
        '<?xml version="1.0"?><grammar xmlns="http://relaxng.org/ns/structure/1.0">'
        '<start><element name="root"><text/></element></start></grammar>'
    )
    proc = await portal_task.validate_rng(xmlfile, rng_schema)
    assert proc.returncode != 0


@pytest.mark.skipif(not is_jing_installed(), reason="jing not found")
async def test_validate_rng_without_xinclude(tmp_path: Path):
    xmlfile = tmp_path / Path("file.xml")
    xmlfile.write_text("<root/>")
    rng_schema = tmp_path / Path("schema.rng")
    rng_schema.write_text(
        '<?xml version="1.0"?><grammar xmlns="http://relaxng.org/ns/structure/1.0">'
        '<start><element name="root"><text/></element></start></grammar>'
    )
    proc = await portal_task.validate_rng(xmlfile, rng_schema, xinclude=False)
    assert proc.returncode == 0


@pytest.mark.skipif(not is_jing_installed(), reason="jing not found")
async def test_validate_rng_with_invalid_xml_without_xinclude(tmp_path: Path):
    xmlfile = tmp_path / Path("file.xml")
    xmlfile.write_text("<wrong_root/>")
    rng_schema = tmp_path / Path("schema.rng")
    rng_schema.write_text(
        '<?xml version="1.0"?><grammar xmlns="http://relaxng.org/ns/structure/1.0">'
        '<start><element name="root"><text/></element></start></grammar>'
    )
    proc = await portal_task.validate_rng(xmlfile, rng_schema, xinclude=False)
    assert proc.returncode != 0


async def test_validate_rng_jing_failure():
    xmlfile = Path("/mocked/path/to/file.xml")
    rnc_schema = Path("/mocked/path/to/schema.rnc")

    with patch.object(
        portal_task, "run_command", new=AsyncMock(
            return_value=CompletedProcess(
                args=["jing", str(xmlfile), str(rnc_schema)], returncode=1, stdout="Error in jing", stderr=""
            )
        )
    ) as mock_run_command:
        proc = await portal_task.validate_rng(xmlfile, rnc_schema, xinclude=False, idcheck=False)
        assert proc.returncode != 0
        assert proc.stdout == "Error in jing"

        # Add the '-c' flag here!
        mock_run_command.assert_called_once_with(["jing", "-i", "-c", str(rnc_schema), str(xmlfile)])


async def test_validate_rng_command_not_found():
    xmlfile = Path("/mocked/path/to/file.xml")
    rng_schema = Path("/mocked/path/to/schema.rng")
    error = FileNotFoundError(2, "No such file or directory")
    error.filename = "jing"

    with patch.object(portal_task, "run_command", new_callable=AsyncMock, side_effect=error):
        proc = await portal_task.validate_rng(xmlfile, rng_schema, xinclude=False)
    assert proc.returncode != 0
    assert proc.stderr == "jing command not found. Please install it to run validation."


async def test_validate_rng_command_not_found_no_filename():
    xmlfile = Path("/mocked/path/to/file.xml")
    rng_schema = Path("/mocked/path/to/schema.rng")
    error = FileNotFoundError(2, "No such file or directory")
    error.filename = None

    with patch.object(portal_task, "run_command", new_callable=AsyncMock, side_effect=error):
        proc = await portal_task.validate_rng(xmlfile, rng_schema, xinclude=False)
    assert proc.returncode != 0
    assert proc.stderr == "xmllint/jing command not found. Please install it to run validation."


async def test_validate_portal_config_validation_issues(tmp_path):
    with patch.object(
        portal_task, "validate_rng", new=AsyncMock(
            return_value=CompletedProcess(args=["jing"], returncode=1, stdout="", stderr="Validation error")
        )
    ):
        xmlfile = tmp_path / "file.xml"
        xmlfile.touch()
        schema = tmp_path / "schema.rnc"
        result = await portal_task.validate_portal_config(xmlfile, schema, verbose=2)
        assert result == 10


async def test_validate_portal_config_xmlsyntax_error(tmp_path):
    xmlfile = tmp_path / "file.xml"
    xmlfile.touch()
    schema = tmp_path / "schema.rnc"

    with (
        patch.object(
            portal_task.etree, "parse", new=Mock(
                side_effect=portal_task.etree.XMLSyntaxError("XML syntax error", None, 0, 0, "fake.xml")
            )
        ),
        patch.object(
            portal_task, "validate_rng", new=AsyncMock(
                return_value=CompletedProcess(args=["jing"], returncode=0, stdout="", stderr="")
            )
        ),
    ):
        result = await portal_task.validate_portal_config(xmlfile, schema, verbose=2)
    assert result == 200


class TestDisplayResults:
    """Test cases for display_results function."""

    def test_display_results_verbose_0_silent_mode(self, capsys):
        portal_task.display_results([])
        assert capsys.readouterr().out == ""

    @pytest.mark.parametrize(
        "check_results,summary_line,expected_out_substrings",
        [
            ([("check2", CheckResult(message="Error message"))], "Stage 2 (Python checks): failed", ["Stage 2 (Python checks)", "failed"]),
            ([("check2", CheckResult(message="Error"))], "Stage 2 (Python checks): .F => failed", ["Stage 2 (Python checks)", "=>", "failed"]),
            ([], "Stage 2: success", ["success"]),
        ],
    )
    def test_display_results_summary_output(self, capsys, check_results, summary_line, expected_out_substrings):
        portal_task.display_results(check_results, summary_line=summary_line)
        captured = capsys.readouterr()
        for text in expected_out_substrings:
            assert text in captured.out

    def test_display_results_verbose_3_with_detailed_errors(self, capsys):
        tree = etree.fromstring('<portal xml:base="/tmp/config/portal.xml"><docset id="d1"/></portal>').getroottree()
        check_results = [
            ("check1", CheckResult(message="Detailed error message", xpath="/portal/docset[1]")),
            ("check2", CheckResult(message="Another error", filename="/tmp/config/explicit.xml")),
        ]

        portal_task.display_results(check_results, summary_line="Stage 2: failed", tree=tree)
        captured = capsys.readouterr()

        assert "check1" in captured.err
        assert "Detailed error message" in captured.err
        assert "XPath: /portal/docset[1]" in captured.err
        assert "File: /tmp/config/portal.xml" in captured.err
        assert "File: /tmp/config/explicit.xml" in captured.err

    @pytest.mark.parametrize(
        "xml_text,xpath",
        [
            ("<portal><docset id='d1'/></portal>", "/portal/missing[1]"),
            ("<portal><docset id='d1'/></portal>", "/portal/docset/@id"),
            ("<portal><docset id='d1'/></portal>", "/portal/docset[1]"),
            ("<portal><docset id='d1'/></portal>", "["),
        ],
    )
    def test_display_results_no_file_when_xml_base_unresolvable(self, capsys, xml_text, xpath):
        tree = etree.fromstring(xml_text).getroottree()
        assert portal_task.filename_from_xml_base(tree, None) is None
        check_results = [("check1", CheckResult(message="Detailed error message", xpath=xpath))]

        portal_task.display_results(check_results, summary_line="Stage 2: failed", tree=tree)
        assert "File:" not in capsys.readouterr().err


class TestProcessValidation:
    """Test cases for the core validation loop."""

    @patch.object(portal_task, "registry")
    @patch.object(portal_task, "run_validation", new_callable=AsyncMock)
    async def test_process_file_exception(self, mock_run_validation, mock_registry):
        mock_run_validation.return_value = ValidationResult(True, 0, "")
        mock_registry.registry = []
        with pytest.raises(OSError):
            await portal_task.validate_portal_config(Path("/non/existent/file.xml"), Path("schema.rnc"), verbose=1)

    @patch.object(portal_task, "registry")
    @patch.object(portal_task, "run_validation", new_callable=AsyncMock)
    async def test_process_check_exception(self, mock_run_validation, mock_registry, tmp_path):
        mock_run_validation.return_value = ValidationResult(True, 0, "")
        mock_check = Mock(__name__="failing_check", side_effect=Exception("Check failed"))
        mock_registry.registry = [mock_check]

        xml_file = tmp_path / "valid.xml"
        xml_file.write_text('<?xml version="1.0"?><root></root>')

        result = await portal_task.validate_portal_config(xml_file, Path("schema.rnc"), verbose=1)
        assert result == 1

    @pytest.mark.parametrize(
        "check_success,verbose_level,expected_code,expect_stage2_summary",
        [
            (True, 2, 0, False),
            (False, 2, 1, True),
            (False, 1, 1, True),
            (False, 0, 1, True),
            (True, 0, 0, False),
        ],
    )
    @patch.object(portal_task, "registry")
    @patch.object(portal_task, "run_validation", new_callable=AsyncMock)
    async def test_process_check_outcomes(
        self, mock_run_validation, mock_registry, tmp_path, capsys,
        check_success, verbose_level, expected_code, expect_stage2_summary
    ):
        mock_run_validation.return_value = ValidationResult(True, 0, "")

        def generator_func(tree):
            if not check_success:
                yield CheckResult(message="Check failed")

        mock_check = Mock(__name__="check_case", side_effect=generator_func)
        mock_registry.registry = [mock_check]

        xml_file = tmp_path / "valid.xml"
        xml_file.write_text('<?xml version="1.0"?><root></root>')

        result = await portal_task.validate_portal_config(xml_file, Path("schema.rnc"), verbose=verbose_level)

        assert result == expected_code
        captured = capsys.readouterr()
        if expect_stage2_summary:
            assert "Stage 2 (Python checks," in captured.out
            assert "1 check found" in captured.out
            if verbose_level > 1 and not check_success:
                assert "=>" in captured.out
                assert "failed" in captured.out
        else:
            assert "Stage 2 (Python checks," not in captured.out

    @patch.object(portal_task, "run_checks_and_display", new_callable=AsyncMock)
    @patch.object(portal_task, "parse_portal_config", new_callable=AsyncMock)
    @patch.object(portal_task, "run_validation", new_callable=AsyncMock)
    async def test_process_runs_checks_after_successful_schema_validation(
        self, mock_run_validation, mock_parse_portal_config, mock_run_checks_and_display, tmp_path
    ):
        mock_run_validation.return_value = ValidationResult(True, 0, "")
        mock_tree = Mock()
        mock_parse_portal_config.return_value = mock_tree
        mock_run_checks_and_display.return_value = True

        xml_file = tmp_path / "valid.xml"
        schema = tmp_path / "schema.rnc"

        result = await portal_task.validate_portal_config(xml_file, schema, verbose=1)

        assert result == 0
        mock_run_validation.assert_awaited_once_with(xml_file, schema)
        mock_parse_portal_config.assert_awaited_once_with(xml_file)
        mock_run_checks_and_display.assert_awaited_once_with(mock_tree, 1)

    @patch.object(portal_task, "run_checks_and_display", new_callable=AsyncMock)
    @patch.object(portal_task, "run_validation", new_callable=AsyncMock)
    async def test_process_skips_checks_when_schema_validation_fails(
        self, mock_run_validation, mock_run_checks_and_display, tmp_path
    ):
        mock_run_validation.return_value = ValidationResult(False, 10, "RNG validation failed")

        xml_file = tmp_path / "valid.xml"
        schema = tmp_path / "schema.rnc"

        result = await portal_task.validate_portal_config(xml_file, schema, verbose=1)

        assert result == 10
        mock_run_checks_and_display.assert_not_awaited()
