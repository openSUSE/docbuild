"""Unit tests for the EnvConfig Pydantic models."""

from pathlib import Path
from typing import Any

from pydantic import ValidationError
import pytest

import docbuild.models.config.env as env_mod
from docbuild.models.config.env import EnvConfig

# --- Fixture Setup ---


@pytest.fixture
def mock_valid_raw_env_data(tmp_path: Path) -> dict[str, Any]:
    """Provide a minimal, valid dictionary representing env.toml data with writable paths."""

    # Create a base directory for the test inside the pytest temp folder
    base = tmp_path / "docbuild_test"
    base.mkdir()

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

            # These use WritablePath - MUST be in tmp_path
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
                "target_base_dir": "/srv/docs",
                "target_dir_dyn": "{{product}}",
                "backup_dir": str(base / "backups"),
            },
        },
        "build": {
            "daps": {"command": "daps", "meta": "daps meta"},
            "container": {"container": "none"},
        },
        "xslt": {
            "common": {
                "show.edit.link": 1,
                "twittercards.twitter.account": "@SUSE",
                "generate.json-ld": 1,
                "search.description.length": 118,
                "socialmedia.description.length": 65,
            },
            "html": {
                "external.js.onlineonly": "/docserv/res/extra.js",
            },
            "pdf": {}
        }
    }


# --- Unit Test Cases ---


def test_envconfig_full_success(mock_valid_raw_env_data: dict[str, Any]):
    """Test successful validation of the entire EnvConfig schema."""
    config = EnvConfig.from_dict(mock_valid_raw_env_data)

    assert isinstance(config, EnvConfig)

    # Check type coercion for core types
    assert isinstance(config.paths.base_cache_dir, Path)

    # Check tmp_dir instead of tmp_path
    assert config.paths.tmp.tmp_dir.is_absolute()
    assert config.paths.tmp.tmp_dir.name == "doc-example-com"

    # Verify that the default value for tmp_build_dir_dyn is correctly picked up
    assert config.paths.tmp.tmp_build_dir_dyn == "{{product}}-{{docset}}-{{lang}}"
    assert "build" in str(config.paths.tmp.tmp_build_base_dir)

    # Check XSLT params
    assert "external.js.onlineonly" in config.xslt.html
    assert config.xslt.html["external.js.onlineonly"] == "/docserv/res/extra.js"
    assert config.xslt.common["show.edit.link"] == 1

    # Test serialization of LanguageCode fields back to strings
    dumped_config = config.model_dump()
    assert isinstance(dumped_config["general"]["default_lang"], str)
    assert dumped_config["general"]["default_lang"] == "en-us"
    assert isinstance(dumped_config["general"]["languages"], list)
    assert all(isinstance(lang, str) for lang in dumped_config["general"]["languages"])
    assert set(dumped_config["general"]["languages"]) == {"en-us", "de-de"}


def test_envconfig_strictness_extra_field_forbid(tmp_path: Path, monkeypatch: Any):
    """Test that extra fields are forbidden on the top-level EnvConfig model."""
    monkeypatch.setattr(env_mod, "replace_placeholders", lambda data: data)

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
        "general": {
            "name": "D",
            "role": "production",
            "enable_mail": True,
            "default_lang": "en-us",
            "languages": ["en-us"],
            "canonical_url_domain": "https://a.b",
        },
        "paths": {
            "config_dir": str(tmp_path / "config"),
            "main_portal_config": str(tmp_path / "config/portal.xml"),
            "portal_rncschema": str(tmp_path / "portal-config.rnc"),
            "root_config_dir": str(tmp_path),
            "jinja_dir": str(tmp_path),
            "server_rootfiles_dir": str(tmp_path),
            "repo_dir": str(tmp_path),
            "tmp_repo_dir": str(tmp_path),
            "base_cache_dir": str(tmp_path),
            "base_server_cache_dir": str(tmp_path),
            "meta_cache_dir": str(tmp_path),
            "json_cache_dir": str(tmp_path),
            "runtime_base_dir": str(tmp_path),
            "lock_dir": str(tmp_path),
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
        "xslt": {
            "common": {"test": 1},
            "html": {},
            "pdf": {}
        },
        "typo_section": {"key": "value"},
    }

    with pytest.raises(ValidationError) as excinfo:
        EnvConfig.from_dict(raw_data)

    locs = excinfo.value.errors()[0]["loc"]
    assert ("typo_section",) == tuple(locs)


