"""Tests for the custom Pydantic path model."""

import os
import stat
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from pydantic import BaseModel, ValidationError

# Import the custom type under test
from docbuild.models.path import EnsureWritableDirectory 


# --- Test Setup ---

# Define a simple Pydantic model to test the custom type integration
class PathTestModel(BaseModel):
    """Model using the custom path type for testing validation."""
    writable_dir: EnsureWritableDirectory
    
    
# --- Test Cases ---

def test_writable_directory_success_exists(tmp_path: Path):
    """Test successful validation when the directory already exists and is writable."""
    existing_dir = tmp_path / 'existing_test_dir'
    existing_dir.mkdir()
    
    # Validation should succeed and return the custom type instance
    model = PathTestModel(writable_dir=existing_dir) # type: ignore
    
    assert isinstance(model.writable_dir, EnsureWritableDirectory)
    assert model.writable_dir._path == existing_dir.resolve()
    assert model.writable_dir.is_dir() # Test __getattr__ functionality


def test_writable_directory_success_create_new(tmp_path: Path):
    """Test successful validation when the directory must be created."""
    new_dir = tmp_path / 'non_existent' / 'deep' / 'path'
    
    # Assert precondition: Path does not exist
    assert not new_dir.exists()
    
    # Validation should trigger auto-creation
    model = PathTestModel(writable_dir=new_dir) # type: ignore
    
    # Assert postcondition: Path now exists and is a directory
    assert model.writable_dir.exists()
    assert model.writable_dir.is_dir()
    assert model.writable_dir._path == new_dir.resolve()


def test_writable_directory_path_expansion(monkeypatch, tmp_path: Path):
    """Test that the path correctly expands user home directory (~)."""
    
    # 1. Setup Mock Home Directory
    fake_home = tmp_path / 'fake_user_home'
    fake_home.mkdir()
    
    test_path_str = '~/test_output'
    
    # 2. Mock Path.expanduser() to return the resolved path
    expected_resolved_path = (fake_home / 'test_output').resolve()
    
    def fake_expanduser(self):
        # When called on the '~' string path, return the mocked, resolved home path.
        if str(self) == test_path_str:
            return expected_resolved_path
        # Otherwise, return self to allow .resolve() to function correctly on other Path objects
        return self
        
    # Patch the actual method on the Path class
    monkeypatch.setattr(Path, 'expanduser', fake_expanduser) # type: ignore
    
    # 3. Validation should resolve "~" before creation
    model = PathTestModel(writable_dir=test_path_str) # type: ignore
    
    # 4. Assertions
    # The attribute _path should match the expected resolved path
    assert model.writable_dir._path == expected_resolved_path


def test_writable_directory_failure_not_a_directory(tmp_path: Path):
    """Test failure when the path exists but is a file."""
    existing_file = tmp_path / 'a_file.txt'
    existing_file.write_text('content')
    
    with pytest.raises(ValidationError) as excinfo:
        PathTestModel(writable_dir=existing_file) # type: ignore
        
    assert 'Path exists but is not a directory' in excinfo.value.errors()[0]['msg']


def test_writable_directory_failure_not_writable(tmp_path: Path, monkeypatch):
    """Test failure when the directory lacks write permission (robust against root user)."""
    read_only_dir = tmp_path / 'read_only_dir'
    read_only_dir.mkdir()
    
    _original_os_access = os.access 
    
    # Patch os.access() to always report write permission is MISSING on this directory
    def fake_access(path, mode):
        # If we are checking the specific read_only directory for WRITE permission, fail it.
        if path == read_only_dir.resolve() and mode == os.W_OK:
            return False 
        
        # Otherwise, call the safely stored original function.
        return _original_os_access(path, mode)

    monkeypatch.setattr(os, 'access', fake_access)
    
    # The actual chmod is now primarily symbolic, the mock forces the logic path
    read_only_dir.chmod(0o444) 
    
    try:
        with pytest.raises(ValidationError) as excinfo:
            PathTestModel(writable_dir=read_only_dir) # type: ignore
            
        assert 'Insufficient permissions for directory' in excinfo.value.errors()[0]['msg']
        assert 'WRITE' in excinfo.value.errors()[0]['msg']
    finally:
        # Restore permissions to ensure cleanup (Crucial for CI)
        read_only_dir.chmod(0o777) 


def test_writable_directory_failure_not_executable(tmp_path: Path, monkeypatch):
    """Test failure when the directory lacks execute/search permission (robust against root user)."""
    no_exec_dir = tmp_path / 'no_exec_dir'
    no_exec_dir.mkdir()
    
    _original_os_access = os.access

    # Patch os.access() to always report execute permission is MISSING
    def fake_access(path, mode):
        if path == no_exec_dir.resolve() and mode == os.X_OK:
            return False # Force failure on execute check
        
        # Otherwise, call the safely stored original function.
        return _original_os_access(path, mode)

    monkeypatch.setattr(os, 'access', fake_access)
    
    # The actual chmod is now primarily symbolic, the mock forces the logic path
    no_exec_dir.chmod(0o666) 
    
    try:
        with pytest.raises(ValidationError) as excinfo:
            PathTestModel(writable_dir=no_exec_dir) # type: ignore
            
        assert 'Insufficient permissions for directory' in excinfo.value.errors()[0]['msg']
        assert 'EXECUTE' in excinfo.value.errors()[0]['msg']
    finally:
        # Restore permissions
        no_exec_dir.chmod(0o777)


def test_writable_directory_failure_mkdir_os_error(monkeypatch, tmp_path: Path):
    """
    Test that an OSError raised during directory creation (mkdir) is correctly 
    caught and re-raised as a ValueError (100% coverage).
    """
    
    # 1. Mock Path.mkdir to always raise an OSError when called
    def mock_mkdir(*args, **kwargs):
        raise OSError(13, 'Simulated permission denied for mkdir')
        
    monkeypatch.setattr(Path, 'mkdir', mock_mkdir)
    
    # Create a Path object that is guaranteed not to exist yet
    non_existent_path = tmp_path / "new_path" / "fail"
    
    # 2. Action & Assertions
    with pytest.raises(ValidationError) as excinfo:
        PathTestModel(writable_dir=non_existent_path) # type: ignore
        
    # Assert that the error is correctly wrapped in a ValueError/ValidationError
    error_msg = excinfo.value.errors()[0]['msg']
    assert 'Value error' in error_msg
    assert 'Could not create directory' in error_msg
    assert 'Simulated permission denied' in error_msg


def test_writable_directory_attribute_access(tmp_path: Path):
    """Test that attributes of the underlying Path object are accessible via __getattr__."""
    test_dir = tmp_path / 'test_attributes'
    test_dir.mkdir()
    
    model = PathTestModel(writable_dir=test_dir) # type: ignore
    
    # Test built-in Path attributes (via __getattr__)
    assert model.writable_dir.name == 'test_attributes'
    assert model.writable_dir.is_absolute()
    
    # Test string representation
    assert str(model.writable_dir) == str(test_dir.resolve())
    assert repr(model.writable_dir).startswith("EnsureWritableDirectory")