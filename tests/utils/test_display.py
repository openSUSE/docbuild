from unittest.mock import patch

from docbuild.utils.display import LiveProgressManager, get_live_manager


def test_live_manager_singleton_context() -> None:
    """Test that the context manager correctly sets and resets the singleton."""
    assert get_live_manager() is None

    with patch("docbuild.utils.display.Live.start") as mock_start, \
         patch("docbuild.utils.display.Live.stop") as mock_stop:

        with LiveProgressManager() as manager:
            # Inside the context, the manager should be available globally
            assert get_live_manager() is manager
            mock_start.assert_called_once()

        # After exiting, it should be cleared and Live.stop called
        assert get_live_manager() is None
        mock_stop.assert_called_once()


def test_item_state_enums():
    """Test the ItemState enum has the correct values."""
    from docbuild.utils.display import ItemState
    assert "✔" in ItemState.SUCCEEDED
    assert "↷" in ItemState.SKIPPED
    assert "✘" in ItemState.FAILED

def test_live_manager_stage_and_item():
    """Test creating a stage and completing an item."""
    from docbuild.utils.display import ItemState, LiveProgressManager

    with LiveProgressManager(disable=True) as manager:
        with manager.stage("Metadata", total=2) as stage:
            # 1. Test success path
            with stage.item("doc-01") as item:
                pass
            assert item.state == ItemState.SUCCEEDED

            # 2. Test fail path
            with stage.item("doc-02") as item:
                item.fail()
            assert item.state == ItemState.FAILED

            # 3. Test exception path
            try:
                with stage.item("doc-03") as item:
                    raise ValueError("Simulated crash")
            except ValueError:
                pass
            assert item.state == ItemState.FAILED

            assert stage.failed is True

        assert manager.failed is True

def test_format_status():
    """Test the fixed-width status string formatter."""
    from collections import Counter

    from docbuild.utils.display import ItemState, format_status
    counts = Counter({ItemState.SUCCEEDED: 5, ItemState.FAILED: 1})
    status = format_status(counts)
    assert str(ItemState.SUCCEEDED) in status
    assert "  5" in status
    assert str(ItemState.FAILED) in status
    assert "  1" in status
