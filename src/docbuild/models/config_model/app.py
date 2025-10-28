"""Pydantic model for application configuration."""

from copy import deepcopy
from typing import Any, Literal, Sequence, ClassVar

from pydantic import BaseModel, Field, model_validator, ConfigDict

from docbuild.config.app import replace_placeholders
from docbuild.config.app import CircularReferenceError, PlaceholderResolutionError
from docbuild.logging import DEFAULT_LOGGING_CONFIG


# --- 1. Logging Sub-Models (Schema for logging.config.dictConfig) ---

class FormatterConfig(BaseModel):
    model_config = ConfigDict(extra='allow', populate_by_name=True)

    format: str | None = None
    datefmt: str | None = None
    style: Literal['%', '{', '$'] | None = None
    class_name: str | None = Field(
        None, alias='class', description='The fully qualified name of the handler class'
    )
    validate_flag: bool | None = Field(
        None, description="Custom flag (renamed from 'validate' to avoid BaseModel conflict)"
    )


class HandlerConfig(BaseModel):
    model_config = ConfigDict(extra='allow', populate_by_name=True)

    class_name: str | None = Field(
        None, alias='class', description='The fully qualified name of the handler class'
    )
    level: str | int | None = None
    formatter: str | None = Field(None, description="Must match a key in 'formatters'.")
    filters: list[str] | None = None


class LoggerConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    level: str | int | None = None
    handlers: list[str] | None = Field(None, description="Must match keys in 'handlers'.")
    propagate: bool | None = True
    filters: list[str] | None = None


class RootLoggerConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    level: str | int | None = Field('WARNING', description="The minimum severity level to log.")
    handlers: list[str] = Field(default_factory=list, description="Must match keys in 'handlers'.")
    filters: list[str] | None = None


# --- 2. Type Aliases for Dictionaries ---

FormattersDict = dict[str, FormatterConfig]
HandlersDict = dict[str, HandlerConfig]
LoggersDict = dict[str, LoggerConfig]
FiltersDict = dict[str, Any]


# --- 3. The Top-Level Logging Configuration Model (App_LoggingConfig) ---

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

    root: RootLoggerConfig = Field(
    default_factory=lambda: RootLoggerConfig(
        level='WARNING', 
        handlers=[], 
        filters=None
    ),
    description="The root logger configuration."
    )
    incremental: bool = Field(False, description="Allows incremental configuration updates.")

    description: ClassVar[str] = "Application logging configuration."

    # --- CROSS-REFERENCE VALIDATION ---
    @model_validator(mode='after')
    def _validate_cross_references(self) -> "App_LoggingConfig":
        """
        Validates that all loggers and handlers refer to defined components.
        Prevents runtime errors when logging.config.dictConfig is called.
        """
        defined_formatters = set(self.formatters.keys())
        defined_handlers = set(self.handlers.keys())

        def check_names(names: Sequence[str], defined_set: set[str], item_type: str, source_name: str):
            if not names:
                return
            missing = [name for name in names if name not in defined_set]
            if missing:
                raise ValueError(
                    f"Configuration error in {source_name}: The following {item_type} "
                    f"names are referenced but not defined: {', '.join(missing)}"
                )

        # 1. Check Handlers for valid Formatters
        for h_name, handler_config in self.handlers.items():
            formatter_name = handler_config.formatter
            if formatter_name and formatter_name not in defined_formatters:
                raise ValueError(
                    f"Configuration error in handler '{h_name}': Formatter '{formatter_name}' "
                    "is referenced but not defined in the 'formatters' section."
                )

        # 2. Check Loggers and Root Logger for valid Handlers
        for l_name, logger_config in self.loggers.items():
            check_names(logger_config.handlers or [], defined_handlers, 'handler', f"logger '{l_name}'")

        check_names(self.root.handlers or [], defined_handlers, 'handler', 'root logger')

        return self


# --- 4. Root Application Model ---

class AppConfig(BaseModel):
    """Root model for application configuration (config.toml)."""

    logging: App_LoggingConfig = Field(
        default_factory=lambda: App_LoggingConfig.model_validate(DEFAULT_LOGGING_CONFIG),
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
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        """Convenience method to validate and return an instance."""
        return cls.model_validate(data)
