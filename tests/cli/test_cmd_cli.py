from pathlib import Path

import click

import docbuild.cli.cmd_cli as cli_mod
from docbuild.cli.context import DocBuildContext
from docbuild.config.app_model import AppConfig 

cli = cli_mod.cli


@click.command('capture')
@click.pass_context
def capture(ctx):
    click.echo('capture')


# Register the test-only command temporarily
cli.add_command(capture)


# --- Helper Function for AppConfig Data ---
# This creates a minimal, valid dictionary structure that the AppConfig model expects.
def get_valid_app_config_dict(data: dict) -> dict:
    """Returns a dictionary that can be validated by AppConfig."""
    # The AppConfig model requires a "logging" section, so we include a minimal, valid one
    # and merge the test-specific data into it.
    default_logging = {
        'version': 1, 
        'disable_existing_loggers': False,
        'formatters': {},
        'handlers': {},
        'loggers': {},
        'root': {},
    }
    # For testing, we just override the logging defaults with a placeholder
    # to prove the model validates and includes our test key.
    
    # NOTE: The actual data structure being asserted on needs to be adjusted
    # to match the Pydantic model's strictness. 
    return {'logging': default_logging | data.get('logging', {})}

# -------------------------------------------


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
    
    # The context is now the instantiated object we passed in, so access is clean
    assert isinstance(context.appconfig, cli_mod.AppConfig) 
    assert context.appconfig.logging.version == 1


def test_cli_with_app_and_env_config(monkeypatch, runner, tmp_path):
    # Create real temporary files for Click to validate
    app_file = tmp_path / 'app.toml'
    env_file = tmp_path / 'env.toml'
    # Add minimal valid content
    app_file.write_text('[logging]\nversion=1') 
    env_file.write_text('dummy = true')

    def fake_handle_config(user_path, *a, **kw):
        # The mock must return a dictionary that includes valid Pydantic fields.
        if str(user_path) == str(app_file):
            # We insert a specific, known value (version: 2) for assertion
            return (app_file,), {'logging': {'version': 2}}, False
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
    
    # Check for success
    assert result.exit_code == 0
    assert 'capture' in result.output.strip()

    assert context.appconfigfiles == (app_file,)
    # Assert that context.appconfig is now the validated Pydantic object
    assert isinstance(context.appconfig, AppConfig)
    # Assert the specific value that came from the mocked config file
    assert context.appconfig.logging.version == 2
    assert context.appconfig_from_defaults is False

    assert context.envconfigfiles == (env_file,)
    # Env config is still a raw dict, so this assertion remains
    assert context.envconfig == {'env_config_data': 'env_content'} 
    assert context.envconfig_from_defaults is False


def test_cli_verbose_and_debug(monkeypatch, runner, tmp_path):
    # Create a real temporary file for Click to validate
    app_file = tmp_path / 'app.toml'
    app_file.write_text('[logging]\nversion=3') # Change content for assertion

    def fake_handle_config(user_path, *a, **kw):
        if user_path == app_file:
            # Return a dict that AppConfig can validate.
            return (app_file,), {'logging': {'version': 3}}, False
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
    # Assert that context.appconfig is the validated Pydantic object
    assert isinstance(context.appconfig, AppConfig)
    assert context.appconfig.logging.version == 3 # Assert the mocked version number
    assert context.envconfig == {'env_data': 'from_default'}