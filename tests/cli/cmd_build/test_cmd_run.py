"""Tests for docbuild build run subcommand."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner
import pytest

from docbuild.cli.cmd_build import build, cmd_run
from docbuild.cli.cmd_build.cmd_run import run
from docbuild.cli.context import DocBuildContext
from docbuild.models.config.env import EnvConfig
from docbuild.utils import sysdeps


def test_build_group_registers_run_command():
    """Verify 'run' is registered under the 'build' click group."""
    assert "run" in build.commands
    assert build.commands["run"] is run


def test_build_run_help():
    """Verify 'docbuild build run --help' displays descriptions and options."""
    runner = CliRunner()
    result = runner.invoke(build, ["run", "--help"])

    assert result.exit_code == 0
    assert "Build a documentation deliverables from source" in result.output
    assert "--skip-repo-update" in result.output
    assert "--skip-metadata" in result.output


def test_build_group_help_shows_run_subcommand():
    """Verify 'docbuild build --help' lists 'run' as an available subcommand."""
    runner = CliRunner()
    result = runner.invoke(build, ["--help"])

    assert result.exit_code == 0
    assert "run" in result.output


@pytest.mark.parametrize(
    "build_result,options,expected",
    [
        (0, [], True),
        (1, [], False),
        (0, ["--no-sitemap"], False),
    ],
)
def test_run_sitemap_after_success(build_result, options, expected):
    """Only successful builds with sitemap enabled use the progress wrapper."""
    env = EnvConfig.from_dict({})
    context = DocBuildContext(envconfig=env, verbose=2)
    with (
        patch.object(sysdeps, "check_dependencies", return_value=[]),
        patch.object(cmd_run, "build_process", new_callable=AsyncMock) as process,
        patch.object(
            cmd_run, "generate_sitemap_with_progress", new_callable=AsyncMock
        ) as generate,
    ):
        process.return_value = build_result
        result = CliRunner().invoke(run, ["--skip-metadata", *options], obj=context)

    assert result.exit_code == build_result, result.output
    if expected:
        generate.assert_awaited_once_with(
            Path(env.paths.target.target_base_dir),
            str(env.general.canonical_url_domain),
            verbose=2,
        )
    else:
        generate.assert_not_awaited()
