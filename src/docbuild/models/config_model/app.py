"""Pydantic model for application configuration."""

from typing import Any, Self
from pydantic import BaseModel, Field, model_validator, ConfigDict
from copy import deepcopy

from docbuild.config.app import replace_placeholders
from docbuild.config.app import CircularReferenceError, PlaceholderResolutionError
from docbuild.logging import DEFAULT_LOGGING_CONFIG

# 1. Logging Sub-Model
class App_LoggingConfig(BaseModel):
    """Configuration for the application's logging system.
    
    This structure is validated for existence of core sections, but allows
    for the flexible structure required by logging.config.dictConfig.
    """
    version: int = 1
    disable_existing_loggers: bool = False
    
    formatters: dict[str, Any] = Field(
        default_factory=dict,
        title="Formatters Dictionary",
        description="Defines the format strings and styles for log messages."
    )
    handlers: dict[str, Any] = Field(
        default_factory=dict,
        title="Handlers Dictionary",
        description="Defines how log messages are distributed (e.g., console, file, etc.)."
    )
    loggers: dict[str, Any] = Field(
        default_factory=dict,
        title="Loggers Dictionary",
        description="Defines specific loggers by name, overriding settings from the root logger."
    )
    root: dict[str, Any] = Field(
        default_factory=dict,
        title="Root Logger Configuration",
        description="Defines the global fallback settings for all loggers (level and handlers)."
    )
    
    model_config = ConfigDict(extra='allow')


# 2. Root Application Model
class AppConfig(BaseModel):
    """Root model for application configuration (config.toml)."""
    
    # Set the logging configuration. We use the DEFAULT_LOGGING_CONFIG 
    # to provide a working default if the user omits this section.
    logging: App_LoggingConfig = Field(
        default_factory=lambda: App_LoggingConfig.model_validate(DEFAULT_LOGGING_CONFIG),
        description="Configuration for the application's logging system."
    )
    
    # Placeholder field for future app-wide settings (e.g., [app.features])
    # Placeholder fields should be added here as needed later.
    
    @model_validator(mode='before')
    @classmethod
    def _resolve_placeholders(cls, data: Any) -> Any:
        """Resolve placeholders before any other validation.
        
        This method is critical for allowing Path, URLs, etc., to be resolved
        from placeholders before Pydantic validates their structure.
        """
        if isinstance(data, dict):
            try:
                # The function is already defined in src/docbuild/config/app.py
                return replace_placeholders(deepcopy(data))
            except (PlaceholderResolutionError, CircularReferenceError) as e:
                # Re-raise as a ValueError to surface it as a configuration error
                raise ValueError(f"Configuration placeholder error: {e}") from e
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Convenience method to validate and return an instance."""
        return cls.model_validate(data)
