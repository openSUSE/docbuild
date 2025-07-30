from unittest.mock import AsyncMock, Mock, call

import pytest

# Import the module itself to allow patching its logger instance
from docbuild.cli.cmd_repo import process as process_module
from docbuild.cli.cmd_repo.process import clone_repo, process
from docbuild.cli.context import DocBuildContext
from docbuild.models.repo import Repo


@pytest.fixture
def process_mock() -> AsyncMock:
    """Mock the process object returned by create_subprocess_exec."""
    mock = AsyncMock()
    mock.communicate.return_value = (b'Cloning into bare repository...\n', b'')
    mock.returncode = 0
    return mock


@pytest.fixture
def mock_subprocess(monkeypatch, process_mock: AsyncMock) -> AsyncMock:
    """Fixture to mock asyncio.create_subprocess_exec."""
    mock_create_subprocess = AsyncMock(return_value=process_mock)
    monkeypatch.setattr(
        process_module.asyncio, 'create_subprocess_exec', mock_create_subprocess
    )
    return mock_create_subprocess


@pytest.fixture
def mock_clone_repo(monkeypatch) -> AsyncMock:
    """Fixture to mock the clone_repo function."""
    mock = AsyncMock(return_value=True)
    monkeypatch.setattr(process_module, 'clone_repo', mock)
    return mock


@pytest.fixture
def mock_create_stitchfile(monkeypatch) -> AsyncMock:
    """Fixture to mock create_stitchfile to return a predefined set of repos."""
    stitch_mock = Mock()
    git_node1 = Mock()
    git_node1.attrib.get.return_value = 'https://github.com/fakeorg/repo1.git'
    git_node2 = Mock()
    git_node2.attrib.get.return_value = 'https://github.com/fakeorg/repo2.git'
    # Use to_thread to simulate the async call to a sync function
    stitch_mock.xpath = Mock(return_value=[git_node1, git_node2])

    mock = AsyncMock(return_value=stitch_mock)
    monkeypatch.setattr(process_module, 'create_stitchfile', mock)
    return mock


async def test_clone_repo_already_exists(tmp_path, monkeypatch):
    """Test that clone_repo logs and returns if the repo already exists."""
    repo = Repo('https://github.com/org/existing.git')
    base_dir = tmp_path
    repo_path = base_dir / repo.slug
    repo_path.mkdir(parents=True, exist_ok=True)  # Simulate existing repo

    # Directly mock the `info` method of the logger instance.
    mock_log_info = Mock()
    monkeypatch.setattr(process_module.log, 'info', mock_log_info)

    await clone_repo(repo, base_dir)

    mock_log_info.assert_called_once_with(
        'Repository %r already exists at %s', repo.name, repo_path
    )


async def test_clone_repo_success(tmp_path, mock_subprocess, monkeypatch):
    """Test that a successful clone is logged correctly."""
    repo = Repo('https://github.com/org/new.git')
    base_dir = tmp_path

    # Mock both info and error loggers
    mock_log_info = Mock()
    mock_log_error = Mock()
    monkeypatch.setattr(process_module.log, 'info', mock_log_info)
    monkeypatch.setattr(process_module.log, 'error', mock_log_error)

    result = await clone_repo(repo, base_dir)

    assert result is True
    mock_subprocess.assert_awaited_once()

    # Check the exact sequence of info logs
    expected_info_calls = [
        call("Cloning '%s' into '%s'...", repo, str(base_dir / repo.slug)),
        call("Cloned '%s' successfully", repo),
    ]
    mock_log_info.assert_has_calls(expected_info_calls)
    assert mock_log_info.call_count == 2

    # Ensure no errors were logged
    mock_log_error.assert_not_called()


async def test_clone_repo_failure(tmp_path, process_mock, mock_subprocess, monkeypatch):
    """Test that a failed clone is logged correctly."""
    repo = Repo('https://github.com/org/nonexistent.git')
    base_dir = tmp_path
    error_message = b'fatal: repository not found\nAuthentication failed for repo.'

    # Configure the mock to simulate a failure
    process_mock.returncode = 128
    process_mock.communicate.return_value = (b'', error_message)

    mock_log_info = Mock()
    mock_log_error = Mock()
    monkeypatch.setattr(process_module.log, 'info', mock_log_info)
    monkeypatch.setattr(process_module.log, 'error', mock_log_error)

    result = await clone_repo(repo, base_dir)

    assert result is False
    mock_subprocess.assert_awaited_once()

    # Check that the initial "Cloning..." message was logged
    mock_log_info.assert_called_once_with(
        "Cloning '%s' into '%s'...", repo, str(base_dir / repo.slug)
    )

    # Check the exact sequence of error logs
    expected_error_calls = [
        call("Failed to clone '%s' (exit code %i)", repo, 128),
        call('  [git] %s', 'fatal: repository not found'),
        call('  [git] %s', 'Authentication failed for repo.'),
    ]
    mock_log_error.assert_has_calls(expected_error_calls, any_order=False)
    assert mock_log_error.call_count == len(expected_error_calls)


