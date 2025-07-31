"""Tests for the TimerFactory context manager."""
import time
from unittest.mock import MagicMock, patch

import pytest

from docbuild.utils.contextmgr import TimerData, make_timer


def test_timer_as_context_manager_measures_time():
    """Test the timer context manager for time measurement."""
    timer_name = 'test-timer'
    sleep_duration = 0.1
    timer = make_timer(timer_name)

    with timer() as timer_data:
        time.sleep(sleep_duration)

    elapsed = timer_data.elapsed
    assert isinstance(elapsed, float)
    assert elapsed == pytest.approx(sleep_duration, abs=0.05)


def test_timer_factory_creates_independent_timers():
    """Test that timers created by the factory are independent."""
    timer_name1 = 'test-timer-1'
    timer_name2 = 'test-timer-2'
    sleep_duration = 0.1

    timer1 = make_timer(timer_name1)
    timer2 = make_timer(timer_name2)

    with timer1() as timer_data1:
        time.sleep(sleep_duration)

    with timer2() as timer_data2:
        time.sleep(sleep_duration * 2)

    assert timer_data1.name == timer_name1
    assert timer_data2.name == timer_name2
    assert timer_data1.elapsed != timer_data2.elapsed
    assert isinstance(timer_data1.elapsed, float)
    assert isinstance(timer_data2.elapsed, float)
    assert timer_data1.elapsed == pytest.approx(sleep_duration, abs=0.1)


@patch('time.time')
def test_timer_factory_with_mock_time(mock_time: MagicMock):
    """Test the timer factory with a mocked time.time function."""
    mock_time.side_effect = [10.0, 10.5, 20.0, 20.2]

    timer1 = make_timer('mock-timer-1')
    with timer1() as timer_data1:
        pass
    assert timer_data1.elapsed == 0.5
    assert timer_data1.name == 'mock-timer-1'

    timer2 = make_timer('mock-timer-2')
    with timer2() as timer_data2:
        pass
    assert timer_data2.elapsed == 0.2
    assert timer_data2.name == 'mock-timer-2'
