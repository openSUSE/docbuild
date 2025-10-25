"""Pydantic model for application configuration."""

from copy import deepcopy
from typing import Any, Self, Literal
import logging # Needed for DEFAULT_LOGGING_CONFIG usage

from pydantic import BaseModel, Field, model_validator, ConfigDict

from docbuild.config.app import replace_placeholders
from docbuild.config.app import CircularReferenceError, PlaceholderResolutionError
from docbuild.logging import DEFAULT_LOGGING_CONFIG # Note: Must import the actual DEFAULT_LOGGING_CONFIG


# --- 1. Logging Sub-Models (Schema for logging.dictConfig) ---

class FormatterConfig(BaseModel):
    """
    Defines the configuration for a single logging formatter.
    Allows extra keys for custom class/factory arguments.
    """
    model_config = ConfigDict(extra='allow', populate_by_name=True) 

    format: str | None = None
    datefmt: str | None = None
    style: Literal['%', '{', '$'] | None = None
    class_name: str | None = Field(None, alias='class') 
    validate: bool | None = None


class HandlerConfig(BaseModel):
    """
    Defines the configuration for a single logging handler.
    Allows extra keys specific to certain handler classes (e.g., 'filename', 'maxBytes').
    """
    model_config = ConfigDict(extra='allow', populate_by_name=True) 

    class_name: str | None = Field(None, alias='class')
    level: str | int | None = None
    formatter: str | None = Field(None, description="Must match a key in 'formatters'.")
    filters: list[str] | None = None


class LoggerConfig(BaseModel):
    """
    Defines the configuration for a single logger instance.
    """
    model_config = ConfigDict(extra='allow', populate_by_name=True)

    level: str | int | None = None
    handlers: list[str] | None = Field(None, description="Must match keys in 'handlers'.")
    propagate: bool | None = True
    filters: list[str] | None = None


class RootLoggerConfig(BaseModel):
    """
    Defines the configuration for the root logger.
    """
    model_config = ConfigDict(extra='allow', populate_by_name=True)
    
    # Provide a default level and handlers list to prevent crashes 
    level: str | int | None = Field('WARNING', description="The minimum severity level to log.")
    handlers: list[str] | None = Field(default_factory=list, description="Must match keys in 'handlers'.")
    filters: list[str] | None = None

# --- 2. Type Aliases for Dictionaries ---

type FormattersDict = dict[str, FormatterConfig]
type HandlersDict = dict[str, HandlerConfig]
type LoggersDict = dict[str, LoggerConfig]
type FiltersDict = dict[str, Any]

# --- 3. The Top-Level Logging Configuration Model (Replaces App_LoggingConfig) ---

class App_LoggingConfig(BaseModel):
    """
    The complete Pydantic model for Python's logging.dictConfig.
    """
    version: Literal[1] = Field(description="The schema version. Must be 1.")
    disable_existing_loggers: bool = False

    formatters: FormattersDict = Field(default_factory=dict, description="All configured formatters.")
    filters: FiltersDict = Field(default_factory=dict, description="All configured filters.")
    handlers: HandlersDict = Field(default_factory=dict, description="All configured handlers.")
    loggers: LoggersDict = Field(default_factory=dict, description="All specific loggers (e.g., 'my_app').")
    root: RootLoggerConfig = Field(default_factory=RootLoggerConfig, description="The root logger configuration.")
    
    incremental: bool = Field(False, description="Allows incremental configuration updates.")
    


# --- 4. Root Application Model ---

class AppConfig(BaseModel):
    """Root model for application configuration (config.toml)."""
    
    logging: App_LoggingConfig = Field(
        default_factory=lambda: App_LoggingConfig.model_validate(
            DEFAULT_LOGGING_CONFIG
        ),
        description="Configuration for the application's logging system."
    )
    
    model_config = ConfigDict(extra='allow') 

    @model_validator(mode='before')
    @classmethod
    def _resolve_placeholders(cls, data: Any) -> Any:
        if isinstance(data, dict):
            try:
                return replace_placeholders(deepcopy(data))
            except (PlaceholderResolutionError, CircularReferenceError) as e:
                raise ValueError(f"Configuration placeholder error: {e}") from e
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Convenience method to validate and return an instance."""
        return cls.model_validate(data)