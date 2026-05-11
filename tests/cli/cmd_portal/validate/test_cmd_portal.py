"""Tests for the validate CLI command."""

from collections.abc import Iterator
from os import PathLike
from pathlib import Path
import tempfile
from unittest.mock import AsyncMock, Mock, patch

from lxml import etree
import pytest

from docbuild.cli.cmd_portal.cmd_validate import validate
import docbuild.cli.cmd_portal.process as process_mod
from docbuild.cli.cmd_portal.process import ValidationResult
from docbuild.cli.context import DocBuildContext
from docbuild.config.xml.checks import CheckResult


class TestDisplayResults:
    """Test cases for display_results function."""

    def test_display_results_verbose_0_silent_mode(self, capsys):
        """Test that verbose=0 produces no output (silent mode)."""
        check_results = [("check1", CheckResult(success=True, messages=[]))]

        process_mod.display_results(check_results)

        captured = capsys.readouterr()
        assert captured.out == ""

    @pytest.mark.parametrize(
        "check_results,summary_line,expected_out_substrings",
        [
            (
                [
                    ("check1", CheckResult(success=True, messages=[])),
                    ("check2", CheckResult(success=False, messages=["Error message"])),
                ],
                "Stage 2 (Python checks): failed",
                ["Stage 2 (Python checks)", "failed"],
            ),
            (
                [
                    ("check1", CheckResult(success=True, messages=[])),
                    ("check2", CheckResult(success=False, messages=["Error"])),
                ],
                "Stage 2 (Python checks): .F => failed",
                ["Stage 2 (Python checks)", "=>", "failed"],
            ),
            (
                [
                    ("check1", CheckResult(success=True, messages=[])),
                    ("check2", CheckResult(success=True, messages=[])),
                ],
                "Stage 2: success",
                ["success"],
            ),
        ],
    )
    def test_display_results_summary_output(
        self,
        capsys,
        check_results: list[tuple[str, CheckResult]],
        summary_line: str,
        expected_out_substrings: list[str],
    ) -> None:
        """Summary output includes expected status fragments for each scenario."""
        process_mod.display_results(check_results, summary_line=summary_line)

        captured = capsys.readouterr()
        for text in expected_out_substrings:
            assert text in captured.out

    def test_display_results_verbose_3_with_detailed_errors(self, capsys):
        """Test multiple errors include check names, messages, and XPath output."""
        tree = etree.fromstring(
            """
            <portal xml:base="/tmp/config/portal.xml">
                <docset id="d1"/>
            </portal>
            """
        ).getroottree()
        check_results = [
            (
                "check1",
                CheckResult(
                    success=False,
                    messages=["Detailed error message"],
                    xpath="/portal/docset[1]",
                ),
            ),
            ("check2", CheckResult(success=False, messages=["Another error"])),
        ]

        process_mod.display_results(
            check_results,
            summary_line="Stage 2: failed",
            tree=tree,
        )

        captured = capsys.readouterr()
        assert "check1" in captured.err
        assert "Detailed error message" in captured.err
        assert "2." in captured.err
        assert "XPath: /portal/docset[1]" in captured.err
        assert "File: /tmp/config/portal.xml" in captured.err

    @pytest.mark.parametrize(
        "xml_text,xpath",
        [
            # No XPath matches -> helper returns None at the empty-match branch.
            ("<portal><docset id='d1'/></portal>", "/portal/missing[1]"),
            # XPath returns a scalar, not an element -> helper returns None.
            ("<portal><docset id='d1'/></portal>", "/portal/docset/@id"),
            # Match exists but no ancestor has xml:base -> helper returns None after walk.
            ("<portal><docset id='d1'/></portal>", "/portal/docset[1]"),
        ],
    )
    def test_display_results_no_file_when_xml_base_unresolvable(
        self,
        capsys,
        xml_text: str,
        xpath: str,
    ) -> None:
        """No file line is shown when xml:base cannot be resolved for an XPath."""
        tree = etree.fromstring(xml_text).getroottree()
        check_results = [
            (
                "check1",
                CheckResult(success=False, messages=["Detailed error message"], xpath=xpath),
            ),
        ]

        process_mod.display_results(
            check_results,
            summary_line="Stage 2: failed",
            tree=tree,
        )

        captured = capsys.readouterr()
        assert "File:" not in captured.err

