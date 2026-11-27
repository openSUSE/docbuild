"""Tests for product catalog immutability, layered [products] config, and typo checks."""

from pathlib import Path
from typing import Any

from lxml import etree  # type: ignore
import pytest

from docbuild.config.load import handle_config
from docbuild.config.xml.checks import check_unknown_product_ids
from docbuild.models.config.env import EnvConfig
from docbuild.models.product import ProductCatalog, ProductInfo
from docbuild.tasks.build.llms.generator import resolve_product_name
from docbuild.tasks.portal import run_python_checks


def _build_raw_env_data(tmp_path: Path) -> dict[str, Any]:
    """Build a minimal valid raw env config dictionary rooted under *tmp_path*."""
    base = tmp_path / "docbuild_test"
    base.mkdir(exist_ok=True)
    return {
        "general": {
            "name": "doc-example-com",
            "role": "production",
            "enable_mail": True,
            "default_lang": "en-us",
            "languages": ["en-us", "de-de"],
            "canonical_url_domain": "https://docs.example.com",
        },
        "paths": {
            "config_dir": str(base / "config"),
            "main_portal_config": str(base / "config/portal.xml"),
            "portal_rncschema": str(base / "portal-config.rnc"),
            "root_config_dir": str(base / "etc/docbuild"),
            "jinja_dir": str(base / "etc/docbuild/jinja"),
            "server_rootfiles_dir": str(base / "etc/docbuild/rootfiles"),
            "base_cache_dir": str(base / "cache"),
            "base_server_cache_dir": str(base / "cache/server"),
            "runtime_base_dir": str(base / "runtime"),
            "lock_dir": str(base / "runtime/locks"),
            "repo_dir": str(base / "repos/perm"),
            "tmp_repo_dir": str(base / "repos/temp"),
            "meta_cache_dir": str(base / "cache/meta"),
            "json_cache_dir": str(base / "cache/json"),
            "tmp": {
                "tmp_base_dir": str(base / "var/tmp"),
                "tmp_dir": "{tmp_base_dir}/doc-example-com",
                "tmp_deliverable_dir": "{tmp_dir}/deliverable/",
                "tmp_build_base_dir": "{tmp_dir}/build",
                "tmp_out_dir": "{tmp_dir}/out/",
                "log_dir": "{tmp_dir}/log",
                "tmp_metadata_dir": "{tmp_dir}/metadata",
                "tmp_deliverable_name_dyn": "{{product}}_{{docset}}_{{lang}}_XXXXXX",
            },
            "target": {
                "target_base_dir": str(base / "target"),
                "target_dir_dyn": "{{product}}",
                "backup_dir": str(base / "backups"),
            },
        },
        "build": {
            "daps": {"command": "daps", "meta": "daps meta"},
            "container": {"container": "none"},
        },
        "xslt": {
            "common": {"show.edit.link": 1},
            "html": {},
            "pdf": {},
        },
    }


def test_product_catalog_is_read_only() -> None:
    """Verify ProductCatalog exposes read-only entries and rejects mutation."""
    catalog = ProductCatalog.from_mapping({"sles": "SUSE Linux Enterprise Server"})
    assert catalog["sles"] == ProductInfo(
        acronym="sles", name="SUSE Linux Enterprise Server"
    )
    assert "sles" in catalog
    assert len(catalog) == 1

    with pytest.raises(TypeError):
        catalog._products["sles"] = ProductInfo(  # type: ignore[index]
            acronym="sles", name="Mutated"
        )


def test_layered_env_products_merge_across_files(tmp_path: Path) -> None:
    """Verify [products] merges across layered env.toml files while keeping defaults."""
    base_dir = tmp_path / "base"
    override_dir = tmp_path / "override"
    base_dir.mkdir()
    override_dir.mkdir()

    (base_dir / "env.toml").write_text(
        '[products]\nsles = "SUSE Linux Enterprise Server"\ncustom-pro = "Custom Pro"\n',
        encoding="utf-8",
    )
    (override_dir / "env.toml").write_text(
        '[products]\ncustom-pro = "Custom Pro Override"\nextra-app = "Extra App"\n',
        encoding="utf-8",
    )

    _, merged_raw, from_defaults = handle_config(
        user_path=None,
        search_dirs=[base_dir, override_dir],
        basenames=["env.toml"],
        default_config=_build_raw_env_data(tmp_path),
    )
    assert not from_defaults

    env_cfg = EnvConfig.from_dict(merged_raw)
    catalog = env_cfg.product_catalog
    assert catalog["custom-pro"].name == "Custom Pro Override"
    assert catalog["extra-app"].name == "Extra App"
    assert "sles" in catalog


def test_check_unknown_product_ids_reports_typo_and_suggestions() -> None:
    """Verify misspelled product IDs in portal XML are flagged with suggestions."""
    tree = etree.fromstring(
        b"""
        <portal schemaversion="7.0">
          <product xml:id="slse"><name>Typo Product</name></product>
        </portal>
        """
    )
    catalog = ProductCatalog.from_mapping({"sles": "SUSE Linux Enterprise Server"})

    results = list(check_unknown_product_ids(tree, catalog=catalog))
    assert len(results) == 1
    assert results[0].error_code == "unknown_product_id"
    assert "slse" in results[0].message
    assert "sles" in results[0].message


async def test_run_python_checks_accepts_custom_catalog() -> None:
    """Verify run_python_checks passes a custom catalog into product ID checks."""
    tree = etree.ElementTree(
        etree.fromstring(
            b"""
            <portal schemaversion="7.0">
              <product xml:id="acme-cloud"><name>Acme Cloud</name></product>
            </portal>
            """
        )
    )
    catalog = ProductCatalog.from_mapping({"acme-cloud": "Acme Cloud"})

    results = await run_python_checks(tree, catalog=catalog)
    unknown_id_results = [
        res for name, res in results if name == "check_unknown_product_ids"
    ]
    assert unknown_id_results == []


def test_resolve_product_name_uses_catalog_before_fallback() -> None:
    """Verify resolve_product_name prefers catalog entries and falls back cleanly."""
    catalog = ProductCatalog.from_mapping({"sles": "Custom SLES Name"})
    assert resolve_product_name("sles", catalog=catalog) == "Custom SLES Name"
    assert resolve_product_name("unlisted-id", catalog=catalog) == "unlisted-id"
