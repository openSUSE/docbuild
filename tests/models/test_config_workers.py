import os

import pytest

from docbuild.models.config.app import AppConfig


def test_max_workers_resolution_keywords():
    cpu = os.cpu_count() or 1

    # Test 'all'
    assert AppConfig(max_workers="all").max_workers == cpu

    # Test 'half' and 'all2'
    expected_half = max(1, cpu // 2)
    assert AppConfig(max_workers="half").max_workers == expected_half
    assert AppConfig(max_workers="all2").max_workers == expected_half

def test_max_workers_resolution_integers():
    # Test strict int
    assert AppConfig(max_workers=4).max_workers == 4
    # Test string digit
    assert AppConfig(max_workers="8").max_workers == 8

def test_max_workers_validation_errors():
    with pytest.raises(ValueError, match="at least 1"):
        AppConfig(max_workers=0)

    with pytest.raises(ValueError, match="Invalid max_workers"):
        AppConfig(max_workers="unlimited")
