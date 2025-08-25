"""Tests for the XML validation process module."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from lxml import etree
import pytest

from docbuild.cli.cmd_validate import process as process_module
from docbuild.cli.cmd_validate.process import (
    process,
    process_file,
    registry,
    run_python_checks,
    validate_rng_lxml,
)
from docbuild.cli.context import DocBuildContext
from docbuild.config.xml.checks import CheckResult


@pytest.fixture
def mock_context() -> DocBuildContext:
    context = MagicMock(spec=DocBuildContext)
    context.verbose = 3
    context.envconfig = {
        'paths': {
            'config_dir': '/fake/dir',
            'base_server_cache_dir': '/fake/cache',
        }
    }
    context.validation_method = 'jing'
    return context


@patch.object(process_module, 'validate_rng', new_callable=AsyncMock, return_value=(True, ''))
@patch.object(process_module.etree, 'parse', side_effect=ValueError('Generic test error'))
async def test_process_file_with_generic_parsing_error(
    mock_etree_parse, mock_validate_rng, mock_context, tmp_path, capsys
):
    xml_file = tmp_path / 'file.xml'
    xml_file.touch()

    exit_code = await process_file(xml_file, mock_context, max_len=20)

    assert exit_code == 200
    mock_validate_rng.assert_awaited_once()
    mock_etree_parse.assert_called_once()
    captured = capsys.readouterr()
    assert 'Error:' in captured.err
    assert 'Generic test error' in captured.err


async def test_process_no_envconfig(mock_context):
    mock_context.envconfig = None
    with pytest.raises(ValueError, match='No envconfig found in context.'):
        await process(mock_context, xmlfiles=(Path('dummy.xml'),))


@patch.object(process_module, 'process_file', new_callable=AsyncMock, return_value=0)
@patch.object(process_module, 'create_stitchfile', new_callable=AsyncMock)
async def test_process_with_stitchfile_failure(
    mock_create_stitchfile, mock_process_file, mock_context, capsys
):
    mock_create_stitchfile.side_effect = ValueError('Duplicate product IDs found')
    xml_files = (Path('/fake/file1.xml'),)

    exit_code = await process(mock_context, xmlfiles=xml_files)

    assert exit_code == 1
    captured = capsys.readouterr()
    assert 'Stitch-file validation failed:' in captured.err
    assert 'Duplicate product IDs found' in captured.err


@patch.object(process_module, 'validate_rng_lxml', new_callable=MagicMock, return_value=(True, ''))
@patch.object(process_module, 'etree')
@patch.object(process_module, 'run_python_checks', new_callable=AsyncMock)
async def test_process_file_with_lxml_validation_success(
    mock_run_checks, mock_etree, mock_validate_lxml, mock_context, tmp_path
):
    xml_file = tmp_path / 'file.xml'
    xml_file.touch()
    mock_context.validation_method = 'lxml'
    mock_etree.parse.return_value = etree.ElementTree(etree.Element('root'))
    mock_run_checks.return_value = [(None, CheckResult(success=True))]

    exit_code = await process_file(xml_file, mock_context, max_len=20)

    assert exit_code == 0
    mock_validate_lxml.assert_called_once()
    mock_run_checks.assert_awaited_once()


@patch.object(process_module, 'validate_rng_lxml', new_callable=MagicMock, return_value=(False, 'error message'))
async def test_process_file_with_lxml_validation_failure(
    mock_validate_rng_lxml, mock_context, tmp_path
):
    xml_file = tmp_path / 'file.xml'
    xml_file.touch()
    mock_context.validation_method = 'lxml'

    exit_code = await process_file(xml_file, mock_context, max_len=20)

    assert exit_code == 10
    mock_validate_rng_lxml.assert_called_once()


async def test_process_file_with_unknown_validation_method(mock_context, tmp_path):
    xml_file = tmp_path / 'file.xml'
    xml_file.touch()
    mock_context.validation_method = 'unknown_method'

    exit_code = await process_file(xml_file, mock_context, max_len=20)

    assert exit_code == 11
