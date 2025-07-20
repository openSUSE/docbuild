"""Unit tests for the metadata CLI command."""

from unittest.mock import AsyncMock, Mock, patch

from click.testing import CliRunner
import pytest

from docbuild.cli import cmd_metadata
from docbuild.cli.cmd_cli import cli as main_cli
from docbuild.cli.cmd_metadata import metadata
from docbuild.cli.context import DocBuildContext
from docbuild.config import load as load_config_module
from docbuild.models.doctype import Doctype


class TestMetadataCommand:
    """Tests for the metadata CLI command."""

    @patch.object(load_config_module, 'process_envconfig')
    def test_metadata_no_envconfig_raises_error(
        self, mock_process_envconfig: Mock, runner: CliRunner, context: DocBuildContext
    ):
        """Test that metadata command raises ValueError if envconfig is not set."""
        # Prevent the main CLI from loading a real environment config file by
        # patching the processing function to return an empty dictionary.
        # This ensures that context.envconfig remains None when the `metadata`
        # command is called.
        mock_process_envconfig.return_value = {}
        context.envconfig = None
        result = runner.invoke(metadata, obj=context)
        assert result.exit_code != 0
        assert isinstance(result.exception, ValueError)
        assert 'No envconfig found in context' in str(result.exception)

    @patch.object(cmd_metadata, 'process', new_callable=AsyncMock)
    @patch.object(cmd_metadata.console_out, 'print')
    def test_metadata_success(
        self,
        mock_print: Mock,
        mock_process: AsyncMock,
        runner: CliRunner,
        context: DocBuildContext,
    ):
        """Test successful execution of the metadata command."""
        # Arrange
        context.envconfig = {'paths': {'config_dir': '/fake/dir'}}
        mock_process.return_value = 0  # Success

        # Act
        result = runner.invoke(main_cli, ['metadata', '//en-us'], obj=context)

        # Assert
        assert result.exit_code == 0
        mock_process.assert_awaited_once()
        # Check that the context and doctypes were passed correctly
        call_args = mock_process.call_args[0]
        assert call_args[0] is context
        assert len(call_args[1]) == 1
        assert isinstance(call_args[1][0], Doctype)
        assert str(call_args[1][0]) == '*/*@unknown/en-us'  # Doctype normalizes '//' to '*/*' and adds default lifecycle

        # Check that elapsed time was printed
        last_call_args = mock_print.call_args[0]
        assert 'Elapsed time' in last_call_args[0]

    @patch.object(cmd_metadata, 'process', new_callable=AsyncMock)
    def test_metadata_failure_exit_code(
        self, mock_process: AsyncMock, runner: CliRunner, context: DocBuildContext
    ):
        """Test that the command exits with the correct code on failure."""
        # Arrange
        context.envconfig = {'paths': {'config_dir': '/fake/dir'}}
        mock_process.return_value = 1  # Failure

        # Act
        result = runner.invoke(main_cli, ['metadata'], obj=context)

        # Assert
        assert result.exit_code == 1
        mock_process.assert_awaited_once()

    @patch.object(
        cmd_metadata, 'process', side_effect=Exception('async error')
    )
    @patch.object(cmd_metadata.console_out, 'print')
    def test_metadata_handles_async_exception(
        self,
        mock_print: Mock,
        mock_process: Mock,
        runner: CliRunner,
        context: DocBuildContext,
    ):
        """Test that exceptions during async processing are handled and time is printed."""
        # Arrange
        context.envconfig = {'paths': {'config_dir': '/fake/dir'}}

        # Act
        result = runner.invoke(main_cli, ['metadata'], obj=context)

        # Assert
        assert result.exit_code == 1
        assert isinstance(result.exception, Exception)
        assert 'async error' in str(result.exception)

        # Check that elapsed time was printed
        last_call_args = mock_print.call_args[0]
        assert 'Elapsed time' in last_call_args[0]

    @patch.object(cmd_metadata, 'process', side_effect=KeyboardInterrupt)
    @patch.object(cmd_metadata.console_out, 'print')
    def test_metadata_keyboard_interrupt(
        self,
        mock_print: Mock,
        mock_process: Mock,
        runner: CliRunner,
        context: DocBuildContext,
    ):
        """Test that KeyboardInterrupt is handled gracefully."""
        # Arrange
        context.envconfig = {'paths': {'config_dir': '/fake/dir'}}

        # Act
        result = runner.invoke(main_cli, ['metadata'], obj=context)

        # Assert
        assert result.exit_code == 1
        assert result.exception  #, KeyboardInterrupt

        # Check that elapsed time was printed
        last_call_args = mock_print.call_args[0]
        assert 'Elapsed time' in last_call_args[0]
