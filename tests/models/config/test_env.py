"""Unit tests for the EnvConfig Pydantic models."""

from ipaddress import IPv4Address
from pathlib import Path
from typing import Any

from pydantic import ValidationError
import pytest

import docbuild.config.app as config_app_mod
from docbuild.models.config.env import EnvConfig
from docbuild.models.path import EnsureWritableDirectory

# --- Fixture Setup ---


def _mock_successful_placeholder_resolver(data: dict[str, Any]) -> dict[str, Any]:
    """Mock the placeholder resolver to return a clean, resolved dictionary."""
    resolved_data = data.copy()

    # Define resolved paths based on the EnvConfig structure
    tmp_general = "/var/tmp/docbuild/doc-example-com"

    resolved_data["paths"]["config_dir"] = "/etc/docbuild"
    resolved_data["paths"]["root_config_dir"] = "/etc/docbuild"
    resolved_data["paths"]["jinja_dir"] = "/etc/docbuild/jinja-doc-suse-com"
    resolved_data["paths"]["server_rootfiles_dir"] = (
        "/etc/docbuild/server-root-files-doc-suse-com"
    )
    resolved_data["paths"]["repo_dir"] = "/var/cache/docbuild/repos/permanent-full/"
    resolved_data["paths"]["tmp_repo_dir"] = (
        "/var/cache/docbuild/repos/temporary-branches/"
    )
    resolved_data["paths"]["base_cache_dir"] = "/var/cache/docserv"
    resolved_data["paths"]["base_server_cache_dir"] = (
        "/var/cache/docserv/doc-example-com"
    )
    resolved_data["paths"]["meta_cache_dir"] = (
        "/var/cache/docbuild/doc-example-com/meta"
    )
    resolved_data["paths"]["base_tmp_dir"] = "/var/tmp/docbuild"
    resolved_data["paths"]["tmp"]["tmp_base_dir"] = "/var/tmp/docbuild"
    resolved_data["paths"]["tmp"]["tmp_dir"] = tmp_general
    resolved_data["paths"]["tmp"]["tmp_deliverable_dir"] = tmp_general + "/deliverable"
    resolved_data["paths"]["tmp"]["tmp_metadata_dir"] = tmp_general + "/metadata"

    # Split build_dir: base is provided, dyn is optional (tested via default)
    resolved_data["paths"]["tmp"]["tmp_build_base_dir"] = tmp_general + "/build"

    resolved_data["paths"]["tmp"]["tmp_out_dir"] = tmp_general + "/out"
    resolved_data["paths"]["tmp"]["log_dir"] = tmp_general + "/log"

    # Renamed to match the updated model and use standard placeholder
    resolved_data["paths"]["tmp"]["tmp_deliverable_name_dyn"] = (
        "{{product}}_{{docset}}_{{lang}}_XXXXXX"
    )

    # Split target_dir and use placeholder requested by reviewer
    resolved_data["paths"]["target"]["target_base_dir"] = "doc@10.100.100.100:/srv/docs"
    resolved_data["paths"]["target"]["target_dir_dyn"] = "{{product}}"
    resolved_data["paths"]["target"]["backup_dir"] = Path(
        "/data/docbuild/external-builds/"
    )

    # Ensure mandatory top-level fields (like 'build') are present
    resolved_data.setdefault(
        "build",
        {
            "daps": {"command": "daps", "meta": "daps meta"},
            "container": {"container": "none"},
        },
    )

    return resolved_data


@pytest.fixture(autouse=True)
def mock_placeholder_resolution(monkeypatch):
    """Mock the replace_placeholders utility used inside EnvConfig."""
    monkeypatch.setattr(
        config_app_mod, "replace_placeholders", _mock_successful_placeholder_resolver
    )


@pytest.fixture
def mock_valid_raw_env_data(tmp_path: Path) -> dict[str, Any]:
    """Provide a minimal, valid dictionary representing env.toml data with writable paths."""

    # Create a base directory for the test inside the pytest temp folder
    base = tmp_path / "docbuild_test"
    base.mkdir()

    nested_xslt_params = {
        "external": {"js": {"onlineonly": "/docserv/res/extra.js"}},
        "show": {"edit": {"link": 1}},
        "twittercards": {"twitter": {"account": "@SUSE"}},
        "generate": {"json-ld": 1},
        "search": {"description": {"length": 118}},
        "socialmedia": {"description": {"length": 65}},
    }

    return {
        "server": {
            "name": "doc-example-com",
            "role": "production",
            "host": "127.0.0.1",
            "enable_mail": True,
        },
        "config": {
            "default_lang": "en-us",
            "languages": ["en-us", "de-de"],
            "canonical_url_domain": "https://docs.example.com",
        },
        "paths": {
            "config_dir": str(base / "config"),
            "root_config_dir": str(base / "etc/docbuild"),
            "jinja_dir": str(base / "etc/docbuild/jinja"),
            "server_rootfiles_dir": str(base / "etc/docbuild/rootfiles"),

            # These use EnsureWritableDirectory - MUST be in tmp_path
            "base_cache_dir": str(base / "cache"),
            "base_server_cache_dir": str(base / "cache/server"),
            "base_tmp_dir": str(base / "var/tmp"),
            "repo_dir": str(base / "repos/perm"),
            "tmp_repo_dir": str(base / "repos/temp"),
            "meta_cache_dir": str(base / "cache/meta"),

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
                "target_base_dir": "doc@10.100.100.100:/srv/docs",
                "target_dir_dyn": "{{product}}",
                "backup_dir": str(base / "backups"),
            },
        },
        "build": {
            "daps": {"command": "daps", "meta": "daps meta"},
            "container": {"container": "none"},
        },
        "xslt-params": nested_xslt_params,
    }


