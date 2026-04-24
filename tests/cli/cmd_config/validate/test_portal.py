from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from docbuild.cli.cmd_config.validate.portal import validate_portal_content


@pytest.mark.asyncio
@patch("docbuild.cli.cmd_config.validate.portal.process", new_callable=AsyncMock)
async def test_validate_portal_content_calls_process(mock_process):
    """Verify that validate_portal_content extracts paths and calls process."""
    # Arrange
    mock_ctx = MagicMock()
    # Mock doctypes with valid paths
    mock_dt = MagicMock()
    mock_dt.path = "/tmp/test.xml"
    mock_ctx.doctypes = [mock_dt]

    mock_process.return_value = 0  # Success
    console = Console()

    # Act
    result = await validate_portal_content(mock_ctx, console)

    # Assert
    assert result is True
    # Ensure it converted the string/path to a Path object and passed it as a tuple
    mock_process.assert_awaited_once_with(mock_ctx, (Path("/tmp/test.xml"),))


@pytest.mark.asyncio
async def test_validate_portal_content_no_doctypes():
    """Verify it returns False immediately if no doctypes exist."""
    mock_ctx = MagicMock()
    mock_ctx.doctypes = []

    result = await validate_portal_content(mock_ctx, Console())

    assert result is False


@pytest.mark.asyncio
@patch("docbuild.cli.cmd_config.validate.portal.validate_rng", new_callable=AsyncMock)
@patch("docbuild.cli.cmd_config.validate.portal.create_stitchfile", new_callable=AsyncMock)
async def test_process_logic_success(mock_stitch, mock_rng):
    """Deep test of the process function logic now residing in portal.py."""
    from docbuild.cli.cmd_config.validate.portal import process

    # Arrange
    mock_rng.return_value = MagicMock(returncode=0)
    xml_files = (Path("file1.xml"), Path("file2.xml"))
    mock_ctx = MagicMock()

    # Act
    exit_code = await process(mock_ctx, xml_files)

    # Assert
    assert exit_code == 0
    assert mock_rng.call_count == 2
    mock_stitch.assert_awaited_once()
