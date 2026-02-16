from docbuild.cli.cmd_repo.cmd_list import cmd_list
from docbuild.cli.context import DocBuildContext


class _DummyPaths:
    """Minimal paths holder exposing ``repo_dir`` only."""

    def __init__(self, repo_dir: str) -> None:
        self.repo_dir = repo_dir


class _DummyEnv:
    """Fake EnvConfig-like object with a ``paths`` attribute."""

    def __init__(self, repo_dir: str) -> None:
        self.paths = _DummyPaths(repo_dir)


def test_cmd_list_repo_dir_not_exists(runner, tmp_path):
    repo_dir = tmp_path / "repos"
    context = DocBuildContext(envconfig=_DummyEnv(str(repo_dir)))
    result = runner.invoke(cmd_list, obj=context)
    assert result.exit_code == 1
    assert "No permanent repositories found" in result.output
    assert str(repo_dir) in result.output.replace("\n", "")


def test_cmd_list_success(runner, tmp_path):
    repo_dir = tmp_path / "repos"
    repo_dir.mkdir()
    (repo_dir / "repo1").mkdir()
    (repo_dir / "repo2").mkdir()
    (repo_dir / ".hidden").mkdir()
    context = DocBuildContext(envconfig=_DummyEnv(str(repo_dir)))
    result = runner.invoke(cmd_list, obj=context)
    assert result.exit_code == 0
    assert "Available permanent repositories" in result.output
    assert str(repo_dir) in result.output.replace("\n", "")
    assert "repo1" in result.output
    assert "repo2" in result.output
    assert ".hidden" not in result.output
