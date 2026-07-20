"""Tests for metadata service orchestration helpers."""

from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from lxml import etree
import pytest

from docbuild.cli.context import DocBuildContext
from docbuild.constants import DEFAULT_DELIVERABLES
from docbuild.models.deliverable.translation import TranslationInfo
from docbuild.models.doctype import Doctype
from docbuild.models.language import LanguageCode
import docbuild.tasks.metadata.service as service_mod
from docbuild.tasks.metadata.service import process, process_doctype_group


@asynccontextmanager
async def dummy_shared_worktrees(*args, **kwargs):
    """Provide an empty shared-worktree mapping for service tests."""
    del args, kwargs
    yield {}


class TestServiceHelpers:
    """Tests for metadata service helper functions."""

    def test_collect_repo_urls_and_branches(self, deliverable) -> None:
        """Extract repository URLs and branch sets from deliverables."""
        deliverable.__dict__["translations"] = {
            LanguageCode(language="de-de"): TranslationInfo(
                LanguageCode(language="de-de"),
                branch=None,
                subdir="l10n/sles/de-de",
            ),
            LanguageCode(language="fr-fr"): TranslationInfo(
                LanguageCode(language="fr-fr"),
                branch="stable",
                subdir="l10n/sles/fr-fr",
            ),
        }
        deliverable_without_git = Mock()
        deliverable_without_git.xml.git_remote.return_value = None
        deliverable_without_git.git = None

        repo_urls = service_mod._collect_repo_urls([deliverable, deliverable_without_git])
        repo_branches = service_mod._collect_repo_branches(
            [deliverable, deliverable_without_git]
        )

        assert repo_urls == {str(deliverable.xml.git_remote())}
        assert repo_branches == {
            (deliverable.git.url, deliverable.branch),
            (deliverable.git.url, "stable"),
        }

    @pytest.mark.asyncio
    @patch.object(service_mod, "shared_worktrees", new=dummy_shared_worktrees)
    @patch.object(service_mod, "report_failed_deliverables")
    @patch.object(service_mod, "write_manifest_json")
    @patch.object(service_mod, "compile_manifest")
    @patch.object(service_mod, "run_metadata_progress", new_callable=AsyncMock)
    async def test_process_doctype_group_writes_manifest(
        self,
        mock_run_metadata: AsyncMock,
        mock_compile_manifest: Mock,
        mock_write_manifest_json: Mock,
        mock_report_failed: Mock,
        deliverable,
        tmp_path: Path,
    ) -> None:
        """Write a manifest JSON file when manifest compilation succeeds."""
        mock_run_metadata.return_value = {deliverable.full_id: "OK"}
        mock_manifest = Mock()
        mock_compile_manifest.return_value = mock_manifest

        context = Mock(spec=DocBuildContext)
        context.envconfig = Mock()
        context.envconfig.paths = Mock()
        context.envconfig.paths.tmp_repo_dir = tmp_path / "tmp_repos"
        context.envconfig.paths.tmp_repo_dir.mkdir(parents=True, exist_ok=True)

        await process_doctype_group(
            context,
            deliverable.xml.productid,
            deliverable.xml.docsetid,
            [deliverable],
            repo_dir=tmp_path / "repos",
            updated_repos=set(),
            meta_cache_dir=tmp_path / "cache" / "metadata",
            json_cache_dir=tmp_path / "cache" / "json",
            limit=1,
            skip_repo_update=True,
        )

        mock_write_manifest_json.assert_called_once()
        mock_report_failed.assert_called_once()


@pytest.mark.asyncio
class TestProcessDoctypeGroup:
    """Tests for process_doctype_group."""

    @patch.object(service_mod, "shared_worktrees", new=dummy_shared_worktrees)
    @patch.object(service_mod, "report_failed_deliverables")
    @patch.object(service_mod, "compile_manifest")
    @patch.object(service_mod, "run_metadata_progress", new_callable=AsyncMock)
    @patch.object(service_mod, "update_managed_repositories", new_callable=AsyncMock)
    async def test_process_doctype_group_updates_repos(
        self,
        mock_update_repositories: AsyncMock,
        mock_run_metadata: AsyncMock,
        mock_compile_manifest: Mock,
        mock_report_failed: Mock,
        deliverable,
        tmp_path: Path,
    ):
        """Ensure repositories are updated when repo updates are enabled."""
        mock_run_metadata.return_value = {deliverable.full_id: "OK"}
        mock_compile_manifest.return_value = None

        context = Mock(spec=DocBuildContext)
        context.envconfig = Mock()
        context.envconfig.paths = Mock()
        context.envconfig.paths.tmp_repo_dir = tmp_path / "tmp_repos"
        context.envconfig.paths.tmp_repo_dir.mkdir(parents=True, exist_ok=True)

        await process_doctype_group(
            context,
            deliverable.xml.productid,
            deliverable.xml.docsetid,
            [deliverable],
            repo_dir=tmp_path / "repos",
            updated_repos=set(),
            meta_cache_dir=tmp_path / "cache" / "metadata",
            json_cache_dir=tmp_path / "cache" / "json",
            limit=1,
            skip_repo_update=False,
        )

        mock_update_repositories.assert_awaited_once()
        mock_run_metadata.assert_awaited_once()
        mock_report_failed.assert_called_once_with(
            [deliverable],
            {deliverable.full_id: "OK"},
        )

    @patch.object(service_mod, "shared_worktrees", new=dummy_shared_worktrees)
    @patch.object(service_mod, "report_failed_deliverables")
    @patch.object(service_mod, "compile_manifest")
    @patch.object(service_mod, "run_metadata_progress", new_callable=AsyncMock)
    @patch.object(service_mod, "update_managed_repositories", new_callable=AsyncMock)
    async def test_process_doctype_group_skips_repo_update(
        self,
        mock_update_repositories: AsyncMock,
        mock_run_metadata: AsyncMock,
        mock_compile_manifest: Mock,
        mock_report_failed: Mock,
        deliverable,
        tmp_path: Path,
    ):
        """Ensure repository updates can be skipped."""
        mock_run_metadata.return_value = {deliverable.full_id: "OK"}
        mock_compile_manifest.return_value = None

        context = Mock(spec=DocBuildContext)
        context.envconfig = Mock()
        context.envconfig.paths = Mock()
        context.envconfig.paths.tmp_repo_dir = tmp_path / "tmp_repos"
        context.envconfig.paths.tmp_repo_dir.mkdir(parents=True, exist_ok=True)

        await process_doctype_group(
            context,
            deliverable.xml.productid,
            deliverable.xml.docsetid,
            [deliverable],
            repo_dir=tmp_path / "repos",
            updated_repos=set(),
            meta_cache_dir=tmp_path / "cache" / "metadata",
            json_cache_dir=tmp_path / "cache" / "json",
            limit=1,
            skip_repo_update=True,
        )

        mock_update_repositories.assert_not_called()
        mock_run_metadata.assert_awaited_once()
        mock_report_failed.assert_called_once_with(
            [deliverable],
            {deliverable.full_id: "OK"},
        )


