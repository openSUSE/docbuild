"""Constants for the CLI application."""

from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Final

from lxml.etree import QName
import platformdirs

from .models.envroles import EnvRole
from .models.lifecycle import LifecycleFlag

# ---------------------------------------------------------------
DOCBUILD_BANNER: Final[str] = """
       █          █         ▀ █     █
    █▀▀█ █▀▀█ █▀▀ █▀▀█ █  █ █ █  █▀▀█
    █  █ █  █ █   █  █ █  █ █ █  █  █
    ▀▀▀▀ ▀▀▀▀ ▀▀▀ ▀▀▀▀ ▀▀▀▀ ▀ ▀▀ ▀▀▀▀
"""

APP_NAME: str = "docbuild"
"""The name of the application, used in paths and config files."""

DEFAULT_ENV_NAME = "default-env"
"""The default server name used in the application configuration."""

DEFAULT_LANG: str = "en-us"
"""The default language used by the application."""

ALLOWED_LANGUAGES: frozenset[str] = frozenset(
    "de-de en-us es-es fr-fr ja-jp ko-kr pt-br zh-cn".split(" "),
)
"""The languages supported by the documentation portal."""

DEFAULT_DELIVERABLES: str = "*/@supported/en-us"
"""The default deliverables when no specific doctype is provided."""

# The primary, unique values of the Enum ('production', 'staging', 'testing')
ENV_ROLES: tuple[str, ...] = tuple(
    [role.value for role in EnvRole]
)
"""The unique primary env role values."""

# Every single valid name and alias defined in the Enum
# ('PRODUCTION', 'PROD', 'P', 'production', 'prod', 'p', 'devel', etc.)
ENV_ROLES_ALIASES: tuple[str, ...] = tuple(EnvRole.__members__.keys())
"""All valid env role names and aliases for validation and testing."""

DEFAULT_LIFECYCLE: str = "supported"
"""The default lifecycle state for a docset."""

ALLOWED_LIFECYCLES: tuple[str, ...] = tuple(str(lc.name) for lc in LifecycleFlag if lc.name)
# ('supported', 'beta', 'hidden', 'unsupported')
"""The available lifecycle states for a docset (without 'unknown')."""


SINGLE_LANG_REGEX: re.Pattern = re.compile(r"[a-z]{2}-[a-z]{2}")
"""Regex for a single language code in the format 'xx-XX' (e.g., 'en-us')."""

MULTIPLE_LANG_REGEX: re.Pattern = re.compile(
    rf"^({SINGLE_LANG_REGEX.pattern},)*"
    rf"{SINGLE_LANG_REGEX.pattern}",
)
"""Regex for multiple languages, separated by commas."""

LIFECYCLES_STR: str = "|".join(ALLOWED_LIFECYCLES)
"""Regex for lifecycle states, separated by pipe (|)."""

HOSTNAME_REGEX: Final[re.Pattern[str]] = re.compile(
    r"^(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$"
)
"""Regex for a fully qualified host name (DNS name), similar to an FQDN."""

SSH_USERNAME_REGEX: Final[re.Pattern[str]] = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
"""Regex for an SSH login name. Must start lowercase or underscore."""


# --- PATHS AND CONFIGURATION CONSTANTS ---
PROJECT_DIR: Path = Path.cwd()
"""The current working directory, used as the project directory."""

CONFIG_HOME: Path = platformdirs.user_config_path(APP_NAME)
"""The user-specific configuration directory, typically located at ~/.config/docbuild.

Overridden by the :envvar:`XDG_CONFIG_HOME` environment variable (``$XDG_CONFIG_HOME/docbuild``)."""

SYSTEM_CONFIG_DIR: Path = Path("/etc") / APP_NAME
"""The system-wide configuration directory, typically located
at /etc/docbuild."""


def xdg_site_config_dirs(appname: str) -> tuple[Path, ...]:
    """Return system config directories from :envvar:`XDG_CONFIG_DIRS`.

    Directories keep the order defined by the XDG Base Directory Specification
    (the first entry has the highest priority) and duplicates are removed.

    :param appname: Name of the application.
    :returns: Tuple of directory paths ordered highest-to-lowest priority.
    """
    raw = platformdirs.site_config_dir(appname, multipath=True).split(os.pathsep)
    return tuple(Path(p) for p in dict.fromkeys(raw) if p)


XDG_CONFIG_DIRS_PATHS: tuple[Path, ...] = xdg_site_config_dirs(APP_NAME)
"""The system-wide configuration directories from :envvar:`XDG_CONFIG_DIRS`,
highest priority first (default: :file:`/etc/xdg/docbuild` on Linux). Together,
they form the lowest-priority system-wide location."""

CONFIG_PATHS: tuple[Path, ...] = (
    # XDG system dirs (unpacked lowest-priority first, so first XDG dir wins among XDG):
    *reversed(XDG_CONFIG_DIRS_PATHS),
    # The fixed system-wide config path (overrides the XDG default(s)):
    SYSTEM_CONFIG_DIR,
    # The user config path:
    CONFIG_HOME,
    # The current working/project directory:
    PROJECT_DIR,
)
"""The paths where the application will look for configuration files."""

