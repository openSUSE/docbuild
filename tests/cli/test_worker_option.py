from click.testing import CliRunner

from docbuild.cli.cmd_cli import cli


def test_workers_option_integration():
    runner = CliRunner()

    # We use a command that exists but we don't care if it fails
    # due to the directory permissions seen above.
    # We are testing the CLI parsing logic here.
    result = runner.invoke(cli, ["-j", "1", "config", "show"])

    # If '-j' was invalid, exit code would be 2 (Click usage error)
    # Since it's valid, it should proceed to validation logic (exit code 1 or 0)
    assert result.exit_code != 2
    assert "no such option: -j" not in result.output

def test_workers_option_invalid_value():
    runner = CliRunner()

    # Test an invalid string that should trigger our Pydantic ValueError
    result = runner.invoke(cli, ["-j", "not-a-number", "config", "show"])

    # This should trigger our 'handle_validation_error' logic
    assert result.exit_code == 1
    assert "Invalid max_workers value" in result.output
