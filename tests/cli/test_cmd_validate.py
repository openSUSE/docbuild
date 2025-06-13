"""Tests for the validate CLI command."""

from collections.abc import Iterator
from os import PathLike
from pathlib import Path
import tempfile
from unittest.mock import AsyncMock, Mock, patch

import pytest

from docbuild.cli import cmd_validate, process_validation
from docbuild.cli.cmd_validate import validate
from docbuild.cli.context import DocBuildContext
from docbuild.cli.process_validation import display_results, process
from docbuild.config.xml.checks import CheckResult


class TestDisplayResults:
    """Test cases for display_results function."""

    def test_display_results_verbose_0_silent_mode(self, capsys):
        """Test that verbose=0 produces no output (silent mode)."""
        check_results = [('check1', CheckResult(success=True, messages=[]))]

        display_results('test.xml', check_results, verbose=0, max_len=40)

        captured = capsys.readouterr()
        assert captured.out == ''

    def test_display_results_verbose_1_basic_output(self, capsys):
        """Test verbose=1 shows filename and overall result only."""
        check_results = [
            ('check1', CheckResult(success=True, messages=[])),
            ('check2', CheckResult(success=False, messages=['Error message'])),
        ]

        display_results('test.xml', check_results, verbose=1, max_len=40)

        captured = capsys.readouterr()
        assert 'test.xml' in captured.out
        assert 'failed' in captured.out

    def test_display_results_verbose_2_with_dots(self, capsys):
        """Test verbose=2 shows dots and status."""
        check_results = [
            ('check1', CheckResult(success=True, messages=[])),
            ('check2', CheckResult(success=False, messages=['Error'])),
        ]

        display_results('test.xml', check_results, verbose=2, max_len=40)

        captured = capsys.readouterr()
        assert 'test.xml' in captured.out
        assert '=>' in captured.out
        assert 'failed' in captured.out

    def test_display_results_verbose_3_with_detailed_errors(self, capsys):
        """Test verbose>2 shows detailed error messages."""
        check_results = [
            ('check1', CheckResult(success=False, messages=['Detailed error message'])),
            ('check2', CheckResult(success=True, messages=[])),
        ]

        display_results('test.xml', check_results, verbose=3, max_len=40)

        captured = capsys.readouterr()
        assert '✗ check1:' in captured.err
        assert 'Detailed error message' in captured.err

    def test_display_results_all_success(self, capsys):
        """Test display when all checks succeed."""
        check_results = [
            ('check1', CheckResult(success=True, messages=[])),
            ('check2', CheckResult(success=True, messages=[])),
        ]

        display_results('test.xml', check_results, verbose=2, max_len=40)

        captured = capsys.readouterr()
        assert 'success' in captured.out


