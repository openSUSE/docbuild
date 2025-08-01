

from docbuild.cli.cmd_repo.cmd_list import cmd_list
from docbuild.cli.context import DocBuildContext


def test_cmd_list_envconfig_none(runner):
    context = DocBuildContext(envconfig=None)
    result = runner.invoke(cmd_list, obj=context)
    assert result.exit_code != 0
    assert 'No envconfig found in context.' in str(result.exception)


def test_cmd_list_repo_dir_none(runner):
    context = DocBuildContext(envconfig={'paths': {}})
    result = runner.invoke(cmd_list, obj=context)
    assert result.exit_code != 0
    assert 'No permanent repositories defined' in str(result.exception)


def test_cmd_list_repo_dir_not_exists(runner, tmp_path):
    repo_dir = tmp_path / 'repos'
    context = DocBuildContext(envconfig={'paths': {'repo_dir': str(repo_dir)}})
    result = runner.invoke(cmd_list, obj=context)
    assert result.exit_code == 1
    assert 'No permanent repositories found' in result.output
    assert str(repo_dir) in result.output.replace('\n', '')


def test_cmd_list_success(runner, tmp_path):
    repo_dir = tmp_path / 'repos'
    repo_dir.mkdir()
    (repo_dir / 'repo1').mkdir()
    (repo_dir / 'repo2').mkdir()
    (repo_dir / '.hidden').mkdir()
    context = DocBuildContext(envconfig={'paths': {'repo_dir': str(repo_dir)}})
    result = runner.invoke(cmd_list, obj=context)
    assert result.exit_code == 0
    assert 'Available permanent repositories' in result.output
    assert str(repo_dir) in result.output.replace('\n', '')
    assert 'repo1' in result.output
    assert 'repo2' in result.output
    assert '.hidden' not in result.output
