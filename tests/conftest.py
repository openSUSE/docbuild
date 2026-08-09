"""Pytest fixtures and global logging mock."""

from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock

from click.testing import CliRunner
import pytest

import docbuild.cli.cmd_cli as cli
from docbuild.cli.context import DocBuildContext

# Import the module containing setup_logging for mocking
import docbuild.logging


# Adding info to test report header
# https://docs.pytest.org/en/stable/example/simple.html#adding-info-to-test-report-header
def pytest_report_header(config: pytest.Config) -> str:
    """Add DocBuild version to the pytest report header."""
    from docbuild.__about__ import __version__

    return f"DocBuild Version: {__version__}"


# --- Global Fixture to Mute Logging Setup (Debugging Step) ---
@pytest.fixture(autouse=True, scope="function")
def mock_setup_logging_globally(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock out the setup_logging call.

    To prevent any initialization side-effects in tests.
    """
    mock_func = MagicMock()
    # This prevents docbuild.logging.setup_logging from ever running during tests.
    monkeypatch.setattr(docbuild.logging, "setup_logging", mock_func)
    return mock_func


# --- Original Fixtures ---


@pytest.fixture(scope="function")
def runner() -> CliRunner:
    """Provide a CliRunner instance for testing."""
    return CliRunner()


@pytest.fixture
def mock_context() -> DocBuildContext:
    """Mock DocBuildContext."""
    context = Mock(spec=DocBuildContext)
    context.verbose = 2
    return context


class DummyCtx:
    """A dummy context class."""

    def __init__(self, obj: Any = None) -> None:  # noqa: ANN401
        self.obj = obj
        self.dry_run = None
        self.verbose = None
        self.envconfigfiles = None
        self.role = None


@pytest.fixture
def ctx() -> type[DummyCtx]:
    """Provide a dummy context object for testing."""
    return DummyCtx


@pytest.fixture
def context() -> DocBuildContext:
    """Provide a DocBuildContext instance for testing."""
    return DocBuildContext()


@pytest.fixture
def app_config_file(tmp_path: Path) -> Path:
    """Create a simple `app.toml` file and return its path."""
    app = tmp_path / "app.toml"
    app.write_text("[logging]\nversion=1\n")
    return app


@pytest.fixture
def env_config_file(tmp_path: Path) -> Path:
    """Create a simple `env.toml` file and return its path."""
    env = tmp_path / "env.toml"
    env.write_text("[paths]\nrepo_dir = '/tmp/repos'\nconfig_dir = '/etc/docbuild'\n")
    return env


@pytest.fixture
def fake_handle_config(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[Callable[[Any], tuple]], None]:
    """Return a helper that installs a resolver as the `handle_config` implementation.

    The resolver should be a callable accepting `user_path` and returning
    `(files_tuple, raw_dict, from_defaults_bool)`.
    Example usage in a test:

        fake_handle_config(lambda p: ((p,), {'logging': {...}}, False))
    """

    def install(resolver: Callable[[Any], tuple]) -> None:
        monkeypatch.setattr(
            cli, "handle_config", lambda user_path, *a, **kw: resolver(user_path)
        )

    return install
