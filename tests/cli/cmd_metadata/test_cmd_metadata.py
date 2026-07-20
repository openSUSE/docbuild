"""Unit tests for metadata command helper functions."""

from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from lxml import etree
import pytest

from docbuild.cli.context import DocBuildContext
from docbuild.constants import DEFAULT_DELIVERABLES
from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
import docbuild.tasks.metadata.collect as collect_mod
from docbuild.tasks.metadata.collect import collect_dynamic_metadata
from docbuild.tasks.metadata.discovery import (
    get_deliverables_for_doctype,
    iter_doctype_groups,
)
from docbuild.tasks.metadata.manifest import (
    build_document_for_deliverable,
    compile_manifest,
    write_manifest_json,
)
import docbuild.tasks.metadata.service as service_mod
from docbuild.tasks.metadata.service import process, process_doctype_group
import docbuild.tasks.repository.sync as repo_sync_mod
from docbuild.tasks.repository.sync import update_managed_repositories


@asynccontextmanager
async def dummy_shared_worktrees(*args, **kwargs):
    """Provide an empty shared-worktree mapping for service tests."""
    del args, kwargs
    yield {}


@pytest.fixture
def mock_envconfig(tmp_path: Path) -> Mock:
    """Provide a mock EnvConfig object with necessary paths and build config.

    This fixture creates a Mock object that simulates the structure of
    the EnvConfig Pydantic model, allowing attribute-style access to
    nested configurations like `env.paths.repo_dir` and `env.build.daps.meta`.
    """
    mock_paths = Mock()
    mock_paths.repo_dir = tmp_path / "repos"
    mock_paths.base_cache_dir = tmp_path / "cache"
    mock_paths.meta_cache_dir = tmp_path / "cache" / "metadata"
    mock_paths.json_cache_dir = tmp_path / "cache" / "json"
    mock_paths.tmp_repo_dir = tmp_path / "tmp_repos"

    mock_build = Mock()
    mock_build.daps.meta = "daps-command-template"

    mock_envconfig = Mock()
    mock_envconfig.paths = mock_paths
    mock_envconfig.build = mock_build
    return mock_envconfig


@pytest.fixture
def xmlconfig(request) -> etree.ElementTree:
    """Parse an XML string into an ElementTree.

    Can be used with or without @pytest.mark.parametrize.
    If used with parametrize, it expects the XML string as the parameter.
    If used without, it provides a default empty <config/> tree.
    """
    xml_string = None
    if hasattr(request, "param"):
        xml_string = request.param

    if not xml_string:
        xml_string = "<docservconfig/>"
    root = etree.fromstring(xml_string)
    return etree.ElementTree(root)


@pytest.fixture
def mock_context_with_config_dir(
    tmp_path: Path, mock_envconfig: Mock
) -> DocBuildContext:
    """Provide a mock DocBuildContext with a valid config_dir.

    This fixture builds upon `mock_envconfig` and customizes it
    for scenarios requiring a `config_dir` and `tmp.tmp_metadata_dir`.
    """
    context = Mock(spec=DocBuildContext)
    config_dir = tmp_path / "config"
    tmp_metadata_dir = tmp_path / "tmp" / "metadata"

    config_dir.mkdir()
    tmp_metadata_dir.mkdir(parents=True)

    (config_dir / "dummy.xml").write_text("<docservconfig/>")

    # Customize the mock_envconfig for this fixture's needs
    mock_envconfig.paths.config_dir = config_dir
    mock_envconfig.paths.main_portal_config = config_dir / "dummy.xml"
    mock_envconfig.paths.meta_cache_dir.mkdir(parents=True)  # Ensure it exists

    # Create a mock for envconfig.paths.tmp
    mock_tmp = Mock()
    mock_tmp.tmp_metadata_dir = tmp_metadata_dir
    mock_envconfig.paths.tmp = mock_tmp

    context.envconfig = mock_envconfig
    context.appconfig = None
    return context