async def test_process_with_specific_repos(tmp_path, mock_clone_repo, monkeypatch):
    """Test `process` when specific repos are provided, including duplicates."""
    # We don't need the stitchfile logic for this test, so we can patch it.
    monkeypatch.setattr(
        process_module, 'create_stitchfile', AsyncMock(return_value=Mock())
    )

    repo_dir = tmp_path / 'repos'
    context = DocBuildContext(
        envconfig={
            'paths': {
                'repo_dir': str(repo_dir),
                'config_dir': str(tmp_path / 'config'),
            },
        },
    )
    # The directories must exist for the function to run
    (tmp_path / 'config').mkdir()
    repo_dir.mkdir()

    # Provide a list of repos with a duplicate
    input_repos = ('org/repo1', 'org/repo2', 'org/repo1')

    exit_code = await process(context, repos=input_repos)

    assert exit_code == 0

    # Check that clone_repo was called with the unique repos, preserving order
    assert mock_clone_repo.call_count == 2
    called_repos = [call.args[0] for call in mock_clone_repo.call_args_list]
    expected_repos = [Repo('org/repo1'), Repo('org/repo2')]
    assert called_repos == expected_repos


async def test_process_with_all_repos_from_xml(
    tmp_path, mock_clone_repo, mock_create_stitchfile
):
    """Test `process` when no specific repos are provided, using XML config."""
    repo_dir = tmp_path / 'repos'
    context = DocBuildContext(
        envconfig={
            'paths': {
                'repo_dir': str(repo_dir),
                'config_dir': str(tmp_path / 'config'),
            },
        },
    )
    (tmp_path / 'config').mkdir()
    repo_dir.mkdir()

    exit_code = await process(context, repos=())

    assert exit_code == 0
    mock_create_stitchfile.assert_awaited_once()

    assert mock_clone_repo.call_count == 2
    called_repos = [call.args[0] for call in mock_clone_repo.call_args_list]
    expected_repos = [
        Repo('https://github.com/fakeorg/repo1.git'),
        Repo('https://github.com/fakeorg/repo2.git'),
    ]
    assert called_repos == expected_repos


async def test_process_with_no_repos_found(tmp_path, mock_clone_repo, monkeypatch):
    """Test `process` when no repositories are found, ensuring it exits gracefully."""
    # Mock create_stitchfile to return a stitch node that has no git remotes
    stitch_mock = Mock()
    stitch_mock.xpath.return_value = []  # No git nodes found
    monkeypatch.setattr(
        process_module, 'create_stitchfile', AsyncMock(return_value=stitch_mock)
    )

    # Mock the logger to check for the "No repositories" message
    mock_log_info = Mock()
    monkeypatch.setattr(process_module.log, 'info', mock_log_info)

    repo_dir = tmp_path / 'repos'
    context = DocBuildContext(
        envconfig={
            'paths': {
                'repo_dir': str(repo_dir),
                'config_dir': str(tmp_path / 'config'),
            },
        },
    )
    (tmp_path / 'config').mkdir()
    repo_dir.mkdir()

    # Call process with no specific repos, so it reads from the (empty) config
    exit_code = await process(context, repos=())

    assert exit_code == 0
    mock_clone_repo.assert_not_called()
    mock_log_info.assert_called_once_with('No repositories found to clone.')


async def test_process_failure_if_one_clone_fails(
    tmp_path, mock_clone_repo, monkeypatch
):
    """Test that `process` returns 1 if any clone operation fails."""
    # We don't need the stitchfile logic for this test.
    monkeypatch.setattr(
        process_module, 'create_stitchfile', AsyncMock(return_value=Mock())
    )

    # Configure the mock to simulate one success and one failure
    mock_clone_repo.side_effect = [True, False]

    repo_dir = tmp_path / 'repos'
    context = DocBuildContext(
        envconfig={
            'paths': {
                'repo_dir': str(repo_dir),
                'config_dir': str(tmp_path / 'config'),
            },
        },
    )
    (tmp_path / 'config').mkdir()
    repo_dir.mkdir()

    exit_code = await process(context, repos=('org/repo1', 'org/repo2'))

    assert exit_code == 1
    assert mock_clone_repo.call_count == 2


async def test_clone_repo_failure_no_stderr(
    tmp_path, process_mock, mock_subprocess, monkeypatch
):
    """Test that a failed clone with empty stderr is logged correctly."""
    repo = Repo('https://github.com/org/nonexistent.git')
    base_dir = tmp_path

    # Configure the mock to simulate a failure with empty stderr
    process_mock.returncode = 128
    process_mock.communicate.return_value = (b'', b'')

    mock_log_info = Mock()
    mock_log_error = Mock()
    monkeypatch.setattr(process_module.log, 'info', mock_log_info)
    monkeypatch.setattr(process_module.log, 'error', mock_log_error)

    result = await clone_repo(repo, base_dir)

    assert result is False
    mock_subprocess.assert_awaited_once()
    mock_log_info.assert_called_once()

    # Check that only the main error was logged, as stderr was empty
    mock_log_error.assert_called_once_with(
        "Failed to clone '%s' (exit code %i)", repo, 128
    )


async def test_clone_repo_failure_whitespace_stderr(
    tmp_path, process_mock, mock_subprocess, monkeypatch
):
    """Test a failed clone with only whitespace in stderr."""
    repo = Repo('https://github.com/org/nonexistent.git')
    base_dir = tmp_path

    # Configure the mock to simulate a failure with whitespace-only stderr
    process_mock.returncode = 128
    process_mock.communicate.return_value = (b'', b' \n \t \n')

    mock_log_info = Mock()
    mock_log_error = Mock()
    monkeypatch.setattr(process_module.log, 'info', mock_log_info)
    monkeypatch.setattr(process_module.log, 'error', mock_log_error)

    result = await clone_repo(repo, base_dir)

    assert result is False
    mock_subprocess.assert_awaited_once()
    mock_log_info.assert_called_once()

    # Check that only the main error was logged, as stderr was just whitespace
    mock_log_error.assert_called_once_with(
        "Failed to clone '%s' (exit code %i)", repo, 128
    )
