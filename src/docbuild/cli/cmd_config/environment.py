"""CLI interface to showsthe configuration of the environment files."""

import click
from rich import print 
from rich.pretty import Pretty
from rich import print_json


@click.command(
    help=__doc__,
)
@click.pass_context
def env(ctx: click.Context) -> None:
    """Subcommand to show the ENV configuration.

    :param ctx: The Click context object.
    """

    # Check if envconfigfiles is None (which it is when the default config is used)
    if ctx.obj.envconfigfiles is None:
        path = '(Default configuration used)'
    else:
        path = ', '.join(str(path) for path in ctx.obj.envconfigfiles)
        
    click.secho(f"# ENV Config file '{path}'", fg='blue')
    
    serialized_config = ctx.obj.envconfig.model_dump_json()

    print_json(serialized_config)