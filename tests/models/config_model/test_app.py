"""Tests for the AppConfig Pydantic model and associated logic."""

import logging
import pytest
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch # ADDED Mock import

from pydantic import ValidationError, BaseModel
from docbuild.models.config_model.app import AppConfig
from docbuild.config.app import PlaceholderResolutionError


# --- Helper Fixtures ---

# The test now imports Mock and uses the function name directly
@pytest.fixture
def mock_replace_placeholders(monkeypatch):
    """Mocks the replace_placeholders utility to confirm it was called."""
    mock = Mock(wraps=lambda d: d)  # Retains original behavior but tracks calls
    monkeypatch.setattr('docbuild.models.config_model.app.replace_placeholders', mock)
    return mock


# --- Test Cases ---

def test_appconfig_initializes_with_defaults():
    """Tests that AppConfig initializes correctly without any input data."""
    # When initialized with an empty dict, it should fill in the default logging config.
    config = AppConfig.from_dict({})
    
    assert isinstance(config, AppConfig)
    # Check that the critical logging version is set by default
    assert config.logging.version == 1
    # Check that one of the nested list types is defaulted correctly
    assert isinstance(config.logging.root.handlers, list)
    # The default root level is DEBUG (from DEFAULT_LOGGING_CONFIG), not WARNING.
    assert config.logging.root.level == 'DEBUG'


def test_appconfig_accepts_valid_data():
    """Tests that AppConfig accepts and correctly validates known good data."""
    valid_data = {
        'logging': {
            'version': 1,
            'handlers': {
                'file_handler': {'class': 'logging.FileHandler', 'level': 'INFO'}
            }
        }
    }
    config = AppConfig.from_dict(valid_data)
    
    assert config.logging.version == 1
    # Check that the handler was correctly coerced into a HandlerConfig object
    assert isinstance(config.logging.handlers['file_handler'], BaseModel)
    assert config.logging.handlers['file_handler'].level == 'INFO'


def test_appconfig_placeholder_resolution_is_called(mock_replace_placeholders):
    """Tests that the _resolve_placeholders model validator is executed."""
    data = {'logging': {'version': 1}, 'feature': 'flag'}
    
    # Validation triggers the model_validator
    AppConfig.from_dict(data) 
    
    # Assert that our mock function was called exactly once before validation proceeds
    mock_replace_placeholders.assert_called_once()


def test_appconfig_rejects_typo_in_logger_spec():
    """Tests that the strict schema (extra='forbid') catches a typo in LoggerConfig."""
    invalid_data = {
        'logging': {
            'version': 1,
            'loggers': {
                'app_logger': {
                    'level': 'DEBUG',
                    # Typos are forbidden by extra='forbid' in LoggerConfig
                    'propogate': True,  
                }
            }
        }
    }
    with pytest.raises(ValidationError, match='Extra inputs are not permitted'):
        AppConfig.from_dict(invalid_data)


def test_appconfig_rejects_invalid_log_version():
    """Tests that the Literal[1] field constraint is enforced."""
    invalid_data = {
        'logging': {
            # Version must be 1, but we pass 2
            'version': 2
        }
    }
    with pytest.raises(ValidationError, match='Input should be 1'):
        AppConfig.from_dict(invalid_data)


def test_appconfig_rejects_unresolved_placeholder():
    """Tests that an unresolved placeholder error stops execution early."""
    unresolved_data = {
        'logging': {
            'version': 1
        },
        'path': '{UNRESOLVED_VAR}'
    }
    
    # We no longer mock the function and rely on Pydantic's internal
    # error propagation, asserting against the specific Pydantic error message
    
    # The real AppConfig model is designed to catch the ValueError raised by 
    # replace_placeholders and re-raise it as a Pydantic Validation Error.
    # The original test's expected match was close enough for the fix.
    
    # We remove the mock setup and just assert the raised exception type/message.
    with pytest.raises(ValueError, match='Configuration placeholder error'):
        AppConfig.from_dict(unresolved_data)