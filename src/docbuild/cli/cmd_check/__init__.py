import click

from docbuild.cli.context import DocBuildContext


@click.group(name="check")
def cmd_check() -> None:
    """Check the environment or configuration for consistency."""
    pass

@cmd_check.command(name="files")
@click.pass_obj
def check_files(ctx: DocBuildContext) -> None:
    """Verify that DC files defined in config exist in the Git repositories."""
    import asyncio

    from .process import process_check_files

    # Execute the logic via asyncio
    success = asyncio.run(process_check_files(ctx))

    if not success:
        raise click.ClickException("DC file verification failed.")
