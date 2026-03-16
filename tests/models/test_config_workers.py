from unittest.mock import patch

import pytest

from docbuild.models.config import app
from docbuild.models.config.app import AppConfig


# os.cpu_count() returns None if the count is indeterminate.
@pytest.fixture(params=[1, 2, 8, None])
def mock_cpu_count(request):
    """Mock os.cpu_count in app module to ensure deterministic tests."""
    cpu_count = request.param
    with patch.object(app, "os") as mock_os:
        mock_os.cpu_count.return_value = cpu_count
        yield cpu_count

# Separate test cases for better clarity
def test_max_workers_resolution_all(mock_cpu_count):
    """Verify 'all' keyword resolves to the full CPU count (min 1)."""
    expected = mock_cpu_count or 1
    conf = AppConfig(max_workers="all")
    assert conf.max_workers == expected

def test_max_workers_resolution_half(mock_cpu_count):
    """Verify 'half' and 'all2' resolve to 50% CPU count (min 1)."""
    cpu = mock_cpu_count or 1
    expected_half = max(1, cpu // 2)

    assert AppConfig(max_workers="half").max_workers == expected_half
    assert AppConfig(max_workers="all2").max_workers == expected_half

def test_max_workers_resolution_explicit_values():
    """Verify that specific integers/strings override CPU-based logic.
    We don't need the fixture here because these values are
    independent of the host hardware.
    """
    assert AppConfig(max_workers=4).max_workers == 4
    assert AppConfig(max_workers="8").max_workers == 8

def test_max_workers_validation_errors():
    """Verify error handling for invalid inputs."""
    with pytest.raises(ValueError, match="at least 1"):
        AppConfig(max_workers=0)

    with pytest.raises(ValueError, match="Invalid max_workers"):
        AppConfig(max_workers="infinite")
