from pathlib import Path

import click
import pytest

from docbuild.cli.cmd_cli import cli


# Define a throwaway command just for testing context mutation
@cli.command('capture-context')
@click.pass_context
def capture_context(ctx):
    """Create a dummy command that simulates work.

    Stores final context for inspection in testing.
    """
    # We don't echo anything; we only mutate the context
    # click.echo(ctx.obj)
    pass


# Register the test-only command temporarily
cli.add_command(capture_context)


def test_showconfig_env_help_option(runner):
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
    assert '--env-config' in result.output
    # assert "[mutually_exclusive]" in result.output
    # assert "--role" in result.output


def test_showconfig_env_config_option(
    context,
    fake_envfile,
    runner,
):
    mock = fake_envfile.mock
    configfile = Path(__file__).parent / 'sample-env.toml'
    mock.return_value = (configfile, {'mocked': True})

    result = runner.invoke(
        cli,
        [
            '--env-config',
            configfile,
            'config',
            'env',
        ],
        obj=context,
    )
    assert result.exit_code == 0
    assert context.envconfigfiles == (configfile,)


@pytest.mark.skip('Replace --role with --env-config')
def test_showconfig_env_role_option(
    context,
    fake_envfile,
    runner,
):
    return_value = {
        'paths': {
            'config_dir': '/etc/docbuild',
            'repo_dir': '/data/docserv/repos/permanent-full/',
            'temp_repo_dir': '/data/docserv/repos/temporary-branches/',
            'tmp': {
                'tmp_base_dir': '/tmp',
                'tmp_dir': '/tmp/doc-example-com',
            },
        },
    }
    fake_envfile.mock.return_value = (
        fake_envfile.fakefile,
        return_value,
    )

    result = runner.invoke(
        cli,
        ['--env-config', fake_envfile.fakefile, 'config', 'env'],
        obj=context,
    )

    assert fake_envfile.mock.call_count == 1
    # assert fake_envfile.fakefile
    assert result.exit_code == 0
    assert context.envconfigfiles == (fake_envfile.fakefile.absolute(),)
    assert context.envconfig == return_value


@pytest.mark.skip('Replace --role with --env-config')
def test_env_no_config_no_role(
    context,
    fake_envfile,
    runner,
):
    mock = fake_envfile.mock
    mock.side_effect = FileNotFoundError(
        "No such file or directory: 'env.production.toml'",
    )
    result = runner.invoke(
        cli,
        ['--role=production', 'config', 'env'],
        obj=context,
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, FileNotFoundError)
    assert 'No such file or directory' in str(result.exception)
