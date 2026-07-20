"""Tests for metadata cache helpers."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

import docbuild.tasks.metadata.cache as cache_mod


def _logged_message_contains(mock_log: Mock, text: str) -> bool:
    """Return True when a mocked logger received a matching format string."""
    return any(text in call.args[0] for call in mock_log.call_args_list if call.args)


class TestMetadataCacheHelpers:
    """Tests for metadata cache helper functions."""

    @pytest.mark.parametrize(
        ("template", "values", "expected"),
        [
            (
                "daps --dc-file={dcfile}",
                {"dcfile": "DC-file"},
                ["daps", "--dc-file=DC-file"],
            ),
            ("   ", {}, ValueError),
        ],
        ids=["renders_command", "empty_command"],
    )
    def test_render_command_template(self, template, values, expected) -> None:
        """Render commands and reject templates that become empty."""
        if expected is ValueError:
            with pytest.raises(ValueError):
                cache_mod.render_command_template(template, values)
            return

        assert cache_mod.render_command_template(template, values) == expected

    def test_build_metadata_output_path_override(
        self,
        deliverable,
        tmp_path: Path,
    ) -> None:
        """Allow the output path language to be overridden."""
        output_path = cache_mod.build_metadata_output_path(
            deliverable,
            tmp_path,
            lang="de-de",
        )

        assert output_path == (
            tmp_path / "de-de" / "sles" / "15-SP7" / "DC-SLES-deployment"
        )

    def test_build_metadata_output_path_missing_dcfile(self, tmp_path: Path) -> None:
        """Reject deliverables that do not define a DC file."""
        deliverable_mock = Mock()
        deliverable_mock.xml = Mock(dcfile=None)

        with pytest.raises(ValueError):
            cache_mod.build_metadata_output_path(deliverable_mock, tmp_path)

    @pytest.mark.asyncio
    async def test_write_metadata_cache_logs_oserror(
        self,
        deliverable,
        tmp_path: Path,
    ) -> None:
        """Log and return False when cache writing fails."""
        with (
            patch.object(
                cache_mod,
                "write_metadata_cache_file",
                side_effect=OSError("disk full"),
            ),
            patch.object(cache_mod.log, "warning") as mock_warning,
        ):
            result = await cache_mod.write_metadata_cache(
                tmp_path / "meta.json",
                "{}",
                deliverable,
            )

        assert result is False
        assert _logged_message_contains(mock_warning, "Failed to write metadata cache")

    def test_compile_metadata_rejects_non_object(self) -> None:
        """Only JSON objects are accepted as metadata payloads."""
        with pytest.raises(ValueError):
            cache_mod.compile_metadata("[]")

    @pytest.mark.asyncio
    async def test_read_metadata_text_branches(
        self,
        deliverable,
        tmp_path: Path,
    ) -> None:
        """Prefer cached text, then stdout, and log empty output."""
        cache_file = tmp_path / "meta.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text('{"cached": true}', encoding="utf-8")

        cached = await cache_mod.read_metadata_text("stdout text", cache_file, deliverable)
        assert cached == '{"cached": true}'

        cache_file.write_text("   ", encoding="utf-8")
        stdout_value = await cache_mod.read_metadata_text(
            "stdout text",
            cache_file,
            deliverable,
        )
        assert stdout_value == "stdout text"

        with patch.object(cache_mod.log, "error") as mock_error:
            empty_value = await cache_mod.read_metadata_text("   ", cache_file, deliverable)

        assert empty_value is None
        assert _logged_message_contains(mock_error, "DAPS metadata produced no output")

    @pytest.mark.asyncio
    async def test_read_metadata_text_logs_read_error(
        self,
        deliverable,
        tmp_path: Path,
    ) -> None:
        """Log and return None when cache reading fails."""
        with (
            patch.object(
                cache_mod,
                "read_metadata_cache_file",
                side_effect=OSError("broken fs"),
            ),
            patch.object(cache_mod.log, "error") as mock_error,
        ):
            result = await cache_mod.read_metadata_text(
                "",
                tmp_path / "meta.json",
                deliverable,
            )

        assert result is None
        assert _logged_message_contains(mock_error, "Failed to read metadata cache")

    @pytest.mark.asyncio
    async def test_ensure_metadata_cache_uses_existing_file(
        self,
        deliverable,
        tmp_path: Path,
    ) -> None:
        """Skip writes when the cache file already exists."""
        cache_file = tmp_path / "meta.json"
        cache_file.write_text("{}", encoding="utf-8")

        with patch.object(cache_mod, "write_metadata_cache", new=AsyncMock()) as mock_write:
            result = await cache_mod.ensure_metadata_cache("{}", cache_file, deliverable)

        assert result is True
        mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_parse_metadata_text_logs_error(self, deliverable) -> None:
        """Log parse failures and return None."""
        with (
            patch.object(
                cache_mod,
                "compile_metadata",
                side_effect=ValueError("bad json"),
            ),
            patch.object(cache_mod.log, "error") as mock_error,
        ):
            result = await cache_mod.parse_metadata_text("{broken}", deliverable)

        assert result is None
        assert _logged_message_contains(mock_error, "Failed to parse metadata")