def test_envconfig_invalid_role_fails(mock_valid_raw_env_data: dict[str, Any]):
    """Test that an invalid role string is rejected by EnvRole enum."""
    data = mock_valid_raw_env_data.copy()
    data["general"]["role"] = "testing_invalid"

    with pytest.raises(ValidationError) as excinfo:
        EnvConfig.from_dict(data)

    locs = excinfo.value.errors()[0]["loc"]
    assert ("general", "role") == tuple(locs)


def test_envconfig_unresolved_placeholder_fails(
    mock_valid_raw_env_data: dict[str, Any],
    monkeypatch
):
    """Test that an unresolved placeholder raises a ValueError."""
    from docbuild.config.app import PlaceholderResolutionError

    def mock_raise(*args, **kwargs):
        raise PlaceholderResolutionError("Unresolved placeholder")

    monkeypatch.setattr(env_mod, "replace_placeholders", mock_raise)

    data = mock_valid_raw_env_data.copy()
    # Introduce an unresolvable placeholder
    data["paths"]["jinja_dir"] = "/etc/docbuild/{UNRESOLVED_PLACEHOLDER}"

    with pytest.raises(ValueError, match="Configuration placeholder error"):
        EnvConfig.from_dict(data)


def test_envconfig_with_non_dict_input():
    """Test that passing non-dict input to the validator is handled."""
    # This covers the `else: return data` path in `_resolve_placeholders`.
    # Pydantic will then raise a ValidationError because the input is not a dict.
    with pytest.raises(ValidationError, match="Input should be a valid dictionary"):
        EnvConfig.model_validate("not a dict")


def test_env_config_invalid_placeholder_syntax(monkeypatch):
    """Ensure EnvConfig raises ValueError for malformed placeholders."""
    from docbuild.config.app import PlaceholderSyntaxError

    def mock_raise(*args, **kwargs):
        raise PlaceholderSyntaxError("Malformed placeholder syntax")

    monkeypatch.setattr(env_mod, "replace_placeholders", mock_raise)

    invalid_data = {
        "general": {"name": "test", "role": "production", "enable_mail": False, "default_lang": "en", "languages": ["en"], "canonical_url_domain": "https://example.com"},
        "paths": {
            # ... other required paths ...
            "base_server_cache_dir": "{base_cache_dir}/{general.name" # THE BUG
        },
        "build": {
            "daps": {"command": "daps", "meta": "daps metadata"},
            "container": {"container": "some-image"}
        }
    }
    # We expect a ValueError because our model validator wraps PlaceholderSyntaxError
    with pytest.raises(ValueError, match="Configuration placeholder error"):
        EnvConfig.from_dict(invalid_data)


def test_get_default_config_unresolved():
    """
    Test that get_default_config(resolve_placeholders=False) returns
    a dictionary with unresolved placeholders.
    """
    unresolved_config = EnvConfig.get_default_config(resolve_placeholders=False)
    assert isinstance(unresolved_config, dict)
    # Check for a known placeholder
    assert "{base_cache_dir}" in unresolved_config["paths"]["base_server_cache_dir"]


def _with_remote(data: dict[str, Any], server: Any, path: str | Path) -> dict[str, Any]:
    """Return a copy of *data* with the given ``[remote]`` section."""
    result = data.copy()
    result["remote"] = {"server": server, "path": str(path)}
    return result


def test_env_remote_section_omitted_gives_no_remote(
    mock_valid_raw_env_data: dict[str, Any],
) -> None:
    """Test that omitting the [remote] section leaves server and path as None."""
    config = EnvConfig.from_dict(mock_valid_raw_env_data)
    assert config.remote.server is None
    assert config.remote.path is None


@pytest.mark.parametrize(
    ("server", "expected_user", "expected_host"),
    [
        ("doc@example.com", "doc", "example.com"),
        ("docs.example.com", None, "docs.example.com"),
        ("192.0.2.10", None, "192.0.2.10"),
        ("2001:db8::1", None, "2001:db8::1"),
    ],
    ids=["user_and_host", "hostname_only", "ipv4", "ipv6"],
)
def test_env_remote_server_string_shorthand(
    mock_valid_raw_env_data: dict[str, Any],
    tmp_path: Path,
    server: str,
    expected_user: str | None,
    expected_host: str,
) -> None:
    """Test that the ``user@host`` string shorthand parses correctly."""
    data = _with_remote(mock_valid_raw_env_data, server, tmp_path / "remote")
    config = EnvConfig.from_dict(data)
    assert config.remote.server is not None
    assert config.remote.server.user == expected_user
    assert str(config.remote.server.host) == expected_host
    assert config.remote.path == (tmp_path / "remote")


