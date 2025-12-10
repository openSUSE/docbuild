"""Tests for the AppConfig Pydantic model and its validation logic."""

import pytest
from unittest.mock import Mock
from pydantic import ValidationError

from docbuild.models.config.app import AppConfig
from docbuild.models.config import app as app_module


# --- Helper Fixtures ---

@pytest.fixture
def mock_replace_placeholders(monkeypatch):
    """Mock the replace_placeholders utility to confirm it was invoked."""
    mock = Mock(return_value={
        'logging': {'version': 1},
        'feature': 'flag',
        'path_with_placeholder': 'resolved/path/APP_NAME_VALUE',
    })

    # Patch the actual symbol used inside AppConfig’s module
    monkeypatch.setattr(app_module, "replace_placeholders", mock)
    return mock


# --- Test Cases ---

def test_appconfig_initializes_with_defaults():
    """Ensure AppConfig initializes correctly with default logging configuration."""
    config = AppConfig.from_dict({})

    assert isinstance(config, AppConfig)
    assert config.logging.version == 1
    assert isinstance(config.logging.root.handlers, list)
    assert config.logging.root.level == 'DEBUG'


def test_appconfig_accepts_valid_data():
    """Ensure AppConfig accepts and validates well-formed configuration data."""
    valid_data = {
        'logging': {
            'version': 1,
            'handlers': {
                'file_handler': {'class': 'logging.FileHandler', 'level': 'INFO'},
            },
            'formatters': {
                'simple': {'format': '(%s)'},
            },
            'loggers': {
                'app_logger': {'handlers': ['file_handler']},
            },
        },
    }

    config = AppConfig.from_dict(valid_data)

    assert config.logging.version == 1
    assert config.logging.handlers['file_handler'].level == 'INFO'
    assert config.logging.loggers['app_logger'].handlers == ['file_handler']


def test_appconfig_placeholder_resolution_is_called(mock_replace_placeholders):
    """Verify that the model validator triggers placeholder resolution."""
    data = {
        'logging': {'version': 1},
        'path_with_placeholder': 'some/path/{APP_NAME}',  # Placeholder triggers resolution logic
        'feature': 'flag',
    }

    AppConfig.from_dict(data)

    mock_replace_placeholders.assert_called_once()


def test_appconfig_rejects_typo_in_logger_spec():
    """Reject configurations with unexpected keys in LoggerConfig."""
    invalid_data = {
        'logging': {
            'version': 1,
            'loggers': {
                'app_logger': {
                    'level': 'DEBUG',
                    'propogate': True,  # typo: should be 'propagate'
                },
            },
        },
    }

    with pytest.raises(ValidationError, match='Extra inputs are not permitted'):
        AppConfig.from_dict(invalid_data)


def test_appconfig_rejects_invalid_log_version():
    """Reject invalid logging version (must be Literal[1])."""
    invalid_data = {'logging': {'version': 2}}

    with pytest.raises(ValidationError, match='Input should be 1'):
        AppConfig.from_dict(invalid_data)


def test_appconfig_rejects_unresolved_placeholder():
    """Raise error if a configuration placeholder cannot be resolved."""
    unresolved_data = {
        'logging': {'version': 1},
        'path': '{UNRESOLVED_VAR}',
    }

    with pytest.raises(ValueError, match='Configuration placeholder error'):
        AppConfig.from_dict(unresolved_data)


# --- Cross-Reference Validation Tests ---

def test_appconfig_valid_cross_reference():
    """Allow valid handler and logger cross-references."""
    valid_data = {
        'logging': {
            'version': 1,
            'handlers': {
                'h1': {'class': 'logging.StreamHandler'},
                'h2': {'class': 'logging.FileHandler'},
            },
            'loggers': {
                'app_logger': {'level': 'DEBUG', 'handlers': ['h1', 'h2']},
            },
            'root': {
                'level': 'INFO',
                'handlers': ['h2'],
            },
        },
    }

    config = AppConfig.from_dict(valid_data)

    assert config.logging.loggers['app_logger'].handlers == ['h1', 'h2']
    assert config.logging.root.handlers == ['h2']


def test_appconfig_rejects_missing_handler_reference():
    """Raise error when a logger references a handler that doesn't exist."""
    invalid_data = {
        'logging': {
            'version': 1,
            'handlers': {'h1': {'class': 'logging.StreamHandler'}},
            'loggers': {
                'app_logger': {'level': 'DEBUG', 'handlers': ['h1', 'file_log']},
            },
        },
    }

    with pytest.raises(
        ValueError,
        match="logger 'app_logger': The following handler names are referenced but not defined: file_log",
    ):
        AppConfig.from_dict(invalid_data)


def test_appconfig_rejects_missing_formatter_reference():
    """Raise error when a handler references a non-existent formatter."""
    invalid_data = {
        'logging': {
            'version': 1,
            'formatters': {'simple': {'format': '%(message)s'}},
            'handlers': {
                'h1': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'detailed',  # formatter not defined
                },
            },
        },
    }

    with pytest.raises(
        ValueError,
        match="Configuration error in handler 'h1': Formatter 'detailed' is referenced but not defined",
    ):
        AppConfig.from_dict(invalid_data)
