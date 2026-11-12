import logging
import os
from pathlib import Path
import threading
from unittest.mock import patch

from lxml import etree
import pytest

from docbuild.constants import SITEMAP_NS
from docbuild.tasks import sitemap
from docbuild.tasks.sitemap import generate_sitemap


@pytest.fixture
def published_html(tmp_path: Path) -> Path:
    """Create a published tree with nested HTML and unrelated assets."""
    for name in (
        "en-us/sles/15/html/guide/index.html",
        "en-us/sles/15/html/guide/chapter.html",
        "en-us/sles/15/single-html/book.html",
        "de-de/sles/15/html/guide/index.html",
        "en-us/404.html",
        "en-us/500.html",
        "en-us/sles/15/book.pdf",
        "en-us/sles/15/style.css",
        "en-us/sles/15/upper.HTML",
        "index.html",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "<!doctype html><title>Published fixture</title>", encoding="utf-8"
        )
        os.utime(path, (1704067200, 1704067200))  # 2024-01-01 UTC
    (tmp_path / "en-us/empty").mkdir()
    return tmp_path


@pytest.mark.asyncio
@pytest.mark.parametrize("language_root", [False, True])
async def test_nested_published_html(published_html: Path, language_root: bool) -> None:
    """Only eligible English HTML is indexed, with or without progress."""
    target = published_html / "en-us" if language_root else published_html
    output = await generate_sitemap(target, "https://docs.test.com")
    expected = output.read_bytes()
    updates = []
    await generate_sitemap(
        target, "https://docs.test.com", on_progress=lambda *args: updates.append(args)
    )
    assert output.read_bytes() == expected
    tree = etree.fromstring(expected)
    ns = {"s": SITEMAP_NS}
    assert set(tree.xpath("s:url/s:loc/text()", namespaces=ns)) == {
        "https://docs.test.com/sles/15/html/guide/index.html",
        "https://docs.test.com/sles/15/html/guide/chapter.html",
        "https://docs.test.com/sles/15/single-html/book.html",
    }
    assert tree.xpath("s:url/s:lastmod/text()", namespaces=ns) == ["2024-01-01"] * 3
    assert (
        "Scanning HTML files",
        published_html / "en-us/sles/15/html/guide",
    ) in updates


@pytest.mark.asyncio
async def test_empty_english_directory(tmp_path: Path) -> None:
    """The presence of en-us alone does not create sitemap entries."""
    (tmp_path / "en-us").mkdir()
    output = await generate_sitemap(tmp_path, "https://docs.test.com")
    assert len(etree.parse(output).getroot()) == 0


@pytest.mark.asyncio
async def test_html_directory_symlink(tmp_path: Path) -> None:
    """Directory symlinks are not traversed by the existing HTML discovery."""
    target = tmp_path / "target"
    (target / "en-us").mkdir(parents=True)
    prebuilt = tmp_path / "prebuilt"
    prebuilt.mkdir()
    (prebuilt / "index.html").write_text("<title>Prebuilt</title>", encoding="utf-8")
    (target / "en-us/guide").symlink_to(prebuilt, target_is_directory=True)
    output = await generate_sitemap(target, "https://docs.test.com")
    assert len(etree.parse(output).getroot()) == 0


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
@pytest.mark.parametrize("language_root", [False, True])
@pytest.mark.parametrize("relative_link", [False, True])
async def test_symlinked_english_root(tmp_path, language_root, relative_link):
    """A published language symlink indexes nested HTML using logical paths."""
    target = tmp_path / "target"
    target.mkdir()
    external = tmp_path / "external/en-us"
    for name in (
        "sles/16.0/index.html",
        "sles/16.0/html/page.html",
        "404.html",
        "500.html",
    ):
        path = external / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<title>External build</title>", encoding="utf-8")
        os.utime(path, (1704067200, 1704067200))
    destination = Path("../external/en-us") if relative_link else external
    (target / "en-us").symlink_to(destination, target_is_directory=True)
    # Another published alias must not cause a second traversal.
    (target / "alias").symlink_to(external, target_is_directory=True)
    selected = target / "en-us" if language_root else target
    output = await generate_sitemap(selected, "https://docs.test.com")
    expected = output.read_bytes()
    updates = []
    await generate_sitemap(
        selected,
        "https://docs.test.com",
        on_progress=lambda *args: updates.append(args),
    )
    assert output.read_bytes() == expected
    tree = etree.fromstring(expected)
    ns = {"s": SITEMAP_NS}
    assert sorted(tree.xpath("s:url/s:loc/text()", namespaces=ns)) == [
        "https://docs.test.com/sles/16.0/html/page.html",
        "https://docs.test.com/sles/16.0/index.html",
    ]
    assert tree.xpath("s:url/s:lastmod/text()", namespaces=ns) == ["2024-01-01"] * 2
    for directory in (target / "en-us/sles/16.0", target / "en-us/sles/16.0/html"):
        assert ("Scanning HTML files", directory) in updates


@pytest.mark.asyncio
async def test_linked_english_root_does_not_follow_nested_links(tmp_path):
    """Only the selected root link is followed; loops and escapes are skipped."""
    target = tmp_path / "target"
    target.mkdir()
    external = tmp_path / "external/en-us"
    external.mkdir(parents=True)
    (external / "index.html").write_text("<title>English</title>", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "escape.html").touch()
    (target / "en-us").symlink_to(external, target_is_directory=True)
    (external / "loop").symlink_to(external, target_is_directory=True)
    (external / "back").symlink_to(target, target_is_directory=True)
    (external / "escape").symlink_to(outside, target_is_directory=True)
    (external / "escape.html").symlink_to(outside / "escape.html")
    (external / "alias.html").symlink_to(external / "index.html")
    (external / "broken.html").symlink_to(outside / "missing.html")
    output = await generate_sitemap(target, "https://docs.test.com")
    assert etree.parse(output).xpath("//*[local-name()='loc']/text()") == [
        "https://docs.test.com/index.html"
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "destination", ["missing", "self", "cycle", "target", "ancestor", "file"]
)
async def test_invalid_english_root_link(tmp_path, destination, caplog):
    """Invalid links and roots that lead back outside the content are skipped."""
    target = tmp_path / "target"
    target.mkdir()
    link = target / "en-us"
    destinations = {
        "missing": tmp_path / "missing",
        "self": link,
        "cycle": tmp_path / "cycle",
        "target": target,
        "ancestor": tmp_path,
        "file": tmp_path / "plain-file",
    }
    (tmp_path / "plain-file").touch()
    if destination == "cycle":
        (tmp_path / "cycle").symlink_to(link)
    link.symlink_to(destinations[destination], target_is_directory=True)
    output = await generate_sitemap(target, "https://docs.test.com")
    assert len(etree.parse(output).getroot()) == 0
    warnings = [
        record.getMessage()
        for record in caplog.records
        if record.name == sitemap.__name__ and record.levelno == logging.WARNING
    ]
    if destination in {"missing", "self", "cycle"}:
        assert warnings == [f"Sitemap: Skipping broken or cyclic symlink {link}"]
    else:
        assert warnings == []


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