def test_env_remote_table_form(
    mock_valid_raw_env_data: dict[str, Any],
    tmp_path: Path,
) -> None:
    """Test that the [remote] section accepts the structured table form."""
    data = mock_valid_raw_env_data.copy()
    data["remote"] = {
        "server": {"user": "doc", "host": "docs.example.com"},
        "path": str(tmp_path / "remote"),
    }
    config = EnvConfig.from_dict(data)
    assert config.remote.server is not None
    assert config.remote.server.user == "doc"
    assert config.remote.server.host == "docs.example.com"
    assert config.remote.path == (tmp_path / "remote")


@pytest.mark.parametrize(
    "server",
    [
        "-bad",
        "Doc@x.example.com",
        "a@b@host",
        "@example.com",
        " ",
    ],
    ids=["dash_bad_host", "uppercase_user", "double_at", "empty_user", "only_whitespace"],
)
def test_env_remote_invalid_server_rejected(
    mock_valid_raw_env_data: dict[str, Any],
    tmp_path: Path,
    server: str,
) -> None:
    """Test that invalid server values are rejected."""
    data = _with_remote(mock_valid_raw_env_data, server, tmp_path / "remote")
    with pytest.raises(ValidationError):
        EnvConfig.from_dict(data)


@pytest.mark.parametrize(
    "character",
    ["\n", "\t", "\r", " ", "\x00", "\x1f", "\x7f"],
    ids=["newline", "tab", "carriage_return", "space", "nul", "unit_separator", "del"],
)
def test_env_remote_rejects_control_characters_in_dict_user(
    mock_valid_raw_env_data: dict[str, Any],
    tmp_path: Path,
    character: str,
) -> None:
    """Test that whitespace/control chars in the dict ``user`` field are rejected."""
    data = mock_valid_raw_env_data.copy()
    data["remote"] = {
        "server": {"user": f"doc{character}", "host": "docs.example.com"},
        "path": str(tmp_path / "remote"),
    }
    with pytest.raises(ValidationError):
        EnvConfig.from_dict(data)


@pytest.mark.parametrize(
    "character",
    ["\n", "\t", "\r", " ", "\x00", "\x1f", "\x7f"],
    ids=["newline", "tab", "carriage_return", "space", "nul", "unit_separator", "del"],
)
def test_env_remote_rejects_control_characters_in_dict_host(
    mock_valid_raw_env_data: dict[str, Any],
    tmp_path: Path,
    character: str,
) -> None:
    """Test that whitespace/control chars in the dict ``host`` field are rejected."""
    data = mock_valid_raw_env_data.copy()
    data["remote"] = {
        "server": {"user": "doc", "host": f"docs.example.com{character}"},
        "path": str(tmp_path / "remote"),
    }
    with pytest.raises(ValidationError):
        EnvConfig.from_dict(data)


@pytest.mark.parametrize(
    "character",
    ["\n", "\t", "\r", " ", "\x00", "\x1f", "\x7f"],
    ids=["newline", "tab", "carriage_return", "space", "nul", "unit_separator", "del"],
)
def test_env_remote_rejects_control_characters_in_shorthand_user(
    mock_valid_raw_env_data: dict[str, Any],
    tmp_path: Path,
    character: str,
) -> None:
    """Test that whitespace/control chars in the shorthand ``user`` are rejected."""
    data = _with_remote(
        mock_valid_raw_env_data, f"doc{character}@docs.example.com", tmp_path / "remote"
    )
    with pytest.raises(ValidationError):
        EnvConfig.from_dict(data)


@pytest.mark.parametrize(
    "character",
    ["\n", "\t", "\r", " ", "\x00", "\x1f", "\x7f"],
    ids=["newline", "tab", "carriage_return", "space", "nul", "unit_separator", "del"],
)
def test_env_remote_rejects_control_characters_in_shorthand_host(
    mock_valid_raw_env_data: dict[str, Any],
    tmp_path: Path,
    character: str,
) -> None:
    """Test that whitespace/control chars in the shorthand ``host`` are rejected."""
    data = _with_remote(
        mock_valid_raw_env_data, f"doc@docs.example.com{character}", tmp_path / "remote"
    )
    with pytest.raises(ValidationError):
        EnvConfig.from_dict(data)


