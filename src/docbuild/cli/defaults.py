"""Defaults for the CLI and environment configuration.

These are hardcoded defaults for the application and environment configurations.
They are used when no configuration files are provided or when the configuration
files do not contain the necessary settings.

They can be overridden by the user through configuration files or command-line options.
"""

from ..constants import APP_NAME

DEFAULT_APP_CONFIG = {
    "debug": False,
    "role": "production",
    "paths": {
        "config_dir": "/etc/docbuild",
        "repo_dir": "/data/docserv/repos/permanent-full/",
        "tmp_repo_dir": "/data/docserv/repos/temporary-branches/",
    },
    "paths.tmp": {
        "tmp_base_dir": "/tmp",
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
        "config_dir": "/etc/docbuild",
        "root_config_dir": "/etc/docbuild",
        "jinja_dir": "/etc/docbuild/jinja",
        "server_rootfiles_dir": "/etc/docbuild/root-files",
        "tmp_repo_dir": "/data/docserv/repos/temporary-branches/",
        "base_cache_dir": "/var/cache/docserv",
        "base_server_cache_dir": "/var/cache/docserv/default",
        "meta_cache_dir": "/var/cache/docserv/default/meta",
        "base_tmp_dir": f"/var/tmp/{APP_NAME}",
        "tmp": {
            "tmp_base_dir": f"/var/tmp/{APP_NAME}",
            "tmp_dir": "{tmp_base_dir}/default-local",
            "tmp_deliverable_dir": "{tmp_dir}/deliverable",
            "tmp_metadata_dir": "{tmp_dir}/metadata",
            # build_dir has become build_base_dir + dir_dyn
            "tmp_build_base_dir": "{tmp_dir}/build",
            "tmp_out_dir": "{tmp_dir}/out",
            "log_dir": "{tmp_dir}/log",
            # deliverable_name has become name_dyn
            "tmp_deliverable_name_dyn": "{{product}}_{{docset}}_{{lang}}_XXXXXX",
        },
        "target": {
            # target_dir has become base_dir + dir_dyn
            "target_base_dir": "file:///tmp/docbuild/target",
            "target_dir_dyn": "{{product}}",
            "backup_dir": "/tmp/docbuild/backup",
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
