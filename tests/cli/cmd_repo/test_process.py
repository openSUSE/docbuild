from unittest.mock import AsyncMock, Mock, call

import pytest

# Import the module itself to allow patching its logger instance
from docbuild.cli.cmd_repo import process as process_module
from docbuild.cli.cmd_repo.process import process
from docbuild.cli.context import DocBuildContext
from docbuild.models.repo import Repo


@pytest.fixture
def mock_managed_git_repo(monkeypatch) -> AsyncMock:
    """Fixture to mock the ManagedGitRepo class."""
    mock_instance = AsyncMock()
    mock_instance.clone_bare.return_value = True
    mock_class = Mock(return_value=mock_instance)
    monkeypatch.setattr(process_module, 'ManagedGitRepo', mock_class)
    return mock_class


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


async def test_process_with_specific_repos(
    tmp_path, mock_managed_git_repo, monkeypatch
):
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

    # Check that ManagedGitRepo was instantiated with the unique repos, preserving order
    assert mock_managed_git_repo.call_count == 2
    called_repos = [Repo(call[0][0]) for call in mock_managed_git_repo.call_args_list]
    expected_repos = [Repo('org/repo1'), Repo('org/repo2')]
    assert called_repos == expected_repos


async def test_process_with_all_repos_from_xml(
    tmp_path, mock_managed_git_repo, mock_create_stitchfile
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

    assert mock_managed_git_repo.call_count == 2
    called_repos = [Repo(call[0][0]) for call in mock_managed_git_repo.call_args_list]
    expected_repos = [
        Repo('https://github.com/fakeorg/repo1.git'),
        Repo('https://github.com/fakeorg/repo2.git'),
    ]
    assert called_repos == expected_repos


async def test_process_with_no_repos_found(
    tmp_path, mock_managed_git_repo, monkeypatch
):
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
    mock_managed_git_repo.assert_not_called()
    mock_log_info.assert_called_once_with('No repositories found to clone.')


async def test_process_failure_if_one_clone_fails(
    tmp_path, mock_managed_git_repo, monkeypatch
):
    """Test that `process` returns 1 if any clone operation fails."""
    # We don't need the stitchfile logic for this test.
    monkeypatch.setattr(
        process_module, 'create_stitchfile', AsyncMock(return_value=Mock())
    )

    # Configure the mock to simulate one success and one failure from clone_bare()
    mock_managed_git_repo.return_value.clone_bare.side_effect = [True, False]

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
    assert mock_managed_git_repo.call_count == 2
