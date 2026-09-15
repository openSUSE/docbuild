"""Tests for the cache management CLI commands."""

from pathlib import Path
from unittest.mock import MagicMock

from click.testing import CliRunner
import pytest

from docbuild.cli.cmd_cache import cache_dir, cache_list, cache_prune
from docbuild.cli.context import DocBuildContext


@pytest.fixture
def mock_context(tmp_path: Path) -> DocBuildContext:
    """Provide a mock DocBuildContext with safe temporary paths."""
    env = MagicMock()
    # Set up fake cache directories
    env.paths.base_cache_dir = tmp_path / "base"
    env.paths.meta_cache_dir = tmp_path / "meta"
    env.paths.json_cache_dir = tmp_path / "json"

    context = DocBuildContext()
    context.envconfig = env
    return context


def test_cache_dir(mock_context: DocBuildContext):
    """Test the cache dir command prints the correct paths."""
    runner = CliRunner()
    result = runner.invoke(cache_dir, obj=mock_context)

    assert result.exit_code == 0

    # Rich line-wraps very long macOS temp paths.
    # Strip newlines so our substring match works safely.
    clean_output = result.output.replace("\n", "")

    assert "Base Cache Dir:" in clean_output

    # Satisfy Pylance strict typing
    assert mock_context.envconfig is not None
    assert str(mock_context.envconfig.paths.meta_cache_dir) in clean_output


def test_cache_list_empty(mock_context: DocBuildContext):
    """Test cache list when no files exist."""
    runner = CliRunner()
    result = runner.invoke(cache_list, obj=mock_context)

    assert result.exit_code == 0
    assert "Cache directory does not exist" in result.output or "No cache files found" in result.output


def test_cache_list_with_files(mock_context: DocBuildContext):
    """Test cache list correctly finds and prints cache files."""
    assert mock_context.envconfig is not None
    meta_dir = mock_context.envconfig.paths.meta_cache_dir
    target_dir = meta_dir / "sles" / "15" / "en-us"
    target_dir.mkdir(parents=True)
    (target_dir / "DC-test.cache").touch()

    runner = CliRunner()
    result = runner.invoke(cache_list, obj=mock_context)

    assert result.exit_code == 0
    assert "Meta Cache" in result.output
    assert "DC-test.cache" in result.output


def test_cache_prune_all_yes(mock_context: DocBuildContext):
    """Test cache prune deletes all files when --yes is passed."""
    assert mock_context.envconfig is not None
    meta_dir = mock_context.envconfig.paths.meta_cache_dir
    target_dir = meta_dir / "sles" / "15" / "en-us"
    target_dir.mkdir(parents=True)
    fake_cache = target_dir / "DC-test.cache"
    fake_cache.touch()

    assert fake_cache.exists()

    runner = CliRunner()
    result = runner.invoke(cache_prune, ["--yes"], obj=mock_context)

    assert result.exit_code == 0
    assert "Successfully pruned 1 cache file" in result.output
    assert not fake_cache.exists()


def test_cache_prune_aborted(mock_context: DocBuildContext):
    """Test cache prune respects user abortion when prompted."""
    assert mock_context.envconfig is not None
    meta_dir = mock_context.envconfig.paths.meta_cache_dir
    target_dir = meta_dir / "sles" / "15" / "en-us"
    target_dir.mkdir(parents=True)
    fake_cache = target_dir / "DC-test.cache"
    fake_cache.touch()

    runner = CliRunner()
    # Pass "n" to simulate user saying no to the confirmation prompt
    result = runner.invoke(cache_prune, input="n\n", obj=mock_context)

    # Click confirmation aborts with exit code 1
    assert result.exit_code == 1
    assert fake_cache.exists()