class TestProcessValidation:
    """Test cases for the process function."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock DocBuildContext."""
        context = Mock(spec=DocBuildContext)
        context.envconfig = {'paths': {'config_dir': '/test/config'}}
        context.verbose = 1
        return context

    @pytest.fixture
    def valid_xml_file(self) -> Iterator[PathLike]:
        """Create a temporary valid XML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write('<?xml version="1.0"?><root><test>content</test></root>')
            f.flush()
            yield Path(f.name)
        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def invalid_xml_file(self):
        """Create a temporary invalid XML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write('<?xml version="1.0"?><root><unclosed-tag></root>')
            f.flush()
            yield Path(f.name)
        Path(f.name).unlink(missing_ok=True)

    async def test_process_no_envconfig(self):
        """Test process raises ValueError when no envconfig."""
        context = Mock(spec=DocBuildContext)
        context.envconfig = None

        with pytest.raises(ValueError, match='No envconfig found in context'):
            await process(context, [])

    async def test_process_invalid_paths_config(self):
        """Test process raises ValueError when paths is not a dict."""
        context = Mock(spec=DocBuildContext)
        context.envconfig = {'paths': 'not_a_dict'}

        with pytest.raises(ValueError, match="'paths.config' must be a dictionary"):
            await process(context, [])

    async def test_process_with_no_xml_files(self, mock_context, caplog):
        """Test that process returns 0 when no XML files are provided."""
        # Set the log level to capture WARNING messages
        # caplog.set_level(logging.WARNING, logger="docbuild.cli.process_validation")

        result = await process(mock_context, xmlfiles=())
        assert result == 0
        # assert 'No XML files found to validate.' in caplog.text

    @patch.object(process_validation, 'registry')
    async def test_process_xml_syntax_error(
        self, mock_registry, mock_context, invalid_xml_file
    ):
        """Test processing file with XML syntax error returns exit code 10."""
        mock_registry.registry = []

        result = await process(mock_context, [invalid_xml_file])

        assert result == 1  # Should return 1 for any failures

    @patch.object(process_validation, 'registry')
    async def test_process_file_exception(self, mock_registry, mock_context):
        """Test processing non-existent file returns exit code 200."""
        mock_registry.registry = []
        non_existent_file = Path('/non/existent/file.xml')

        result = await process(mock_context, [non_existent_file])

        assert result == 1  # Should return 1 for any failures

    @patch.object(process_validation, 'registry')
    @patch.object(process_validation, 'validate_rng', new_callable=AsyncMock)
    async def test_process_check_exception(
        self, mock_validate_rng, mock_registry, mock_context, valid_xml_file: PathLike
    ):
        """Test processing when a check raises an exception."""
        mock_validate_rng.return_value = (True, '')
        # Create a mock check that raises an exception
        mock_check = Mock()
        mock_check.__name__ = 'failing_check'
        mock_check.side_effect = Exception('Check failed')
        mock_registry.registry = [mock_check]

        result = await process(mock_context, [valid_xml_file])

        assert result == 1  # Should return 1 for failures

    @patch.object(process_validation, 'registry')
    @patch.object(process_validation, 'validate_rng', new_callable=AsyncMock)
    async def test_process_successful_checks(
        self, mock_validate_rng, mock_registry, mock_context, valid_xml_file
    ):
        """Test processing with successful checks returns 0."""
        mock_validate_rng.return_value = (True, '')
        # Create a mock check that succeeds
        mock_check = Mock()
        mock_check.__name__ = 'passing_check'
        mock_check.return_value = CheckResult(success=True, messages=[])
        mock_registry.registry = [mock_check]

        result = await process(mock_context, [valid_xml_file])

        assert result == 0  # Should return 0 for success

    @patch.object(process_validation, 'registry')
    @patch.object(process_validation, 'validate_rng', new_callable=AsyncMock)
    async def test_process_failed_checks(
        self, mock_validate_rng, mock_registry, mock_context, valid_xml_file
    ):
        """Test processing with failed checks returns 1."""
        mock_validate_rng.return_value = (True, '')
        # Create a mock check that fails
        mock_check = Mock()
        mock_check.__name__ = 'failing_check'
        mock_check.return_value = CheckResult(success=False, messages=['Check failed'])
        mock_registry.registry = [mock_check]

        result = await process(mock_context, [valid_xml_file])

        assert result == 1  # Should return 1 for failures

    @patch.object(process_validation, 'validate_rng', new_callable=AsyncMock)
    async def test_process_shortname_generation(
        self, mock_validate_rng, mock_context, valid_xml_file
    ):
        """Test that shortname is generated correctly for display."""
        mock_validate_rng.return_value = (True, '')
        with patch.object(process_validation, 'registry') as mock_registry:
            mock_registry.registry = []

            # This test primarily verifies the shortname logic doesn't crash
            result = await process(mock_context, [valid_xml_file])

            # The result should be 0 since no checks are registered (all succeed)
            assert result == 0

    @patch.object(process_validation, 'validate_rng', new_callable=AsyncMock)
    async def test_process_with_multiple_files_and_iterator(
        self, mock_validate_rng, mock_context, valid_xml_file
    ):
        """Test that processing multiple files works with an iterator."""
        mock_validate_rng.return_value = (True, '')
        with patch.object(process_validation, 'registry') as mock_registry:
            mock_registry.registry = []

            # This test primarily verifies the shortname logic doesn't crash
            result = await process(mock_context, iter([valid_xml_file]))

            # The result should be 0 since no checks are registered (all succeed)
            assert result == 0

    @patch.object(process_validation, 'validate_rng', new_callable=AsyncMock)
    async def test_process_stitch_validation_fails_on_duplicates(
        self, mock_validate_rng, mock_context, tmp_path, capsys
    ):
        """Test `process` fails if stitch validation finds duplicate product IDs."""
        mock_validate_rng.return_value = (True, '')

        file1: Path = tmp_path / 'file1.xml'
        file1.write_text('<product productid="sles"><docset setid="15-sp4"/></product>')
        file2: Path = tmp_path / 'file2.xml'
        file2.write_text('<product productid="sles"><docset setid="15-sp5"/></product>')

        with patch.object(process_validation, 'registry') as mock_registry:
            mock_registry.registry = []
            result = await process(mock_context, [file1, file2])

        assert result == 1
        captured = capsys.readouterr()
        assert (
            'Stitch-file validation failed: Duplicate product IDs found: sles'
            in captured.err
        )


