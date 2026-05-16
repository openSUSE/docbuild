"""Tests for the XML validation process module."""

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import AsyncMock, MagicMock, patch

from lxml import etree
import pytest

from docbuild.cli.cmd_portal import process as process_module
from docbuild.cli.cmd_portal.process import (
    ValidationResult,
    process,
    validate_rng,
)
from docbuild.cli.context import DocBuildContext


@pytest.fixture
def mock_context() -> DocBuildContext:
    context = MagicMock(spec=DocBuildContext)
    context.verbose = 3
    envconfig_mock = MagicMock()
    envconfig_mock.paths.config_dir = "/fake/dir"
    envconfig_mock.paths.base_server_cache_dir = "/fake/cache"
    context.envconfig = envconfig_mock
    context.validation_method = "jing"
    return context


@patch.object(
    process_module, "run_validation",
    new_callable=AsyncMock,
)
@patch.object(
    process_module.etree, "parse", side_effect=ValueError("Generic test error")
)
async def test_process_with_generic_parsing_error(
    mock_etree_parse, mock_run_validation, mock_context, tmp_path
):
    mock_run_validation.return_value = ValidationResult(True, 0, "")
    xml_file = tmp_path / "file.xml"
    xml_file.touch()
    schema = tmp_path / "schema.rnc"

    with pytest.raises(ValueError, match="Generic test error"):
        await process(mock_context, xml_file, schema)

    mock_run_validation.assert_awaited_once()
    mock_etree_parse.assert_called_once()


@patch.object(process_module, "run_command", new_callable=AsyncMock)
async def test_validate_rng_with_idcheck_success(mock_run_command, tmp_path):
    """Test that validate_rng with idcheck=True succeeds for a valid XML."""
    mock_run_command.return_value = CompletedProcess(
        args=["fake-command"], returncode=0, stdout="", stderr=""
    )
    xml_file = tmp_path / "valid.xml"
    xml_file.touch()
    rng_schema = tmp_path / "schema.rnc"
    rng_schema.touch()

    proc = await validate_rng(xml_file, rng_schema, xinclude=False, idcheck=True)

    assert proc.returncode == 0
    assert proc.stdout == "" and proc.stderr == ""
    # Ensure -i flag is NOT passed to jing when idcheck=True
    assert "-i" not in mock_run_command.call_args.args[0]


@patch.object(process_module, "run_command", new_callable=AsyncMock)
async def test_validate_rng_with_idcheck_duplicate_failure(mock_run_command, tmp_path):
    """Test that validate_rng with idcheck=True fails for a duplicate ID."""
    mock_run_command.return_value = CompletedProcess(
        args=["fake-command"],
        returncode=1,
        stdout="",
        stderr='error: duplicate ID "test-id"',
    )
    xml_file = tmp_path / "duplicate_id.xml"
    xml_file.touch()
    rng_schema = tmp_path / "schema.rnc"
    rng_schema.touch()

    proc = await validate_rng(xml_file, rng_schema, xinclude=False, idcheck=True)

    assert proc.returncode != 0
    assert "duplicate ID" in proc.stderr
    # Ensure -i flag is NOT passed to jing when idcheck=True
    assert "-i" not in mock_run_command.call_args.args[0]


@patch.object(process_module, "run_command", new_callable=AsyncMock)
async def test_validate_rng_without_idcheck_success(mock_run_command, tmp_path):
    """Test that validate_rng with idcheck=False succeeds despite a duplicate ID."""
    mock_run_command.return_value = CompletedProcess(
        args=["fake-command"],
        returncode=0,
        stdout="",
        stderr="",
    )
    xml_file = tmp_path / "duplicate_id.xml"
    xml_file.touch()
    rng_schema = tmp_path / "schema.rnc"
    rng_schema.touch()

    proc = await validate_rng(xml_file, rng_schema, xinclude=False, idcheck=False)

    assert proc.returncode == 0
    assert proc.stdout == "" and proc.stderr == ""
    # Ensure -i flag IS passed to jing when idcheck=False
    assert "-i" in mock_run_command.call_args.args[0]


@patch.object(process_module, "display_results")
@patch.object(process_module, "run_python_checks", new_callable=AsyncMock)
async def test_run_checks_and_display_skips_render_for_empty_results(
    mock_run_python_checks, mock_display_results
):
    """No output should be rendered when no checks are registered."""
    mock_run_python_checks.return_value = []
    context = MagicMock(spec=DocBuildContext)
    context.verbose = 2

    success = await process_module.run_checks_and_display(MagicMock(), context)

    assert success is True
    mock_display_results.assert_not_called()


async def test_cache_resolved_portal_config_returns_none_without_cache_dir(tmp_path):
    """Return None when no cache directory is configured."""
    context = MagicMock(spec=DocBuildContext)
    context.envconfig = MagicMock()
    context.envconfig.paths = MagicMock()
    context.envconfig.paths.base_server_cache_dir = None

    tree = etree.ElementTree(etree.Element("portal"))

    cached_path = await process_module.cache_resolved_portal_config(
        context,
        tree,
        tmp_path / "portal.xml",
    )

    assert cached_path is None


async def test_cache_resolved_portal_config_writes_resolved_xml(tmp_path):
    """Write resolved XML when cache directory is configured."""
    cache_dir = tmp_path / "cache"
    context = MagicMock(spec=DocBuildContext)
    context.envconfig = MagicMock()
    context.envconfig.paths = MagicMock()
    context.envconfig.paths.base_server_cache_dir = str(cache_dir)

    tree = etree.ElementTree(etree.Element("portal"))
    main_portal_config = tmp_path / "portal.xml"

    cached_path = await process_module.cache_resolved_portal_config(
        context,
        tree,
        main_portal_config,
    )

    assert cached_path == Path(cache_dir) / "portal.resolved.xml"
    assert cached_path is not None and cached_path.exists()
