"""Context for the docbuild CLI commands."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models.config.env import EnvConfig
from ..models.doctype import Doctype


@dataclass
class DocBuildContext:
    """The CLI context shared between different subcommands."""

    dry_run: bool = False
    """If set, just pretend to run the command without making any changes"""

    verbose: int = 0
    """verbosity level"""

    appconfigfiles: tuple[str | Path, ...] | None = None
    """The app's config files to load, if any"""

    appconfig_from_defaults: bool = False
    """If set, the app's config was loaded from defaults"""

    appconfig: dict[str, Any] | None = None
    """The accumulated content of all app config files"""

    envconfigfiles: tuple[str | Path, ...] | None = None
    """The env's config files to load, if any"""

    envconfig_from_defaults: bool = False
    """Internal flag to indicate if the env's config was loaded from defaults"""

    envconfig: EnvConfig | None = None
    """The accumulated content of all env config files"""

    doctypes: list[Doctype] | None = None
    """The doctypes to process, if any"""

    debug: bool = False
    """If set, enable debug mode"""

    validation_method: str = "jing"
    """Method used to validate XML files: 'jing' (default) or 'lxml'"""
