"""Tests for the docbuild.tasks.metadata.runner module."""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from lxml import etree
import pytest

from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
import docbuild.tasks.metadata.runner as runner_pkg
from docbuild.tasks.metadata.runner import (
    execute_build_pipeline,
    fallback_to_english_xref,
    gather_build_tasks,
    get_deliverable_worker_limit,
    process,
    resolve_effective_dcfile,
    resolve_single_translation,
)


def test_get_deliverable_worker_limit() -> None:
    """Test the get_deliverable_worker_limit function."""
    assert get_deliverable_worker_limit(4, 10) == 4
    assert get_deliverable_worker_limit(4, 2) == 2
    assert get_deliverable_worker_limit(4, 0) == 1
    assert get_deliverable_worker_limit(4, -1) == 1
    assert get_deliverable_worker_limit(1, 10) == 1


class SortableMock(Mock):
    """A mock that can be sorted for testing."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.full_id = f"mock_{id(self)}"

    def __lt__(self, other: object) -> bool:
        return self.full_id < getattr(other, "full_id", "")


@pytest.fixture
def empty_xml_root() -> etree._ElementTree:
    """Return an empty parsed XML element tree."""
    return etree.ElementTree(etree.Element("portal"))


class TestGatherBuildTasks:
    """Tests for the gather_build_tasks phase."""

    @patch.object(runner_pkg, "get_deliverable_from_doctype")
    def test_gathers_and_deduplicates_deliverables(
        self, mock_get_deliverables: Mock, empty_xml_root: etree._ElementTree
    ) -> None:
        """Verify phase 1 dependency discovery and xref unwrapping."""
        doctype = Doctype.from_str("sles/15/en-us")

        # Create normal deliverable
        d1 = SortableMock(spec=Deliverable)
        d1.full_id = "d1"
        d1.xml.is_xref = False
        d1.xml.lang = "en-us"

        # Create xref pointing to a deliverable
        d2 = SortableMock(spec=Deliverable)
        d2.full_id = "d2"
        d2.xml.is_xref = True
        d2.xml.lang = "en-us"
        target_elem = etree.Element("deliverable")
        d2.xml.final_target_node = target_elem

        mock_get_deliverables.return_value = [d1, d2]

        # Patch Deliverable instantiation inside the xref block
        with patch.object(runner_pkg, "Deliverable") as mock_deliverable:
            d_target = SortableMock(spec=Deliverable)
            d_target.full_id = "target"
            mock_deliverable.return_value = d_target

            result = gather_build_tasks(empty_xml_root, [doctype])

        mock_get_deliverables.assert_called_once_with(empty_xml_root, doctype)

        # Results should be sorted by full_id ("d1", "target")
        assert len(result) == 2
        assert result[0].full_id == "d1"
        assert result[1].full_id == "target"


type TranslationXmlFactory = Callable[..., etree._ElementTree]


class TestTranslationMetadataChecks:
    """Tests for Phase 2 Virtual Translation Inheritance Git checks."""

    @pytest.fixture
    def make_translation_xml(self) -> TranslationXmlFactory:
        """Provide a factory fixture to build XML trees with custom deliverables.

        :return: Factory callable that generates the ElementTree.
        """
        def _factory(*deliverables: str) -> etree._ElementTree:
            """Construct an ElementTree with specified deliverable elements.

            :param deliverables: Variadic XML strings representing deliverable nodes
                or their inner child elements.
            :return: Fully parsed ElementTree containing the requested nodes.
            """
            # Filter out None or empty strings, then join deliverables with newlines
            deliverables_xml = "\n".join(d for d in deliverables if d)

            xml_str = f"""
            <portal xmlns:xml="http://www.w3.org/XML/1998/namespace">
                <product xml:id="sles">
                  <docset xml:id="sles.15" path="15">
                    <resources>
                      <locale lang="en-us">
                        <branch>main</branch>
                        <deliverable xml:id="doc1"><dc file="DC-test"/></deliverable>
                      </locale>
                      <locale lang="de-de">
                        <branch>translations</branch>
                        <subdir>l10n/de</subdir>
                        {deliverables_xml}
                      </locale>
                    </resources>
                  </docset>
                </product>
            </portal>
            """
            return etree.ElementTree(etree.fromstring(xml_str.encode("utf-8")))

        return _factory

    def test_resolve_effective_dcfile_from_xref(
        self, make_translation_xml: TranslationXmlFactory
    ) -> None:
        """Verify dcfile resolution when deliverable references an existing doc via xref.

        :param make_translation_xml: Factory fixture creating portal ElementTree instances.
        """
        tree = make_translation_xml('<deliverable><xref linkend="doc1"/></deliverable>')
        node = tree.find(".//locale[@lang='de-de']/deliverable")
        assert node is not None

        deliverable = Deliverable(_node=node)
        assert resolve_effective_dcfile(deliverable) == "DC-test"

    def test_resolve_effective_dcfile_explicit(
        self, make_translation_xml: TranslationXmlFactory
    ) -> None:
        """Verify dcfile resolution for an explicitly declared dc file.

        :param make_translation_xml: Factory fixture creating portal ElementTree instances.
        """
        tree = make_translation_xml('<deliverable><dc file="DC-explicit"/></deliverable>')
        node = tree.find(".//locale[@lang='de-de']/deliverable")
        assert node is not None

        deliverable = Deliverable(_node=node)
        assert resolve_effective_dcfile(deliverable) == "DC-explicit"

    def test_resolve_effective_dcfile_broken_xref(
        self, make_translation_xml: TranslationXmlFactory
    ) -> None:
        """Verify dcfile resolution returns None when xref points to an unresolvable ID.

        :param make_translation_xml: Factory fixture creating portal ElementTree instances.
        """
        tree = make_translation_xml('<deliverable><xref linkend="missing"/></deliverable>')
        node = tree.find(".//locale[@lang='de-de']/deliverable")
        assert node is not None

        deliverable = Deliverable(_node=node)
        assert resolve_effective_dcfile(deliverable) is None

    def test_fallback_to_english_xref(self, make_translation_xml: TranslationXmlFactory) -> None:
        """Verify explicit translations safely convert into xrefs on failure."""
        tree = make_translation_xml('<deliverable><dc file="DC-explicit"/></deliverable>')
        node = tree.find(".//locale[@lang='de-de']/deliverable")
        assert node is not None
        d_explicit = Deliverable(_node=node)

        # Add a matching file to the english blueprint dynamically to test resolution
        en_locale = tree.find(".//locale[@lang='en-us']")
        assert en_locale is not None
        en_d = etree.Element("deliverable")
        en_d.set("{http://www.w3.org/XML/1998/namespace}id", "explicit-blueprint")
        en_d.append(etree.Element("dc", file="DC-explicit"))
        en_locale.append(en_d)

        fallback_to_english_xref(d_explicit, "DC-explicit", "l10n/de/DC-explicit")

        # The <dc> should be gone, replaced by <xref linkend="explicit-blueprint">
        assert d_explicit.xml.node.find("dc") is None
        assert d_explicit.xml.node.find("xref").get("linkend") == "explicit-blueprint"

    @patch("docbuild.tasks.metadata.runner.ManagedGitRepo", autospec=True)
    async def test_resolve_single_translation_found(self, mock_repo_class: Mock, make_translation_xml: TranslationXmlFactory, tmp_path: Path) -> None:
        """Verify xrefs are dropped when the localized DC file exists."""
        tree = make_translation_xml('<deliverable><xref linkend="doc1"/></deliverable>')
        node = tree.find(".//locale[@lang='de-de']/deliverable")
        assert node is not None
        d_xref = Deliverable(_node=node)
        d_xref.git = Mock(url="git@test")

        # Mock ls_tree to return the file
        mock_repo = AsyncMock()
        mock_repo.ls_tree.return_value = ["l10n/de/DC-test"]
        mock_repo_class.return_value = mock_repo

        cache = {}
        result = await resolve_single_translation(d_xref, tmp_path, cache)

        assert result is not None
        assert result.xml.node.find("xref") is None
        assert result.xml.node.find("dc").get("file") == "DC-test"
        assert cache == {("git@test", "translations"): ["l10n/de/DC-test"]}

    @patch("docbuild.tasks.metadata.runner.ManagedGitRepo", autospec=True)
    async def test_resolve_single_translation_missing(self, mock_repo_class: Mock, make_translation_xml: TranslationXmlFactory, tmp_path: Path) -> None:
        """Verify missing translations are skipped (xrefs stay xrefs)."""
        tree = make_translation_xml('<deliverable><xref linkend="doc1"/></deliverable>')
        node = tree.find(".//locale[@lang='de-de']/deliverable")
        assert node is not None
        d_xref = Deliverable(_node=node)
        d_xref.git = Mock(url="git@test")

        # Mock ls_tree to return empty (file not found)
        mock_repo = AsyncMock()
        mock_repo.ls_tree.return_value = []
        mock_repo_class.return_value = mock_repo

        result = await resolve_single_translation(d_xref, tmp_path, {})

        assert result is None  # Skipped!
        assert d_xref.xml.node.find("xref") is not None  # Kept as xref


class TestExecuteBuildPipeline:
    """Tests for the execute_build_pipeline phase."""

    @patch.object(runner_pkg, "update_repositories", new_callable=AsyncMock)
    @patch.object(runner_pkg, "process_deliverable", new_callable=AsyncMock)
    async def test_success_with_deliverables(
        self, mock_process_deliverable: AsyncMock, mock_update_repositories: AsyncMock, tmp_path: Path
    ) -> None:
        """Verify pipeline processes deliverables cleanly."""
        d1 = SortableMock(spec=Deliverable)
        d1.full_id = "d1"
        d1.xml.lang = "en-us"
        d1.xml.is_xref = False
        d1.xml.git_remote.return_value = "https://github.com/foo/bar.git"

        d2 = SortableMock(spec=Deliverable)
        d2.full_id = "d2"
        d2.xml.lang = "en-us"
        d2.xml.is_xref = False
        d2.xml.git_remote.return_value = None

        mock_process_deliverable.side_effect = [(True, d1), (True, d2)]

        result = await execute_build_pipeline(
            [d1, d2],
            repo_dir=tmp_path,
            tmp_repo_dir=tmp_path,
            meta_cache_dir=tmp_path,
            prebuilt_dir=tmp_path,
            dapsmetatmpl="daps_meta",
            daps_list_srcfiles_tmpl="daps_list",
            skip_repo_update=False,
            env_config_hash="hash",
            max_workers=2,
            exitfirst=False,
        )

        # Repositories should only be updated for deliverables with a git remote
        mock_update_repositories.assert_awaited_once_with([d1], tmp_path)
        assert mock_process_deliverable.await_count == 2
        assert result == []

    @patch.object(runner_pkg, "update_repositories", new_callable=AsyncMock)
    @patch.object(runner_pkg, "process_deliverable", new_callable=AsyncMock)
    async def test_exitfirst_stops_on_first_failure(
        self, mock_process_deliverable: AsyncMock, mock_update_repositories: AsyncMock, tmp_path: Path
    ) -> None:
        """Verify exitfirst halts processing immediately on first failure."""
        d1 = SortableMock(spec=Deliverable)
        d1.xml.lang = "en-us"
        d1.xml.is_xref = False

        d2 = SortableMock(spec=Deliverable)
        d2.xml.lang = "en-us"
        d2.xml.is_xref = False

        # First fails, second succeeds
        mock_process_deliverable.side_effect = [(False, d1), (True, d2)]

        failed = await execute_build_pipeline(
            [d1, d2],
            repo_dir=tmp_path,
            tmp_repo_dir=tmp_path,
            meta_cache_dir=tmp_path,
            prebuilt_dir=tmp_path,
            dapsmetatmpl="daps",
            daps_list_srcfiles_tmpl="daps_list",
            skip_repo_update=True,
            env_config_hash="hash",
            max_workers=1,  # Must be 1 to guarantee sequential execution order
            exitfirst=True,
        )

        assert failed == [d1]

    @patch.object(runner_pkg, "process_deliverable", new_callable=AsyncMock)
    async def test_exception_in_process_deliverable_caught(
        self, mock_process_deliverable: AsyncMock, tmp_path: Path
    ) -> None:
        """Verify pipeline handles generic exceptions gracefully."""
        mock_d = SortableMock(spec=Deliverable)
        mock_d.full_id = "fail_mock"
        mock_d.xml.lang = "en-us"
        mock_d.xml.is_xref = False
        mock_process_deliverable.side_effect = Exception("Simulated DAPS failure")

        failed = await execute_build_pipeline(
            [mock_d],
            repo_dir=tmp_path,
            tmp_repo_dir=tmp_path,
            meta_cache_dir=tmp_path,
            prebuilt_dir=tmp_path,
            dapsmetatmpl="daps",
            daps_list_srcfiles_tmpl="daps_list",
            skip_repo_update=True,
            env_config_hash="hash",
            max_workers=1,
            exitfirst=False,
        )

        assert failed == [mock_d]


class TestProcess:
    """Tests for the main process() orchestration function."""

    @pytest.fixture
    def runner_kwargs(self, tmp_path: Path) -> dict[str, object]:
        return {
            "main_portal_config": tmp_path / "portal.xml",
            "tmp_metadata_dir": tmp_path / "tmp" / "metadata",
            "repo_dir": tmp_path / "repos",
            "tmp_repo_dir": tmp_path / "tmp_repos",
            "meta_cache_dir": tmp_path / "cache" / "metadata",
            "json_cache_dir": tmp_path / "cache" / "json",
            "prebuilt_dir": tmp_path / "cache" / "prebuilt",
            "dapsmetatmpl": "daps",
            "daps_list_srcfiles_tmpl": "daps_list",
            "max_workers": 2,
            "doctypes": None,
        }

    async def test_empty_doctypes_uses_default(
        self,
        runner_kwargs: dict[str, object],
        tmp_path: Path,
    ) -> None:
        """Verify omitting doctypes runs default deliverables via actual data flow."""
        xml_string = """
        <portal xmlns:xml="http://www.w3.org/XML/1998/namespace">
            <product xml:id="sles">
              <name>SUSE Linux Enterprise Server</name>
              <docset xml:id="sles.15-sp6" path="15-SP6" lifecycle="supported">
                <resources>
                  <locale lang="en-us">
                    <branch>main</branch>
                    <deliverable xml:id="test-doc"><dc file="DC-test"/></deliverable>
                  </locale>
                </resources>
              </docset>
            </product>
        </portal>
        """
        (tmp_path / "portal.xml").write_text(xml_string)

        import docbuild.tasks.metadata.runner as runner_pkg
        with patch.object(runner_pkg, "store_productdocset_json"), \
             patch.object(runner_pkg, "generate_homepage"), \
             patch.object(runner_pkg, "update_repositories", new_callable=AsyncMock), \
             patch.object(runner_pkg, "process_deliverable", new_callable=AsyncMock) as mock_pd:

            mock_pd.return_value = (True, Mock())

            result = await process(**runner_kwargs)  # type: ignore

            assert result == 0
            mock_pd.assert_awaited_once()
            args, _ = mock_pd.call_args
            assert args[0].xml.deliverableid == "test-doc"

    async def test_failed_deliverables_returns_one(
        self,
        runner_kwargs: dict[str, object],
        tmp_path: Path,
    ) -> None:
        """Verify failures correctly surface exit code 1."""
        xml_string = """
        <portal xmlns:xml="http://www.w3.org/XML/1998/namespace">
            <product xml:id="sles">
              <name>SUSE Linux Enterprise Server</name>
              <docset xml:id="sles.15-sp6" path="15-SP6" lifecycle="supported">
                <resources>
                  <locale lang="en-us">
                    <branch>main</branch>
                    <deliverable xml:id="fail-doc"><dc file="DC-fail"/></deliverable>
                  </locale>
                </resources>
              </docset>
            </product>
        </portal>
        """
        (tmp_path / "portal.xml").write_text(xml_string)

        import docbuild.tasks.metadata.runner as runner_pkg
        with patch.object(runner_pkg, "store_productdocset_json"), \
             patch.object(runner_pkg, "generate_homepage"), \
             patch.object(runner_pkg, "update_repositories", new_callable=AsyncMock), \
             patch.object(runner_pkg, "process_deliverable", new_callable=AsyncMock) as mock_pd, \
             patch.object(runner_pkg, "console_err") as mock_cerr:

            failed_d = Mock()
            failed_d.full_id = "fail-doc"
            mock_pd.return_value = (False, failed_d)

            result = await process(**runner_kwargs)  # type: ignore

            assert result == 1
            assert mock_cerr.print.called

    async def test_provided_doctypes_skips_default(
        self,
        runner_kwargs: dict[str, object],
        tmp_path: Path,
    ) -> None:
        """Verify targeted execution isolates requested doctypes without mocking pipeline."""
        xml_string = """
        <portal xmlns:xml="http://www.w3.org/XML/1998/namespace">
            <product xml:id="sles">
              <name>SUSE Linux Enterprise Server</name>
              <docset xml:id="sles.15-sp6" path="15-SP6" lifecycle="supported">
                <resources>
                  <locale lang="en-us">
                    <branch>main</branch>
                    <deliverable xml:id="doc1"><dc file="DC-1"/></deliverable>
                  </locale>
                  <locale lang="de-de">
                    <branch>main</branch>
                    <deliverable xml:id="doc2"><dc file="DC-2"/></deliverable>
                  </locale>
                </resources>
              </docset>
            </product>
        </portal>
        """
        (tmp_path / "portal.xml").write_text(xml_string)

        provided_doctype = Doctype.from_str("sles/15-SP6/de-de")
        runner_kwargs["doctypes"] = [provided_doctype]

        import docbuild.tasks.metadata.runner as runner_pkg
        with patch.object(runner_pkg, "store_productdocset_json"), \
             patch.object(runner_pkg, "generate_homepage"), \
             patch.object(runner_pkg, "update_repositories", new_callable=AsyncMock), \
             patch.object(runner_pkg, "process_deliverable", new_callable=AsyncMock) as mock_pd:

            mock_pd.return_value = (True, Mock())

            result = await process(**runner_kwargs)  # type: ignore

            assert result == 0
            # Only the de-de deliverable should be processed
            mock_pd.assert_awaited_once()
            args, _ = mock_pd.call_args
            assert args[0].xml.deliverableid == "doc2"
