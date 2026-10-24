from unittest.mock import MagicMock

from docbuild.cli.cmd_portal import portal
from docbuild.cli.context import DocBuildContext


def test_portal_dir(runner):
    context = DocBuildContext()
    mock_env = MagicMock()
    mock_env.paths.config_dir = "/fake/env/portal/config"
    context.envconfig = mock_env

    result = runner.invoke(portal, ["dir"], obj=context)
    assert result.exit_code == 0
    assert "/fake/env/portal/config" in result.output


def test_portal_dir_missing_config(runner):
    context = DocBuildContext()
    context.envconfig = None

    # Catch the AssertionError raised when envconfig is None
    result = runner.invoke(portal, ["dir"], obj=context, catch_exceptions=True)
    assert result.exit_code != 0
    assert isinstance(result.exception, AssertionError)
