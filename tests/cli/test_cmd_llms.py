"""Tests for the llms CLI subcommand."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner
import pytest

from docbuild.cli.cmd_cli import cli
import docbuild.cli.cmd_llms as cmd_llms_module
from docbuild.cli.cmd_llms import llms
from docbuild.cli.context import DocBuildContext


@pytest.fixture
def runner() -> CliRunner:
    """Provide a Click CLI test runner."""
    return CliRunner()


def test_llms_requires_doctypes_or_all(runner: CliRunner) -> None:
    """No arguments must fail with a UsageError instead of running everything."""
    result = runner.invoke(cli, ["llms"])

    assert result.exit_code == 2
    assert "one or more doctypes" in result.output
    assert "--all" in result.output


def test_llms_all_and_doctypes_are_mutually_exclusive(runner: CliRunner) -> None:
    """Using --all together with doctypes must be rejected."""
    result = runner.invoke(cli, ["llms", "--all", "sles/16.0/en-us"])

    assert result.exit_code == 2
    assert "cannot be combined" in result.output


def test_llms_missing_envconfig(runner: CliRunner) -> None:
    """Missing environment configuration exits with code 1."""
    result = runner.invoke(llms, ["--all"], obj=DocBuildContext())

    assert result.exit_code == 1
    assert "Environment configuration not found." in result.output


def test_llms_disabled(runner: CliRunner) -> None:
    """Test the llms command exits safely when disabled in config."""
    result = runner.invoke(cli, ["-C", "build.build_llmstxt=false", "llms", "--all"])

    assert result.exit_code == 0
    assert "LLMs generation is disabled" in result.output


@patch.object(cmd_llms_module, "process_llms", new_callable=AsyncMock)
def test_llms_with_doctypes(mock_process_llms: AsyncMock, runner: CliRunner, tmp_path: Path) -> None:
    """Passing doctypes forwards them to process_llms."""
    mock_process_llms.return_value = 0

    result = runner.invoke(
        cli,
        [
            "-C", "build.build_llmstxt=true",
            "-C", f"paths.target.target_base_dir={tmp_path}",
            "llms",
            "cloudnative/rancher-ai/en-us",
        ],
    )

    assert result.exit_code == 0
    assert "Starting retroactive LLMs generation" in result.output
    assert "Retroactive LLMs generation completed successfully." in result.output
    mock_process_llms.assert_awaited_once()
    passed_doctypes = mock_process_llms.call_args.kwargs["doctypes"]
    assert passed_doctypes is not None
    assert passed_doctypes[0].product.acronym == "cloudnative"
    assert passed_doctypes[0].docset == ["rancher-ai"]


@patch.object(cmd_llms_module, "process_llms", new_callable=AsyncMock)
def test_llms_all(mock_process_llms: AsyncMock, runner: CliRunner, tmp_path: Path) -> None:
    """Passing --all forwards doctypes=None to process_llms."""
    mock_process_llms.return_value = 0

    result = runner.invoke(
        cli,
        [
            "-C", "build.build_llmstxt=true",
            "-C", f"paths.target.target_base_dir={tmp_path}",
            "llms",
            "--all",
        ],
    )

    assert result.exit_code == 0
    mock_process_llms.assert_awaited_once()
    assert mock_process_llms.call_args.kwargs["doctypes"] is None


@patch.object(cmd_llms_module, "process_llms", new_callable=AsyncMock)
def test_llms_failure_exit_code(mock_process_llms: AsyncMock, runner: CliRunner, tmp_path: Path) -> None:
    """When process_llms returns non-zero, llms exits with that code."""
    mock_process_llms.return_value = 1

    result = runner.invoke(
        cli,
        [
            "-C", "build.build_llmstxt=true",
            "-C", f"paths.target.target_base_dir={tmp_path}",
            "llms",
            "--all",
        ],
    )

    assert result.exit_code == 1
    assert "Failed to execute retroactive LLMs generation" in result.output


@patch.object(cmd_llms_module, "process_llms", new_callable=AsyncMock)
def test_llms_exception_handling(mock_process_llms: AsyncMock, runner: CliRunner, tmp_path: Path) -> None:
    """When process_llms raises an unexpected exception, llms logs and exits with code 1."""
    mock_process_llms.side_effect = RuntimeError("Unexpected boom")

    result = runner.invoke(
        cli,
        [
            "-C", "build.build_llmstxt=true",
            "-C", f"paths.target.target_base_dir={tmp_path}",
            "llms",
            "--all",
        ],
    )

    assert result.exit_code == 1
    assert "Failed to execute retroactive LLMs generation: Unexpected boom" in result.output


def test_llms_end_to_end_dc_and_prebuilt(runner: CliRunner, tmp_path: Path) -> None:
    """Test retroactive LLMs generation for both DAPS builds and prebuilt deliverables."""
    target_dir = tmp_path / "target_base"
    prebuilt_dir = tmp_path / "prebuilt_base"
    portal_xml = tmp_path / "portal.xml"

    portal_xml.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<portal schemaversion="7.0">
  <product xml:id="sles">
    <name>SUSE Linux Enterprise Server</name>
    <acronym>SLES</acronym>
    <docset xml:id="sles.16.0" path="16.0" lifecycle="supported">
      <version>16.0</version>
      <resources>
        <git remote="https://github.com/SUSE/doc-modular.git"/>
        <locale lang="en-us">
          <branch>main</branch>
          <deliverable xml:id="sles-16-admin">
            <dc file="DC-SLES-admin">
              <format html="1" pdf="0"/>
            </dc>
          </deliverable>
        </locale>
      </resources>
    </docset>
  </product>
  <product xml:id="cloudnative">
    <name>Cloud Native</name>
    <acronym>CN</acronym>
    <docset xml:id="cloudnative.rancher-ai" path="rancher-ai" lifecycle="supported">
      <version>Liz: The SUSE Rancher AI Assistant</version>
      <resources>
        <locale lang="en-us">
          <branch>main</branch>
          <deliverable xml:id="cn.rancher-ai.intro" type="prebuilt">
            <prebuilt>
              <title>Liz: The SUSE Rancher AI Assistant</title>
              <url format="html" href="/cloudnative/rancher-ai/latest/en/introduction.html"/>
            </prebuilt>
          </deliverable>
        </locale>
      </resources>
    </docset>
  </product>
</portal>
""",
        encoding="utf-8",
    )

    # 1. Create a DAPS HTML build in target_base_dir
    daps_html_dir = target_dir / "en-us" / "sles" / "16.0" / "html"
    daps_html_dir.mkdir(parents=True)
    sample_daps_html = """<!DOCTYPE html>
<html>
<head>
    <meta name="generator" content="DAPS 3.3.0">
    <title>Sample Guide</title>
</head>
<body>
    <nav class="navbar">Menu</nav>
    <main><h1>Introduction</h1><p>Core doc content.</p></main>
</body>
</html>"""
    (daps_html_dir / "index.html").write_text(sample_daps_html, encoding="utf-8")

    # 2. Create a prebuilt HTML file in prebuilt_dir
    prebuilt_html_file = prebuilt_dir / "cloudnative" / "rancher-ai" / "latest" / "en" / "introduction.html"
    prebuilt_html_file.parent.mkdir(parents=True)
    sample_prebuilt_html = """<!DOCTYPE html>
<html>
<head>
    <meta name="generator" content="Antora 3.1">
    <title>Rancher AI Intro</title>
</head>
<body>
    <div class="toolbar">Toolbar</div>
    <main><h1>Rancher AI</h1><p>Prebuilt AI content.</p></main>
</body>
</html>"""
    prebuilt_html_file.write_text(sample_prebuilt_html, encoding="utf-8")

    # Test running for the prebuilt doctype specifically
    res_prebuilt = runner.invoke(
        cli,
        [
            "-C", "build.build_llmstxt=true",
            "-C", f"paths.main_portal_config={portal_xml}",
            "-C", f"paths.target.target_base_dir={target_dir}",
            "-C", f"paths.prebuilt_dir={prebuilt_dir}",
            "-C", "paths.llmstxt_dir=docs",
            "llms",
            "cloudnative/rancher-ai/en-us",
        ],
    )
    assert res_prebuilt.exit_code == 0

    prebuilt_target = target_dir / "en-us" / "cloudnative" / "rancher-ai" / "html"
    assert (prebuilt_target / "llms.txt").exists()
    md_prebuilt = prebuilt_target / "docs" / "latest" / "en" / "introduction.md"
    assert md_prebuilt.exists()
    assert "Prebuilt AI content." in md_prebuilt.read_text(encoding="utf-8")

    # Test running with --all
    res_all = runner.invoke(
        cli,
        [
            "-C", "build.build_llmstxt=true",
            "-C", f"paths.main_portal_config={portal_xml}",
            "-C", f"paths.target.target_base_dir={target_dir}",
            "-C", f"paths.prebuilt_dir={prebuilt_dir}",
            "-C", "paths.llmstxt_dir=docs",
            "llms",
            "--all",
        ],
    )
    assert res_all.exit_code == 0

    assert (daps_html_dir / "llms.txt").exists()
    assert (daps_html_dir / "docs" / "index.md").exists()
    md_text = (daps_html_dir / "docs" / "index.md").read_text(encoding="utf-8")
    assert "Introduction" in md_text
    assert "Core doc content." in md_text
    updated_html = (daps_html_dir / "index.html").read_text(encoding="utf-8")
    assert 'rel="alternate"' in updated_html
