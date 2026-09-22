"""Tests for the llms CLI subcommand."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from docbuild.cli.cmd_cli import cli


def test_llms_disabled() -> None:
    """Test the llms command exits safely when disabled in config."""
    runner = CliRunner()
    result = runner.invoke(cli, ["-C", "build.build_llmstxt=false", "llms"])

    assert result.exit_code == 0
    assert "LLMs generation is disabled" in result.output


def test_llms_missing_prebuilt_dir(tmp_path: Path) -> None:
    """Test the llms command fails if prebuilt_dir does not exist."""
    runner = CliRunner()
    fake_dir = tmp_path / "does_not_exist"

    result = runner.invoke(
        cli,
        ["-C", "build.build_llmstxt=true", "-C", f"paths.prebuilt_dir={fake_dir}", "llms"],
    )

    assert result.exit_code == 1
    assert "prebuilt directory does not exist" in result.output


@patch("docbuild.cli.cmd_llms.generate_llmstxt", new_callable=AsyncMock)
def test_llms_success_mocked(mock_generate, tmp_path: Path) -> None:
    """Test the llms command runs successfully with a valid directory."""
    runner = CliRunner()
    valid_dir = tmp_path / "valid_builds"
    valid_dir.mkdir()

    result = runner.invoke(
        cli,
        ["-C", "build.build_llmstxt=true", "-C", f"paths.prebuilt_dir={valid_dir}", "llms"],
    )

    assert result.exit_code == 0
    assert "Starting retroactive LLMs generation" in result.output
    assert "Retroactive LLMs generation completed successfully." in result.output
    mock_generate.assert_called_once()


def test_llms_end_to_end_execution(tmp_path: Path) -> None:
    """Test retroactive LLMs generation against real HTML files in prebuilt_dir."""
    runner = CliRunner()
    prebuilt_dir = tmp_path / "prebuilt"
    prebuilt_dir.mkdir()

    # Create dummy DAPS and Antora HTML files
    sample_html = """<!DOCTYPE html>
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
    html_file = prebuilt_dir / "index.html"
    html_file.write_text(sample_html, encoding="utf-8")

    result = runner.invoke(
        cli,
        [
            "-C", "build.build_llmstxt=true",
            "-C", f"paths.prebuilt_dir={prebuilt_dir}",
            "-C", "paths.llmstxt_dir=docs",
            "llms",
        ],
    )

    assert result.exit_code == 0
    assert (prebuilt_dir / "llms.txt").exists()
    assert (prebuilt_dir / "docs" / "index.md").exists()

    md_text = (prebuilt_dir / "docs" / "index.md").read_text(encoding="utf-8")
    assert "Introduction" in md_text
    assert "Core doc content." in md_text

    updated_html = html_file.read_text(encoding="utf-8")
    assert 'rel="alternate"' in updated_html
