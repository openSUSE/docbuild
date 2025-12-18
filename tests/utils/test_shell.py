"""Tests for shell command utilities."""

from pathlib import Path

import pytest

from docbuild.utils.shell import execute_git_command, CompletedProcess


async def test_execute_git_command_with_gitconfig(tmp_path):
    """Verify that execute_git_command uses the config file.

      This is provided in the`gitconfig` parameter to replace the user's configuration.
    """
    # The tmp_path fixture provides a temporary directory as a Path object
    repo_path = tmp_path

    # Initialize a Git repository in the temporary directory
    await execute_git_command("init", cwd=repo_path)

    # Create a project-specific gitconfig file
    config_content = "[user]\n    name = Test User From Project Config\n"
    project_config_path = repo_path / ".gitconfig"
    project_config_path.write_text(config_content)

    # Execute 'git config' to read the value, passing the project config
    process = await execute_git_command(
        "config", "--get", "user.name", cwd=repo_path, gitconfig=project_config_path
    )

    # Assert that the output matches the value from our project-specific config
    assert process.stdout == "Test User From Project Config"


async def test_execute_git_command_without_gitconfig(tmp_path):
    """Verify that execute_git_command falls back to the default.

    Fall back to GIT_CONFIG_FILENAME when the `gitconfig` parameter is not
    provided.
    """
    repo_path = tmp_path

    # Execute 'git config' to read the value from our default config file.
    # We call it without the `gitconfig` parameter to test the default behavior.
    process = await execute_git_command(
        "config", "--get", "docbuild.name", cwd=repo_path
    )

    # This asserts that the value from 'etc/git/gitconfig' is read correctly.
    assert process.stdout == "docbuild-project"


async def test_execute_git_command_with_nonexistent_cwd():
    with pytest.raises(FileNotFoundError):
        await execute_git_command(
            'config', '--get', 'docbuild.name', cwd=Path("does-not-exist")
        )

async def test_execute_git_command_with_failed_command():
    with pytest.raises(RuntimeError):
        await execute_git_command(
            'foo',  # wrong git command
        )
