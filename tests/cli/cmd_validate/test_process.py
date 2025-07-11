"""Tests for the XML validation process module."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from lxml import etree
import pytest

# Import the module to allow patching with patch.object
from docbuild.cli.cmd_validate import process as process_module
from docbuild.cli.cmd_validate.process import (
    process,
    process_file,
    registry,
    run_python_checks,
)
from docbuild.cli.context import DocBuildContext
from docbuild.config.xml.checks import CheckResult


@pytest.fixture
def mock_context() -> DocBuildContext:
    """Fixture for a mocked DocBuildContext."""
    context = MagicMock(spec=DocBuildContext)
    context.verbose = 3
    context.envconfig = {
        'paths': {
            'config_dir': '/fake/dir',
            'base_server_cache_dir': '/fake/cache',
        }
    }
    return context


@patch.object(
    process_module, 'validate_rng', new_callable=AsyncMock, return_value=(True, '')
)
@patch.object(process_module.asyncio, 'to_thread')
async def test_process_file_with_generic_parsing_error(
    mock_to_thread: MagicMock,
    mock_validate_rng: AsyncMock,
    mock_context: DocBuildContext,
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
):
    """Test process_file with a generic exception during parsing.

    This covers the `except Exception` block.
    """
    mock_to_thread.side_effect = ValueError('Generic test error')
    xml_file = tmp_path / 'file.xml'
    xml_file.touch()

    exit_code = await process_file(xml_file, mock_context, max_len=20)

    assert exit_code == 200
    captured = capsys.readouterr()
    assert 'Error:' in captured.err
    assert 'Generic test error' in captured.err


async def test_process_no_envconfig(mock_context: DocBuildContext):
    """Test that process raises ValueError if envconfig is missing."""
    mock_context.envconfig = None
    with pytest.raises(ValueError, match='No envconfig found in context.'):
        await process(mock_context, xmlfiles=(Path('dummy.xml'),))


@patch.object(process_module, 'process_file', new_callable=AsyncMock, return_value=0)
@patch.object(process_module, 'create_stitchfile', new_callable=AsyncMock)
async def test_process_with_stitchfile_failure(
    mock_create_stitchfile: AsyncMock,
    mock_process_file: AsyncMock,
    mock_context: DocBuildContext,
    capsys: pytest.CaptureFixture,
):
    """Test process function when create_stitchfile raises a ValueError.

    This covers the `except ValueError` block during stitch-file validation.
    """
    mock_create_stitchfile.side_effect = ValueError('Duplicate product IDs found')
    xml_files = (Path('/fake/file1.xml'),)  # Need at least one successful file

    exit_code = await process(mock_context, xmlfiles=xml_files)

    assert exit_code == 1
    captured = capsys.readouterr()
    assert 'Stitch-file validation failed:' in captured.err
    assert 'Duplicate product IDs found' in captured.err
