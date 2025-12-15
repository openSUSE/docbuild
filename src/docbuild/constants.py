"""Constants for the CLI application."""

from pathlib import Path
import re

from .models.lifecycle import LifecycleFlag
from .models.serverroles import ServerRole

APP_NAME = 'docbuild'
"""The name of the application, used in paths and config files."""

DEFAULT_LANGS = ('en-us',)
"""The default languages used by the application."""

ALLOWED_LANGUAGES = frozenset(
    'de-de en-us es-es fr-fr ja-jp ko-kr pt-br zh-cn'.split(' '),
)
"""The languages supported by the documentation portal."""

DEFAULT_DELIVERABLES = '*/@supported/en-us'
"""The default deliverables when no specific doctype is provided."""

# SERVER_ROLES = (
#     "production", "prod", "p",
#     "testing", "test", "t",
#     "staging", "stage", "s",
# )
SERVER_ROLES = tuple(
    [role.value for role in ServerRole]  # type: ignore[call-arg]
)
"""The different server roles, including long and short spelling."""

DEFAULT_LIFECYCLE = 'supported'
"""The default lifecycle state for a docset."""

ALLOWED_LIFECYCLES: tuple[str] = tuple(
    lc.name
    for lc in LifecycleFlag
)
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
        line.split(' ', 1)
        # Syntax: acronym <SPACE> full name:
        for line in """appliance Appliance building
cloudnative Cloud Native
compliance Compliance Documentation
container Container Documentation
liberty SUSE Multi-Linux Support
sbp SUSE Best Practices
ses SUSE Enterprise Storage
sled SUSE Linux Enterprise Desktop
sle-ha SUSE Linux Enterprise High Availability (incl. SLE HA GEO)
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
suse-ai SUSE AI
suse-caasp SUSE CaaS Platform
suse-cap SUSE Cloud Application Platform
suse-distribution-migration-system SUSE Distribution Migration System
suse-edge SUSE Edge
trd Technical Reference Documentation""".strip().splitlines()
    )
}
"""A dictionary of valid products acronyms and their full names."""

ALLOWED_PRODUCTS = tuple([item for item in VALID_PRODUCTS])
"""A tuple of valid product acronyms."""

SINGLE_LANG_REGEX = re.compile(r'[a-z]{2}-[a-z]{2}')
"""Regex for a single language code in the format 'xx-XX' (e.g., 'en-us')."""

MULTIPLE_LANG_REGEX = re.compile(
    rf'^({SINGLE_LANG_REGEX.pattern},)*'
    rf'{SINGLE_LANG_REGEX.pattern}',
)
"""Regex for multiple languages, separated by commas."""

LIFECYCLES_STR = '|'.join(ALLOWED_LIFECYCLES)
"""Regex for lifecycle states, separated by pipe (|)."""


# --- PATHS AND CONFIGURATION CONSTANTS ---
PROJECT_DIR = Path.cwd()
"""The current working directory, used as the project directory."""

USER_CONFIG_DIR = Path.home() / '.config' / APP_NAME
"""The user-specific configuration directory, typically located
at ~/.config/docbuild."""

SYSTEM_CONFIG_DIR = Path('/etc') / APP_NAME
"""The system-wide configuration directory, typically located
at /etc/docbuild."""

CONFIG_PATHS = (
    # The system-wide config path:
    SYSTEM_CONFIG_DIR,
    # The user config path:
    USER_CONFIG_DIR,
    # The current working/project directory:
    PROJECT_DIR,
)
"""The paths where the application will look for configuration files."""

APP_CONFIG_BASENAMES = ('.config.toml', 'config.toml')
"""The base filenames for the application configuration files, in
order of priority."""

PROJECT_LEVEL_APP_CONFIG_FILENAMES = (
    f'.{APP_NAME}.config.toml',
    f'{APP_NAME}.config.toml',
    # 'app.config.toml',
)
"""Additional configuration filenames at the project level."""

APP_CONFIG_FILENAME = 'config.toml'
"""The filename of the application's config file without any paths."""

ENV_CONFIG_FILENAME = 'env.{role}.toml'
"""The filename of the environment's config file without any paths."""

DEFAULT_ENV_CONFIG_FILENAME = ENV_CONFIG_FILENAME.format(role='production')
"""The default filename for the environment's config file, typically
used in production."""

GIT_CONFIG_FILENAME = Path(__file__).parent / 'etc/git/gitconfig'
"""The project-specific Git configuration file (relative to this project)"""

# --- State and Logging Constants (Refactored) ---

BASE_STATE_DIR = Path.home() / '.local' / 'state' / APP_NAME
"""The directory where application state, logs, and locks are stored,
per XDG Base Directory Specification."""

GITLOGGER_NAME = "docbuild.git"
"""The standardized name for the Git-related logger."""

BASE_LOG_DIR = BASE_STATE_DIR / 'logs'
"""The directory where log files will be stored."""

# --- Locking constants ---
BASE_LOCK_DIR = BASE_STATE_DIR / 'locks'
"""The directory where PID lock files will be stored."""

XMLDATADIR = Path(__file__).parent / 'config' / 'xml' / 'data'
"""Directory where additional files (RNC, XSLT) for XML processing are stored."""
