"""Pass ENV exclusions into the build pipeline."""

from unittest.mock import AsyncMock, patch

from click.testing import CliRunner
import pytest

import docbuild.cli.cmd_build.cmd_run as cmd_build
from docbuild.cli.context import DocBuildContext
from docbuild.constants import DEFAULT_RSYNC_EXCLUDES
from docbuild.models.config.env import EnvConfig
from docbuild.utils import sysdeps


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        ({}, list(DEFAULT_RSYNC_EXCLUDES)),
        ({"exclude_extra": ["*.tmp"]}, [*DEFAULT_RSYNC_EXCLUDES, "*.tmp"]),
        ({"exclude": ["drafts/"]}, ["drafts/"]),
        ({"exclude": []}, []),
    ],
)
def test_build_uses_env_exclusions(settings, expected):
    """The CLI must forward defaults, extensions, and explicit replacements."""
    context = DocBuildContext(envconfig=EnvConfig.from_dict({"rsync": settings}))
    with (
        patch.object(sysdeps, "check_dependencies", return_value=[]),
        patch.object(cmd_build, "build_process", new_callable=AsyncMock) as build_process,
    ):
        build_process.return_value = 0
        result = CliRunner().invoke(cmd_build.run, ["--skip-metadata"], obj=context)

    assert result.exit_code == 0, result.output
    build_process.assert_awaited_once()
    assert build_process.call_args.kwargs["rsync_options"].exclude == expected
