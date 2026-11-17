"""Unit tests for monotonic build run ID generation."""

from pathlib import Path

from docbuild.utils.run_id import get_next_run_id


def test_get_next_run_id_initial(tmp_path: Path) -> None:
    """Verify first allocation starts at 1 and creates directory."""
    run_id, run_dir = get_next_run_id(tmp_path, "production")
    assert run_id == 1
    assert run_dir == tmp_path / "production" / "1"
    assert run_dir.is_dir()

    counter_file = tmp_path / "production" / ".last_run_id"
    assert counter_file.is_file()
    assert counter_file.read_text(encoding="utf-8").strip() == "1"


def test_get_next_run_id_sequential(tmp_path: Path) -> None:
    """Verify sequential calls produce strictly monotonic IDs."""
    id1, dir1 = get_next_run_id(tmp_path, "staging")
    id2, dir2 = get_next_run_id(tmp_path, "staging")
    id3, dir3 = get_next_run_id(tmp_path, "staging")

    assert id1 == 1
    assert id2 == 2
    assert id3 == 3
    assert dir1.is_dir()
    assert dir2.is_dir()
    assert dir3.is_dir()


def test_get_next_run_id_role_isolation(tmp_path: Path) -> None:
    """Verify different environment roles maintain separate counters."""
    prod_id, prod_dir = get_next_run_id(tmp_path, "production")
    dev_id, dev_dir = get_next_run_id(tmp_path, "development")

    assert prod_id == 1
    assert dev_id == 1
    assert prod_dir == tmp_path / "production" / "1"
    assert dev_dir == tmp_path / "development" / "1"


def test_get_next_run_id_recovers_without_counter_file(tmp_path: Path) -> None:
    """Verify recovery when .last_run_id is deleted but directories exist."""
    role_dir = tmp_path / "production"
    (role_dir / "1").mkdir(parents=True)
    (role_dir / "2").mkdir(parents=True)
    (role_dir / "7").mkdir(parents=True)

    next_id, next_dir = get_next_run_id(tmp_path, "production")
    assert next_id == 8
    assert next_dir == role_dir / "8"
    assert next_dir.is_dir()


def test_get_next_run_id_skips_existing_directory(tmp_path: Path) -> None:
    """Verify candidate is incremented if directory already exists."""
    role_dir = tmp_path / "production"
    role_dir.mkdir(parents=True)
    (role_dir / ".last_run_id").write_text("2", encoding="utf-8")
    (role_dir / "3").mkdir(parents=True)

    next_id, next_dir = get_next_run_id(tmp_path, "production")
    assert next_id == 4
    assert next_dir == role_dir / "4"
    assert next_dir.is_dir()
