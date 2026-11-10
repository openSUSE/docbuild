from pathlib import Path
import threading
from unittest.mock import patch

import pytest

from docbuild.tasks import sitemap
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


@pytest.mark.asyncio
async def test_progress_preserves_sitemap(tmp_path: Path) -> None:
    """Progress includes excluded directories without changing output bytes."""
    for name in (
        "en-us/index.html",
        "sles/15/en-us/chapter.html",
        "de-de/index.html",
        "errors/en-us/404.html",
        "index.html",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    output = await generate_sitemap(tmp_path, "https://docs.test.com")
    expected = output.read_bytes()
    updates = []

    def report(description: str, directory: Path) -> None:
        updates.append((description, directory, threading.get_ident()))

    await generate_sitemap(tmp_path, "https://docs.test.com", on_progress=report)

    assert output.read_bytes() == expected
    assert updates[0][:2] == ("Scanning HTML files", tmp_path)
    assert updates[-1] == ("Writing sitemap.xml", tmp_path, threading.get_ident())
    scanned = {directory for description, directory, _ in updates[:-1]}
    assert scanned == {
        tmp_path,
        tmp_path / "en-us",
        tmp_path / "sles/15/en-us",
        tmp_path / "de-de",
        tmp_path / "errors/en-us",
    }
    assert all(thread != threading.get_ident() for _, _, thread in updates[:-1])
    assert b"https://docs.test.com/index.html" in expected
    assert b"https://docs.test.com/sles/15/chapter.html" in expected


@pytest.mark.asyncio
async def test_empty_sitemap_progress(tmp_path: Path) -> None:
    """An empty target still reports scanning and writing."""
    updates = []
    output = await generate_sitemap(
        tmp_path,
        "https://docs.test.com/",
        on_progress=lambda *update: updates.append(update),
    )
    assert output.exists()
    assert updates == [
        ("Scanning HTML files", tmp_path),
        ("Writing sitemap.xml", tmp_path),
    ]


@pytest.mark.asyncio
async def test_missing_target_progress(tmp_path: Path) -> None:
    """A missing target is skipped without traversal or write notifications."""
    updates = []
    target = tmp_path / "missing"
    output = await generate_sitemap(
        target, "https://docs.test.com", on_progress=lambda *args: updates.append(args)
    )
    assert output == target / "sitemap.xml"
    assert not output.exists()
    assert updates == []


@pytest.mark.asyncio
async def test_traversal_failure_propagates(tmp_path: Path) -> None:
    """Worker failures are not hidden by progress reporting."""
    with patch.object(
        sitemap, "build_sitemap_tree", side_effect=OSError("scan failed")
    ):
        with pytest.raises(OSError, match="scan failed"):
            await generate_sitemap(tmp_path, "https://docs.test.com")
