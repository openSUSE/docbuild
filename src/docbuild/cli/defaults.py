"""Defaults for the CLI and environment configuration.

These are hardcoded defaults for the application and environment configurations.
They are used when no configuration files are provided or when the configuration
files do not contain the necessary settings.

They can be overridden by the user through configuration files or command-line options.
"""

import os
from pathlib import Path

import platformdirs

from ..constants import APP_NAME
from ..utils.paths import mark_cache_dir

# --- XDG Base Directory Setup ---
CONFIG_HOME = platformdirs.user_config_dir(APP_NAME)
DATA_HOME = platformdirs.user_data_dir(APP_NAME)
STATE_HOME = platformdirs.user_state_dir(APP_NAME)
CACHE_HOME = platformdirs.user_cache_dir(APP_NAME)

# Dynamically resolve POSIX runtime dir (/run/user/1000/docbuild)
RUNTIME_DIR = platformdirs.user_runtime_dir(APP_NAME)


DEFAULT_APP_CONFIG = {
    "debug": False,
    "role": "production",
    "max_workers": "half",
    "paths": {
        "config_dir": f"{CONFIG_HOME}/config.d",
        "": "",
        "repo_dir": f"{STATE_HOME}/repos/permanent",
        "tmp_repo_dir": f"{STATE_HOME}/repos/branches",
    },
    "paths.tmp": {
        "tmp_base_dir": f"/tmp/{APP_NAME}",
        "tmp_dir": "{tmp_base_dir}/doc-example-com",
    },
}
"""Default configuration for the application."""

# --- FIXED DEFAULT_ENV_CONFIG ---
DEFAULT_ENV_CONFIG = {
    # 1. ROOT SECTIONS MUST BE PRESENT AND VALIDATED AGAINST EnvConfig
    "server": {
        "name": "default-local-env",
        "role": "production",
        "host": "127.0.0.1",
        "enable_mail": False,
    },
    "config": {
        "default_lang": "en-us",
        "languages": ["en-us"],
        "canonical_url_domain": "http://localhost/",
    },
    "paths": {
        "config_dir": f"{CONFIG_HOME}/config.d",
        "main_portal_config": f"{CONFIG_HOME}/config.d/portal.xml",
        "root_config_dir": f"{CONFIG_HOME}",
        "jinja_dir": f"{DATA_HOME}/jinja",
        "server_rootfiles_dir": f"{CONFIG_HOME}/server-root-files",
        "tmp_repo_dir": f"{STATE_HOME}/repos/branches",
        "repo_dir": f"{STATE_HOME}/repos/permanent",
        "base_cache_dir": f"{CACHE_HOME}",
        "base_server_cache_dir": f"{CACHE_HOME}/default",
        "meta_cache_dir": f"{CACHE_HOME}/default/meta",
        "base_tmp_dir": RUNTIME_DIR,
        "tmp": {
            "tmp_base_dir": f"/tmp/{APP_NAME}",
            "tmp_dir": "{tmp_base_dir}/default-local",
            "tmp_deliverable_dir": "{tmp_dir}/deliverable",
            "tmp_metadata_dir": f"{STATE_HOME}/metadata",
            "tmp_build_base_dir": f"{CACHE_HOME}/build",
            "tmp_out_dir": "{tmp_dir}/out",
            "log_dir": f"{STATE_HOME}/log",
            "tmp_deliverable_name_dyn": "{{product}}_{{docset}}_{{lang}}_XXXXXX",
        },
        "target": {
            "target_base_dir": f"{Path.home()}/Documents/{APP_NAME}/target",
            "target_dir_dyn": "{{product}}",
            "backup_dir": f"{STATE_HOME}/backup",
        },
    },
    "build": {
        "daps": {
            "command": "daps",
            "meta": "daps metadata",
        },
        "container": {
            "container": "none",
        },
    },
    "xslt-params": {},
}
"""Default configuration for the environment."""

# --- Apply CACHEDIR.TAG to required directories ---
for _cache_dir in [
    CACHE_HOME,
    f"{STATE_HOME}/repos/permanent",
    f"{STATE_HOME}/repos/branches",
]:
    mark_cache_dir(_cache_dir)
