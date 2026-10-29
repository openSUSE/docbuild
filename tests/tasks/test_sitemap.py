from pathlib import Path

import pytest

from docbuild.tasks.sitemap import generate_sitemap


@pytest.mark.asyncio
async def test_generate_sitemap(tmp_path: Path) -> None:
    """Test that sitemap correctly filters for en-us and skips errors."""

    # 1. Create a valid English HTML file
    en_dir = tmp_path / "sles" / "15" / "en-us"
    en_dir.mkdir(parents=True)
    (en_dir / "index.html").touch()

    # 2. Create error pages that should be ignored
    (en_dir / "404.html").touch()
    (en_dir / "500.html").touch()

    # 3. Create a German HTML file that should be ignored
    de_dir = tmp_path / "sles" / "15" / "de-de"
    de_dir.mkdir(parents=True)
    (de_dir / "index.html").touch()

    # Generate the sitemap
    sitemap_xml = await generate_sitemap(tmp_path, "https://docs.test.com")

    assert sitemap_xml.exists()
    content = sitemap_xml.read_text(encoding="utf-8")

    # Verify inclusions and exclusions
    assert "https://docs.test.com/sles/15/index.html" in content
    assert "de-de" not in content
    assert "404.html" not in content
    assert "500.html" not in content
