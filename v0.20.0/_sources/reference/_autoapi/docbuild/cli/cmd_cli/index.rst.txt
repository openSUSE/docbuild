docbuild.cli.cmd_cli
====================

.. py:module:: docbuild.cli.cmd_cli

.. autoapi-nested-parse::

   Main CLI tool for document operations.



Functions
---------

.. autoapisummary::

   docbuild.cli.cmd_cli.handle_validation_error
   docbuild.cli.cmd_cli.load_app_config
   docbuild.cli.cmd_cli.load_env_config
   docbuild.cli.cmd_cli.cli


Module Contents
---------------

.. py:function:: handle_validation_error(e: Exception, model_class: type[pydantic.BaseModel], config_files: collections.abc.Sequence[pathlib.Path] | None, verbose: int, ctx: click.Context) -> None

   Format validation errors and exit the CLI.

   Outsourced logic to avoid code duplication between App and Env config phases.
   Using Sequence[Path] ensures compatibility with both lists and tuples.

   :param e: The exception that was raised during validation.
   :param model_class: The Pydantic model class that was being validated
      (AppConfig or EnvConfig).
   :param config_files: The list of config files that were attempted to be
      loaded, used for error context.
   :param verbose: The verbosity level from the CLI options, which can be
      used to control the level of detail in the error output.
   :param ctx: The Click context, used to exit the CLI with an appropriate
      status code after handling the error.


.. py:function:: load_app_config(ctx: click.Context, app_config: pathlib.Path, max_workers: str | None) -> None

   Load and validate Application configuration.

   :param ctx: The Click context object. The result will be added to ``ctx.obj.appconfig``.
   :param app_config: The path to the application config file provided via CLI.
   :param max_workers: The max_workers value from CLI options.


.. py:function:: load_env_config(ctx: click.Context, env_config: pathlib.Path) -> None

   Load and validate Environment configuration.

   :param ctx: The Click context object. The result will be added to ``ctx.obj.envconfig``.
   :param env_config: The path to the environment config file provided via CLI.


.. py:function:: cli(ctx: click.Context, verbose: int, dry_run: bool, debug: bool, app_config: pathlib.Path, env_config: pathlib.Path, max_workers: str | None, **kwargs: dict) -> None

   Acts as a main entry point for CLI tool.

   :param ctx: The Click context object.
   :param verbose: The verbosity level.
   :param dry_run: If set, just pretend to run the command without making any changes.
   :param debug: If set, enable debug mode.
   :param app_config: Filename to the application TOML config file.
   :param env_config: Filename to a environment's TOML config file.
   :param kwargs: Additional keyword arguments.


