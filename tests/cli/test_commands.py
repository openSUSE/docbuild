"""Tests for the command execution helper functions."""

import asyncio
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import AsyncMock, Mock, patch

import pytest

from docbuild.cli import commands as commands_module


class TestRunCommand:
    """Tests for the run_command function."""

    async def test_run_command(self):
        """Test the run_command function."""
        # Use a simple command that is guaranteed to exist
        command = ['echo', 'Hello, World!']

        process = await commands_module.run_command(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        returncode, stdout, stderr = process.returncode, process.stdout, process.stderr

        # Assert the return code is 0 (success)
        assert returncode == 0, f'Expected return code 0, got {returncode}'

        # Assert the stdout contains the expected output
        assert stdout == 'Hello, World!\n', f'Unexpected stdout: {stdout}'

        # Assert stderr is empty
        assert stderr is None, f'Unexpected stderr: {stderr}'

    @patch.object(
        commands_module.asyncio, 'create_subprocess_exec', new_callable=AsyncMock
    )
    async def test_run_command_success(self, mock_create_subprocess_exec: AsyncMock):
        """Test that run_command successfully executes a command."""
        # Arrange
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b'output data', b'error data')
        mock_create_subprocess_exec.return_value = mock_process

        program = '/bin/echo'
        args = ('hello', 'world')

        # Act
        result = await commands_module.run_command(program, *args)

        # Assert
        mock_create_subprocess_exec.assert_awaited_once_with(
            program,
            *args,
            cwd=None,
            env=None,
            stdin=None,
            stderr=None,
            stdout=None,
        )
        mock_process.communicate.assert_awaited_once()
        assert isinstance(result, CompletedProcess)
        assert result.returncode == 0
        assert result.stdout == 'output data'
        assert result.stderr == 'error data'
        assert result.args == [program, *args]

    @patch.object(
        commands_module.asyncio, 'create_subprocess_exec', new_callable=AsyncMock
    )
    async def test_run_command_failure(self, mock_create_subprocess_exec: AsyncMock):
        """Test that run_command handles a failed command execution."""
        # Arrange
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b'', b'command failed')
        mock_create_subprocess_exec.return_value = mock_process
        program = 'false'

        # Act
        result = await commands_module.run_command(program)

        # Assert
        assert result.returncode == 1
        assert result.stdout is None
        assert result.stderr == 'command failed'

    @patch.object(
        commands_module.asyncio, 'create_subprocess_exec', new_callable=AsyncMock
    )
    async def test_run_command_with_cwd_and_env(
        self,
        mock_create_subprocess_exec: AsyncMock,
    ) -> None:
        """Test that run_command passes cwd and env to the subprocess."""
        # Arrange
        mock_process = AsyncMock(returncode=0)
        mock_process.communicate.return_value = (b'', b'')
        mock_create_subprocess_exec.return_value = mock_process

        cwd = '/tmp'
        env = {'VAR': 'value'}

        program = '/bin/ls'
        # Act
        await commands_module.run_command(program, cwd=cwd, env=env)

        # Assert
        mock_create_subprocess_exec.assert_awaited_once_with(
            program,
            cwd=cwd,
            env=env,
            stdin=None,
            stderr=None,
            stdout=None,
        )

    @patch.object(
        commands_module.asyncio, 'create_subprocess_exec', new_callable=AsyncMock
    )
    async def test_run_command_converts_args_to_str(
        self, mock_create_subprocess_exec: AsyncMock
    ):
        """Test that run_command converts all arguments to strings."""
        # Arrange
        mock_process = AsyncMock(returncode=0)
        mock_process.communicate.return_value = (b'', b'')
        mock_create_subprocess_exec.return_value = mock_process

        program = Path('/usr/bin/cmd')
        args = (123, True, Path('/some/path'))

        # Act
        await commands_module.run_command(program, *args)

        # Assert
        mock_create_subprocess_exec.assert_awaited_once_with(
            str(program), '123', 'True', '/some/path',
            cwd=None, env=None, stdin=None, stderr=None, stdout=None
        )


