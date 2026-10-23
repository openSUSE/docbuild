"""Tests for the cache management CLI commands."""

from pathlib import Path
from unittest.mock import MagicMock

from click.testing import CliRunner
import pytest

from docbuild.cli.cmd_cache import (
    cache,
    cache_dir,
    cache_list,
    cache_prune,
    expand_json_paths,
    expand_meta_paths,
    get_prune_confirmation_msg,
)
from docbuild.cli.context import DocBuildContext
from docbuild.constants import CACHE_FILE_EXT
from docbuild.models.doctype import Doctype


@pytest.fixture
def mock_context(tmp_path: Path) -> DocBuildContext:
    """Provide a mock DocBuildContext with safe temporary paths."""
    env = MagicMock()
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
    clean_output = result.output.replace("\n", "")
    assert "Base Cache Dir:" in clean_output

    assert mock_context.envconfig is not None
    assert str(mock_context.envconfig.paths.meta_cache_dir) in clean_output


def test_cache_list_empty(mock_context: DocBuildContext):
    """Test cache list when no files exist."""
    runner = CliRunner()
    result = runner.invoke(cache_list, obj=mock_context)

    assert result.exit_code == 0
    assert (
        "does not exist" in result.output
        or "No meta cache files found" in result.output
    )


def test_cache_list_with_files(mock_context: DocBuildContext):
    """Test cache list correctly finds and prints cache files."""
    assert mock_context.envconfig is not None
    meta_dir = mock_context.envconfig.paths.meta_cache_dir
    target_dir = meta_dir / "en-us" / "sles" / "15"
    target_dir.mkdir(parents=True)
    (target_dir / f"DC-test{CACHE_FILE_EXT}").touch()

    runner = CliRunner()
    result = runner.invoke(cache_list, obj=mock_context)

    assert result.exit_code == 0
    assert "Meta Cache:" in result.output
    # Expect flattened output
    assert f"en-us/sles/15/DC-test{CACHE_FILE_EXT}" in result.output


def test_cache_prune_all_yes(mock_context: DocBuildContext):
    """Test cache prune deletes all files when --yes is passed."""
    assert mock_context.envconfig is not None
    meta_dir = mock_context.envconfig.paths.meta_cache_dir
    target_dir = meta_dir / "sles" / "15" / "en-us"
    target_dir.mkdir(parents=True)
    fake_cache = target_dir / f"DC-test{CACHE_FILE_EXT}"
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
    fake_cache = target_dir / f"DC-test{CACHE_FILE_EXT}"
    fake_cache.touch()

    runner = CliRunner()
    result = runner.invoke(cache_prune, input="n\n", obj=mock_context)

    assert result.exit_code == 1
    assert fake_cache.exists()


def make_cache_files(context: DocBuildContext) -> tuple[Path, Path]:
    """Create one meta and one json cache file for sles/15-SP5/en-us."""
    assert context.envconfig is not None
    meta_file = (
        context.envconfig.paths.meta_cache_dir
        / "en-us"
        / "sles"
        / "15-SP5"
        / f"DC-test{CACHE_FILE_EXT}"
    )
    json_file = context.envconfig.paths.json_cache_dir / "sles" / "test.json"
    for path in (meta_file, json_file):
        path.parent.mkdir(parents=True)
        path.touch()
    return meta_file, json_file


def test_expand_meta_paths_with_doctypes(tmp_path: Path):
    """Test that doctypes expand into lang/product/docset meta paths."""
    doctypes = (Doctype.from_str("sles/15-SP5,16.0/en-us,de-de"),)
    paths = expand_meta_paths(tmp_path, doctypes)

    assert sorted(paths) == sorted(
        [
            tmp_path / "en-us" / "sles" / "15-SP5",
            tmp_path / "en-us" / "sles" / "16.0",
            tmp_path / "de-de" / "sles" / "15-SP5",
            tmp_path / "de-de" / "sles" / "16.0",
        ]
    )


def test_expand_json_paths_with_doctypes(tmp_path: Path):
    """Test that doctypes expand into product json paths."""
    doctypes = (Doctype.from_str("sles/15-SP5/en-us"),)

    assert expand_json_paths(tmp_path, doctypes) == [tmp_path / "sles"]