@pytest.mark.parametrize(
    "xmlconfig, doctype_str, expected_count, expected_ids",
    [
        (
            """
            <portal>
              <product id="sles">
                <docset id="sles.16-sp6" path="15-sp6">
                  <resources>
                    <locale lang="en-us">
                        <deliverable id="sles.16-sp6.admin">
                            <dc file="DC-SLE-Micro-5.5-admin">
                                <format html="1"/>
                            </dc>
                        </deliverable>
                    </locale>
                  </resources>
                </docset>
              </product>
              <product id="other">
                <docset id="other.1.0" path="1.0">
                   <resources>
                     <locale lang="en-us">
                        <deliverable>
                            <dc file="DC-Micro-5.4-cockpit">
                                <format html="1"/>
                            </dc>
                        </deliverable>
                        <deliverable>
                            <dc file="DC-Micro-5.5-cockpit">
                                <format html="1"/>
                            </dc>
                        </deliverable>
                    </locale>
                   </resources>
                </docset>
              </product>
            </portal>
            """,
            "sles/15-sp6/en-us",
            1,
            {"sles/15-sp6/en-us:DC-SLE-Micro-5.5-admin"},
        ),
        (
            """
            <portal>
              <product id="sles">
                <docset id="sles.16-sp6" path="15-sp6">
                    <resources>
                        <locale lang="en-us">
                            <deliverable>
                                <dc file="DC-SLE-Micro-5.5-admin">
                                    <format html="1"/>
                                </dc>
                            </deliverable>
                        </locale>
                    </resources>
                </docset>
              </product>
              <product id="other">
              <docset id="other.1.0" path="1.0">
                  <resources>
                    <locale lang="en-us">
                      <deliverable>
                        <dc file="DC-Micro-5.4-cockpit">
                            <format html="1"/>
                        </dc>
                      </deliverable>
                    </locale>
                  </resources>
                </docset>
              </product>
            </portal>
            """,
            "//en-us",
            2,
            {
                "other/1.0/en-us:DC-Micro-5.4-cockpit",
                "sles/15-sp6/en-us:DC-SLE-Micro-5.5-admin",
            },
        ),
        ("<portal/>", "nonexistent/1.0/en-us", 0, set()),
        (
            """<portal>
                 <product id='sles'>
                    <docset id='sles.15-sp6' path="15-sp6" />
                 </product>
               </portal>""",
            "sles/15-sp6/de-de",
            0,
            set(),
        ),
    ],
    indirect=["xmlconfig"],
    ids=[
        "specific_doctype",
        "wildcard_doctype",
        "nonexistent_product",
        "nonexistent_lang",
    ],
)
def test_get_deliverables_for_doctype(
    xmlconfig, doctype_str, expected_count, expected_ids
):
    """Verify deliverables are correctly extracted for various doctypes."""
    # Arrange & Act
    if "nonexistent" in doctype_str:
        with pytest.raises(ValueError):
            Doctype.from_str(doctype_str)
        return  # Test passes if validation error is raised
    else:
        doctype = Doctype.from_str(doctype_str)

    # Act
    deliverables = list(get_deliverables_for_doctype(xmlconfig, doctype))

    # Assert
    assert len(deliverables) == expected_count
    if expected_ids:
        assert {d.docsuite for d in deliverables} == expected_ids


@pytest.fixture
def deliverable() -> Deliverable:
    """Provide a mock Deliverable object for testing."""
    xml_string = """
    <docservconfig>
      <product id="sles">
        <docset id="sles.15-sp7" path="15-SP7">
          <resources>
             <git remote="https://github.com/SUSE/doc-sle.git"/>
             <locale lang="en-us">
                <branch>main</branch>
                <subdir>l10n/sles/en-us</subdir>
                <deliverable>
                    <dc file="DC-SLES-deployment">
                        <format html="1" pdf="1" single-html="0"/>
                    </dc>
                </deliverable>
             </locale>
          </resources>
        </docset>
      </product>
    </docservconfig>
    """
    root = etree.fromstring(xml_string)
    locale_node = root.find(".//locale")
    deliverable_node = locale_node.find("deliverable")
    return Deliverable(deliverable_node)


@pytest.fixture
def stitchnode(deliverable: Deliverable) -> etree._ElementTree:
    """Build a minimal stitched `docservconfig` ElementTree from a Deliverable fixture.

    Provides the common product/docset/name/acronym structure used by tests.
    """
    prod_node = etree.Element("product", id=deliverable.xml.productid, productid=deliverable.xml.productid)
    name_el = etree.SubElement(prod_node, "name")
    name_el.text = "SUSE Linux Enterprise Server"
    etree.SubElement(prod_node, "acronym").text = "SLES"
    etree.SubElement(prod_node, "docset", id=deliverable.xml.docsetid, path=deliverable.xml.docsetid, setid=deliverable.xml.docsetid, productid=deliverable.xml.productid)
    root = etree.Element("docservconfig")
    root.append(prod_node)
    return etree.ElementTree(root)


