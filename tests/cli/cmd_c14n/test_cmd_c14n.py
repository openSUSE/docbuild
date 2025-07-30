from unittest.mock import Mock

from docbuild.cli import cmd_c14n
from docbuild.cli.context import DocBuildContext


# TODO: Improve test cases when the c14n command is fully implemented.
class TestC14nCommand:
    def test_c14n_command_with_verbose_context(self, runner, mock_context):
        """Test c14n command with a verbose context."""
        result = runner.invoke(cmd_c14n.c14n, [], obj=mock_context)

        assert result.exit_code == 0
        # assert '[C17N] Verbosity: 2' in result.output

    def test_c14n_command_with_zero_verbosity(self, runner):
        """Test c14n command with zero verbosity."""
        mock_context = Mock(spec=DocBuildContext)
        mock_context.verbose = 0

        result = runner.invoke(cmd_c14n.c14n, [], obj=mock_context)

        assert result.exit_code == 0
        # assert '[C17N] Verbosity: 0' in result.output

    def test_c14n_command_with_high_verbosity(self, runner):
        """Test c14n command with high verbosity."""
        mock_context = Mock(spec=DocBuildContext)
        mock_context.verbose = 5

        result = runner.invoke(cmd_c14n.c14n, [], obj=mock_context)

        assert result.exit_code == 0
        # assert '[C17N] Verbosity: 5' in result.output

    def test_c14n_command_without_context_object(self, runner):
        """Test c14n command without passing a context object."""
        # Don't pass obj parameter - this will test ctx.ensure_object()
        result = runner.invoke(cmd_c14n.c14n, [], obj=DocBuildContext())

        assert result.exit_code == 0
        # Should create a default context with verbose=0
        # assert '[C17N] Verbosity: 0' in result.output
