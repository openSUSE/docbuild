from docbuild.cli.cmd_repo.cmd_dir import cmd_dir


def test_cmd_dir_prints_repo_dir(runner, monkeypatch):
    dummy_repo_dir = "/tmp/myrepo"

    class DummyContext:
        def __init__(self, repo_dir):
            self.envconfig = {"paths": {"repo_dir": repo_dir}}

    ctx_obj = DummyContext(dummy_repo_dir)

    result = runner.invoke(cmd_dir, obj=ctx_obj)

    assert result.exit_code == 0
    assert dummy_repo_dir in result.output


def test_cmd_dir_no_envconfig(runner, capsys):
    class DummyContextNoEnv:
        envconfig = None

    result = runner.invoke(cmd_dir, obj=DummyContextNoEnv())

    captured = capsys.readouterr()

    assert captured.out == ""
    assert result.exit_code != 0
    assert isinstance(result.exception, ValueError)
    assert "No envconfig found in context." in str(result.exception)
