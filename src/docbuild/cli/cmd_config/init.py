"""Create starter configuration files from the built-in model defaults."""

from typing import Any

import click
import tomlkit
from tomlkit.items import Table

from ...constants import APP_CONFIG_FILENAME, CONFIG_HOME, DEFAULT_ENV_CONFIG_FILENAME
from ...models.config.app import AppConfig
from ...models.config.env import EnvConfig


def config_table(values: dict[str, Any]) -> Table:
    """Convert defaults to TOML, omitting unset optional values.

    TOML has no null value. Leaving these keys out preserves model defaults.

    :param values: JSON-compatible configuration defaults.
    :return: A TOML table with placeholders left intact.
    """
    table = tomlkit.table()
    for key, value in values.items():
        if value is not None:
            table.add(key, config_table(value) if isinstance(value, dict) else value)
    return table


@click.command(name="init")
@click.option("--app", is_flag=True, help="Create only application configuration.")
@click.option("--env", is_flag=True, help="Create only environment configuration.")
@click.pass_context
def init_config(ctx: click.Context, app: bool, env: bool) -> None:
    """Create default configuration in the user configuration directory.

    With no flags, create both files. Existing files are never overwritten.
    \f

    :param ctx: The Click context holding the global dry-run option.
    :param app: Create application configuration.
    :param env: Create environment configuration.
    :raises click.ClickException: If a destination exists or cannot be written.
    """  # noqa: D301 - Click requires an interpreted form-feed separator.
    create_both = not (app or env)
    configs = {}
    if app or create_both:
        configs[CONFIG_HOME / APP_CONFIG_FILENAME] = AppConfig.get_default_config()
    if env or create_both:
        configs[CONFIG_HOME / DEFAULT_ENV_CONFIG_FILENAME] = (
            EnvConfig.get_default_config(resolve_placeholders=False)
        )

    # Check all destinations before creating anything, including dangling links.
    for path in configs:
        if path.exists() or path.is_symlink():
            raise click.ClickException(f"Refusing to overwrite existing path: {path}")

    for path, values in configs.items():
        if ctx.find_root().params.get("dry_run", False):
            click.echo(f"Would create {path}")
            continue

        document = tomlkit.document()
        document.add(tomlkit.comment("Generated from Docbuild's built-in defaults."))
        document.update(config_table(values))
        content = tomlkit.dumps(document)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation also protects files created after the preflight.
            with path.open("x", encoding="utf-8") as stream:
                stream.write(content)
        except OSError as error:
            raise click.ClickException(f"Could not create {path}: {error}") from error
        click.echo(f"Created {path}")
