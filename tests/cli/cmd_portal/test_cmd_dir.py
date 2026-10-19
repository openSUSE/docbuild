from unittest.mock import MagicMock

from docbuild.cli.cmd_portal import portal
from docbuild.cli.context import DocBuildContext


def test_portal_dir_env_default(runner):
    context = DocBuildContext()
    mock_env = MagicMock()
    mock_env.paths.config_dir = "/fake/env/portal/config"
    context.envconfig = mock_env

    result = runner.invoke(portal, ["dir"], obj=context)
    assert result.exit_code == 0
    assert "/fake/env/portal/config" in result.output


def test_portal_dir_app_flag(runner):
    context = DocBuildContext()
    mock_app = MagicMock()
    mock_app.paths.config_dir = "/fake/app/portal/config"
    context.appconfig = mock_app

    result = runner.invoke(portal, ["dir", "--app"], obj=context)
    assert result.exit_code == 0
    assert "/fake/app/portal/config" in result.output


def test_portal_dir_missing_config(runner):
    context = DocBuildContext()
    context.envconfig = None
    result = runner.invoke(portal, ["dir"], obj=context)
    assert result.exit_code != 0