@pytest.mark.asyncio
class TestCollectDynamicMetadata:
    """Tests for the collect_dynamic_metadata function."""

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
        deliverable: Deliverable,
        setup_paths: dict[str, Path],
        caplog,
        scenario: str,
        expected_result: bool,
        expected_log: str | None,
    ):
        """Test various scenarios for collect_dynamic_metadata."""
        caplog.set_level(logging.ERROR)

        repo_url = deliverable.git.url
        worktrees = {(repo_url, deliverable.branch): setup_paths["tmp_repo_dir"] / "shared"}

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
        mock_envconfig.build.daps.meta = (
            "daps --dc-file={dcfile} --output={output}"
        )

        mock_context = Mock(spec=DocBuildContext)
        mock_context.envconfig = mock_envconfig

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
            assert expected_log in caplog.text

        if scenario == "worktree_missing":
            mock_run_command.assert_not_called()


class TestIterDoctypeGroups:
    """Tests for iter_doctype_groups."""

    def test_iter_doctype_groups_returns_grouped_deliverables(self) -> None:
        """Ensure deliverables are grouped by product and docset."""
        xml_string = """
        <portal>
          <product id="sles">
            <docset id="sles.16-sp6" path="15-sp6">
              <resources>
                <locale lang="en-us">
                    <deliverable>
                        <dc file="DC-SLE-Micro-5.5-admin">
                            <format html="1"/>
                        </dc>
                    </deliverable>
                    <deliverable>
                        <dc file="DC-SLE-Micro-5.6-admin">
                            <format html="1"/>
                        </dc>
                    </deliverable>
                </locale>
              </resources>
            </docset>
          </product>
        </portal>
        """
        root = etree.ElementTree(etree.fromstring(xml_string))
        doctype = Doctype.from_str("sles/15-sp6/en-us")

        groups = list(iter_doctype_groups(root, [doctype]))

        assert len(groups) == 1
        product, docset, deliverables = groups[0]
        assert product == "sles"
        assert docset == "15-sp6"
        assert len(deliverables) == 2

    def test_iter_doctype_groups_wildcard_docset(self) -> None:
        """Wildcard doctypes should return one group per docset."""
        xml_string = """
        <portal>
          <product id="smart">
            <docset id="smart.deploy" path="deploy-upgrade">
              <resources>
                <locale lang="en-us">
                    <deliverable>
                        <dc file="DC-a">
                            <format html="1"/>
                        </dc>
                    </deliverable>
                </locale>
              </resources>
            </docset>
            <docset id="smart.ops" path="operations-guide">
              <resources>
                <locale lang="en-us">
                    <deliverable>
                        <dc file="DC-b">
                            <format html="1"/>
                        </dc>
                    </deliverable>
                </locale>
              </resources>
            </docset>
          </product>
        </portal>
        """
        root = etree.ElementTree(etree.fromstring(xml_string))
        doctype = Doctype.from_str("smart/*/en-us")

        groups = list(iter_doctype_groups(root, [doctype]))
        docsets = {docset for _, docset, _ in groups}

        assert docsets == {"deploy-upgrade", "operations-guide"}