@pytest.mark.asyncio
class TestProcessEmptyDoctypes:
    """Tests for the case when no doctypes are passed to process."""

    @patch.object(service_mod, "process_doctype_group", new_callable=AsyncMock)
    @patch.object(service_mod, "iter_doctype_groups")
    @patch.object(service_mod, "parse_portal_config", new_callable=AsyncMock)
    async def test_process_empty_doctypes(
        self,
        mock_parse_portal_config: AsyncMock,
        mock_iter_doctype_groups: Mock,
        mock_process_doctype_group: AsyncMock,
        mock_context_with_config_dir: DocBuildContext,
        deliverable,
    ):
        """Use the default doctype when no doctypes are provided."""
        xml_string = """
        <docservconfig>
            <product id="sles">
              <name>SUSE Linux Enterprise Server</name>
              <acronym>SLES</acronym>
              <docset id="sles.15-sp6" path="15-SP6"/>
            </product>
        </docservconfig>
        """
        mock_stitch_node = etree.ElementTree(etree.fromstring(xml_string))
        mock_parse_portal_config.return_value = mock_stitch_node
        sentinel_doctype = Mock(spec=Doctype)
        mock_iter_doctype_groups.return_value = [
            (deliverable.xml.productid, deliverable.xml.docsetid, [deliverable])
        ]

        with (
            patch.object(service_mod.Doctype, "from_str", return_value=sentinel_doctype) as mock_from_str,
            patch.object(service_mod, "stdout"),
        ):
            result = await process(mock_context_with_config_dir, doctypes=())

        mock_from_str.assert_called_once_with(DEFAULT_DELIVERABLES)
        mock_parse_portal_config.assert_awaited_once()
        mock_iter_doctype_groups.assert_called_once_with(
            mock_stitch_node,
            [sentinel_doctype],
        )
        assert mock_process_doctype_group.await_count == 1
        assert result == 0

    @patch.object(service_mod, "process_doctype_group", new_callable=AsyncMock)
    @patch.object(service_mod, "iter_doctype_groups")
    @patch.object(service_mod, "parse_portal_config", new_callable=AsyncMock)
    async def test_process_uses_provided_doctypes(
        self,
        mock_parse_portal_config: AsyncMock,
        mock_iter_doctype_groups: Mock,
        mock_process_doctype_group: AsyncMock,
        mock_context_with_config_dir: DocBuildContext,
        deliverable,
    ):
        """Test process accepts explicit doctypes without defaults."""
        xml_string = """
        <docservconfig>
            <product id="sles">
              <name>SUSE Linux Enterprise Server</name>
              <acronym>SLES</acronym>
              <docset id="sles.15-sp6" path="15-SP6"/>
            </product>
        </docservconfig>
        """
        mock_stitch_node = etree.ElementTree(etree.fromstring(xml_string))
        mock_parse_portal_config.return_value = mock_stitch_node

        provided_doctypes = [Mock(spec=Doctype)]
        mock_iter_doctype_groups.return_value = [
            (deliverable.xml.productid, deliverable.xml.docsetid, [deliverable])
        ]

        result = await process(mock_context_with_config_dir, doctypes=provided_doctypes)

        assert result == 0
        mock_iter_doctype_groups.assert_called_once_with(
            mock_stitch_node,
            provided_doctypes,
        )
        assert mock_process_doctype_group.await_count == 1

    @patch.object(service_mod, "process_doctype_group", new_callable=AsyncMock)
    @patch.object(service_mod, "iter_doctype_groups")
    @patch.object(service_mod, "parse_portal_config", new_callable=AsyncMock)
    async def test_process_iterates_all_groups(
        self,
        mock_parse_portal_config: AsyncMock,
        mock_iter_doctype_groups: Mock,
        mock_process_doctype_group: AsyncMock,
        mock_context_with_config_dir: DocBuildContext,
        deliverable,
    ):
        """Ensure process calls group processing for each yielded group."""
        mock_parse_portal_config.return_value = etree.ElementTree(
            etree.fromstring("<docservconfig />")
        )
        mock_iter_doctype_groups.return_value = [
            (deliverable.xml.productid, "docset-a", [deliverable]),
            (deliverable.xml.productid, "docset-b", [deliverable]),
        ]

        result = await process(mock_context_with_config_dir, doctypes=())

        assert result == 0
        assert mock_process_doctype_group.await_count == 2
