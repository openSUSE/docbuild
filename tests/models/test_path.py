"""Tests for the custom Pydantic path model."""

import os
from pathlib import Path

from pydantic import BaseModel, ValidationError
import pytest

# Import the custom type under test
from docbuild.models.path import AbsolutePath, WritablePath

# --- Test Setup ---


# Define a simple Pydantic model to test the custom type integration
class PathTestModel(BaseModel):
    """Model using the custom path type for testing validation."""

    writable_dir: WritablePath


# Define a simple Pydantic model to test the custom absolute path type
class AbsolutePathTestModel(BaseModel):
    """Model using the absolute path type for testing validation."""

    absolute_path: AbsolutePath


# --- Test Cases ---


def test_writable_directory_creates_and_resolves(tmp_path: Path):
    """Test that a non-existent path is created and the field is a Path object."""
    new_dir = tmp_path / "new_dir"
    assert not new_dir.exists()

    model = PathTestModel(writable_dir=new_dir)  # type: ignore

    assert new_dir.exists()
    assert new_dir.is_dir()
    assert isinstance(model.writable_dir, Path)
    assert model.writable_dir == new_dir.resolve()


def test_writable_directory_path_expansion(monkeypatch, tmp_path: Path):
    """Test that the path correctly expands the user home directory (~)."""
    # 1. Setup Mock Home Directory
    fake_home = tmp_path / "fake_user_home"
    fake_home.mkdir()

    test_path_str = "~/test_output"

    # 2. Mock Path.expanduser() to return the resolved path
    expected_resolved_path = (fake_home / "test_output").resolve()
    monkeypatch.setenv("HOME", str(fake_home))

    # 3. Validation should resolve "~" before creation
    model = PathTestModel(writable_dir=test_path_str)  # type: ignore

    # 4. Assertions
    assert model.writable_dir == expected_resolved_path
    assert expected_resolved_path.is_dir()


def test_writable_directory_failure_not_a_directory(tmp_path: Path):
    """Test validation fails when the path exists but is a file."""
    existing_file = tmp_path / "a_file.txt"
    existing_file.write_text("content")

    with pytest.raises(ValidationError) as excinfo:
        PathTestModel(writable_dir=existing_file)  # type: ignore

    assert "Path exists but is not a directory" in excinfo.value.errors()[0]["msg"]


def test_writable_directory_failure_mkdir_os_error(monkeypatch, tmp_path: Path):
    """Test that an OSError during directory creation is handled."""

    # 1. Mock Path.mkdir to always raise an OSError when called
    def mock_mkdir(*args, **kwargs):
        raise OSError(13, "Simulated permission denied for mkdir")

    monkeypatch.setattr(Path, "mkdir", mock_mkdir)

    # Create a Path object that is guaranteed not to exist yet
    non_existent_path = tmp_path / "new_path" / "fail"

    # 2. Action & Assertions
    with pytest.raises(ValidationError) as excinfo:
        PathTestModel(writable_dir=non_existent_path)  # type: ignore

    # Assert that the error is correctly wrapped in a ValueError/ValidationError
    error_msg = excinfo.value.errors()[0]["msg"]
    assert "Failed to create directory" in error_msg
    assert "Simulated permission denied" in error_msg


def test_writable_directory_attributes_are_path_attributes(tmp_path: Path):
    """Test that the validated field is a Path and has its attributes."""
    test_dir = tmp_path / "test_attributes"
    test_dir.mkdir()

    model = PathTestModel(writable_dir=test_dir)  # type: ignore

    # Test that the field is a Path object
    assert isinstance(model.writable_dir, Path)

    # Test built-in Path attributes
    assert model.writable_dir.name == "test_attributes"
    assert model.writable_dir.is_absolute()

    # Test string representation
    assert str(model.writable_dir) == str(test_dir.resolve())


def test_writable_directory_creation_ignores_parent_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Let mkdir decide access instead of prechecking parent permissions."""
    parent_dir = tmp_path / "parent"
    parent_dir.mkdir()
    target_dir = parent_dir / "new_child_dir" / "nested"
    original_os_access = os.access

    def fake_access(path: Path, mode: int) -> bool:
        if path == parent_dir and mode == os.W_OK:
            return False
        return original_os_access(path, mode)

    monkeypatch.setattr(os, "access", fake_access)

    model = PathTestModel(writable_dir=target_dir)  # type: ignore

    assert target_dir.is_dir()
    assert model.writable_dir == target_dir.resolve()


@pytest.mark.parametrize(
    "permission_to_fail, expected_missing_perm",
    [
        (os.R_OK, "READ"),
        (os.W_OK, "WRITE"),
        (os.X_OK, "EXECUTE"),
    ],
    ids=["missing_read", "missing_write", "missing_execute"],
)
def test_writable_directory_permission_failures(
    tmp_path: Path, monkeypatch, permission_to_fail, expected_missing_perm
):
    """Test validation fails when a specific permission is missing."""
    test_dir = tmp_path / "permission_test_dir"
    test_dir.mkdir()

    original_os_access = os.access

    # Patch os.access() to fail only for the specified permission check
    def fake_access(path, mode):
        if Path(path).resolve() == test_dir.resolve() and mode == permission_to_fail:
            return False
        return original_os_access(path, mode)

    monkeypatch.setattr(os, "access", fake_access)

    with pytest.raises(ValidationError) as excinfo:
        PathTestModel(writable_dir=test_dir)  # type: ignore

    error_msg = excinfo.value.errors()[0]["msg"]
    assert "Insufficient permissions for directory" in error_msg
    assert f"Missing: {expected_missing_perm}" in error_msg


def test_absolute_path_accepts_absolute(tmp_path: Path):
    """Test that an absolute path derived from tmp_path is accepted on all platforms."""
    abs_dir = tmp_path / "remote"
    model = AbsolutePathTestModel(absolute_path=abs_dir)  # type: ignore
    assert model.absolute_path == abs_dir
    assert model.absolute_path.is_absolute()


def test_absolute_path_rejects_relative():
    """Test that a relative path is rejected."""
    with pytest.raises(ValidationError) as excinfo:
        AbsolutePathTestModel(absolute_path=Path("srv/docs"))  # type: ignore
    assert "must be an absolute path" in excinfo.value.errors()[0]["msg"]


def test_absolute_path_no_filesystem_access(tmp_path: Path):
    """Test that AbsolutePath neither creates nor checks the filesystem."""
    missing = tmp_path / "does" / "not" / "exist"
    assert not missing.exists()

    model = AbsolutePathTestModel(absolute_path=missing)  # type: ignore

    assert model.absolute_path == missing
    assert not missing.exists()