class TestProcessValidation:
    """Test cases for the process function."""

    class _DummyPaths:
        def __init__(self, config_dir: str) -> None:
            self.config_dir = Path(config_dir)
            self.base_server_cache_dir = None

    class _DummyEnv:
        """Fake envconfig exposing expected attributes."""

        def __init__(self, *, config_dir: str) -> None:
            self.paths = TestProcessValidation._DummyPaths(config_dir)

    @pytest.fixture
    def mock_context(self):
        """Create a mock DocBuildContext."""
        context = Mock(spec=DocBuildContext)
        context.envconfig = self._DummyEnv(config_dir="/test/config")
        context.verbose = 1
        context.validation_method = "jing"
        return context

    @pytest.fixture
    def valid_xml_file(self) -> Iterator[PathLike]:
        """Create a temporary valid XML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write('<?xml version="1.0"?><root><test>content</test></root>')
            f.flush()
            yield Path(f.name)
        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def invalid_xml_file(self):
        """Create a temporary invalid XML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write('<?xml version="1.0"?><root><unclosed-tag></root>')
            f.flush()
            yield Path(f.name)
        Path(f.name).unlink(missing_ok=True)

    async def test_process_no_envconfig(self):
        """This error path is now handled earlier by the CLI.

        The validate command ensures ``envconfig`` is an EnvConfig instance
        before calling the async ``process`` function, so passing ``None``
        here is no longer a realistic scenario. Retain this test as a minimal
        smoke check to ensure ``process`` can still be invoked with a
        structurally valid envconfig-like object and returns an int.
        """

        context = Mock(spec=DocBuildContext)
        context.envconfig = self._DummyEnv(config_dir="/test/config")

        result = await process_mod.process(context, Path("portal.xml"), Path("schema.rnc"))
        assert isinstance(result, int)

    @patch.object(process_mod, "registry")
    @patch.object(process_mod, "run_validation", new_callable=AsyncMock)
    async def test_process_xml_syntax_error(
        self, mock_run_validation, mock_registry, mock_context, invalid_xml_file
    ):
        """Test processing file with XML syntax error returns exit code 20."""
        mock_run_validation.return_value = ValidationResult(True, 0, "")
        mock_registry.registry = []

        result = await process_mod.process(mock_context, invalid_xml_file, Path("schema.rnc"))

        assert result == 200

    @patch.object(process_mod, "registry")
    @patch.object(process_mod, "run_validation", new_callable=AsyncMock)
    async def test_process_file_exception(
        self, mock_run_validation, mock_registry, mock_context
    ):
        """Test processing non-existent file propagates an OSError."""
        mock_run_validation.return_value = ValidationResult(True, 0, "")
        mock_registry.registry = []
        non_existent_file = Path("/non/existent/file.xml")

        with pytest.raises(OSError, match="Error reading file"):
            await process_mod.process(mock_context, non_existent_file, Path("schema.rnc"))

    @patch.object(process_mod, "registry")
    @patch.object(process_mod, "run_validation", new_callable=AsyncMock)
    async def test_process_check_exception(
        self, mock_run_validation, mock_registry, mock_context, valid_xml_file: PathLike
    ):
        """Test processing when a check raises an exception."""
        mock_run_validation.return_value = ValidationResult(True, 0, "")
        # Create a mock check that raises an exception
        mock_check = Mock()
        mock_check.__name__ = "failing_check"
        mock_check.side_effect = Exception("Check failed")
        mock_registry.registry = [mock_check]

        result = await process_mod.process(mock_context, Path(valid_xml_file), Path("schema.rnc"))

        assert result == 1  # Should return 1 for failures

    @pytest.mark.parametrize(
        "check_success,verbose_level,expected_code,expect_stage2_summary",
        [
            (True, 2, 0, True),
            (False, 1, 1, True),
            (False, 0, 1, True),
            (True, 0, 0, False),
        ],
    )
    @patch.object(process_mod, "registry")
    @patch.object(process_mod, "run_validation", new_callable=AsyncMock)
    async def test_process_check_outcomes(
        self,
        mock_run_validation,
        mock_registry,
        mock_context,
        valid_xml_file,
        capsys,
        check_success: bool,
        verbose_level: int,
        expected_code: int,
        expect_stage2_summary: bool,
    ):
        """Processing returns expected code for successful and failing checks."""
        mock_run_validation.return_value = ValidationResult(True, 0, "")
        mock_context.verbose = verbose_level
        mock_check = Mock()
        mock_check.__name__ = "check_case"
        mock_check.return_value = (
            CheckResult(success=True, messages=[])
            if check_success
            else CheckResult(success=False, messages=["Check failed"])
        )
        mock_registry.registry = [mock_check]

        result = await process_mod.process(mock_context, Path(valid_xml_file), Path("schema.rnc"))

        assert result == expected_code
        captured = capsys.readouterr()
        if expect_stage2_summary:
            assert "Stage 2 (Python checks," in captured.out
            assert "1 check found" in captured.out
        else:
            assert "Stage 2 (Python checks," not in captured.out

    @patch.object(process_mod, "cache_resolved_portal_config", new_callable=AsyncMock)
    @patch.object(process_mod, "run_checks_and_display", new_callable=AsyncMock)
    @patch.object(process_mod, "parse_portal_config", new_callable=AsyncMock)
    @patch.object(process_mod, "run_validation", new_callable=AsyncMock)
    async def test_process_runs_checks_after_successful_schema_validation(
        self,
        mock_run_validation,
        mock_parse_portal_config,
        mock_run_checks_and_display,
        mock_cache_resolved,
        mock_context,
        valid_xml_file,
    ):
        """Ensure Python checks are executed only after RNG validation passes."""
        mock_run_validation.return_value = ValidationResult(True, 0, "")
        mock_tree = Mock()
        mock_parse_portal_config.return_value = mock_tree
        mock_run_checks_and_display.return_value = True
        mock_cache_resolved.return_value = None

        result = await process_mod.process(
            mock_context, Path(valid_xml_file), Path("schema.rnc")
        )

        assert result == 0
        mock_run_validation.assert_awaited_once_with(
            Path(valid_xml_file), Path("schema.rnc")
        )
        mock_parse_portal_config.assert_awaited_once_with(Path(valid_xml_file))
        mock_run_checks_and_display.assert_awaited_once()
        call_args = mock_run_checks_and_display.await_args.args
        assert call_args[0] is mock_tree
        assert call_args[1] is mock_context

    @patch.object(process_mod, "run_checks_and_display", new_callable=AsyncMock)
    @patch.object(process_mod, "run_validation", new_callable=AsyncMock)
    async def test_process_skips_checks_when_schema_validation_fails(
        self,
        mock_run_validation,
        mock_run_checks_and_display,
        mock_context,
        valid_xml_file,
    ):
        """Ensure Python checks are not executed when RNG validation fails."""

        mock_run_validation.return_value = ValidationResult(
            False, 10, "RNG validation failed"
        )

        result = await process_mod.process(
            mock_context, Path(valid_xml_file), Path("schema.rnc")
        )

        assert result == 10
        mock_run_checks_and_display.assert_not_awaited()


