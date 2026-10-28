"""Pytest fixtures and global logging mock."""

from collections.abc import Callable
from pathlib import Path
import tempfile
from typing import Any
from unittest.mock import MagicMock, Mock

from click.testing import CliRunner
import pytest

import docbuild.cli.cmd_cli as cli
import docbuild.cli.completion as completion
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


# --- Global Fixture to Isolate Configuration Discovery ---
@pytest.fixture(autouse=True, scope="function")
def isolate_test_config_discovery(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Path:
    """Redirect configuration discovery to an empty temporary directory.

    Without this, tests consult the real user/system/project configuration
    (``docbuild.constants.CONFIG_PATHS`` is captured at import time), so a
    malformed user ``env.*.toml`` can fail unrelated CLI tests. Both modules
    that import ``CONFIG_PATHS`` directly are patched, since patching only
    ``docbuild.constants`` would leave their existing references unchanged.
    The ``docbuild.constants`` module itself is intentionally left alone:
    ``test_constants.py`` checks its production structure.

    Tests that need configuration can request this fixture and write
    controlled files into the returned directory, or patch discovery paths
    themselves as before.
    """
    # A unique directory (not a fixed name like ``config``) so tests that
    # create their own ``tmp_path / "config"`` do not collide with this one.
    config_dir = Path(tempfile.mkdtemp(prefix="isolated-config-", dir=tmp_path))
    monkeypatch.setattr(cli, "CONFIG_PATHS", (config_dir,))
    monkeypatch.setattr(completion, "CONFIG_PATHS", (config_dir,))
    return config_dir


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


@pytest.fixture(scope="session")
def example_env_toml() -> Path:
    """Return the path to the shipped example environment configuration."""
    return Path(__file__).resolve().parents[1] / "etc/docbuild/env.example.toml"


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
