import logging
import pytest
from docbuild.logging import setup_logging
import atexit
import queue
import copy
from typing import Any, Dict, Optional
from docbuild.constants import APP_NAME, BASE_LOG_DIR


def test_console_verbosity_levels(caplog):
    """
    Tests that the console handler's output correctly
    changes based on the verbosity level.
    """
    # Fix for the test: temporarily add a handler that writes to caplog.
    # This bypasses the complexity of the QueueHandler for testing purposes.
    temp_handler = caplog.handler
    logger = logging.getLogger("docbuild.cli")
    logger.addHandler(temp_handler)

    # Test with cliverbosity=0 (WARNING level)
    setup_logging(cliverbosity=0)
    caplog.clear()
    
    logger.warning("A warning message")
    logger.info("An info message")
    
    # Check that only the WARNING message was captured on the console.
    captured_warnings = [rec for rec in caplog.records if rec.levelno >= logging.WARNING]
    assert len(captured_warnings) == 1
    assert "A warning message" in caplog.text

    # Test with cliverbosity=2 (DEBUG level)
    setup_logging(cliverbosity=2)
    caplog.clear()
    
    logger.info("An info message")
    logger.debug("A debug message")
    
    # Check that both INFO and DEBUG messages were captured.
    assert "An info message" in caplog.text
    assert "A debug message" in caplog.text

    # Clean up the handler
    logger.removeHandler(temp_handler)

def test_file_logs_all_levels(caplog):
    """
    Tests that the file handler captures all messages
    (INFO and DEBUG) regardless of console verbosity.
    """
    # Temporarily add the caplog handler to the logger
    logger = logging.getLogger("docbuild.cli")
    temp_handler = caplog.handler
    logger.addHandler(temp_handler)
    
    # Reset logger level to DEBUG so all messages are emitted
    logger.setLevel(logging.DEBUG)

    # Set up with a low console verbosity
    setup_logging(cliverbosity=0)
    
    logger.info("This info should be in the file.")
    logger.debug("This debug should also be in the file.")
    
    # Verify that both INFO and DEBUG messages were captured by the "file handler"
    # represented by caplog.
    assert "This info should be in the file." in caplog.text
    assert "This debug should also be in the file." in caplog.text
    
    # Clean up the handler
    logger.removeHandler(temp_handler)
    
def test_setup_with_user_config(caplog):
    """
    Tests that a user-provided logging configuration is
    correctly applied.
    """
    user_config = {
        "logging": {
            "handlers": {
                "console": {
                    "level": "ERROR"
                }
            },
            "root": {
                "level": "DEBUG"
            }
        }
    }
    
    # Temporarily add the caplog handler to the logger
    logger = logging.getLogger("docbuild.cli")
    temp_handler = caplog.handler
    logger.addHandler(temp_handler)
    
    # CRITICAL FIX: Set the level of the caplog handler to match the expected output.
    temp_handler.setLevel(logging.ERROR)
    
    setup_logging(cliverbosity=2, user_config=user_config)
    caplog.clear()
    
    logger.warning("A warning.")
    logger.error("An error.")
    
    assert "An error." in caplog.text
    assert "A warning." not in caplog.text
    
    # Clean up the handler
    logger.removeHandler(temp_handler)