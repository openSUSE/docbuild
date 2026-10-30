import logging
from unittest.mock import MagicMock, patch

from rich.text import Text

from docbuild.utils.display import LiveLogHandler, LiveProgressManager, get_live_manager


def test_live_manager_singleton_context() -> None:
    """Test that the context manager correctly sets and resets the singleton."""
    assert get_live_manager() is None

    with patch("docbuild.utils.display.Live.start") as mock_start, \
         patch("docbuild.utils.display.Live.stop") as mock_stop:

        with LiveProgressManager(title="Test").start() as manager:
            # Inside the context, the manager should be available globally
            assert get_live_manager() is manager
            mock_start.assert_called_once()

        # After exiting, it should be cleared and Live.stop called
        assert get_live_manager() is None
        mock_stop.assert_called_once()


def test_live_log_handler_buffers_messages() -> None:
    """Test that the log handler buffers messages and colors them by level."""
    mock_manager = MagicMock()
    handler = LiveLogHandler(display_manager=mock_manager, max_lines=2)

    # Create a dummy ERROR log record
    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname="fake.py",
        lineno=1,
        msg="This is an error",
        args=(),
        exc_info=None,
    )

    handler.emit(record)

    assert len(handler.log_buffer) == 1
    # Check that it triggered the UI update
    mock_manager.update_logs.assert_called_once()

    # Check that error logs are colored red
    buffered_text: Text = handler.log_buffer[0]
    assert "red" in buffered_text.style or buffered_text.style == "red"
