"""Tests for the AppConfig Pydantic model and associated logic."""

import logging
import pytest
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch 

from pydantic import ValidationError, BaseModel
from docbuild.models.config_model.app import AppConfig
from docbuild.config.app import PlaceholderResolutionError, replace_placeholders


# --- Helper Fixtures ---

@pytest.fixture
def mock_replace_placeholders(monkeypatch):
    """Mocks the replace_placeholders utility to confirm it was called."""
    mock = Mock(wraps=lambda d: d)  # Retains original behavior but tracks calls
    
    # Use the object reference for monkeypatch.setattr for safety (Reviewer's feedback)
    monkeypatch.setattr(replace_placeholders, mock) 
    
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
    # The default root level is DEBUG (from DEFAULT_LOGGING_CONFIG)
    assert config.logging.root.level == 'DEBUG'


def test_appconfig_accepts_valid_data():
    """Tests that AppConfig accepts and correctly validates known good data."""
    valid_data = {
        'logging': {
            'version': 1,
            'handlers': {
                # This tests that FormatterConfig and HandlerConfig can be instantiated
                'file_handler': {'class': 'logging.FileHandler', 'level': 'INFO'}
            },
            'formatters': {
                'simple': {'format': '(%s)'}
            },
            'loggers': {
                'app_logger': {'handlers': ['file_handler']}
            }
        }
    }
    config = AppConfig.from_dict(valid_data)
    
    assert config.logging.version == 1
    assert config.logging.handlers['file_handler'].level == 'INFO'
    assert config.logging.loggers['app_logger'].handlers == ['file_handler']


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
    
    # The real AppConfig model is designed to catch the ValueError raised by 
    # replace_placeholders and re-raise it as a Pydantic Validation Error.
    # We assert the raised exception type/message.
    with pytest.raises(ValueError, match='Configuration placeholder error'):
        AppConfig.from_dict(unresolved_data)


# --- CROSS-REFERENCE VALIDATION TESTS ---

def test_appconfig_valid_cross_reference():
    """Tests that a logger/handler setup with valid references passes validation."""
    valid_cross_ref_data = {
        'logging': {
            'version': 1,
            'handlers': {
                'h1': {'class': 'logging.StreamHandler'},
                'h2': {'class': 'logging.FileHandler'},
            },
            'loggers': {
                'app_logger': {'level': 'DEBUG', 'handlers': ['h1', 'h2']}
            },
            'root': {
                'level': 'INFO',
                'handlers': ['h2']
            }
        }
    }
    
    # Should initialize without raising an error
    config = AppConfig.from_dict(valid_cross_ref_data)
    assert config.logging.loggers['app_logger'].handlers == ['h1', 'h2']
    assert config.logging.root.handlers == ['h2']


def test_appconfig_rejects_missing_handler_reference():
    """Tests that validation fails when a logger references a non-existent handler."""
    missing_ref_data = {
        'logging': {
            'version': 1,
            'handlers': {
                'h1': {'class': 'logging.StreamHandler'}
            },
            'loggers': {
                'app_logger': {
                    'level': 'DEBUG',
                    # 'file_log' is referenced but missing in 'handlers'
                    'handlers': ['h1', 'file_log'] 
                }
            }
        }
    }
    
    # Expect ValueError raised by the _validate_cross_references method
    with pytest.raises(ValueError, match="logger 'app_logger': The following handler names are referenced but not defined: file_log"):
        AppConfig.from_dict(missing_ref_data)


def test_appconfig_rejects_missing_formatter_reference():
    """Tests that validation fails when a handler references a non-existent formatter."""
    missing_formatter_data = {
        'logging': {
            'version': 1,
            'formatters': {
                'simple': {'format': '%(message)s'}
            },
            'handlers': {
                'h1': {
                    'class': 'logging.StreamHandler',
                    # 'detailed' is referenced but missing in 'formatters'
                    'formatter': 'detailed' 
                }
            }
        }
    }
    
    # Expect ValueError raised by the _validate_cross_references method
    with pytest.raises(ValueError, match="Configuration error in handler 'h1': Formatter 'detailed' is referenced but not defined"):
        AppConfig.from_dict(missing_formatter_data)