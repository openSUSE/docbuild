"""Pytest fixtures.

Naming conventions:
- `runner`: provides a `CliRunner` instance for testing CLI commands.
- `default_env_config_filename`: provides a default environment configuration file path.
- `env_content`: provides a default content for the environment configuration file.
- `ctx`: provides a simple dummy context object.
- `context`: provides a `DocBuildContext` instance.
- `fake_*`: Fixtures that patch specific functions or methods.
"""

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
from tests.common import changedir


@pytest.fixture(scope='function')
def runner() -> CliRunner:
    """Provide a CliRunner instance for testing."""
    return CliRunner()


@pytest.fixture(scope='function')
def default_env_config_filename(tmp_path: Path) -> Path:
    """Provide a default env config file path."""
    envfile = tmp_path / DEFAULT_ENV_CONFIG_FILENAME
    envfile.write_text('')
    return envfile


@pytest.fixture(scope='function')
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


def make_path_mock(**members: Any | Callable[[], Any]) -> MagicMock:
    """Create a MagicMock object that mimics a pathlib.Path.

      Use with preconfigured attributes and methods.

    - If the value is callable, it's used as the return_value of a method.
    - If the value is not callable, it's set as a plain attribute.

    Example:
        mock_path = make_path_mock(
            name="example.txt",
            suffix=".txt",
            exists=lambda: True,
            read_text=lambda: "file contents"
        )

    """
    mock = MagicMock(spec=Path)

    for name, value in members.items():
        if callable(value):
            # Assume it's meant to mock a method
            getattr(mock, name).return_value = value()
        else:
            # Mock an attribute
            setattr(mock, name, value)

    return mock


def make_path_mock(
    path: str = '',
    return_values: dict = None,
    side_effects: dict = None,
    attributes: dict = None,
) -> MagicMock:
    from pathlib import Path
    from unittest.mock import MagicMock

    path_obj = Path(path) if path else Path('mocked')
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
def fake_envfile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Generator[MockEnvConfig, None, None]:
    """Patch the `docbuild.cli.cli.process_envconfig` function."""
    mock_path = make_path_mock(
        '/home/tux',
        return_values={
            'exists': True,
            'is_file': True,
        },
        side_effects={
            'read_text': lambda: 'dynamic content',
        },
        attributes={
            'name': 'file.txt',
        },
    )

    # mock_path = MagicMock(spec=Path)
    # mock_path.name = 'fake_envfile'
    # mock_path.exists.return_value = True
    # mock_path.is_file.return_value = True
    # mock_path.suffix = '.txt'

    mock = MagicMock()
    mock.return_value = mock_path

    monkeypatch.setattr(
        load_mod,
        'process_envconfig',
        mock,
    )

    with changedir(tmp_path):
        yield MockEnvConfig(mock_path, mock)


@pytest.fixture
def fake_confiles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Generator[MockEnvConfig, None, None]:
    """Patch the `docbuild.cli.cli.load_and_merge_configs` function."""
    with changedir(tmp_path):
        fakefile = Path('fake_config.toml')
        mock = MagicMock(
            return_value=(
                [fakefile],
                {
                    # Example return value,
                    # can be customized with fake_confiles.mock.return_value
                    'fake_config_key': 'fake_config_value',
                },
            ),
        )
        monkeypatch.setattr(
            cli,
            'load_and_merge_configs',
            mock,
        )
        yield MockEnvConfig(fakefile, mock)


@pytest.fixture
def fake_validate_options(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Generator[MockCombinedConfig, None, None]:
    """Patch the `docbuild.cli.validate_options` function.

    Use a temporary directory to simulate the environment.
    """
    with changedir(tmp_path):
        fakefile = Path('fake_validate_options.toml').absolute()

        mock = MagicMock()
        # This function does not return anything
        mock.return_value = None
        # monkeypatch.setattr(
        #    cli_module, 'validate_options', mock,
        # )

        mock_load_and_merge_configs = MagicMock()
        mock_load_and_merge_configs.return_value = (
            [fakefile],
            {'fake_key': 'fake_value'},
        )
        monkeypatch.setattr(
            cli_module,
            'load_and_merge_configs',
            mock_load_and_merge_configs,
        )

        mock_load_single_config = MagicMock()
        mock_load_single_config.return_value = {'fake_key': 'fake_value'}
        monkeypatch.setattr(
            cli_module,
            'load_single_config',
            mock_load_single_config,
        )

        yield MockCombinedConfig(
            fakefile,
            mock,
            mock_load_and_merge_configs,
            mock_load_single_config,
        )