@pytest.mark.parametrize(
    "host",
    ["192.0.2.10", "2001:db8::1"],
    ids=["ipv4", "ipv6"],
)
def test_env_remote_dict_host_ip_address_passes(
    mock_valid_raw_env_data: dict[str, Any],
    tmp_path: Path,
    host: str,
) -> None:
    """Test that valid IP address hosts still pass (str() conversion in the validator)."""
    data = mock_valid_raw_env_data.copy()
    data["remote"] = {
        "server": {"user": "doc", "host": host},
        "path": str(tmp_path / "remote"),
    }
    config = EnvConfig.from_dict(data)
    assert config.remote.server is not None
    assert config.remote.server.user == "doc"
    assert str(config.remote.server.host) == host
    assert config.remote.path == (tmp_path / "remote")


def test_env_remote_relative_path_rejected(
    mock_valid_raw_env_data: dict[str, Any],
) -> None:
    """Test that a relative remote path is rejected."""
    data = _with_remote(mock_valid_raw_env_data, "doc@example.com", "srv/docs")
    with pytest.raises(ValidationError):
        EnvConfig.from_dict(data)


def test_env_remote_requires_both_or_neither(
    mock_valid_raw_env_data: dict[str, Any],
    tmp_path: Path,
) -> None:
    """Test that [remote] with only server or only path is rejected."""
    data = mock_valid_raw_env_data.copy()
    data["remote"] = {"server": "doc@example.com"}
    with pytest.raises(ValidationError) as excinfo:
        EnvConfig.from_dict(data)
    assert "both 'server' and 'path'" in str(excinfo.value)

    data = mock_valid_raw_env_data.copy()
    data["remote"] = {"path": str(tmp_path / "remote")}
    with pytest.raises(ValidationError) as excinfo:
        EnvConfig.from_dict(data)
    assert "both 'server' and 'path'" in str(excinfo.value)


def test_env_remote_unknown_key_rejected(
    mock_valid_raw_env_data: dict[str, Any],
) -> None:
    """Test that an unknown key inside [remote] raises a ValidationError."""
    data = mock_valid_raw_env_data.copy()
    data["remote"] = {"rsync_options": []}
    with pytest.raises(ValidationError) as excinfo:
        EnvConfig.from_dict(data)
    locs = excinfo.value.errors()[0]["loc"]
    assert ("remote", "rsync_options") == tuple(locs)


def test_env_remote_wrong_type_rejected(
    mock_valid_raw_env_data: dict[str, Any],
) -> None:
    """Test that a non-dict, non-string server value inside [remote] raises a ValidationError."""
    data = mock_valid_raw_env_data.copy()
    data["remote"] = {"server": 123}
    with pytest.raises(ValidationError) as excinfo:
        EnvConfig.from_dict(data)
    locs = excinfo.value.errors()[0]["loc"]
    assert ("remote", "server") == tuple(locs)


def test_envconfig_remote_round_trip() -> None:
    """Test that the default config round-trips through model_dump and from_dict.

    ``resolve_placeholders=False`` is required here: the default daps templates
    intentionally keep *runtime* placeholders in escaped form (``{{builddir}}``).
    ``get_default_config()`` (with resolution enabled) unescapes them to
    ``{builddir}``, and feeding that output back through ``from_dict`` tries to
    resolve ``{builddir}`` a second time and fails before any model validation.
    This is pre-existing placeholder behaviour in ``docbuild.config.app``,
    unrelated to the new ``[remote]`` section.
    """
    dumped = EnvConfig.get_default_config(resolve_placeholders=False)
    config = EnvConfig.from_dict(dumped)
    assert config.remote.server is None
    assert config.remote.path is None


def test_envconfig_remote_none_config_list_smoke(
    mock_valid_raw_env_data: dict[str, Any],
) -> None:
    """Smoke-test the 'docbuild config list' serialization path with None values."""
    from docbuild.cli.cmd_config.list import print_section

    config = EnvConfig.from_dict(mock_valid_raw_env_data)
    assert config.remote.server is None
    assert config.remote.path is None

    data = config.model_dump(mode="json")
    assert data["remote"] == {"server": None, "path": None}

    # This is exactly the code path 'docbuild config list --env' uses.
    print_section("Environment Configuration", data, "env", False, "yellow")


