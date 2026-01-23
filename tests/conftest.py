"""Pytest fixtures and global logging mock."""

from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any, NamedTuple
from unittest.mock import MagicMock, Mock

from click.testing import CliRunner
import pytest

import docbuild.cli as cli_module
import docbuild.cli.cmd_cli as cli
from docbuild.cli.context import DocBuildContext
from docbuild.config import load as load_mod
from docbuild.constants import DEFAULT_ENV_CONFIG_FILENAME

# Import the module containing setup_logging for mocking
import docbuild.logging
from tests.common import changedir


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


@pytest.fixture(scope="function")
def default_env_config_filename(tmp_path: Path) -> Path:
    """Provide a default env config file path."""
    envfile = tmp_path / DEFAULT_ENV_CONFIG_FILENAME
    envfile.write_text("")
    return envfile


@pytest.fixture(scope="function")
def env_content(default_env_config_filename: Path) -> Path:
    """Provide a default content for the env config file."""
    content = """# Test file
[paths]
config_dir = "/etc/docbuild"
repo_dir = "/data/docserv/repos/permanent-full/"
temp_repo_dir = "/data/docserv/repos/temporary-branches/"

[paths.tmp]
tmp_base_dir = "/tmp"
tmp_path = "{tmp_base_dir}/doc-example-com"
"""
    default_env_config_filename.write_text(content)
    return default_env_config_filename


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


# --- Mocking fixtures


class MockEnvConfig(NamedTuple):
    """Named tuple to hold the fake env file and mock."""

    fakefile: Path
    mock: MagicMock


class MockCombinedConfig(NamedTuple):
    """Named tuple to hold the fake validate_options."""

    fakefile: Path
    mock: MagicMock
    mock_load_and_merge_configs: MagicMock
    mock_load_single_config: MagicMock


def make_path_mock(
    path: str = "",
    return_values: dict | None = None,
    side_effects: dict | None = None,
    attributes: dict | None = None,
) -> MagicMock:
    """Create a MagicMock object that mimics a pathlib.Path."""
    from pathlib import Path
    from unittest.mock import MagicMock

    path_obj = Path(path) if path else Path("mocked")
    mock = MagicMock(spec=Path)

    # Path-like behavior
    mock.__str__.return_value = str(path_obj)  # type: ignore
    mock.__fspath__.return_value = str(path_obj)
    mock.name = path_obj.name
    mock.suffix = path_obj.suffix
    mock.parts = path_obj.parts
    mock.parent = (
        make_path_mock(str(path_obj.parent)) if path_obj != path_obj.parent else mock
    )

    # / operator
    def truediv(other: str) -> MagicMock:
        return make_path_mock(
            str(path_obj / other), return_values, side_effects, attributes
        )

    mock.__truediv__.side_effect = truediv

    # Attributes (direct set)
    if attributes:
        for name, value in attributes.items():
            setattr(mock, name, value)

    # return_value setup (static)
    if return_values:
        for method, value in return_values.items():
            getattr(mock, method).return_value = value

    # side_effect setup (dynamic)
    if side_effects:
        for method, func in side_effects.items():
            getattr(mock, method).side_effect = func

    return mock


@pytest.fixture
def fake_confiles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Generator[MockEnvConfig, None, None]:
    """Patch the `docbuild.cli.cli.load_and_merge_configs` function."""
    with changedir(tmp_path):
        fakefile = Path("fake_config.toml")
        mock = MagicMock(
            return_value=(
                [fakefile],
                {
                    "fake_config_key": "fake_config_value",
                },
            ),
        )
        monkeypatch.setattr(
            load_mod,
            "load_and_merge_configs",
            mock,
        )
        yield MockEnvConfig(fakefile, mock)


@pytest.fixture
def fake_validate_options(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Generator[MockCombinedConfig, None, None]:
    """Patch the `docbuild.cli.validate_options` function."""
    with changedir(tmp_path):
        fakefile = Path("fake_validate_options.toml").absolute()

        mock = MagicMock()
        mock.return_value = None

        mock_load_and_merge_configs = MagicMock()
        mock_load_and_merge_configs.return_value = (
            [fakefile],
            {"fake_key": "fake_value"},
        )
        monkeypatch.setattr(
            cli_module,
            "load_and_merge_configs",
            mock_load_and_merge_configs,
        )

        mock_load_single_config = MagicMock()
        mock_load_single_config.return_value = {"fake_key": "fake_value"}
        monkeypatch.setattr(
            cli_module,
            "load_single_config",
            mock_load_single_config,
        )

        yield MockCombinedConfig(
            fakefile,
            mock,
            mock_load_and_merge_configs,
            mock_load_single_config,
        )


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