@pytest.mark.asyncio
class TestProcessDoctypeGroup:
    """Tests for the process_doctype_group function."""

    @patch.object(service_mod, "shared_worktrees", new=dummy_shared_worktrees)
    @patch.object(service_mod, "report_failed_deliverables")
    @patch.object(service_mod, "compile_manifest")
    @patch.object(service_mod, "run_metadata_progress", new_callable=AsyncMock)
    @patch.object(
        service_mod,
        "update_managed_repositories",
        new_callable=AsyncMock,
    )
    async def test_process_doctype_group_updates_repos(
        self,
        mock_update_repositories: AsyncMock,
        mock_run_metadata: AsyncMock,
        mock_compile_manifest: Mock,
        mock_report_failed: Mock,
        deliverable: Deliverable,
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
        repo_dir = tmp_path / "repos"
        meta_cache_dir = tmp_path / "cache" / "metadata"
        json_cache_dir = tmp_path / "cache" / "json"

        await process_doctype_group(
            context,
            deliverable.xml.productid,
            deliverable.xml.docsetid,
            [deliverable],
            repo_dir=repo_dir,
            updated_repos=set(),
            meta_cache_dir=meta_cache_dir,
            json_cache_dir=json_cache_dir,
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
    @patch.object(
        service_mod,
        "update_managed_repositories",
        new_callable=AsyncMock,
    )
    async def test_process_doctype_group_skips_repo_update(
        self,
        mock_update_repositories: AsyncMock,
        mock_run_metadata: AsyncMock,
        mock_compile_manifest: Mock,
        mock_report_failed: Mock,
        deliverable: Deliverable,
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
        repo_dir = tmp_path / "repos"
        meta_cache_dir = tmp_path / "cache" / "metadata"
        json_cache_dir = tmp_path / "cache" / "json"

        await process_doctype_group(
            context,
            deliverable.xml.productid,
            deliverable.xml.docsetid,
            [deliverable],
            repo_dir=repo_dir,
            updated_repos=set(),
            meta_cache_dir=meta_cache_dir,
            json_cache_dir=json_cache_dir,
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
        deliverable: Deliverable,
    ):
        """Test process function with an empty tuple of doctypes.

        This test ensures that when no doctypes are provided, the process
        uses the default doctype and runs the grouped processing step.
        """
        # This mock needs a minimal stitched XML config so the doctype
        # grouping has a product and docset to work with.
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
            patch.object(
                service_mod.Doctype,
                "from_str",
                return_value=sentinel_doctype,
            ) as mock_from_str,
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
        deliverable: Deliverable,
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

        result = await process(
            mock_context_with_config_dir,
            doctypes=provided_doctypes,
        )

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
        deliverable: Deliverable,
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


@pytest.mark.asyncio
async def test_compile_manifest_writes_json(
    tmp_path: Path, deliverable: Deliverable
):
    """Write manifest JSON for a compiled document list."""
    metadata_payload: dict[str, object] = {
        "docs": [{"rootid": "doc-root", "title": "Doc1"}]
    }
    document = build_document_for_deliverable(deliverable, metadata_payload)
    deliverable.document = document

    manifest = compile_manifest(
        deliverable.xml.productid,
        deliverable.xml.docsetid,
        [deliverable],
    )
    assert manifest is not None

    out_file = tmp_path / "manifest.json"
    write_manifest_json(out_file, manifest)

    merged = json.loads(out_file.read_text(encoding="utf-8"))
    assert merged["documents"][0]["docs"][0]["title"] == "Doc1"
    assert merged["hide-productname"] is False


def test_compile_manifest_missing_documents_returns_none(
    deliverable: Deliverable,
) -> None:
    """Return None when no deliverable documents are present."""
    manifest = compile_manifest(
        deliverable.xml.productid,
        deliverable.xml.docsetid,
        [deliverable],
    )
    assert manifest is None


def test_compile_manifest_empty_deliverables_returns_none() -> None:
    """Return None when no deliverables are provided."""
    manifest = compile_manifest("sles", "15-sp6", [])
    assert manifest is None


@pytest.mark.asyncio
class TestUpdateManagedRepositories:
    """Tests for the update_managed_repositories function."""

    @patch.object(repo_sync_mod, "ManagedGitRepo")
    async def test_update_managed_repositories_success(
        self, mock_repo_class: Mock, tmp_path: Path
    ) -> None:
        """Verify repositories are updated successfully."""
        mock_repo = AsyncMock()
        mock_repo.clone_bare.return_value = True
        mock_repo.slug = "SUSE-doc-test"
        mock_repo_class.return_value = mock_repo

        updated_repos: set[str] = set()
        updated = await update_managed_repositories(
            tmp_path / "repos",
            {"gh://SUSE/doc-test"},
            updated_repos,
            limit=1,
        )

        assert updated == ["SUSE-doc-test"]
        assert "gh://SUSE/doc-test" in updated_repos
        mock_repo.clone_bare.assert_awaited_once()

    @patch.object(repo_sync_mod, "ManagedGitRepo")
    async def test_update_managed_repositories_failed(
        self, mock_repo_class: Mock, tmp_path: Path, caplog
    ) -> None:
        """Verify failures are reported when repo updates fail."""
        caplog.set_level(logging.ERROR)
        mock_repo = AsyncMock()
        mock_repo.clone_bare.return_value = False
        mock_repo.slug = "SUSE-fail"
        mock_repo_class.return_value = mock_repo

        updated_repos: set[str] = set()
        updated = await update_managed_repositories(
            tmp_path / "repos",
            {"gh://SUSE/fail"},
            updated_repos,
            limit=1,
        )

        assert updated == []
        assert "Failed to update repository" in caplog.text
