"""Defaults for the CLI and environment configuration.

These are hardcoded defaults for the application and environment configurations.
They are used when no configuration files are provided or when the configuration
files do not contain the necessary settings.

They can be overridden by the user through configuration files or command-line options.
"""

from pathlib import Path

from ..constants import (
    APP_NAME,
    BASE_LOG_DIR,
    CACHE_HOME,
    CONFIG_HOME,
    DATA_HOME,
    DEFAULT_SERVER_NAME,
    RUNTIME_DIR,
    STATE_HOME,
)
from ..utils.paths import mark_cache_dir

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
    # ROOT SECTIONS MUST BE PRESENT AND VALIDATED AGAINST EnvConfig
    # Rule of thumb:
    # * Put it in cache if deleting it is safe and the app can rebuild it automatically.
    # * Put it in state if it is authoritative local state that should survive cache cleanup.
    # * Put it in tmp/runtime if it is per-run scratch space.
    "server": {
        "name": DEFAULT_SERVER_NAME,
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
        "root_config_dir": f"{CONFIG_HOME}",
        "config_dir": "{root_config_dir}/config.d",
        "main_portal_config": "{config_dir}/portal.xml",
        "portal_rncschema": "{root_config_dir}/portal-config.rnc",
        "jinja_dir": f"{DATA_HOME}/jinja",
        "server_rootfiles_dir": "{root_config_dir}/server-root-files",
        "tmp_repo_dir": f"{STATE_HOME}/repos/branches",
        "repo_dir": f"{STATE_HOME}/repos/permanent",
        "base_cache_dir": f"{CACHE_HOME}",
        "base_server_cache_dir": "{base_cache_dir}/{server.name}",
        "meta_cache_dir": "{base_server_cache_dir}/meta",
        # "base_tmp_dir": "",
        "runtime_base_dir": f"{RUNTIME_DIR}",
        "lock_dir": "{runtime_base_dir}/locks",
        "json_cache_dir": "{base_server_cache_dir}/json",
        "tmp": {
            "tmp_base_dir": f"/tmp/{APP_NAME}",
            "tmp_dir": "{tmp_base_dir}/{server.name}",
            "tmp_deliverable_dir": "{tmp_dir}/deliverable",
            "tmp_metadata_dir": "{tmp_dir}/metadata",
            "tmp_build_base_dir": "{tmp_dir}/build",
            "tmp_out_dir": "{tmp_dir}/out",
            "log_dir": BASE_LOG_DIR,
            "tmp_deliverable_name_dyn": "{{{product}}}_{{{docset}}}_{{{lang}}}_XXXXXX",
        },
        "target": {
            "target_base_dir": f"{Path.home()}/Documents/{APP_NAME}/target",
            "target_dir_dyn": "{{{product}}}",
            "backup_dir": f"{STATE_HOME}/{{server.name}}/backup",
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
