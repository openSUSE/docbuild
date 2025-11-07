import logging
import pytest
from docbuild.logging import setup_logging, _shutdown_logging
from docbuild.constants import APP_NAME


@pytest.fixture(autouse=True)
def clean_logging_state():
    """
    Automatically ensure each test starts with a clean logging state.
    Prevents QueueListener from previous tests from persisting.
    """
    yield
    # Stop listener and close handlers after each test
    _shutdown_logging()
    logging.shutdown()


def test_console_verbosity_levels(caplog):
    """
    Tests that the console handler's output correctly
    changes based on the verbosity level.
    """
    logger = logging.getLogger("docbuild.cli")
    temp_handler = caplog.handler
    logger.addHandler(temp_handler)

    # Test with cliverbosity=0 (WARNING level)
    setup_logging(cliverbosity=0)
    caplog.clear()

    logger.warning("A warning message")
    logger.info("An info message")

    captured_warnings = [rec for rec in caplog.records if rec.levelno >= logging.WARNING]
    assert len(captured_warnings) == 1
    assert "A warning message" in caplog.text

    # Test with cliverbosity=2 (DEBUG level)
    setup_logging(cliverbosity=2)
    caplog.clear()

    logger.info("An info message")
    logger.debug("A debug message")

    assert "An info message" in caplog.text
    assert "A debug message" in caplog.text

    logger.removeHandler(temp_handler)


def test_file_logs_all_levels(caplog):
    """
    Tests that the file handler captures all messages
    (INFO and DEBUG) regardless of console verbosity.
    """
    logger = logging.getLogger("docbuild.cli")
    temp_handler = caplog.handler
    logger.addHandler(temp_handler)

    logger.setLevel(logging.DEBUG)
    setup_logging(cliverbosity=0)

    logger.info("This info should be in the file.")
    logger.debug("This debug should also be in the file.")

    assert "This info should be in the file." in caplog.text
    assert "This debug should also be in the file." in caplog.text

    logger.removeHandler(temp_handler)


def test_setup_with_user_config(caplog):
    """
    Tests that a user-provided logging configuration is
    correctly applied.
    """
    user_config = {
        "logging": {
            "handlers": {
                "console": {"level": "ERROR"}
            },
            "root": {"level": "DEBUG"},
        }
    }

    logger = logging.getLogger("docbuild.cli")
    temp_handler = caplog.handler
    logger.addHandler(temp_handler)
    temp_handler.setLevel(logging.ERROR)

    setup_logging(cliverbosity=2, user_config=user_config)
    caplog.clear()

    logger.warning("A warning.")
    logger.error("An error.")

    assert "An error." in caplog.text
    assert "A warning." not in caplog.text

    logger.removeHandler(temp_handler)
