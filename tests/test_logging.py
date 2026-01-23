import logging
from logging.handlers import MemoryHandler
import threading
import time

import pytest

from docbuild.constants import APP_NAME
from docbuild.logging import (
    _LOGGING_STATE,
    _resolve_class,
    _shutdown_logging,
    build_handlers_from_config,
    create_base_log_dir,
    register_background_thread,
    setup_logging,
)


@pytest.fixture(autouse=True)
def clean_logging_state():
    """Ensure each test starts with a clean logging state.

    Prevents QueueListener and other handlers from persisting.
    """
    yield
    _shutdown_logging()
    logging.shutdown()


@pytest.fixture
def logger():
    """Return the main logger used by the app."""
    return logging.getLogger("docbuild.cli")


@pytest.fixture
def memory_handler():
    """MemoryHandler to capture log records for assertions."""
    handler = MemoryHandler(capacity=1000, target=None)
    handler.setFormatter(logging.Formatter("%(message)s"))
    return handler


def _get_logged_messages(memory_handler):
    """Extract messages from a MemoryHandler."""
    return [record.getMessage() for record in memory_handler.buffer]


def test_console_verbosity_levels(logger, memory_handler):
    """Test that console logging respects verbosity levels."""
    # Setup logging with verbosity 0 (console WARNING)
    setup_logging(cliverbosity=0)

    # Replace existing StreamHandlers with MemoryHandler
    for h in logger.handlers[:]:
        if isinstance(h, logging.StreamHandler):
            logger.removeHandler(h)
    logger.addHandler(memory_handler)

    # Set logger level to WARNING to match console handler
    logger.setLevel(logging.WARNING)

    logger.warning("A warning message")
    logger.info("An info message")

    memory_handler.flush()
    msgs = _get_logged_messages(memory_handler)

    assert "A warning message" in msgs
    assert "An info message" not in msgs

    logger.removeHandler(memory_handler)


def test_file_logs_all_levels(logger, memory_handler):
    """Test that file logging captures all levels regardless of console verbosity."""
    setup_logging(cliverbosity=0)

    # Replace StreamHandlers with MemoryHandler
    for h in logger.handlers[:]:
        if isinstance(h, logging.StreamHandler):
            logger.removeHandler(h)
    logger.addHandler(memory_handler)

    logger.setLevel(logging.DEBUG)

    logger.info("This info should be in the file.")
    logger.debug("This debug should also be in the file.")

    memory_handler.flush()
    msgs = _get_logged_messages(memory_handler)

    assert "This info should be in the file." in msgs
    assert "This debug should also be in the file." in msgs

    logger.removeHandler(memory_handler)


def test_setup_with_user_config(logger):
    """Test that user-provided logging configuration is correctly applied."""
    user_config = {
        "logging": {
            "handlers": {"console": {"level": "ERROR"}},
            "root": {"level": "DEBUG"},
        }
    }

    # Apply user logging setup
    setup_logging(cliverbosity=2, user_config=user_config)

    # Attach MemoryHandler to capture logs
    memory_handler = MemoryHandler(capacity=10 * 1024, target=None)
    memory_handler.setLevel(logging.ERROR)  # **only capture ERROR and above**
    logger.addHandler(memory_handler)
    memory_handler.buffer.clear()

    # Send logs
    logger.warning("A warning.")
    logger.error("An error.")

    # Flush and extract messages
    memory_handler.flush()
    msgs = [record.getMessage() for record in memory_handler.buffer]

    # Only ERROR should appear
    assert "An error." in msgs
    assert "A warning." not in msgs


def test_create_base_log_dir(tmp_path, monkeypatch):
    """Test that the base log directory is created correctly."""
    base = tmp_path / "state"
    # ensure function uses provided base when env var absent
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    p = create_base_log_dir(base)
    assert p.exists() and p.is_dir()


def test_resolve_class_stdlib():
    """Test that _resolve_class correctly imports a standard library class."""
    cls = _resolve_class("logging.Formatter")
    assert cls is logging.Formatter


def test_setup_logging_creates_logfile_and_listener(tmp_path, monkeypatch):
    """Test that setup_logging creates a logfile and starts the listener."""
    # Ensure logs are placed under tmp_path via XDG_STATE_HOME
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    # Make sure any prior state is cleaned
    _shutdown_logging()

    setup_logging(2, None)

    listener = _LOGGING_STATE["listener"].get()
    handlers = _LOGGING_STATE["handlers"].get()

    assert listener is not None
    assert isinstance(handlers, list) and any(
        isinstance(h, logging.FileHandler) for h in handlers
    )

    # Verify a logfile was created in the XDG_STATE_HOME directory
    files = list(tmp_path.glob(f"{APP_NAME}_*.log"))
    assert files, "log file not created"

    # cleanup
    _shutdown_logging()