def test_envconfig_example_file_validates_and_enables_remote(
    example_env_toml: Path,
    mock_valid_raw_env_data: dict[str, Any],
) -> None:
    """The shipped example must validate and enable [remote] with local paths.

    The example's own [paths] use home-directory locations, so it is replaced
    with the tmp_path-based [paths] from the fixture. The [remote] section stays
    as shipped. On Windows this test fails because ``path = "/srv/docs"`` is not
    absolute there; Linux CI decides.
    """
    from docbuild.config.load import load_single_config

    raw_config = load_single_config(example_env_toml)
    raw_config["paths"] = mock_valid_raw_env_data["paths"]

    config = EnvConfig.from_dict(raw_config)

    assert config.remote.server is not None
    assert config.remote.path is not None


def test_envconfig_remote_section_from_file_loads_tmp_path(
    example_env_toml: Path,
    mock_valid_raw_env_data: dict[str, Any],
    tmp_path: Path,
) -> None:
    """A [remote] section written to tmp_path loads into EnvConfig."""
    from docbuild.config.load import load_single_config

    config_file = tmp_path / "remote.toml"
    config_file.write_text(
        "[remote]\n"
        'server = "doc@example.com"\n'
        f'path = "{(tmp_path / "remote").as_posix()}"\n'
    )

    raw_config = mock_valid_raw_env_data.copy()
    raw_config["remote"] = load_single_config(config_file)["remote"]

    config = EnvConfig.from_dict(raw_config)

    assert config.remote is not None
    assert config.remote.server is not None
    assert config.remote.server.user == "doc"
    assert str(config.remote.server.host) == "example.com"
    assert config.remote.path == (tmp_path / "remote")


@pytest.mark.parametrize(
    "value",
    [
        "user@host:/srv/docs",
        "host:/srv/docs",
        "rsync://host/module",
        "host::module",
        "ssh://host/x",
    ],
)
def test_envconfig_remote_target_base_dir_rejected(
    mock_valid_raw_env_data: dict[str, Any],
    value: str,
) -> None:
    """Test that remote-looking target_base_dir values are rejected."""
    data = mock_valid_raw_env_data.copy()
    data["paths"]["target"]["target_base_dir"] = value

    with pytest.raises(ValidationError) as excinfo:
        EnvConfig.from_dict(data)

    locs = excinfo.value.errors()[0]["loc"]
    assert ("paths", "target", "target_base_dir") == tuple(locs)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("/srv/docs", "/srv/docs"),
        ("relative/dir", "relative/dir"),
        ("~/Documents/docbuild/target", "~/Documents/docbuild/target"),
        ("my:dir", "my:dir"),
        ("a:b/c", "a:b/c"),
    ],
)
def test_envconfig_local_target_base_dir_accepted(
    mock_valid_raw_env_data: dict[str, Any],
    value: str,
    expected: str,
) -> None:
    """Test that local target_base_dir values are accepted."""
    data = mock_valid_raw_env_data.copy()
    data["paths"]["target"]["target_base_dir"] = value

    config = EnvConfig.from_dict(data)

    assert config.paths.target.target_base_dir == expected


def test_envconfig_remote_target_base_dir_error_message(
    mock_valid_raw_env_data: dict[str, Any],
) -> None:
    """Test that the rejection message mentions [remote] and the offending value."""
    data = mock_valid_raw_env_data.copy()
    data["paths"]["target"]["target_base_dir"] = "doc@example.com:/srv/docs"

    with pytest.raises(ValidationError) as excinfo:
        EnvConfig.from_dict(data)

    message = str(excinfo.value)
    assert "[remote]" in message
    assert "doc@example.com:/srv/docs" in message


def test_envconfig_target_base_dir_default_is_local(
    mock_valid_raw_env_data: dict[str, Any],
) -> None:
    """Test that omitting target_base_dir keeps a local, non-remote default."""
    from docbuild.utils.sync import is_remote_path

    data = mock_valid_raw_env_data.copy()
    del data["paths"]["target"]["target_base_dir"]

    config = EnvConfig.from_dict(data)

    assert not is_remote_path(config.paths.target.target_base_dir)
