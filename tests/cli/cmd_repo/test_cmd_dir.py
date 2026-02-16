from docbuild.cli.cmd_repo.cmd_dir import cmd_dir


class _DummyPaths:
    """Minimal paths holder exposing ``repo_dir`` only."""

    def __init__(self, repo_dir: str) -> None:
        self.repo_dir = repo_dir


class _DummyEnv:
    """Fake EnvConfig-like object with a ``paths`` attribute."""

    def __init__(self, repo_dir: str) -> None:
        self.paths = _DummyPaths(repo_dir)


def test_cmd_dir_prints_repo_dir(runner):
    dummy_repo_dir = "/tmp/myrepo"

    class DummyContext:
        def __init__(self, repo_dir: str) -> None:
            self.envconfig = _DummyEnv(repo_dir)

    ctx_obj = DummyContext(dummy_repo_dir)

    result = runner.invoke(cmd_dir, obj=ctx_obj)

    assert result.exit_code == 0
    assert dummy_repo_dir in result.output