# --- XDG Base Directory Setup ---
STATE_HOME: Path = platformdirs.user_state_path(APP_NAME)
"""The base directory for application state, logs, and locks, per XDG Base Directory Specification.

Overridden by the :envvar:`XDG_STATE_HOME` environment variable (``$XDG_STATE_HOME/docbuild``)."""

DATA_HOME: Path = platformdirs.user_data_path(APP_NAME)
"""The user-specific data directory, typically located at ~/.local/share/docbuild.

Overridden by the :envvar:`XDG_DATA_HOME` environment variable (``$XDG_DATA_HOME/docbuild``)."""

CACHE_HOME: Path = platformdirs.user_cache_path(APP_NAME)
"""The user-specific cache directory, typically located at ~/.cache/docbuild.

Overridden by the :envvar:`XDG_CACHE_HOME` environment variable (``$XDG_CACHE_HOME/docbuild``)."""

CACHE_FILE_EXT: str = ".cache.json"
"""The standard file extension used for docbuild cache files."""

RUNTIME_DIR: Path = platformdirs.user_runtime_path(APP_NAME)
"""The user-specific runtime directory, typically located at /run/user/1000/docbuild.

Overridden by the :envvar:`XDG_RUNTIME_DIR` environment variable (``$XDG_RUNTIME_DIR/docbuild``).
Unlike the other directories, this variable has no default and is set by the login session."""


# --- Config files ---
APP_CONFIG_BASENAMES: tuple[str, ...] = (".config.toml", "config.toml")
"""The base filenames for the application configuration files, in
order of priority."""

PROJECT_LEVEL_APP_CONFIG_FILENAMES: tuple[str, ...] = (
    f".{APP_NAME}.config.toml",
    f"{APP_NAME}.config.toml",
    # 'app.config.toml',
)
"""Additional configuration filenames at the project level."""

APP_CONFIG_FILENAME: str = "config.toml"
"""The filename of the application's config file without any paths."""

ENV_CONFIG_FILENAME: str = "env.{role}.toml"
"""The filename of the environment's config file without any paths."""

DEFAULT_ENV_CONFIG_FILENAME: str = ENV_CONFIG_FILENAME.format(role="production")
"""The default filename for the environment's config file, typically
used in production."""

GIT_CONFIG_FILENAME: Path = Path(__file__).parent / "etc/git/gitconfig"
"""The project-specific Git configuration file (relative to this project)"""

# --- State and Logging Constants ---
BASE_LOG_DIR: Path = Path(f"{STATE_HOME}/{DEFAULT_ENV_NAME}/log")
"""The directory where log files will be stored."""

BASE_STATE_DIR: Path = STATE_HOME / DEFAULT_ENV_NAME
"""The directory where application state, logs, and locks are stored,
per XDG Base Directory Specification."""

GITLOGGER_NAME: str = f"{APP_NAME}.git"
"""The standardized name for the Git-related logger."""

PORTALLOGGER_NAME: str = f"{APP_NAME}.portal"
"""The standardized name for the Portal-related logger."""

# --- Locking constants ---

BASE_LOCK_DIR: Path = RUNTIME_DIR / "locks"
"""The directory where PID lock files will be stored."""

XMLDATADIR: Path = Path(__file__).parent / "config" / "xml" / "data"
"""Directory where additional files (RNC, XSLT) for XML processing are stored."""


# --- UI and Error Reporting Constants ---

DEFAULT_ERROR_LIMIT: int = 5
"""The maximum number of validation errors to display before truncating the output."""


# --- XML namespaces ---

XML_NS: Final[str] = "http://www.w3.org/XML/1998/namespace"
"""The XML namespace URI for XML elements."""

XML_ID: Final[QName] = QName(XML_NS, "id")
"""The QName for the xml:id attribute."""

XINCLUDE_NS: Final[str] = "http://www.w3.org/2001/XInclude"
"""The XML namespace URI for XInclude elements."""

DOCBOOK_NS: Final[str] = "http://docbook.org/ns/docbook"
"""The XML namespace URI for DocBook elements."""

XLINK_NS: Final[str] = "http://www.w3.org/1999/xlink"
"""The XML namespace URI for XLink attributes."""


@dataclass(frozen=True)
class DependencySpec:
    """Specification for a system dependency."""

    required: str | None = None
    args: tuple[str, ...] = ("--version",)


# First-order dependencies required by docbuild
SYSTEM_DEPENDENCIES: Final[dict[str, DependencySpec]] = {
    "jing": DependencySpec(required=">=20220510", args=()),
    "trang": DependencySpec(required=None, args=()),
    "daps": DependencySpec(required=">=4"),
    "xmllint": DependencySpec(required=None),
    "xsltproc": DependencySpec(required=None),
    "rsync": DependencySpec(required=None),
}

RUNTIME_PLACEHOLDERS: frozenset[str] = frozenset(
    {"builddir", "dcfile", "output", "product", "docset", "lang", "format"}
)
"""Set of placeholder names that are resolved at runtime by the build system."""

ESCAPE_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\{\{(?P<runtime>" + "|".join(sorted(RUNTIME_PLACEHOLDERS)) + r")\}\}|\{\{|\}\}"
)
"""Regex to identify escape sequences and runtime placeholders."""
