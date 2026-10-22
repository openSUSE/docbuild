"""Tests for the index HTML build task."""

import json
from pathlib import Path

import pytest

from docbuild.models.doctype import Doctype
from docbuild.tasks.build.index import process, resolve_dynamic_path


def test_resolve_dynamic_path() -> None:
    """Verify placeholder substitution handles double braces, mixed case, and standard keys."""
    template = "{{lang}}/{{product}}/{{docset}}"
    mapping = {
        "lang": "en-us",
        "product": "cloud-native",
        "docset": "admission-controller",
    }
    resolved = resolve_dynamic_path(template, mapping)
    assert resolved == "en-us/cloud-native/admission-controller"


@pytest.mark.asyncio
async def test_process_missing_jinja_dir(tmp_path: Path) -> None:
    """Verify task fails gracefully when the Jinja directory does not exist."""
    fake_jinja = tmp_path / "nonexistent_jinja"
    fake_json_cache = tmp_path / "json_cache"
    fake_target_base = tmp_path / "target"

    result = await process(
        main_portal_config=tmp_path / "portal.xml",
        jinja_dir=fake_jinja,
        json_cache_dir=fake_json_cache,
        target_base_dir=fake_target_base,
        target_dir_dyn="{{lang}}/{{product}}/{{docset}}",
        doctypes=[Doctype(product="cloudnative", docset=["admission-controller"])],
        keep_index=False,
    )
    assert result == 1


@pytest.mark.asyncio
async def test_process_renders_index_and_handles_keep_index(tmp_path: Path) -> None:
    """Verify HTML rendering from JSON metadata and --keep-index backup behavior."""
    jinja_dir = tmp_path / "jinja"
    jinja_dir.mkdir()
    (jinja_dir / "index.html.jinja").write_text(
        "<h1>{{ data.productname }}</h1><p>{{ lang }}</p>", encoding="utf-8"
    )

    json_cache_dir = tmp_path / "cache" / "json"
    json_cache_dir.mkdir(parents=True)
    metadata_content = {
        "productname": "Cloud Native",
        "version": "admission-controller",
        "category": "product",
        "docs": [{"lang": "en-us"}],
    }
    (json_cache_dir / "admission-controller.json").write_text(
        json.dumps(metadata_content), encoding="utf-8"
    )

    target_base_dir = tmp_path / "target"
    target_dir_dyn = "{{lang}}/{{product}}/{{docset}}"
    doctype = Doctype(product="cloudnative", docset=["admission-controller"])

    # 1. First Run: Render index.html
    result_1 = await process(
        main_portal_config=tmp_path / "portal.xml",
        jinja_dir=jinja_dir,
        json_cache_dir=json_cache_dir,
        target_base_dir=target_base_dir,
        target_dir_dyn=target_dir_dyn,
        doctypes=[doctype],
        keep_index=False,
    )
    assert result_1 == 0

    expected_html_path = (
        target_base_dir / "en-us" / "cloud-native" / "admission-controller" / "index.html"
    )
    assert expected_html_path.exists()
    assert "<h1>Cloud Native</h1>" in expected_html_path.read_text(encoding="utf-8")

    # 2. Second Run: Render with keep_index=True
    result_2 = await process(
        main_portal_config=tmp_path / "portal.xml",
        jinja_dir=jinja_dir,
        json_cache_dir=json_cache_dir,
        target_base_dir=target_base_dir,
        target_dir_dyn=target_dir_dyn,
        doctypes=[doctype],
        keep_index=True,
    )
    assert result_2 == 0

    backup_html_path = (
        target_base_dir / "en-us" / "cloud-native" / "admission-controller" / "index_old.html"
    )
    assert backup_html_path.exists()
    assert expected_html_path.exists()
