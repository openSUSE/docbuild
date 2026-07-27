from unittest.mock import AsyncMock, Mock

import pytest

from docbuild.models.repo import Repo

# Import the module itself to allow patching
from docbuild.tasks import repo as repo_module
from docbuild.tasks.repo import clone_repositories


@pytest.fixture
def mock_managed_git_repo(monkeypatch) -> AsyncMock:
    """Fixture to mock the ManagedGitRepo class."""
    mock_instance = AsyncMock()
    mock_instance.clone_bare.return_value = True
    mock_class = Mock(return_value=mock_instance)
    monkeypatch.setattr(repo_module, "ManagedGitRepo", mock_class)
    return mock_class


@pytest.fixture
def mock_parse_portal_config(monkeypatch) -> AsyncMock:
    """Fixture to mock parse_portal_config to return a predefined set of repos."""
    stitch_mock = Mock()
    git_node1 = Mock()
    git_node1.attrib.get.return_value = "https://github.com/fakeorg/repo1.git"
    git_node2 = Mock()
    git_node2.attrib.get.return_value = "https://github.com/fakeorg/repo2.git"
    # Use to_thread to simulate the async call to a sync function
    stitch_mock.xpath = Mock(return_value=[git_node1, git_node2])

    mock = AsyncMock(return_value=stitch_mock)
    monkeypatch.setattr(repo_module, "parse_portal_config", mock)
    return mock


async def test_clone_repositories_with_specific_repos(
    tmp_path, mock_managed_git_repo, monkeypatch
):
    """Test cloning when specific repos are provided, including duplicates."""
    monkeypatch.setattr(
        repo_module, "parse_portal_config", AsyncMock(return_value=Mock())
    )

    main_portal_config = tmp_path / "config" / "portal.xml"
    repo_dir = tmp_path / "repos"

    input_repos = ("org/repo1", "org/repo2", "org/repo1")

    exit_code = await clone_repositories(main_portal_config, repo_dir, input_repos)

    assert exit_code == 0
    assert mock_managed_git_repo.call_count == 2
    called_repos = [Repo(call[0][0]) for call in mock_managed_git_repo.call_args_list]
    expected_repos = [Repo("org/repo1"), Repo("org/repo2")]
    assert called_repos == expected_repos


async def test_clone_repositories_with_all_repos_from_xml(
    tmp_path, mock_managed_git_repo, mock_parse_portal_config
):
    """Test cloning when no specific repos are provided, using XML config."""
    main_portal_config = tmp_path / "config" / "portal.xml"
    repo_dir = tmp_path / "repos"

    exit_code = await clone_repositories(main_portal_config, repo_dir, ())

    assert exit_code == 0
    mock_parse_portal_config.assert_awaited_once()

    assert mock_managed_git_repo.call_count == 2
    called_repos = [Repo(call[0][0]) for call in mock_managed_git_repo.call_args_list]
    expected_repos = [
        Repo("https://github.com/fakeorg/repo1.git"),
        Repo("https://github.com/fakeorg/repo2.git"),
    ]
    assert called_repos == expected_repos


async def test_clone_repositories_with_no_repos_found(
    tmp_path, mock_managed_git_repo, monkeypatch
):
    """Test cloning when no repositories are found, ensuring it exits gracefully."""
    stitch_mock = Mock()
    stitch_mock.xpath.return_value = []  # No git nodes found
    monkeypatch.setattr(
        repo_module, "parse_portal_config", AsyncMock(return_value=stitch_mock)
    )

    mock_log_info = Mock()
    monkeypatch.setattr(repo_module.log, "info", mock_log_info)

    main_portal_config = tmp_path / "config" / "portal.xml"
    repo_dir = tmp_path / "repos"

    exit_code = await clone_repositories(main_portal_config, repo_dir, ())

    assert exit_code == 0
    mock_managed_git_repo.assert_not_called()
    mock_log_info.assert_called_once_with("No repositories found to clone.")


async def test_clone_repositories_failure_if_one_clone_fails(
    tmp_path, mock_managed_git_repo, monkeypatch
):
    """Test that it returns 1 if any clone operation fails."""
    monkeypatch.setattr(
        repo_module, "parse_portal_config", AsyncMock(return_value=Mock())
    )
    # Simulate one success and one failure
    mock_managed_git_repo.return_value.clone_bare.side_effect = [True, False]

    main_portal_config = tmp_path / "config" / "portal.xml"
    repo_dir = tmp_path / "repos"

    exit_code = await clone_repositories(main_portal_config, repo_dir, ("org/repo1", "org/repo2"))

    assert exit_code == 1
    assert mock_managed_git_repo.call_count == 2
