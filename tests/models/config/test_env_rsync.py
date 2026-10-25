"""Environment configuration for rsync exclusions."""

import tomllib

from pydantic import ValidationError
import pytest

from docbuild.constants import DEFAULT_RSYNC_EXCLUDES
from docbuild.models.config.env import EnvConfig, EnvRsync


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        ("", list(DEFAULT_RSYNC_EXCLUDES)),
        (
            '[rsync]\nexclude_extra = ["*.tmp", "drafts/"]',
            [*DEFAULT_RSYNC_EXCLUDES, "*.tmp", "drafts/"],
        ),
        ('[rsync]\nexclude = [".git/"]', [".git/"]),
        ("[rsync]\nexclude = []", []),
        ('[rsync]\nexclude = []\nexclude_extra = ["*.tmp"]', ["*.tmp"]),
    ],
)
def test_env_rsync_exclusions(settings, expected):
    """TOML may retain, extend, replace, or disable the base exclusions."""
    config = EnvConfig.from_dict(tomllib.loads(settings))
    assert config.rsync.to_options().exclude == expected


@pytest.mark.parametrize(
    "settings",
    [
        {"exclude": "*.tmp"},
        {"exclude": [42]},
        {"exclude_extra": "*.tmp"},
        {"exclude_extra": [False]},
        {"exclude": None},
        {"unknown": []},
    ],
)
def test_env_rsync_rejects_invalid_settings(settings):
    """Reject invalid types and misspelled options instead of changing policy."""
    with pytest.raises(ValidationError):
        EnvRsync.model_validate(settings)


def test_env_rsync_defaults_are_independent():
    """Changing one environment must not change another environment's policy."""
    first = EnvRsync()
    first.exclude.clear()
    first.exclude_extra.append("*.tmp")
    second = EnvRsync()
    assert second.exclude == list(DEFAULT_RSYNC_EXCLUDES)
    assert second.exclude_extra == []


def test_env_rsync_roundtrip():
    """Serialized settings preserve replacement and extension behavior."""
    config = EnvRsync(exclude=[], exclude_extra=["*.tmp"])
    restored = EnvRsync.model_validate(config.model_dump())
    assert restored.to_options().exclude == ["*.tmp"]


@pytest.mark.parametrize("field", ["exclude", "exclude_extra"])
@pytest.mark.parametrize("patterns", [[""], [" \t"], ["*.tmp", "*.tmp"]])
def test_env_rsync_rejects_blank_and_duplicate_patterns(field, patterns):
    """Reject malformed policies rather than silently passing them to rsync."""
    with pytest.raises(ValidationError, match=r"empty|whitespace|duplicates"):
        EnvRsync.model_validate({field: patterns})


@pytest.mark.parametrize(
    "settings",
    [
        {"exclude": ["*.tmp"], "exclude_extra": ["*.tmp"]},
        {"exclude_extra": [DEFAULT_RSYNC_EXCLUDES[0]]},
    ],
)
def test_env_rsync_rejects_duplicate_combined_patterns(settings):
    """Extensions may not repeat an explicit or default base pattern."""
    with pytest.raises(ValidationError, match="must not duplicate"):
        EnvRsync.model_validate(settings)


def test_env_rsync_preserves_significant_pattern_text():
    """Spaces, case, and filter syntax must reach rsync unchanged."""
    patterns = ["draft files/", " *.bak", "*.BAK ", "/drafts/**", "?.[ab]"]
    config = EnvRsync(exclude=patterns, exclude_extra=["*.bak"])
    assert config.to_options().exclude == [*patterns, "*.bak"]
