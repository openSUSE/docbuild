"""Tests for the retroactive LLMs generation CLI command."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from docbuild.cli.cmd_cli import cli


def test_llms_disabled() -> None:
    """Test the llms command exits safely when disabled in config."""
    runner = CliRunner()
    # Add --all so it doesn't fail the early bounds check
    result = runner.invoke(cli, ["-C", "build.build_llmstxt=false", "build", "llms", "--all"])

    assert result.exit_code == 0
    assert "LLMs generation is disabled" in result.output


def test_llms_missing_target_dir(tmp_path: Path) -> None:
    """Test the llms command fails if target directory does not exist."""
    runner = CliRunner()
    fake_dir = tmp_path / "does_not_exist"

    result = runner.invoke(
        cli,
        [
            "-C",
            "build.build_llmstxt=true",
            "-C",
            f"paths.target.target_base_dir={fake_dir}",
            "build",
            "llms",
            "--all",  # <-- Added
        ],
    )

    assert result.exit_code == 1
    assert "is not a directory" in result.output


@patch("docbuild.cli.cmd_build.cmd_llms.generate_llmstxt", new_callable=AsyncMock)
def test_llms_success_mocked(mock_generate, tmp_path: Path) -> None:
    """Test the llms command runs successfully with a valid directory."""
    runner = CliRunner()
    valid_dir = tmp_path / "valid_builds"
    valid_dir.mkdir()

    result = runner.invoke(
        cli,
        ["-C", "build.build_llmstxt=true", "-C", f"paths.target.target_base_dir={valid_dir}", "build", "llms", "--all"],
    )

    assert result.exit_code == 0
    assert "Retroactive LLMs generation completed" in result.output


def test_llms_end_to_end_execution(tmp_path: Path) -> None:
    """Test retroactive LLMs generation against real HTML files in target_base_dir."""
    runner = CliRunner()
    target_dir = tmp_path / "target_base"
    target_dir.mkdir()

    # Create dummy HTML file
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
    html_file = target_dir / "unknown" / "unknown" / "unknown" / "html" / "index.html"
    html_file.parent.mkdir(parents=True, exist_ok=True)
    html_file.write_text(sample_html, encoding="utf-8")

    result = runner.invoke(
        cli,
        [
            "-C", "build.build_llmstxt=true",
            "-C", f"paths.target.target_base_dir={target_dir}",
            "-C", "paths.llmstxt_dir=docs",
            "build", "llms", "--all",  # <-- Added
        ],
    )

    assert result.exit_code == 0
    assert "Retroactive LLMs generation completed successfully" in result.output

    # Verify Markdown file was created (uses the strict "unknown" fallback route)
    md_file = target_dir / "docs" / "unknown" / "unknown" / "unknown" / "html" / "index.md"
    assert md_file.exists()
    assert "# Introduction" in md_file.read_text(encoding="utf-8")
    assert "Core doc content." in md_file.read_text(encoding="utf-8")

    # Verify link injection in HTML
    updated_html = html_file.read_text(encoding="utf-8")
    assert '<link rel="alternate" type="text/markdown"' in updated_html

    # Verify llms.txt index was written (inside llmstxt_dir)
    index_file = target_dir / "docs" / "llms.txt"
    assert index_file.exists()


def test_build_group_help_lists_llms() -> None:
    """Verify that 'docbuild build --help' lists the llms command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["build", "--help"])
    assert result.exit_code == 0
    assert "llms" in result.output


def test_llms_preserves_html_symlinks(tmp_path: Path) -> None:
    """Test that symlinks in HTML output are preserved as symlinks in Markdown output."""
    runner = CliRunner()
    target_dir = tmp_path / "target_base"
    html_dir = target_dir / "en-us" / "sles" / "15-SP7" / "html" / "SLES-amd-sev"
    html_dir.mkdir(parents=True, exist_ok=True)

    article_file = html_dir / "article-amd-sev.html"
    article_file.write_text(
        """<!DOCTYPE html>
<html>
<head><title>AMD SEV Article</title></head>
<body><main><h1>AMD SEV Article</h1><p>Content.</p></main></body>
</html>""",
        encoding="utf-8",
    )

    symlink_file = html_dir / "index.html"
    try:
        symlink_file.symlink_to("article-amd-sev.html")
    except OSError:
        import pytest
        pytest.skip("Creating symlinks is not supported/permitted on this platform")

    result = runner.invoke(
        cli,
        [
            "-C", "build.build_llmstxt=true",
            "-C", f"paths.target.target_base_dir={target_dir}",
            "-C", "paths.llmstxt_dir=docs",
            "build", "llms", "--all",
        ],
    )

    assert result.exit_code == 0

    # 1. Target markdown file was generated
    md_file = target_dir / "docs" / "en-us" / "sles" / "15-SP7" / "html" / "SLES-amd-sev" / "article-amd-sev.md"
    assert md_file.exists()
    assert "# AMD SEV Article" in md_file.read_text(encoding="utf-8")

    # 2. Symlink was preserved in markdown directory pointing to the .md target
    dest_symlink = target_dir / "docs" / "en-us" / "sles" / "15-SP7" / "html" / "SLES-amd-sev" / "index.html"
    assert dest_symlink.is_symlink()
    assert os.readlink(dest_symlink) == "article-amd-sev.md"

    # 3. Target HTML file got alternate markdown link
    assert "/docs/en-us/sles/15-SP7/html/SLES-amd-sev/article-amd-sev.md" in article_file.read_text(encoding="utf-8")

    # 4. llms.txt has only canonical entry, no duplicate index entry
    llms_txt = (target_dir / "docs" / "llms.txt").read_text(encoding="utf-8")
    assert "/docs/en-us/sles/15-SP7/html/SLES-amd-sev/article-amd-sev.md" in llms_txt
    assert "index.md" not in llms_txt