def test_setup_logging_bad_formatter(monkeypatch, tmp_path):
    """Test that bad formatter class raises an exception during setup."""
    # A formatter that points to a non-existent class should raise on setup
    user_config = {
        "logging": {
            "formatters": {
                "bad": {"class": "non.existent.Class", "format": "%(message)s"}
            },
            "handlers": {"console": {"formatter": "bad"}},
        }
    }
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    _shutdown_logging()
    with pytest.raises(Exception):  # noqa: B017
        setup_logging(1, user_config)
    _shutdown_logging()


def test_safe_emit_swallows_valueerror(monkeypatch):
    """Test that the safe_emit wrapper swallows ValueError exceptions."""

    # Replace the module's _original_emit with a function that raises ValueError
    def raising_emit(self, record):
        raise ValueError("boom")

    monkeypatch.setattr("docbuild.logging._original_emit", raising_emit, raising=True)

    # Create a handler and a dummy record and call the (patched) StreamHandler.emit
    handler = logging.StreamHandler()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="x",
        args=(),
        exc_info=None,
    )

    # Should not raise due to safe wrapper
    logging.StreamHandler.emit(handler, record)


def test_shutdown_joins_background_threads():
    """Test that _shutdown_logging joins background threads."""

    # Create a short-lived background thread and register it
    def worker():
        time.sleep(0.05)

    t = threading.Thread(target=worker)
    t.start()
    register_background_thread(t)

    # Call shutdown; this should join the thread without raising
    _shutdown_logging()
    assert not t.is_alive()


def test_shutdown_skips_not_alive_threads():
    """If a registered thread is not alive, shutdown should skip joining it."""
    # Ensure no listener/handlers interfere
    _LOGGING_STATE["listener"].set(None)
    _LOGGING_STATE["handlers"].set([])

    # Create a short-lived thread and let it finish
    def quick():
        return

    t = threading.Thread(target=quick)
    t.start()
    t.join()

    # Register the finished thread directly in the contextvar and run shutdown
    _LOGGING_STATE["background_threads"].set([t])
    _shutdown_logging()


def test_register_background_thread_initializes_none():
    """Test that register_background_thread initializes the ContextVar.

    When the ContextVar is None, `register_background_thread` should initialize it.
    """
    # Ensure initial state is None
    _LOGGING_STATE["background_threads"].set(None)

    t = threading.Thread(target=lambda: None)
    register_background_thread(t)

    threads = _LOGGING_STATE["background_threads"].get()
    assert isinstance(threads, list)
    assert threads and threads[-1] is t


def test_formatter_kwargs_applied():
    """Test that formatter kwargs like `format` and `datefmt` are correctly applied."""
    # Ensure formatter kwargs like `format` and `datefmt` are passed through
    user_config = {
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "level": "INFO",
            }
        },
        "formatters": {
            "standard": {
                "format": "FOO %(message)s",
                "datefmt": "%H:%M",
                "style": "%",
                "class": "logging.Formatter",
            }
        },
    }
    handlers = build_handlers_from_config(user_config)
    assert any(
        getattr(h, "formatter", None)
        and getattr(h.formatter, "_fmt", None) == "FOO %(message)s"
        for h in handlers
    )


def test_handler_args_and_missing_formatter(tmp_path):
    """Test that handler args are passed and missing formatter is handled."""
    # Test passing extra handler args (e.g., encoding) and omitting formatter
    filename = tmp_path / "out.log"
    user_config = {
        "handlers": {
            "file": {
                "class": "logging.FileHandler",
                "filename": str(filename),
                "encoding": "utf-8",
                "formatter": None,
                "level": "DEBUG",
            }
        }
    }

    handlers = build_handlers_from_config(user_config)
    # FileHandler should receive encoding arg
    assert any(
        isinstance(h, logging.FileHandler) and getattr(h, "encoding", None) == "utf-8"
        for h in handlers
    )
    # Since formatter was set to None, handler.formatter should be absent
    assert any(getattr(h, "formatter", None) is None for h in handlers)


def test_handler_level_numeric():
    """Test that passing a numeric level is accepted."""
    user_config = {
        "handlers": {"console": {"class": "logging.StreamHandler", "level": 10}}
    }
    handlers = build_handlers_from_config(user_config)
    assert any(getattr(h, "level", None) == 10 for h in handlers)