class TestValidateCommand:
    """Test cases for the validate CLI command."""

    def test_validate_no_envconfig_in_context(self, runner):
        """Test validate command when no envconfig is found."""
        with runner.isolated_filesystem():
            Path('test.xml').write_text('<?xml version="1.0"?><root></root>')
            # When no context object is passed, a default one is created,
            # which has envconfig=None, triggering the error.
            result = runner.invoke(validate, ['test.xml'])

            assert result.exit_code != 0
            assert isinstance(result.exception, ValueError)
            assert 'No envconfig found in context' in str(result.exception)

    def test_validate_no_paths_in_envconfig(self, runner):
        """Test validate command when no paths are found in envconfig."""
        with runner.isolated_filesystem():
            Path('test.xml').write_text('<?xml version="1.0"?><root></root>')
            context = DocBuildContext(envconfig={'some_other_key': 'value'})
            # We also need to patch replace_placeholders because it's called before the check
            with patch.object(cmd_validate, 'replace_placeholders', lambda x: x):
                result = runner.invoke(validate, ['test.xml'], obj=context)

            assert result.exit_code != 0
            assert isinstance(result.exception, ValueError)
            assert 'No paths found in envconfig' in str(result.exception)

    def test_validate_no_config_dir_in_paths(self, runner):
        """Test validate command when no config_dir is found in paths."""
        with runner.isolated_filesystem():
            Path('test.xml').write_text('<?xml version="1.0"?><root></root>')
            context = DocBuildContext(envconfig={'paths': {'other_dir': '/path'}})
            with patch.object(cmd_validate, 'replace_placeholders', lambda x: x):
                result = runner.invoke(validate, ['test.xml'], obj=context)

            assert result.exit_code != 0
            assert isinstance(result.exception, ValueError)
            assert 'Could not get a value from envconfig.paths.config_dir' in str(
                result.exception
            )

    def test_validate_uses_provided_files(self, runner):
        """Test validate uses XML files provided on the command line."""
        with runner.isolated_filesystem() as fs:
            xml_file1 = Path(fs) / 'test1.xml'
            xml_file1.write_text('<root/>')
            xml_file2 = Path(fs) / 'another.xml'
            xml_file2.write_text('<root/>')

            # A config_dir is still needed to pass the initial checks.
            config_dir = Path(fs) / 'config'
            config_dir.mkdir()
            context = DocBuildContext(
                envconfig={'paths': {'config_dir': str(config_dir)}}
            )

            with (
                patch.object(cmd_validate, 'replace_placeholders', lambda x: x),
                patch.object(
                    cmd_validate, 'process', new_callable=AsyncMock
                ) as mock_process,
            ):
                mock_process.return_value = 0

                result = runner.invoke(
                    validate, [str(xml_file1), str(xml_file2)], obj=context
                )

                assert result.exit_code == 0
                mock_process.assert_awaited_once()

                passed_xmlfiles = mock_process.call_args.kwargs['xmlfiles']
                assert passed_xmlfiles == (xml_file1, xml_file2)

    def test_validate_finds_files_in_config_dir(self, runner):
        """Test validate finds XML files in config_dir when none are provided."""
        with runner.isolated_filesystem() as fs:
            config_dir = Path(fs) / 'config'
            config_dir.mkdir()
            xml_file1 = config_dir / 'test1.xml'
            xml_file1.write_text('<root/>')
            xml_file2 = config_dir / 'another.xml'
            xml_file2.write_text('<root/>')
            # This one should not be picked up by rglob('[a-z]*.xml')
            (config_dir / 'Test3.xml').write_text('<root/>')

            context = DocBuildContext(
                envconfig={'paths': {'config_dir': str(config_dir)}}
            )

            with (
                patch.object(cmd_validate, 'replace_placeholders', lambda x: x),
                patch.object(
                    cmd_validate, 'process', new_callable=AsyncMock
                ) as mock_process,
            ):
                mock_process.return_value = 0
                result = runner.invoke(validate, [], obj=context)

                assert result.exit_code == 0
                mock_process.assert_awaited_once()
                passed_xmlfiles = mock_process.call_args.kwargs['xmlfiles']
                assert set(passed_xmlfiles) == {xml_file1, xml_file2}
