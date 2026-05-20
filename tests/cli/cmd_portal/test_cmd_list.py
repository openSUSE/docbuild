"""Tests for the portal list command."""

from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner
from lxml import etree  # type: ignore

from docbuild.cli.cmd_portal.cmd_list import list_cmd
from docbuild.cli.context import DocBuildContext


def test_portal_list_help() -> None:
    """Test that the help menu renders correctly for 'portal list'."""
    runner = CliRunner()
    result = runner.invoke(list_cmd, ["--help"])

    assert result.exit_code == 0
    assert "List products, docsets, and deliverables from the portal config." in result.output
    assert "Format:" in result.output
    assert "[PRODUCT]" in result.output


def test_portal_list_no_main_config(tmp_path) -> None:
    """Test that the command gracefully aborts if the portal config is missing."""
    runner = CliRunner()

    mock_ctx = DocBuildContext()
    mock_ctx.envconfig = MagicMock()
    # Point to a path that does not exist
    mock_ctx.envconfig.paths.main_portal_config.expanduser.return_value = tmp_path / "does_not_exist.xml"

    result = runner.invoke(list_cmd, obj=mock_ctx)

    assert result.exit_code != 0
    assert "Error loading XML schema:" in result.output


def test_portal_list_invalid_doctype() -> None:
    """Test that the command gracefully aborts if an invalid doctype is passed."""
    runner = CliRunner()
    mock_ctx = DocBuildContext()

    result = runner.invoke(list_cmd, ["invalid_doctype_format!"], obj=mock_ctx)

    assert result.exit_code != 0
    assert "Error parsing doctype:" in result.output


@patch("docbuild.cli.cmd_portal.cmd_list.parse_portal_config", new_callable=AsyncMock)
def test_portal_list_malformed_xml(mock_parse, tmp_path) -> None:
    """Test that the command gracefully aborts if the portal.xml contains unparseable syntax."""
    runner = CliRunner()

    # Simulate the real core function throwing a standard parsing exception
    mock_parse.side_effect = etree.XMLSyntaxError("Malformed", 1, 0, 0)

    mock_ctx = DocBuildContext()
    mock_ctx.envconfig = MagicMock()
    mock_ctx.envconfig.paths.main_portal_config.expanduser.return_value = tmp_path / "portal.xml"

    result = runner.invoke(list_cmd, obj=mock_ctx)

    assert result.exit_code != 0
    assert "Error loading XML schema:" in result.output


@patch("docbuild.cli.cmd_portal.cmd_list.parse_portal_config", new_callable=AsyncMock)
def test_portal_list_success(mock_parse, tmp_path) -> None:
    """Test that 'portal list' parses a valid configuration and displays the tree structure."""
    runner = CliRunner()

    portal_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<portal schemaversion="7.0">\n'
        '    <product id="sles">\n'
        '        <docset path="15sp4" lifecycle="supported">\n'
        '            <resources>\n'
        '                <locale lang="en-us">\n'
        '                    <deliverable id="admin_guide">\n'
        '                        <dc file="DC-admin-guide"/>\n'
        '                    </deliverable>\n'
        '                </locale>\n'
        '            </resources>\n'
        '        </docset>\n'
        '    </product>\n'
        '</portal>\n'
    )
    # Bypass complex application context dependencies by mocking the parsed tree output
    mock_parse.return_value = etree.fromstring(portal_content.encode("utf-8"))

    mock_ctx = DocBuildContext()
    mock_ctx.envconfig = MagicMock()
    mock_ctx.envconfig.paths.main_portal_config.expanduser.return_value = tmp_path / "portal.xml"

    result = runner.invoke(list_cmd, obj=mock_ctx)

    assert result.exit_code == 0, result.output
    assert "en-us" in result.output
    assert "sles" in result.output
    assert "15sp4" in result.output
    assert "admin_guide (DC-admin-guide)" in result.output


@patch("docbuild.cli.cmd_portal.cmd_list.parse_portal_config", new_callable=AsyncMock)
def test_portal_list_with_doctype_filter(mock_parse, tmp_path) -> None:
    """Test that 'portal list' successfully accepts and processes valid Doctype filtering arguments."""
    runner = CliRunner()

    portal_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<portal schemaversion="7.0">\n'
        '    <product id="sles">\n'
        '        <docset path="15sp4" lifecycle="supported">\n'
        '            <resources>\n'
        '                <locale lang="en-us">\n'
        '                    <deliverable id="admin_guide">\n'
        '                        <dc file="DC-admin-guide"/>\n'
        '                    </deliverable>\n'
        '                </locale>\n'
        '            </resources>\n'
        '        </docset>\n'
        '    </product>\n'
        '</portal>\n'
    )
    mock_parse.return_value = etree.fromstring(portal_content.encode("utf-8"))

    mock_ctx = DocBuildContext()
    mock_ctx.envconfig = MagicMock()
    mock_ctx.envconfig.paths.main_portal_config.expanduser.return_value = tmp_path / "portal.xml"

    # Use a known test-suite-approved doctype version string
    result = runner.invoke(list_cmd, ["sles/15sp4"], obj=mock_ctx)

    assert result.exit_code == 0, f"Command aborted unexpectedly. Output: {result.output}"
    assert "en-us" in result.output
    assert "sles" in result.output
    assert "15sp4" in result.output
    assert "admin_guide (DC-admin-guide)" in result.output


@patch("docbuild.cli.cmd_portal.cmd_list.parse_portal_config", new_callable=AsyncMock)
def test_portal_list_no_matching_deliverables(mock_parse, tmp_path) -> None:
    """Test that the command displays a yellow notice if filters yield zero results."""
    runner = CliRunner()

    portal_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<portal schemaversion="7.0">\n'
        '    <product id="sles">\n'
        '        <docset path="15sp4" lifecycle="supported">\n'
        '            <resources>\n'
        '                <locale lang="en-us">\n'
        '                    \n'
        '                </locale>\n'
        '            </resources>\n'
        '        </docset>\n'
        '    </product>\n'
        '</portal>\n'
    )
    mock_parse.return_value = etree.fromstring(portal_content.encode("utf-8"))

    mock_ctx = DocBuildContext()
    mock_ctx.envconfig = MagicMock()
    mock_ctx.envconfig.paths.main_portal_config.expanduser.return_value = tmp_path / "portal.xml"

    result = runner.invoke(list_cmd, obj=mock_ctx)

    assert result.exit_code == 0, result.output
    assert "No deliverables found matching the criteria." in result.output
