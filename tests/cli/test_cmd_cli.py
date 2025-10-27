from pathlib import Path

import click

import docbuild.cli.cmd_cli as cli_mod
from docbuild.cli.context import DocBuildContext

cli = cli_mod.cli


@click.command('capture')
@click.pass_context
def capture(ctx):
    click.echo('capture')


# Register the test-only command temporarily
cli.add_command(capture)


# --- Tests focused purely on CLI argument passing and loading flow ---

def test_cli_defaults(monkeypatch, runner, tmp_path):
    # Create a real temporary file for Click to validate
    app_file = tmp_path / 'app.toml'
    app_file.write_text('[logging]\nversion=1')

    def fake_handle_config(user_path, *a, **kw):
        # Return a simple dictionary (raw config)
        return (user_path,), {'logging': {'version': 1}}, False

    monkeypatch.setattr(cli_mod, 'handle_config', fake_handle_config)
    
    # Instantiate the context object BEFORE invoking the CLI
    context = DocBuildContext()
    
    result = runner.invoke(
        cli, 
        ['--app-config', str(app_file), 'capture'],
        obj=context # Pass the context object
    )
    
    assert result.exit_code == 0
    assert 'capture' in result.output.strip()
    
    # Assertions related to Pydantic validation and structure are now handled in test_app.py
    # We only check for successful execution.


def test_cli_with_app_and_env_config(monkeypatch, runner, tmp_path):
    # Create real temporary files for Click to validate
    app_file = tmp_path / 'app.toml'
    env_file = tmp_path / 'env.toml'
    app_file.write_text('[logging]\nversion=1') 
    env_file.write_text('dummy = true')

    def fake_handle_config(user_path, *a, **kw):
        if str(user_path) == str(app_file):
            # The CLI is responsible for loading the raw file and passing it to Pydantic
            return (app_file,), {'logging': {'version': 1}}, False
        if str(user_path) == str(env_file):
            return (env_file,), {'env_config_data': 'env_content'}, False
        return (None,), {'default_data': 'default_content'}, True

    monkeypatch.setattr(cli_mod, 'handle_config', fake_handle_config)

    context = DocBuildContext()
    result = runner.invoke(
        cli,
        [
            '--app-config',
            str(app_file),
            '--env-config',
            str(env_file),
            'capture',
        ],
        obj=context,
    )
    
    assert result.exit_code == 0
    assert 'capture' in result.output.strip()

    assert context.appconfigfiles == (app_file,)
    assert context.appconfig_from_defaults is False

    assert context.envconfigfiles == (env_file,)
    assert context.envconfig_from_defaults is False


def test_cli_verbose_and_debug(monkeypatch, runner, tmp_path):
    # Create a real temporary file for Click to validate
    app_file = tmp_path / 'app.toml'
    app_file.write_text('[logging]\nversion=1') 

    def fake_handle_config(user_path, *a, **kw):
        if user_path == app_file:
            return (app_file,), {'logging': {'version': 1}}, False
        # For the env_config call...
        return (Path('default_env.toml'),), {'env_data': 'from_default'}, True

    monkeypatch.setattr(cli_mod, 'handle_config', fake_handle_config)

    context = DocBuildContext()
    result = runner.invoke(
        cli,
        ['-vvv', '--debug', '--app-config', str(app_file), 'capture'],
        obj=context,
    )
    
    # Check for success and context variables
    assert result.exit_code == 0
    assert 'capture\n' in result.output
    assert context.verbose == 3
    assert context.debug is True
    
    assert context.appconfigfiles == (app_file,)
    # Assertions on context.appconfig structure are now handled in test_app.py
    assert context.envconfig == {'env_data': 'from_default'}