# --- Unit Test Cases ---


def test_envconfig_full_success(mock_valid_raw_env_data: dict[str, Any]):
    """Test successful validation of the entire EnvConfig schema."""
    config = EnvConfig.from_dict(mock_valid_raw_env_data)

    assert isinstance(config, EnvConfig)

    # Check type coercion for core types
    assert isinstance(config.paths.base_cache_dir, EnsureWritableDirectory)

    # Check tmp_dir instead of tmp_path
    assert config.paths.tmp.tmp_dir.is_absolute()
    assert config.paths.tmp.tmp_dir.name == "doc-example-com"

    # Verify that the default value for tmp_build_dir_dyn is correctly picked up
    assert config.paths.tmp.tmp_build_dir_dyn == "{{product}}-{{docset}}-{{lang}}"
    assert "build" in str(config.paths.tmp.tmp_build_base_dir)

    # Check XSLT params
    assert "external" in config.xslt_params
    assert isinstance(config.xslt_params["external"], dict)
    assert config.xslt_params["show"]["edit"]["link"] == 1


def test_envconfig_type_coercion_ip_host(mock_valid_raw_env_data: dict[str, Any]):
    """Test that the host field handles IPvAnyAddress correctly."""
    data = mock_valid_raw_env_data.copy()
    data["server"]["host"] = "192.168.1.1"

    config = EnvConfig.from_dict(data)

    assert isinstance(config.server.host, IPv4Address)
    assert str(config.server.host) == "192.168.1.1"


def test_envconfig_strictness_extra_field_forbid(tmp_path: Path, monkeypatch: Any):
    """Test that extra fields are forbidden on the top-level EnvConfig model."""
    monkeypatch.setattr(config_app_mod, "replace_placeholders", lambda data: data)

    paths_to_create = [
        tmp_path,
        tmp_path / "config",
        tmp_path / "deliverable",
        tmp_path / "metadata",
        tmp_path / "out",
        tmp_path / "log",
        tmp_path / "backup",
        tmp_path / "build",
    ]
    for p in paths_to_create:
        p.mkdir(exist_ok=True, parents=True)

    raw_data = {
        "build": {
            "daps": {"command": "daps", "meta": "daps meta"},
            "container": {"container": "none"},
        },
        "server": {
            "name": "D",
            "role": "production",
            "host": "1.1.1.1",
            "enable_mail": True,
        },
        "config": {
            "default_lang": "en-us",
            "languages": ["en-us"],
            "canonical_url_domain": "https://a.b",
        },
        "paths": {
            "config_dir": str(tmp_path / "config"),
            "root_config_dir": str(tmp_path),
            "jinja_dir": str(tmp_path),
            "server_rootfiles_dir": str(tmp_path),
            "repo_dir": str(tmp_path),
            "tmp_repo_dir": str(tmp_path),
            "base_cache_dir": str(tmp_path),
            "base_server_cache_dir": str(tmp_path),
            "meta_cache_dir": str(tmp_path),
            "base_tmp_dir": str(tmp_path),
            "tmp": {
                "tmp_base_dir": str(tmp_path),
                "tmp_dir": str(tmp_path),
                "tmp_deliverable_dir": str(tmp_path / "deliverable"),
                "tmp_metadata_dir": str(tmp_path / "metadata"),
                "tmp_build_base_dir": str(tmp_path / "build"),
                "tmp_out_dir": str(tmp_path / "out"),
                "log_dir": str(tmp_path / "log"),
                "tmp_deliverable_name_dyn": "{{product}}_{{docset}}_{{lang}}_XXXXXX",
            },
            "target": {
                "target_base_dir": "/srv",
                "target_dir_dyn": "{{product}}",
                "backup_dir": str(tmp_path / "backup"),
            },
        },
        "xslt-params": {"test": 1},
        "typo_section": {"key": "value"},
    }

    with pytest.raises(ValidationError) as excinfo:
        EnvConfig.from_dict(raw_data)

    locs = excinfo.value.errors()[0]["loc"]
    assert ("typo_section",) == tuple(locs)


def test_envconfig_invalid_role_fails(mock_valid_raw_env_data: dict[str, Any]):
    """Test that an invalid role string is rejected by ServerRole enum."""
    data = mock_valid_raw_env_data.copy()
    data["server"]["role"] = "testing_invalid"

    with pytest.raises(ValidationError) as excinfo:
        EnvConfig.from_dict(data)

    locs = excinfo.value.errors()[0]["loc"]
    assert ("server", "role") == tuple(locs)
