"""Pydantic model for application configuration."""

from collections.abc import Sequence  # Added Sequence for internal use
from copy import deepcopy
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from docbuild.config.app import (
    CircularReferenceError,
    PlaceholderResolutionError,
    replace_placeholders,
)
from docbuild.logging import DEFAULT_LOGGING_CONFIG

# --- 1. Logging Sub-Models (Schema for logging.config.dictConfig) ---


class FormatterConfig(BaseModel):
    """A Pydantic model for logging formatter configuration."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    format: str | None = None
    datefmt: str | None = None
    style: Literal["%", "{", "$"] | None = None
    class_name: str | None = Field(
        None,
        alias="class",
        description="The fully qualified name of the handler class",
    )
    # Renamed to avoid shadowing the BaseModel.validate() method.
    validation: bool | None = Field(
        None,
        alias="validate",
        description="If specified, controls whether configuration is validated.",
    )


class HandlerConfig(BaseModel):
    """A Pydantic model for logging handler configuration."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    class_name: str | None = Field(
        None,
        alias="class",
        description="The fully qualified name of the handler class",
    )
    level: str | int | None = None
    formatter: str | None = Field(None, description="Must match a key in 'formatters'.")
    filters: list[str] | None = None


class LoggerConfig(BaseModel):
    """A Pydantic model for logging logger configuration."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    level: str | int | None = None
    handlers: list[str] | None = Field(
        None, description="Must match keys in 'handlers'."
    )
    propagate: bool | None = True
    filters: list[str] | None = None


class RootLoggerConfig(BaseModel):
    """A Pydantic model for the root logger configuration."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    level: str | int | None = Field(
        "WARNING", description="The minimum severity level to log."
    )
    handlers: list[str] | None = Field(
        default_factory=list, description="Must match keys in 'handlers'."
    )
    filters: list[str] | None = None


# --- 2. Type Aliases for Dictionaries ---

type FormattersDict = dict[str, FormatterConfig]
type HandlersDict = dict[str, HandlerConfig]
type LoggersDict = dict[str, LoggerConfig]
type FiltersDict = dict[str, Any]


# --- 3. The Top-Level Logging Configuration Model (AppLoggingConfig) ---
class AppLoggingConfig(BaseModel):
    """Pydantic model for the logging configuration.

    Used by :func:`logging.config.dictConfig`
    """

    version: Literal[1] = Field(description="The schema version. Must be 1.")
    disable_existing_loggers: bool = False

    formatters: FormattersDict = Field(
        default_factory=dict, description="All configured formatters."
    )
    filters: FiltersDict = Field(
        default_factory=dict, description="All configured filters."
    )
    handlers: HandlersDict = Field(
        default_factory=dict, description="All configured handlers."
    )
    loggers: LoggersDict = Field(
        default_factory=dict, description="All specific loggers (e.g., 'my_app')."
    )
    # Use an instance as we have only one root logger
    root: RootLoggerConfig = Field(
        default_factory=RootLoggerConfig, description="The root logger configuration."
    )

    incremental: bool = Field(
        False, description="Allows incremental configuration updates."
    )

    # --- CROSS-REFERENCE VALIDATION ---
    @model_validator(mode="after")
    def _validate_cross_references(self) -> Self:
        """Validate that all loggers and handlers refer to defined components.

        This prevents runtime errors when logging.config.dictConfig is called.
        """
        defined_formatters = set(self.formatters.keys())
        defined_handlers = set(self.handlers.keys())

        # Helper function to check if a list of names exists in a defined set
        def check_names(
            names: Sequence[str],
            defined_set: set[str],
            item_type: str,
            source_name: str,
        ) -> None:
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
                    f"Configuration error in handler '{h_name}': Formatter '"
                    f"{formatter_name}' "
                    "is referenced but not defined in the 'formatters' section."
                )

            # We skip checking filters here as they can be external/dynamic

        # 2. Check Loggers and Root Logger for valid Handlers

        # Check specific loggers
        for l_name, logger_config in self.loggers.items():
            check_names(
                logger_config.handlers or [],
                defined_handlers,
                "handler",
                f"logger '{l_name}'",
            )

        # Check root logger
        check_names(
            self.root.handlers or [], defined_handlers, "handler", "root logger"
        )

        return self


# --- 4. Root Application Model ---


class AppConfig(BaseModel):
    """Root model for application configuration (:file:`config.toml`)."""

    logging: AppLoggingConfig = Field(
        default_factory=lambda: AppLoggingConfig.model_validate(
            DEFAULT_LOGGING_CONFIG
        ),
        description="Configuration for the application's logging system.",
    )

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    @classmethod
    def _resolve_placeholders(cls, data: dict[str, Any]) -> dict[str, Any] | None:
        if isinstance(data, dict):
            try:
                return replace_placeholders(deepcopy(data))
            except (PlaceholderResolutionError, CircularReferenceError) as e:
                raise ValueError(f"Configuration placeholder error: {e}") from e
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Create an AppConfig instance from a dictionary."""
        return cls.model_validate(data)
