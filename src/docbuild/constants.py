"""Constants for the CLI application."""

from pathlib import Path
import re

import platformdirs

from .models.lifecycle import LifecycleFlag
from .models.serverroles import ServerRole

APP_NAME: str = "docbuild"
"""The name of the application, used in paths and config files."""

DEFAULT_SERVER_NAME = "default-env"
"""The default server name used in the application configuration."""

DEFAULT_LANGS: tuple[str, ...]= ("en-us",)
"""The default languages used by the application."""

ALLOWED_LANGUAGES: frozenset[str] = frozenset(
    "de-de en-us es-es fr-fr ja-jp ko-kr pt-br zh-cn".split(" "),
)
"""The languages supported by the documentation portal."""

DEFAULT_DELIVERABLES: str = "*/@supported/en-us"
"""The default deliverables when no specific doctype is provided."""

# The primary, unique values of the Enum ('production', 'staging', 'testing')
SERVER_ROLES: tuple[str, ...]= tuple(
    [role.value for role in ServerRole]
)
"""The unique primary server role values."""

# Every single valid name and alias defined in the Enum
# ('PRODUCTION', 'PROD', 'P', 'production', 'prod', 'p', 'devel', etc.)
SERVER_ROLES_ALIASES: tuple[str, ...] = tuple(ServerRole.__members__.keys())
"""All valid server role names and aliases for validation and testing."""

DEFAULT_LIFECYCLE: str = "supported"
"""The default lifecycle state for a docset."""

ALLOWED_LIFECYCLES: tuple[str, ...] = tuple(lc.name for lc in LifecycleFlag)
# ('supported', 'beta', 'hidden', 'unsupported')
"""The available lifecycle states for a docset (without 'unknown')."""


# All product acronyms and their names
# - key: /product/@productid
# - value: /product/name
#
# Use the following command to create the output below:
# xmlstarlet sel -t -v '/product/@productid' -o ' '\
#   -v '/product/name' -nl config.d/[a-z]*.xml
VALID_PRODUCTS: dict[str, str] = {
    key.strip(): value.strip()
    for key, value in (
        line.split(" ", 1)
        # Syntax: acronym <SPACE> full name:
        for line in """appliance Appliance building
cloudnative Cloud Native
compliance Compliance Documentation
container Container Documentation
liberty SUSE Multi-Linux Support
releasenotes SUSE Release Notes
sbp SUSE Best Practices
ses SUSE Enterprise Storage
sled SUSE Linux Enterprise Desktop
sle-ha SUSE Linux Enterprise High Availability
sle-hpc SUSE Linux Enterprise High-Performance Computing
sle-micro SUSE Linux Micro
sle-public-cloud SUSE Linux Enterprise in Public Clouds
sle-rt SUSE Linux Enterprise Real Time
sles-sap SUSE Linux Enterprise Server for SAP applications
sles SUSE Linux Enterprise Server
sle-vmdp SUSE Linux Enterprise Virtual Machine Driver Pack
smart SUSE Smart Docs
smt SUSE Linux Enterprise Subscription Management Tool
soc SUSE OpenStack Cloud
style SUSE Documentation Style Guide
subscription Subscription Management
suma-retail SUSE Multi-Linux Manager for Retail
suma SUSE Multi-Linux Manager
suse-ai-factory SUSE AI Factory
suse-ai SUSE AI
suse-caasp SUSE CaaS Platform
suse-cap SUSE Cloud Application Platform
suse-distribution-migration-system SUSE Distribution Migration System
suse-edge SUSE Edge
suse-telco SUSE Telco Cloud
trd Technical Reference Documentation""".strip().splitlines()
    )
}
"""A dictionary of valid products acronyms and their full names."""

ALLOWED_PRODUCTS: tuple[str, ...]= tuple([item for item in VALID_PRODUCTS])
"""A tuple of valid product acronyms."""

SINGLE_LANG_REGEX: re.Pattern = re.compile(r"[a-z]{2}-[a-z]{2}")
"""Regex for a single language code in the format 'xx-XX' (e.g., 'en-us')."""