class TestResolveCommand:
    """Tests for the resolve_command function."""

    @patch.object(commands_module.shutil, 'which')
    def test_resolve_command_success(self, mock_which: Mock):
        """Test that a program in PATH is resolved to its absolute path."""
        # Arrange
        mock_which.return_value = '/usr/bin/echo'
        program = 'echo'
        args = ('hello', 'world')

        # Act
        result = commands_module.resolve_command(program, *args)

        # Assert
        mock_which.assert_called_once_with('echo')
        assert result == ('/usr/bin/echo', 'hello', 'world')

    @patch.object(commands_module.shutil, 'which')
    def test_resolve_command_with_absolute_path(self, mock_which: Mock):
        """Test that an absolute path program is handled correctly."""
        # Arrange
        abs_program_path = '/bin/ls'
        mock_which.return_value = abs_program_path
        args = ('-l', '/tmp')

        # Act
        result = commands_module.resolve_command(abs_program_path, *args)

        # Assert
        mock_which.assert_called_once_with(abs_program_path)
        assert result == ('/bin/ls', '-l', '/tmp')

    @patch.object(commands_module.shutil, 'which', return_value=None)
    def test_resolve_command_not_found_raises_error(self, mock_which: Mock):
        """Test that a non-existent program raises FileNotFoundError."""
        # Arrange
        program = 'nonexistent_program'

        # Act & Assert
        with pytest.raises(
            FileNotFoundError, match=f"Program '{program}' not found in PATH"
        ):
            commands_module.resolve_command(program)
        mock_which.assert_called_once_with(program)

    @patch.object(commands_module.shutil, 'which')
    def test_resolve_command_converts_args_to_str(self, mock_which: Mock):
        """Test that all arguments are converted to strings."""
        # Arrange
        mock_which.return_value = '/usr/bin/cmd'
        program = 'cmd'
        args = (Path('/some/path'), 123, True)

        # Act
        result = commands_module.resolve_command(program, *args)

        # Assert
        assert result == ('/usr/bin/cmd', '/some/path', '123', 'True')
        assert all(isinstance(arg, str) for arg in result)


class TestRunGit:
    """Tests for the run_git function."""

    @patch.object(commands_module, 'resolve_command')
    @patch.object(commands_module, 'run_command', new_callable=AsyncMock)
    async def test_run_git_success(
        self, mock_run_command: AsyncMock, mock_resolve_command: Mock
    ):
        """Test that run_git successfully resolves and calls run_command."""
        # Arrange
        resolved_program = '/usr/bin/git'
        resolved_args = ['status']
        mock_resolve_command.return_value = (resolved_program, *resolved_args)
        expected_result = CompletedProcess(
            args=[resolved_program, *resolved_args], returncode=0
        )
        mock_run_command.return_value = expected_result

        # Act
        result = await commands_module.run_git('status', cwd='/fake/dir')

        # Assert
        mock_resolve_command.assert_called_once_with('git', 'status')
        mock_run_command.assert_awaited_once_with(
            resolved_program,
            *resolved_args,
            cwd='/fake/dir',
            env=None,
        )
        assert result is expected_result

    @patch.object(commands_module, 'resolve_command', side_effect=FileNotFoundError)
    async def test_run_git_not_found(self, mock_resolve_command: Mock):
        """Test that run_git raises FileNotFoundError if git is not found."""
        with pytest.raises(FileNotFoundError):
            await commands_module.run_git('status')
        mock_resolve_command.assert_called_once_with('git', 'status')


class TestRunDaps:
    """Tests for the run_daps function."""

    @patch.object(commands_module, 'resolve_command')
    @patch.object(commands_module, 'run_command', new_callable=AsyncMock)
    async def test_run_daps_success(
        self, mock_run_command: AsyncMock, mock_resolve_command: Mock
    ):
        """Test that run_daps successfully resolves and calls run_command."""
        # Arrange
        resolved_program = '/usr/bin/daps'
        resolved_args = ['-d', 'DC-fake', 'html']
        mock_resolve_command.return_value = (resolved_program, *resolved_args)
        expected_result = CompletedProcess(
            args=[resolved_program, *resolved_args], returncode=0
        )
        mock_run_command.return_value = expected_result

        # Act
        result = await commands_module.run_daps('-d', 'DC-fake', 'html', cwd='/fake/dir')

        # Assert
        mock_resolve_command.assert_called_once_with('daps', '-d', 'DC-fake', 'html')
        mock_run_command.assert_awaited_once_with(
            resolved_program,
            *resolved_args,
            cwd='/fake/dir',
            env=None,
        )
        assert result is expected_result

    @patch.object(commands_module, 'resolve_command', side_effect=FileNotFoundError)
    async def test_run_daps_not_found(self, mock_resolve_command: Mock):
        """Test that run_daps raises FileNotFoundError if daps is not found."""
        with pytest.raises(FileNotFoundError):
            await commands_module.run_daps('help')
        mock_resolve_command.assert_called_once_with('daps', 'help')
