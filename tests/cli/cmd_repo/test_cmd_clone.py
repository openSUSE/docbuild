"""Tests for the 'docbuild repo clone' command."""

import logging
import re
from unittest.mock import AsyncMock

import pytest

from docbuild.cli.cmd_repo.cmd_clone import clone
import docbuild.cli.cmd_repo.process as mod_process
from docbuild.cli.context import DocBuildContext
from docbuild.utils import shell as shell_module

log = logging.getLogger(__name__)


class _DummyPaths:
    """Lightweight stand-in for EnvPathsConfig used in tests.

    Only the attributes accessed by cmd_repo.process are provided.
    """

    def __init__(self, *, config_dir: str, repo_dir: str) -> None:
        self.config_dir = config_dir
        self.repo_dir = repo_dir


class _DummyEnv:
    """Minimal envconfig replacement exposing ``paths`` for tests.

    This avoids constructing a full EnvConfig instance while still matching
    the runtime behaviour expected by the cloning logic.
    """

    def __init__(self, *, config_dir: str, repo_dir: str) -> None:
        self.paths = _DummyPaths(config_dir=config_dir, repo_dir=repo_dir)

#
# @pytest.fixture
# def process_mock() -> AsyncMock:
#     """Mock the process object returned by create_subprocess_exec."""
#     mock = AsyncMock()
#     mock.communicate.return_value = (b'stdout', b'stderr')
#     mock.returncode = 0
#     return mock


@pytest.fixture
def mock_subprocess(monkeypatch) -> AsyncMock:
    """Fixture to mock asyncio.create_subprocess_exec."""
    process_mock = AsyncMock()
    process_mock.communicate.return_value = (b"stdout", b"stderr")
    process_mock.returncode = 0
    mock_create_subprocess = AsyncMock(return_value=process_mock)
    # Git commands go through shell.run_command → asyncio.create_subprocess_exec
    # in the shell utility module.
    monkeypatch.setattr(
        shell_module.asyncio, "create_subprocess_exec", mock_create_subprocess
    )
    return mock_create_subprocess


def test_clone_from_xml_config(runner, tmp_path, mock_subprocess, caplog):
    """Test cloning repositories defined in an XML configuration file."""
    caplog.set_level(logging.INFO, logger="docbuild.git")
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    repo_dir = tmp_path / "repos"
    repo_dir.mkdir()

    # Create a dummy XML config
    xml_content = """
<docservconfig>
  <product productid="sles">
    <docset setid="15-SP1">
      <builddocs>
        <git remote="https://github.com/test/one.git" />
      </builddocs>
    </docset>
    <docset setid="15-SP2">
      <builddocs>
        <git remote="https://github.com/test/two.git" />
      </builddocs>
    </docset>
  </product>
</docservconfig>
"""
    (config_dir / "sles.xml").write_text(xml_content)

    context = DocBuildContext(
        envconfig=_DummyEnv(
            config_dir=str(config_dir),
            repo_dir=str(repo_dir),
        ),
    )

    runner.invoke(clone, [], obj=context)

    assert mock_subprocess.call_count == 2

    calls = mock_subprocess.call_args_list
    cloned_repos = {call[0][6] for call in calls}  # The 7th arg is the repo URL
    assert "https://github.com/test/one.git" in cloned_repos
    assert "https://github.com/test/two.git" in cloned_repos


# @pytest.mark.asyncio
async def test_process_stitchnode_none(monkeypatch, tmp_path):
    """Test that process raises ValueError if create_stitchfile returns None."""
    # Patch create_stitchfile to return None
    monkeypatch.setattr(mod_process, "create_stitchfile", AsyncMock(return_value=None))

    context = DocBuildContext(
        envconfig=_DummyEnv(
            config_dir=str(tmp_path / "config"),
            repo_dir=str(tmp_path / "repos"),
        )
    )

    # The config_dir must exist, even if empty
    (tmp_path / "config").mkdir()
    (tmp_path / "repos").mkdir()

    with pytest.raises(ValueError,
                       match=re.escape("Stitch node could not be created.")):
        await mod_process.process(context, repos=())


async def test_process_configdir_none():
    """This scenario is no longer reachable with validated EnvConfig.

    The higher-level CLI now ensures ``envconfig`` is a fully validated
    environment configuration. Retain this test as a smoke check that
    calling ``process`` with a dummy, but structurally valid, envconfig
    does not raise and returns an integer exit code.
    """

    context = DocBuildContext(
        envconfig=_DummyEnv(config_dir="/non/existent/config", repo_dir="/tmp/repos"),
    )

    result = await mod_process.process(context, repos=())
    assert isinstance(result, int)


async def test_process_repodir_none():
    """See docstring of test_process_configdir_none for rationale."""

    context = DocBuildContext(
        envconfig=_DummyEnv(config_dir="/tmp/config", repo_dir="/non/existent/repos"),
    )

    result = await mod_process.process(context, repos=())
    assert isinstance(result, int)
