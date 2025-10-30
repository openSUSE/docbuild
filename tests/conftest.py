"""Pytest fixtures and thread-safe logging setup."""

from collections.abc import Generator
from pathlib import Path
from typing import Any, NamedTuple
from unittest.mock import MagicMock, Mock
from click.testing import CliRunner
import pytest
import logging
import logging.handlers
import queue
import os

import docbuild.cli as cli_module
import docbuild.cli.cmd_cli as cli
from docbuild.cli.context import DocBuildContext
from docbuild.config import load as load_mod
from docbuild.constants import DEFAULT_ENV_CONFIG_FILENAME
from tests.common import changedir

# ---------------------------
# Safe Logging for Pytest
# ---------------------------

class SafeStreamHandler(logging.StreamHandler):
    """Logging handler that ignores 'I/O operation on closed file' teardown errors."""
    def emit(self, record):
        try:
            super().emit(record)
        except ValueError as e:
            if "I/O operation on closed file" in str(e):
                # Ignore harmless pytest teardown error
                return
            raise


# Global queue and listener for thread-safe logging
_log_queue = queue.Queue(-1)
_log_listener = None


def pytest_configure(config):
    """Configure logging for all tests (thread-safe, teardown-safe)."""
    global _log_listener

    # File handler
    file_handler = logging.FileHandler("test.log", mode="w")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(threadName)s - %(message)s")
    )

    # Safe console handler (fixes teardown ValueError on macOS/Python 3.13)
    console_handler = SafeStreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(levelname)s - %(threadName)s - %(message)s")
    )

    # Queue listener
    _log_listener = logging.handlers.QueueListener(_log_queue, file_handler, console_handler)
    _log_listener.start()

    # Queue handler
    queue_handler = logging.handlers.QueueHandler(_log_queue)
    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(queue_handler)
    root_logger.setLevel(logging.DEBUG)

    # Suppress overly verbose third-party loggers
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # --- Apply Safe Handler for pidlock logger during pytest/CI ---
    if os.getenv("CI") or os.getenv("PYTEST_CURRENT_TEST"):
        pidlock_logger = logging.getLogger("docbuild.utils.pidlock")
        for h in list(pidlock_logger.handlers):
            pidlock_logger.removeHandler(h)
        safe_handler = SafeStreamHandler()
        safe_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        pidlock_logger.addHandler(safe_handler)
        pidlock_logger.propagate = False


def pytest_unconfigure(config):
    """Stop the logging queue listener safely at test teardown."""
    global _log_listener
    if _log_listener:
        try:
            _log_listener.stop()
        except Exception:
            # Prevent "I/O operation on closed file" during pytest shutdown
            pass


# ---------------------------
# Fixtures
# ---------------------------

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


# --- Mocking Fixtures ---

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
    return_values: dict = None,
    side_effects: dict = None,
    attributes: dict = None,
) -> MagicMock:
    """Helper to create a MagicMock that mimics pathlib.Path."""
    from pathlib import Path
    from unittest.mock import MagicMock

    path_obj = Path(path) if path else Path("mocked")
    mock = MagicMock(spec=Path)

    # Basic properties
    mock.__str__.return_value = str(path_obj)
    mock.__fspath__.return_value = str(path_obj)
    mock.name = path_obj.name
    mock.suffix = path_obj.suffix
    mock.parts = path_obj.parts
    mock.parent = (
        make_path_mock(str(path_obj.parent))
        if path_obj != path_obj.parent
        else mock
    )

    # Path join (/ operator)
    def truediv(other: str) -> MagicMock:
        return make_path_mock(
            str(path_obj / other), return_values, side_effects, attributes
        )

    mock.__truediv__.side_effect = truediv

    # Set attributes
    if attributes:
        for name, value in attributes.items():
            setattr(mock, name, value)

    # Set return values
    if return_values:
        for method, value in return_values.items():
            getattr(mock, method).return_value = value

    # Set side effects
    if side_effects:
        for method, func in side_effects.items():
            getattr(mock, method).side_effect = func

    return mock


@pytest.fixture
def fake_envfile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Generator[MockEnvConfig, None, None]:
    """Patch the `docbuild.cli.cli.process_envconfig` function."""
    mock_path = make_path_mock(
        "/home/tux",
        return_values={"exists": True, "is_file": True},
        side_effects={"read_text": lambda: "dynamic content"},
        attributes={"name": "file.txt"},
    )
    mock = MagicMock()
    mock.return_value = mock_path

    monkeypatch.setattr(load_mod, "process_envconfig", mock)

    with changedir(tmp_path):
        yield MockEnvConfig(mock_path, mock)


@pytest.fixture
def fake_confiles(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Generator[MockEnvConfig, None, None]:
    """Patch the `docbuild.cli.cli.load_and_merge_configs` function."""
    with changedir(tmp_path):
        fakefile = Path("fake_config.toml")
        mock = MagicMock(
            return_value=([fakefile], {"fake_config_key": "fake_config_value"})
        )
        monkeypatch.setattr(cli, "load_and_merge_configs", mock)
        yield MockEnvConfig(fakefile, mock)


@pytest.fixture
def fake_validate_options(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Generator[MockCombinedConfig, None, None]:
    """Patch the `docbuild.cli.validate_options` function."""
    with changedir(tmp_path):
        fakefile = Path("fake_validate_options.toml").absolute()

        mock = MagicMock()
        mock.return_value = None

        mock_load_and_merge_configs = MagicMock()
        mock_load_and_merge_configs.return_value = ([fakefile], {"fake_key": "fake_value"})
        monkeypatch.setattr(cli_module, "load_and_merge_configs", mock_load_and_merge_configs)

        mock_load_single_config = MagicMock()
        mock_load_single_config.return_value = {"fake_key": "fake_value"}
        monkeypatch.setattr(cli_module, "load_single_config", mock_load_single_config)

        yield MockCombinedConfig(
            fakefile,
            mock,
            mock_load_and_merge_configs,
            mock_load_single_config,
        )