@pytest.mark.parametrize(
    ("cache_type", "doctypes", "expected"),
    [
        ("all", (), "ALL cache files"),
        ("all", ("x",), "cache files for 1 doctype(s)"),
        ("meta", (), "ALL meta cache files"),
        ("json", ("x", "y"), "json cache files for 2 doctype(s)"),
    ],
)
def test_get_prune_confirmation_msg(cache_type: str, doctypes: tuple, expected: str):
    """Test the prune confirmation message for each type/doctype combination."""
    msg = get_prune_confirmation_msg(cache_type, doctypes)

    assert msg == f"Are you sure you want to delete {expected}?"


def test_cache_group_invokes_subcommand(mock_context: DocBuildContext):
    """Test that the cache group dispatches to its subcommands."""
    result = CliRunner().invoke(cache, ["dir"], obj=mock_context)

    assert result.exit_code == 0
    assert "Base Cache Dir:" in result.output


def test_cache_list_json_only(mock_context: DocBuildContext):
    """Test that --type json lists only json cache files."""
    make_cache_files(mock_context)

    result = CliRunner().invoke(cache_list, ["--type", "json"], obj=mock_context)

    assert result.exit_code == 0
    assert "JSON Cache:" in result.output
    assert "sles/test.json" in result.output
    assert "Meta Cache" not in result.output


def test_cache_list_meta_only_with_doctype(mock_context: DocBuildContext):
    """Test that --type meta with a doctype lists only matching meta files."""
    make_cache_files(mock_context)
    assert mock_context.envconfig is not None

    unrelated = (
        mock_context.envconfig.paths.meta_cache_dir
        / "de-de"
        / "sles"
        / "15-SP5"
        / f"DC-other{CACHE_FILE_EXT}"
    )
    unrelated.parent.mkdir(parents=True)
    unrelated.touch()

    result = CliRunner().invoke(
        cache_list, ["--type", "meta", "sles/15-SP5/en-us"], obj=mock_context
    )

    assert result.exit_code == 0
    assert f"en-us/sles/15-SP5/DC-test{CACHE_FILE_EXT}" in result.output
    assert f"de-de/sles/15-SP5/DC-other{CACHE_FILE_EXT}" not in result.output
    assert "JSON Cache" not in result.output


def test_cache_list_doctype_without_files(mock_context: DocBuildContext):
    """Test listing a doctype whose cache directories do not exist."""
    assert mock_context.envconfig is not None
    mock_context.envconfig.paths.meta_cache_dir.mkdir()
    mock_context.envconfig.paths.json_cache_dir.mkdir()

    result = CliRunner().invoke(cache_list, ["sles/15-SP5/en-us"], obj=mock_context)

    assert result.exit_code == 0
    assert "No meta cache files found." in result.output
    assert "No json cache files found." in result.output


def test_cache_prune_nothing_to_prune(mock_context: DocBuildContext):
    """Test that prune reports when there are no cache files."""
    result = CliRunner().invoke(cache_prune, ["--yes"], obj=mock_context)

    assert result.exit_code == 0
    assert "No cache files found to prune." in result.output


def test_cache_prune_json_only(mock_context: DocBuildContext):
    """Test that --type json deletes json files and keeps meta files."""
    meta_file, json_file = make_cache_files(mock_context)

    result = CliRunner().invoke(
        cache_prune, ["--type", "json", "--yes"], obj=mock_context
    )

    assert result.exit_code == 0
    assert "Successfully pruned 1 cache file" in result.output
    assert meta_file.exists()
    assert not json_file.exists()


def test_cache_prune_all_with_doctype_confirmed(mock_context: DocBuildContext):
    """Test that a confirmed prune for a doctype deletes meta and json files."""
    meta_file, json_file = make_cache_files(mock_context)
    assert mock_context.envconfig is not None

    unrelated_meta = (
        mock_context.envconfig.paths.meta_cache_dir
        / "de-de"
        / "sles"
        / "15-SP5"
        / f"DC-other{CACHE_FILE_EXT}"
    )
    unrelated_json = (
        mock_context.envconfig.paths.json_cache_dir / "opensuse" / "other.json"
    )
    for path in (unrelated_meta, unrelated_json):
        path.parent.mkdir(parents=True)
        path.touch()

    result = CliRunner().invoke(
        cache_prune, ["sles/15-SP5/en-us"], input="y\n", obj=mock_context
    )

    assert result.exit_code == 0
    assert "cache files for 1 doctype(s)" in result.output
    assert "Successfully pruned 2 cache file" in result.output
    assert not meta_file.exists()
    assert not json_file.exists()
    assert unrelated_meta.exists()
    assert unrelated_json.exists()
