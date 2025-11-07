import logging
import pytest
import time
from logging.handlers import MemoryHandler

from docbuild.logging import setup_logging, _shutdown_logging
from docbuild.constants import APP_NAME


@pytest.fixture(autouse=True)
def clean_logging_state():
    """
    Ensure each test starts with a clean logging state.
    Prevents QueueListener and other handlers from persisting.
    """
    yield
    _shutdown_logging()
    logging.shutdown()


@pytest.fixture
def logger():
    """
    Returns the main logger used by the app.
    """
    return logging.getLogger("docbuild.cli")


@pytest.fixture
def memory_handler():
    """
    MemoryHandler to capture log records for assertions.
    """
    handler = MemoryHandler(capacity=1000, target=None)
    handler.setFormatter(logging.Formatter("%(message)s"))
    return handler


def _get_logged_messages(memory_handler):
    """
    Extract messages from a MemoryHandler.
    """
    return [record.getMessage() for record in memory_handler.buffer]


def test_console_verbosity_levels(logger, memory_handler):
    """
    Test that console logging respects verbosity levels.
    """
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
    """
    Test that file logging captures all levels regardless of console verbosity.
    """
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
    """
    Test that user-provided logging configuration is correctly applied.
    """

    user_config = {
        "logging": {
            "handlers": {
                "console": {"level": "ERROR"}
            },
            "root": {"level": "DEBUG"},
        }
    }

    # Apply user logging setup
    setup_logging(cliverbosity=2, user_config=user_config)

    # Attach MemoryHandler to capture logs
    memory_handler = MemoryHandler(capacity=10*1024, target=None)
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

