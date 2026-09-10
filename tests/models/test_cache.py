"""Tests for the metadata caching logic."""

from pathlib import Path

from docbuild.models.cache import Cache


def test_cache_serialization_roundtrip(tmp_path: Path):
    """Test saving and loading a cache from JSON."""
    cache_file = tmp_path / "test.cache.json"

    original = Cache(
        env_config_hash="env123",
        file_hashes={"file_a.xml": "hash_a", "file_b.xml": "hash_b"}
    )

    original.to_json(cache_file)
    assert cache_file.exists()

    loaded = Cache.from_json(cache_file)
    assert loaded.env_config_hash == "env123"
    assert loaded.file_hashes == {"file_a.xml": "hash_a", "file_b.xml": "hash_b"}
    assert loaded.combined_hash == original.combined_hash


def test_cache_from_json_missing_file(tmp_path: Path):
    """Test loading a cache that doesn't exist returns an empty, safe Cache."""
    cache_file = tmp_path / "does_not_exist.json"
    loaded = Cache.from_json(cache_file)

    assert loaded.env_config_hash == ""
    assert loaded.file_hashes == {}
    assert len(loaded.files()) == 0


def test_cache_combined_hash_order_independence():
    """Test that the combined hash is identical regardless of dict insertion order."""
    cache1 = Cache(
        env_config_hash="env123",
        file_hashes={"file_a.xml": "hash_a", "file_b.xml": "hash_b"}
    )

    cache2 = Cache(
        env_config_hash="env123",
        # Inserted in reverse order
        file_hashes={"file_b.xml": "hash_b", "file_a.xml": "hash_a"}
    )

    assert cache1.combined_hash == cache2.combined_hash


def test_cache_combined_hash_detects_changes():
    """Test that changing env config or a single file alters the combined hash."""
    base_cache = Cache("env123", {"file_a.xml": "hash_a"})

    # Change env
    env_changed = Cache("env456", {"file_a.xml": "hash_a"})
    assert base_cache.combined_hash != env_changed.combined_hash

    # Change file hash
    file_changed = Cache("env123", {"file_a.xml": "hash_B_NEW"})
    assert base_cache.combined_hash != file_changed.combined_hash


def test_cache_diff():
    """Test that the diff method accurately finds modified, added, and removed files."""
    old_cache = Cache(
        env_config_hash="env123",
        file_hashes={
            "unchanged.xml": "hash1",
            "modified.xml": "hash2_old",
            "removed.xml": "hash3"
        }
    )

    new_cache = Cache(
        env_config_hash="env123",
        file_hashes={
            "unchanged.xml": "hash1",
            "modified.xml": "hash2_new",  # Hash changed
            "added.xml": "hash4"          # New file
        }
    )

    diff_set = new_cache.diff(old_cache)

    # 'unchanged.xml' should NOT be in the diff
    assert "unchanged.xml" not in diff_set

    # The diff should contain the modified, added, and removed files
    assert diff_set == {"modified.xml", "added.xml", "removed.xml"}
