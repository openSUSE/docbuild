"""Defaults for the CLI and environment configuration.

These are hardcoded defaults for the application and environment configurations.
They are used when no configuration files are provided or when the configuration
files do not contain the necessary settings.

They can be overridden by the user through configuration files or command-line options.
"""

from ..constants import APP_NAME

DEFAULT_APP_CONFIG = {
    'debug': False,
    'role': 'production',
    'paths': {
        'config_dir': '/etc/docbuild',
        'repo_dir': '/data/docserv/repos/permanent-full/',
        'temp_repo_dir': '/data/docserv/repos/temporary-branches/',
    },
    'paths.tmp': {
        'tmp_base_dir': '/tmp',
        'tmp_dir': '{tmp_base_dir}/doc-example-com',
    },
}
"""Default configuration for the application."""

DEFAULT_ENV_CONFIG = {
    'role': 'production',
    'paths': {
        'config_dir': '/etc/docbuild',
        'repo_dir': '/data/docserv/repos/permanent-full/',
        'temp_repo_dir': '/data/docserv/repos/temporary-branches/',
    },
    'paths.tmp': {
        'tmp_base_dir': f'/var/tmp/{APP_NAME}',
        'tmp_dir': '{tmp_base_dir}/doc-example-com',
    },
}
"""Default configuration for the environment."""