class TestValidateCommand:
    """Test cases for the validate CLI command."""
    class _DummyPaths:
        """Minimal paths holder for validate CLI tests."""

        def __init__(self, config_dir: str) -> None:
            self.config_dir = config_dir
            self.main_portal_config = Path(config_dir) / "portal.xml"
            self.portal_rncschema = Path(config_dir) / "portal.rnc"

    class _DummyEnv:
        """Fake EnvConfig-like object exposing necessary paths."""

        def __init__(self, config_dir: str) -> None:
            self.paths = TestValidateCommand._DummyPaths(config_dir)


    @pytest.mark.parametrize("process_return,cli_args", [(0, None), (1, [])])
    @patch.object(process_mod, "process", new_callable=AsyncMock)
    def test_validate_default_paths(self, mock_process, runner, process_return, cli_args):
        """Validate uses env-config paths and propagates process exit code."""
        mock_process.return_value = process_return

        context = Mock(spec=DocBuildContext)
        context.envconfig = self._DummyEnv("/test/config")

        result = runner.invoke(validate, cli_args, obj=context)

        assert result.exit_code == process_return
        mock_process.assert_awaited_once_with(
            context, Path("/test/config/portal.xml"), Path("/test/config/portal.rnc")
        )

    @patch.object(process_mod, "process", new_callable=AsyncMock)
    def test_validate_with_cli_options(self, mock_process, runner):
        """Test validate uses files provided on the command line."""
        mock_process.return_value = 0

        context = Mock(spec=DocBuildContext)
        context.envconfig = self._DummyEnv("/test/config")

        with runner.isolated_filesystem() as fs:
            custom_portal = Path(fs) / "custom_portal.xml"
            custom_portal.touch()
            custom_schema = Path(fs) / "custom_schema.rnc"
            custom_schema.touch()

            result = runner.invoke(
                validate,
                ["--main-portal-config", str(custom_portal), "--portal-schema", str(custom_schema)],
                obj=context
            )

            assert result.exit_code == 0
            mock_process.assert_awaited_once_with(
                context, custom_portal, custom_schema
            )