MULTIPLE_LANG_REGEX: re.Pattern = re.compile(
    rf"^({SINGLE_LANG_REGEX.pattern},)*"
    rf"{SINGLE_LANG_REGEX.pattern}",
)
"""Regex for multiple languages, separated by commas."""

LIFECYCLES_STR: str = "|".join(ALLOWED_LIFECYCLES)
"""Regex for lifecycle states, separated by pipe (|)."""


# --- PATHS AND CONFIGURATION CONSTANTS ---
PROJECT_DIR: Path = Path.cwd()
"""The current working directory, used as the project directory."""

USER_CONFIG_DIR: Path = Path.home() / ".config" / APP_NAME
"""The user-specific configuration directory, typically located
at ~/.config/docbuild."""

SYSTEM_CONFIG_DIR: Path = Path("/etc") / APP_NAME
"""The system-wide configuration directory, typically located
at /etc/docbuild."""

CONFIG_PATHS: tuple[Path, ...] = (
    # The system-wide config path:
    SYSTEM_CONFIG_DIR,
    # The user config path:
    USER_CONFIG_DIR,
    # The current working/project directory:
    PROJECT_DIR,
)
"""The paths where the application will look for configuration files."""

# --- XDG Base Directory Setup ---
STATE_HOME: Path = platformdirs.user_state_path(APP_NAME)
"""The base directory for application state, logs, and locks, per XDG Base Directory Specification."""

CONFIG_HOME: Path = platformdirs.user_config_path(APP_NAME)
"""The user-specific configuration directory, typically located at ~/.config/docbuild."""

DATA_HOME: Path = platformdirs.user_data_path(APP_NAME)
"""The user-specific data directory, typically located at ~/.local/share/docbuild."""

CACHE_HOME: Path = platformdirs.user_cache_path(APP_NAME)
"""The user-specific cache directory, typically located at ~/.cache/docbuild."""

RUNTIME_DIR: Path = platformdirs.user_runtime_path(APP_NAME)
"""The user-specific runtime directory, typically located at /run/user/1000/docbuild."""


# --- Config files ---
APP_CONFIG_BASENAMES: tuple[str|Path, ...] = (".config.toml", "config.toml")
"""The base filenames for the application configuration files, in
order of priority."""

PROJECT_LEVEL_APP_CONFIG_FILENAMES: tuple[str|Path, ...] = (
    f".{APP_NAME}.config.toml",
    f"{APP_NAME}.config.toml",
    # 'app.config.toml',
)
"""Additional configuration filenames at the project level."""

APP_CONFIG_FILENAME: str|Path = "config.toml"
"""The filename of the application's config file without any paths."""

ENV_CONFIG_FILENAME: str|Path = "env.{role}.toml"
"""The filename of the environment's config file without any paths."""

DEFAULT_ENV_CONFIG_FILENAME: str|Path = ENV_CONFIG_FILENAME.format(role="production")
"""The default filename for the environment's config file, typically
used in production."""

GIT_CONFIG_FILENAME: Path = Path(__file__).parent / "etc/git/gitconfig"
"""The project-specific Git configuration file (relative to this project)"""

# --- State and Logging Constants ---
BASE_LOG_DIR: Path = Path(f"{STATE_HOME}/{DEFAULT_SERVER_NAME}/log")
"""The directory where log files will be stored."""

BASE_STATE_DIR: Path = STATE_HOME / DEFAULT_SERVER_NAME
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

XML_NS = "http://www.w3.org/XML/1998/namespace"
"""The XML namespace URI for XML elements."""

XINCLUDE_NS = "http://www.w3.org/2001/XInclude"
"""The XML namespace URI for XInclude elements."""

DOCBOOK_NS = "http://docbook.org/ns/docbook"
"""The XML namespace URI for DocBook elements."""

XLINK_NS = "http://www.w3.org/1999/xlink"
"""The XML namespace URI for XLink attributes."""


# First-order dependencies required by docbuild
SYSTEM_DEPENDENCIES = {
    "jing": ">=20220510",
    "trang": None,  # Any version
    "daps": ">=4",
    "xmllint": None,
    "xsltproc": None,
}
