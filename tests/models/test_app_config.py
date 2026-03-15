import os

import pytest

from docbuild.models.config.app import AppConfig


def test_max_workers_resolution():
    cpu = os.cpu_count() or 1

    # Test keyword "all"
    conf_all = AppConfig(max_workers="all")
    assert conf_all.max_workers == cpu

    # Test keyword "half"
    conf_half = AppConfig(max_workers="half")
    assert conf_half.max_workers == max(1, cpu // 2)

    # Test integer
    conf_int = AppConfig(max_workers=4)
    assert conf_int.max_workers == 4

def test_max_workers_invalid():
    with pytest.raises(ValueError, match="at least 1"):
        AppConfig(max_workers=0)

    with pytest.raises(ValueError, match="Invalid max_workers"):
        AppConfig(max_workers="infinite")
