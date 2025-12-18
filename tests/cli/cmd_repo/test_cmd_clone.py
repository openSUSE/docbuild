"""Tests for the 'docbuild repo clone' command."""

from subprocess import CompletedProcess
import logging
from unittest.mock import AsyncMock

import pytest

from docbuild.cli.cmd_repo.cmd_clone import clone
import docbuild.cli.cmd_repo.process as mod_process
from docbuild.cli.context import DocBuildContext

log = logging.getLogger(__name__)

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
    process_mock.communicate.return_value = (b'stdout', b'stderr')
    process_mock.returncode = 0
    mock_create_subprocess = AsyncMock(return_value=process_mock)
    monkeypatch.setattr(
        mod_process.asyncio, 'create_subprocess_exec', mock_create_subprocess
    )
    return mock_create_subprocess


def test_clone_from_xml_config(runner, tmp_path, mock_subprocess, caplog):
    """Test cloning repositories defined in an XML configuration file."""
    caplog.set_level(logging.INFO, logger="docbuild.git")
    config_dir = tmp_path / 'config'
    config_dir.mkdir()
    repo_dir = tmp_path / 'repos'
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
    (config_dir / 'sles.xml').write_text(xml_content)

    context = DocBuildContext(
        envconfig={
            'paths': {'repo_dir': str(repo_dir), 'config_dir': str(config_dir)},
        },
    )

    runner.invoke(clone, [], obj=context)

    assert mock_subprocess.call_count == 2

    calls = mock_subprocess.call_args_list
    cloned_repos = {call[0][6] for call in calls}  # The 7th arg is the repo URL
    assert 'https://github.com/test/one.git' in cloned_repos
    assert 'https://github.com/test/two.git' in cloned_repos


def test_clone_invalid_envconfig(runner):
    """Test that an error is raised if the environment configuration is invalid."""
    context = DocBuildContext(envconfig=None)

    result = runner.invoke(
        clone,
        ['org/repo'],
        obj=context,
        # catch_exceptions=True,
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, ValueError)
    assert 'No envconfig found in context' in str(result.exception)


# @pytest.mark.asyncio
async def test_process_stitchnode_none(monkeypatch, tmp_path):
    """Test that process raises ValueError if create_stitchfile returns None."""
    # Patch create_stitchfile to return None
    monkeypatch.setattr(mod_process, 'create_stitchfile', AsyncMock(return_value=None))

    context = DocBuildContext(
        envconfig={
            'paths': {
                'repo_dir': str(tmp_path / 'repos'),
                'config_dir': str(tmp_path / 'config'),
            }
        }
    )

    # The config_dir must exist, even if empty
    (tmp_path / 'config').mkdir()
    (tmp_path / 'repos').mkdir()

    with pytest.raises(ValueError, match='Stitch node could not be created.'):
        await mod_process.process(context, repos=())


async def test_process_configdir_none():
    context = DocBuildContext(envconfig={'paths': {}})
    with pytest.raises(
        ValueError,
        match='Could not get a value from envconfig.paths.config_dir',
    ):
        await mod_process.process(context, repos=())


async def test_process_repodir_none():
    context = DocBuildContext(envconfig={'paths': {'config_dir': '/dummy/config'}})
    with pytest.raises(
        ValueError,
        match='Could not get a value from envconfig.paths.repo_dir',
    ):
        await mod_process.process(context, repos=())
