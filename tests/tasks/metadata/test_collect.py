"""Tests for metadata collection helpers."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from docbuild.cli.context import DocBuildContext
from docbuild.models.deliverable.translation import TranslationInfo
from docbuild.models.language import LanguageCode
from docbuild.models.manifest import Document
import docbuild.tasks.metadata.cache as cache_mod
import docbuild.tasks.metadata.collect as collect_mod
from docbuild.tasks.metadata.collect import collect_dynamic_metadata
from docbuild.tasks.metadata.manifest import build_document_for_deliverable
from docbuild.utils.concurrency import TaskFailedError


def _logged_message_contains(mock_log: Mock, text: str) -> bool:
    """Return True when a mocked logger received a matching format string."""
    return any(text in call.args[0] for call in mock_log.call_args_list if call.args)


@pytest.mark.asyncio
class TestCollectDynamicMetadata:
    """Tests for the collect_dynamic_metadata function."""

    def test_translation_jobs_and_limit(self, deliverable) -> None:
        """Sort translation jobs by language and bound translation concurrency."""
        deliverable.__dict__["translations"] = {
            LanguageCode(language="fr-fr"): TranslationInfo(
                LanguageCode(language="fr-fr"),
                branch="stable",
                subdir="l10n/sles/fr-fr",
            ),
            LanguageCode(language="de-de"): TranslationInfo(
                LanguageCode(language="de-de"),
                branch=None,
                subdir=None,
            ),
        }

        jobs = collect_mod._translation_jobs(deliverable)
        limit = collect_mod._translation_limit(
            Mock(appconfig=Mock(max_workers=5)),
            len(jobs),
        )

        assert [str(info.lang) for info, _, _ in jobs] == ["de-de", "fr-fr"]
        assert jobs[0][1] == deliverable.branch
        assert jobs[0][2] == deliverable.subdir
        assert limit == 2

    @pytest.fixture
    def setup_paths(self, tmp_path: Path) -> dict[str, Path]:
        """Set up common paths and directories for tests."""
        paths = {
            "repo_dir": tmp_path / "repos",
            "tmp_repo_dir": tmp_path / "tmp_repos",
            "base_cache_dir": tmp_path / "cache",
            "meta_cache_dir": tmp_path / "cache" / "metadata",
            "json_cache_dir": tmp_path / "cache" / "json",
        }
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
        return paths

    @pytest.mark.parametrize(
        "scenario, expected_result, expected_log",
        [
            ("success", True, None),
            ("worktree_missing", False, "Worktree not found"),
            ("daps_fails", False, "DAPS metadata failed"),
            ("invalid_json", False, "Failed to parse metadata"),
        ],
        ids=["success", "worktree_missing", "daps_fails", "invalid_json"],
    )
    @patch.object(collect_mod, "run_command", new_callable=AsyncMock)
    async def test_collect_dynamic_metadata_scenarios(
        self,
        mock_run_command: AsyncMock,
        deliverable,
        setup_paths: dict[str, Path],
        scenario: str,
        expected_result: bool,
        expected_log: str | None,
    ):
        """Test various scenarios for collect_dynamic_metadata."""
        repo_url = deliverable.git.url
        worktrees = {
            (repo_url, deliverable.branch): setup_paths["tmp_repo_dir"] / "shared"
        }

        metadata_payload = {"docs": [{"rootid": "doc-root", "title": "Doc"}]}
        mock_run_command.return_value = Mock(
            returncode=0,
            stdout=json.dumps(metadata_payload),
            stderr="",
        )

        if scenario == "worktree_missing":
            worktrees = {}
        elif scenario == "daps_fails":
            mock_run_command.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="DAPS Error",
            )
        elif scenario == "invalid_json":
            mock_run_command.return_value = Mock(
                returncode=0,
                stdout="{ not json }",
                stderr="",
            )

        mock_envconfig = Mock()
        mock_paths = Mock()
        mock_paths.repo_dir = setup_paths["repo_dir"]
        mock_paths.tmp_repo_dir = setup_paths["tmp_repo_dir"]
        mock_paths.meta_cache_dir = setup_paths["meta_cache_dir"]
        mock_paths.json_cache_dir = setup_paths["json_cache_dir"]
        mock_envconfig.paths = mock_paths
        mock_envconfig.build = Mock()
        mock_envconfig.build.daps.meta = "daps --dc-file={dcfile} --output={output}"

        mock_context = Mock(spec=DocBuildContext)
        mock_context.envconfig = mock_envconfig

        logger = cache_mod.log if scenario == "invalid_json" else collect_mod.log

        with patch.object(logger, "error") as mock_error:
            success, res_deliverable = await collect_dynamic_metadata(
                context=mock_context,
                deliverable=deliverable,
                meta_cache_dir=setup_paths["meta_cache_dir"],
                worktrees=worktrees,
            )

        assert success is expected_result
        assert res_deliverable == deliverable

        if expected_result:
            assert deliverable.document is not None
            metafile = deliverable.metafile
            assert metafile is not None
            dcfile = deliverable.xml.dcfile
            assert dcfile is not None
            assert dcfile in metafile
        else:
            assert deliverable.document is None

        if expected_log:
            assert _logged_message_contains(mock_error, expected_log)

        if scenario == "worktree_missing":
            mock_run_command.assert_not_called()

    @pytest.mark.parametrize(
        ("translation_result", "expected_success", "expected_docs"),
        [
            (
                TaskFailedError(
                    (TranslationInfo(LanguageCode(language="de-de")), "main", "l10n"),
                    RuntimeError("boom"),
                ),
                False,
                1,
            ),
            (
                (TranslationInfo(LanguageCode(language="de-de")), None),
                False,
                1,
            ),
            (
                (
                    TranslationInfo(LanguageCode(language="de-de")),
                    Document.from_metadata_payload(
                        {"docs": [{"rootid": "translated-root", "title": "Translated"}]},
                        dcfile="DC-SLES-deployment",
                        lang="de-de",
                    ),
                ),
                True,
                2,
            ),
        ],
        ids=["task_failed", "translation_missing_doc", "translation_merged"],
    )
    async def test_collect_dynamic_metadata_translation_outcomes(
        self,
        deliverable,
        tmp_path: Path,
        translation_result,
        expected_success: bool,
        expected_docs: int,
    ) -> None:
        """Verify translation aggregation handles failures and merged docs."""
        base_document = build_document_for_deliverable(
            deliverable,
            {"docs": [{"rootid": "base-root", "title": "Base"}]},
        )
        deliverable.__dict__["translations"] = {
            LanguageCode(language="de-de"): TranslationInfo(
                LanguageCode(language="de-de"),
                branch="main",
                subdir="l10n/sles/de-de",
            )
        }

        async def fake_run_parallel(items, worker_fn, limit):
            del items, worker_fn, limit
            yield translation_result

        with (
            patch.object(
                collect_mod,
                "_collect_language_metadata",
                new=AsyncMock(return_value=(base_document, tmp_path / "meta.json", True)),
            ),
            patch.object(collect_mod, "run_parallel", new=fake_run_parallel),
        ):
            success, updated = await collect_dynamic_metadata(
                Mock(envconfig=Mock(), appconfig=Mock(max_workers=2)),
                deliverable,
                meta_cache_dir=tmp_path,
                worktrees={(deliverable.git.url, deliverable.branch): tmp_path},
            )

        assert success is expected_success
        assert updated.document is not None
        assert len(updated.document.docs) == expected_docs

    async def test_collect_language_metadata_build_path_error(
        self,
        deliverable,
        tmp_path: Path,
    ) -> None:
        """Return a failed result when metadata output path construction fails."""
        context = Mock()
        context.envconfig = Mock()
        context.envconfig.build = Mock()
        context.envconfig.build.daps.meta = "daps {dcfile}"

        with (
            patch.object(
                collect_mod,
                "build_metadata_output_path",
                side_effect=ValueError("missing dcfile"),
            ),
            patch.object(collect_mod.log, "error") as mock_error,
        ):
            document, output_path, wrote_cache = await collect_mod._collect_language_metadata(
                context,
                deliverable,
                deliverable.git.url,
                "DC-SLES-deployment",
                meta_cache_dir=tmp_path,
                worktrees={(deliverable.git.url, deliverable.branch): tmp_path},
                lang=deliverable.xml.lang,
                branch=deliverable.branch,
                subdir=deliverable.subdir,
            )

        assert document is None
        assert output_path is None
        assert wrote_cache is False
        assert _logged_message_contains(mock_error, "Failed to build metadata path")

    async def test_collect_language_metadata_parse_and_document_failures(
        self,
        deliverable,
        tmp_path: Path,
    ) -> None:
        """Propagate cache state through parse and document build failures."""
        context = Mock()
        context.envconfig = Mock()
        context.envconfig.build = Mock()
        context.envconfig.build.daps.meta = "daps {dcfile}"
        output_path = tmp_path / "meta.json"

        with (
            patch.object(
                collect_mod,
                "build_metadata_output_path",
                return_value=output_path,
            ),
            patch.object(
                collect_mod,
                "run_command",
                new=AsyncMock(return_value=Mock(returncode=0, stdout="{}", stderr="")),
            ),
            patch.object(
                collect_mod,
                "read_metadata_text",
                new=AsyncMock(return_value="{}"),
            ),
            patch.object(
                collect_mod,
                "ensure_metadata_cache",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                collect_mod,
                "parse_metadata_text",
                new=AsyncMock(return_value=None),
            ),
        ):
            document, returned_path, wrote_cache = await collect_mod._collect_language_metadata(
                context,
                deliverable,
                deliverable.git.url,
                deliverable.xml.dcfile,
                meta_cache_dir=tmp_path,
                worktrees={(deliverable.git.url, deliverable.branch): tmp_path},
                lang=deliverable.xml.lang,
                branch=deliverable.branch,
                subdir=deliverable.subdir,
            )

        assert document is None
        assert returned_path == output_path
        assert wrote_cache is True

    async def test_collect_language_metadata_command_exception(
        self,
        deliverable,
        tmp_path: Path,
    ) -> None:
        """Return failure when command execution raises an unexpected error."""
        context = Mock()
        context.envconfig = Mock()
        context.envconfig.build = Mock()
        context.envconfig.build.daps.meta = "daps {dcfile}"
        output_path = tmp_path / "meta.json"

        with (
            patch.object(
                collect_mod,
                "build_metadata_output_path",
                return_value=output_path,
            ),
            patch.object(
                collect_mod,
                "run_command",
                new=AsyncMock(side_effect=RuntimeError("boom")),
            ),
            patch.object(collect_mod.log, "error") as mock_error,
        ):
            document, returned_path, wrote_cache = await collect_mod._collect_language_metadata(
                context,
                deliverable,
                deliverable.git.url,
                deliverable.xml.dcfile,
                meta_cache_dir=tmp_path,
                worktrees={(deliverable.git.url, deliverable.branch): tmp_path},
                lang=deliverable.xml.lang,
                branch=deliverable.branch,
                subdir=deliverable.subdir,
            )

        assert document is None
        assert returned_path == output_path
        assert wrote_cache is False
        assert _logged_message_contains(mock_error, "Failed to collect metadata")

    async def test_collect_language_metadata_missing_metadata_text(
        self,
        deliverable,
        tmp_path: Path,
    ) -> None:
        """Return failure when metadata text cannot be resolved from output."""
        context = Mock()
        context.envconfig = Mock()
        context.envconfig.build = Mock()
        context.envconfig.build.daps.meta = "daps {dcfile}"
        output_path = tmp_path / "meta.json"

        with (
            patch.object(
                collect_mod,
                "build_metadata_output_path",
                return_value=output_path,
            ),
            patch.object(
                collect_mod,
                "run_command",
                new=AsyncMock(return_value=Mock(returncode=0, stdout="", stderr="")),
            ),
            patch.object(
                collect_mod,
                "read_metadata_text",
                new=AsyncMock(return_value=None),
            ),
        ):
            document, returned_path, wrote_cache = await collect_mod._collect_language_metadata(
                context,
                deliverable,
                deliverable.git.url,
                deliverable.xml.dcfile,
                meta_cache_dir=tmp_path,
                worktrees={(deliverable.git.url, deliverable.branch): tmp_path},
                lang=deliverable.xml.lang,
                branch=deliverable.branch,
                subdir=deliverable.subdir,
            )

        assert document is None
        assert returned_path == output_path
        assert wrote_cache is False

    async def test_collect_language_metadata_document_build_error(
        self,
        deliverable,
        tmp_path: Path,
    ) -> None:
        """Return failure with cache state when document construction fails."""
        context = Mock()
        context.envconfig = Mock()
        context.envconfig.build = Mock()
        context.envconfig.build.daps.meta = "daps {dcfile}"
        output_path = tmp_path / "meta.json"

        async def fake_to_thread(func, *args, **kwargs):
            if func is collect_mod.build_document_for_deliverable:
                raise ValueError("bad doc")
            return func(*args, **kwargs)

        with (
            patch.object(
                collect_mod,
                "build_metadata_output_path",
                return_value=output_path,
            ),
            patch.object(
                collect_mod,
                "run_command",
                new=AsyncMock(return_value=Mock(returncode=0, stdout="{}", stderr="")),
            ),
            patch.object(
                collect_mod,
                "read_metadata_text",
                new=AsyncMock(return_value="{}"),
            ),
            patch.object(
                collect_mod,
                "ensure_metadata_cache",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                collect_mod,
                "parse_metadata_text",
                new=AsyncMock(return_value={}),
            ),
            patch.object(
                collect_mod,
                "asyncio",
                wraps=collect_mod.asyncio,
            ) as mock_asyncio,
            patch.object(collect_mod.log, "error") as mock_error,
        ):
            mock_asyncio.to_thread = AsyncMock(side_effect=fake_to_thread)

            document, returned_path, wrote_cache = await collect_mod._collect_language_metadata(
                context,
                deliverable,
                deliverable.git.url,
                deliverable.xml.dcfile,
                meta_cache_dir=tmp_path,
                worktrees={(deliverable.git.url, deliverable.branch): tmp_path},
                lang=deliverable.xml.lang,
                branch=deliverable.branch,
                subdir=deliverable.subdir,
            )

        assert document is None
        assert returned_path == output_path
        assert wrote_cache is True
        assert _logged_message_contains(mock_error, "Failed to build document")

    async def test_collect_translations_invokes_language_worker(
        self,
        deliverable,
        tmp_path: Path,
    ) -> None:
        """Run translation worker jobs and merge translated documents."""
        base_document = build_document_for_deliverable(
            deliverable,
            {"docs": [{"rootid": "base-root", "title": "Base"}]},
        )
        translated_document = Document.from_metadata_payload(
            {"docs": [{"rootid": "translated-root", "title": "Translated"}]},
            dcfile=deliverable.xml.dcfile,
            lang="de-de",
        )
        deliverable.__dict__["translations"] = {
            LanguageCode(language="de-de"): TranslationInfo(
                LanguageCode(language="de-de"),
                branch="main",
                subdir="l10n/sles/de-de",
            )
        }

        async def fake_run_parallel(items, worker_fn, limit):
            del limit
            for item in items:
                yield await worker_fn(item)

        with (
            patch.object(
                collect_mod,
                "_collect_language_metadata",
                new=AsyncMock(return_value=(translated_document, tmp_path / "meta-de.json", True)),
            ) as collect_lang,
            patch.object(collect_mod, "run_parallel", new=fake_run_parallel),
        ):
            success = await collect_mod._collect_translations(
                Mock(envconfig=Mock(), appconfig=Mock(max_workers=2)),
                deliverable,
                base_document,
                deliverable.git.url,
                deliverable.xml.dcfile,
                meta_cache_dir=tmp_path,
                worktrees={(deliverable.git.url, deliverable.branch): tmp_path},
            )

        assert success is True
        assert collect_lang.await_count == 1
        assert len(base_document.docs) == 2

    async def test_collect_dynamic_metadata_without_cache_write(
        self,
        deliverable,
        tmp_path: Path,
    ) -> None:
        """Continue with translations when metadata cache is not written."""
        base_document = build_document_for_deliverable(
            deliverable,
            {"docs": [{"rootid": "base-root", "title": "Base"}]},
        )

        with (
            patch.object(
                collect_mod,
                "_collect_language_metadata",
                new=AsyncMock(return_value=(base_document, tmp_path / "meta.json", False)),
            ),
            patch.object(
                collect_mod,
                "_collect_translations",
                new=AsyncMock(return_value=True),
            ) as collect_translations,
        ):
            success, updated = await collect_dynamic_metadata(
                Mock(envconfig=Mock(), appconfig=Mock(max_workers=2)),
                deliverable,
                meta_cache_dir=tmp_path,
                worktrees={(deliverable.git.url, deliverable.branch): tmp_path},
            )

        assert success is True
        assert updated.document is not None
        assert updated.metafile is None
        collect_translations.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("repo_value", "dcfile", "expected_log"),
    [
        (None, "DC-test", "Deliverable missing git remote"),
        ("https://example.invalid/repo.git", None, "Deliverable missing DC file"),
    ],
    ids=["missing_repo", "missing_dcfile"],
)
async def test_collect_dynamic_metadata_missing_inputs(
    repo_value,
    dcfile,
    expected_log: str,
    tmp_path: Path,
) -> None:
    """Return a failed result when required deliverable inputs are missing."""
    deliverable_mock = Mock()
    deliverable_mock.git = repo_value
    deliverable_mock.full_id = "sles/15-sp7/en-us:DC-test"
    deliverable_mock.xml = Mock(dcfile=dcfile)

    with patch.object(collect_mod.log, "error") as mock_error:
        success, returned = await collect_dynamic_metadata(
            Mock(envconfig=Mock(), appconfig=None),
            deliverable_mock,
            meta_cache_dir=tmp_path,
            worktrees={},
        )

    assert success is False
    assert returned is deliverable_mock
    assert _logged_message_contains(mock_error, expected_log)
