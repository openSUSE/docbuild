import ast

from docbuild.cli.cmd_config.application import app


def test_config_app(context, runner):
    context.appconfigfiles = ['/tmp/app1.toml', '/tmp/app2.toml']
    context.appconfig = {'foo': 'bar', 'baz': [1, 2, 3]}

    # Run the command with the fake context
    result = runner.invoke(app, obj=context)

    assert result.exit_code == 0
    assert (
        "# Application config files '/tmp/app1.toml, /tmp/app2.toml'" in result.output
    )

    lines = result.output.splitlines()
    pretty_dict_str = '\n'.join(lines[1:]).strip()
    # Convert to dict
    output_dict = ast.literal_eval(pretty_dict_str)
    assert output_dict == {'foo': 'bar', 'baz': [1, 2, 3]}


def test_config_app_no_config_files(context, runner):
    """Test the app command when no config files are provided."""
    context.appconfigfiles = []  # Empty list
    context.appconfig = {'default': 'config'}

    # Run the command with the fake context
    result = runner.invoke(app, obj=context)

    assert result.exit_code == 0
    assert '# No application config files provided' in result.output

    lines = result.output.splitlines()
    pretty_dict_str = '\n'.join(lines[1:]).strip()
    # Convert to dict
    output_dict = ast.literal_eval(pretty_dict_str)
    assert output_dict == {'default': 'config'}


def test_config_app_none_config_files(context, runner):
    """Test the app command when appconfigfiles is None."""
    context.appconfigfiles = None  # None value
    context.appconfig = {'empty': 'state'}

    # Run the command with the fake context
    result = runner.invoke(app, obj=context)

    assert result.exit_code == 0
    assert '# No application config files provided' in result.output

    lines = result.output.splitlines()
    pretty_dict_str = '\n'.join(lines[1:]).strip()
    # Convert to dict
    output_dict = ast.literal_eval(pretty_dict_str)
    assert output_dict == {'empty': 'state'}
