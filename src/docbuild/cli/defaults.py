"""Defaults for the CLI and environment configuration.

These are hardcoded defaults for the application and environment configurations.
They are used when no configuration files are provided or when the configuration
files do not contain the necessary settings.

They can be overridden by the user through configuration files or command-line options.
"""



from ..constants import (
    APP_NAME,
    CACHE_HOME,
    CONFIG_HOME,
    STATE_HOME,
)
from ..models.config.env import EnvConfig
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


DEFAULT_ENV_CONFIG = EnvConfig.get_default_config(resolve_placeholders=False)
"""Default configuration for the environment."""


# --- Apply CACHEDIR.TAG to required directories ---
for _cache_dir in [
    CACHE_HOME,
    f"{STATE_HOME}/repos/permanent",
    f"{STATE_HOME}/repos/branches",
]:
    mark_cache_dir(_cache_dir)
