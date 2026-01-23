"""Unit tests for metadata command helper functions."""

from collections.abc import Iterator
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from lxml import etree
import pytest

from docbuild.cli.cmd_metadata import metaprocess as metaprocess_pkg
from docbuild.cli.cmd_metadata.metaprocess import (
    collect_files_flat,
    get_deliverable_from_doctype,
    process,
    process_deliverable,
    process_doctype,
)
from docbuild.cli.context import DocBuildContext
from docbuild.constants import DEFAULT_DELIVERABLES
from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
from docbuild.models.repo import Repo


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
    mock_paths.temp_repo_dir = tmp_path / "temp_repos"

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
    mock_envconfig.paths.meta_cache_dir.mkdir(parents=True)  # Ensure it exists

    # Create a mock for envconfig.paths.tmp
    mock_tmp = Mock()
    mock_tmp.tmp_metadata_dir = tmp_metadata_dir
    mock_envconfig.paths.tmp = mock_tmp

    context.envconfig = mock_envconfig
    return context


@pytest.mark.parametrize(
    "xmlconfig, doctype_str, expected_count, expected_ids",
    [
        (
            """
            <docservconfig>
              <product productid="sles">
                <docset setid="15-sp6">
                  <builddocs>
                    <language lang="en-us">
                        <deliverable>
                            <dc>DC-SLE-Micro-5.5-admin</dc>
                            <format html="1"/>
                        </deliverable>
                    </language>
                  </builddocs>
                </docset>
              </product>
              <product productid="other">
                <docset setid="1.0">
                   <builddocs>
                     <language lang="en-us">
                        <deliverable>
                            <dc>DC-Micro-5.4-cockpit</dc>
                            <format html="1"/>
                        </deliverable>
                        <deliverable>
                            <dc>DC-Micro-5.5-cockpit</dc>
                            <format html="1"/>
                        </deliverable>
                    </language>
                   </builddocs>
                </docset>
              </product>
            </docservconfig>
            """,
            "sles/15-sp6/en-us",
            1,
            {"sles/15-sp6/en-us:DC-SLE-Micro-5.5-admin"},
        ),
        (
            """
            <docservconfig>
              <product productid="sles">
                <docset setid="15-sp6">
                    <builddocs>
                        <language lang="en-us">
                            <deliverable>
                                <dc>DC-SLE-Micro-5.5-admin</dc>
                                <format html="1"/>
                            </deliverable>
                        </language>
                    </builddocs>
                </docset>
              </product>
              <product productid="other">
              <docset setid="1.0">
                  <builddocs>
                    <language lang="en-us">
                      <deliverable>
                        <dc>DC-Micro-5.4-cockpit</dc>
                        <format html="1"/>
                      </deliverable>
                    </language>
                  </builddocs>
                </docset>
              </product>
            </docservconfig>
            """,
            "//en-us",
            2,
            {
                "other/1.0/en-us:DC-Micro-5.4-cockpit",
                "sles/15-sp6/en-us:DC-SLE-Micro-5.5-admin",
            },
        ),
        ("<docservconfig/>", "nonexistent/1.0/en-us", 0, set()),
        (
            """<docservconfig>
                 <product productid='sles'>
                    <docset setid='15-sp6'/>
                 </product>
               </docservconfig>""",
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
def test_get_deliverable_from_doctype(
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
    deliverables = get_deliverable_from_doctype(xmlconfig, doctype)

    # Assert
    assert len(deliverables) == expected_count
    if expected_ids:
        assert {d.docsuite for d in deliverables} == expected_ids


@pytest.fixture
def deliverable() -> Deliverable:
    """Provide a mock Deliverable object for testing."""
    xml_string = """
    <docservconfig>
      <product productid="sles">
        <docset setid="15-SP7">
          <builddocs>
             <git remote="https://github.com/SUSE/doc-sle.git"/>
             <language default="1" lang="en-us">
                <branch>main</branch>
                <subdir>l10n/sles/en-us</subdir>
                <deliverable>
                    <dc>DC-SLES-deployment</dc>
                    <format html="1" pdf="1" single-html="0"/>
                </deliverable>
             </language>
          </builddocs>
        </docset>
      </product>
    </docservconfig>
    """
    root = etree.fromstring(xml_string)
    deliverable_node = root.find(".//deliverable")
    return Deliverable(deliverable_node)


@pytest.fixture
def stitchnode(deliverable: Deliverable) -> etree._ElementTree:
    """Build a minimal stitched `docservconfig` ElementTree from a Deliverable fixture.

    Provides the common product/docset/name/acronym structure used by tests.
    """
    prod_node = etree.Element("product", productid=deliverable.productid)
    name_el = etree.SubElement(prod_node, "name")
    name_el.text = "SUSE Linux Enterprise Server"
    etree.SubElement(prod_node, "acronym").text = "SLES"
    etree.SubElement(prod_node, "docset", setid=deliverable.docsetid)
    root = etree.Element("docservconfig")
    root.append(prod_node)
    return etree.ElementTree(root)


@pytest.mark.asyncio
class TestProcessDeliverable:
    """Tests for the process_deliverable function."""

    @pytest.fixture
    def mock_subprocess(self) -> Iterator[AsyncMock]:
        """Fixture to mock asyncio.create_subprocess_exec."""
        # 'docbuild.cli.cmd_metadata.asyncio.create_subprocess_exec',
        with patch.object(
            metaprocess_pkg.asyncio,
            "create_subprocess_exec",
            new_callable=AsyncMock,
        ) as mock:
            yield mock

    @pytest.fixture
    def setup_paths(self, tmp_path: Path, deliverable: Deliverable) -> dict:
        """Set up common paths and directories for tests."""
        paths = {
            "repo_dir": tmp_path / "repos",
            "temp_repo_dir": tmp_path / "temp_repos",
            "base_cache_dir": tmp_path / "cache",
            "meta_cache_dir": tmp_path / "cache" / "metadata",
        }
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)

        # Create a fake bare repo for the success/failure paths
        # (paths['repo_dir'] / deliverable.git.slug).mkdir()
        return paths

    @pytest.mark.parametrize(
        "scenario, setup_mocks, expected_result, expected_log",
        [
            (
                "success",
                lambda mocks: None,  # No special setup for success
                True,
                None,
            ),
            (
                "bare_repo_not_found",
                lambda mocks: mocks["managed_git_repo"].side_effect,
                False,
                "Bare repository not found",
            ),
            (
                "clone_fails",
                lambda mocks: setattr(
                    mocks["repo_instance"], "clone_bare", AsyncMock(return_value=False)
                ),
                False,
                "Failed to ensure bare repository",
            ),
            (
                "daps_fails",
                lambda mocks: mocks["subprocess"].__setattr__(
                    "return_value",
                    AsyncMock(
                        returncode=1,
                        communicate=AsyncMock(return_value=(b"", b"DAPS Error")),
                    ),
                ),
                False,
                "Error processing",
            ),
        ],
        ids=["success", "bare_repo_not_found", "clone_fails", "daps_fails"],
    )
    @patch.object(metaprocess_pkg, "edit_json")
    @patch.object(metaprocess_pkg, "ManagedGitRepo")
    async def test_process_deliverable_scenarios(
        self,
        mock_managed_git_repo: Mock,
        mock_edit_json: Mock,
        deliverable: Deliverable,
        setup_paths: dict,
        mock_subprocess: AsyncMock,
        caplog,
        scenario: str,
        setup_mocks: callable,
        expected_result: bool,
        expected_log: str | None,
    ):
        """Test various scenarios for process_deliverable."""
        # Arrange
        mock_repo_instance = AsyncMock()
        mock_managed_git_repo.return_value = mock_repo_instance
        mock_repo_instance.clone_bare.return_value = True
        mock_repo_instance.create_worktree.return_value = None

        mock_daps_proc = AsyncMock()
        mock_daps_proc.communicate.return_value = (b"", b"")
        mock_daps_proc.returncode = 0
        mock_subprocess.return_value = mock_daps_proc

        mock_json_data = {"docs": [{"format": {}, "lang": ""}]}
        mock_edit_json.return_value.__aenter__.return_value = mock_json_data
        mock_edit_json.return_value.__enter__.return_value = mock_json_data

        # Dynamically set up mocks for the specific scenario
        mocks = {
            "managed_git_repo": mock_managed_git_repo,
            "repo_instance": mock_repo_instance,
            "subprocess": mock_subprocess,
        }
        setup_mocks(mocks)

        if scenario != "bare_repo_not_found":
            (setup_paths["repo_dir"] / deliverable.git.slug).mkdir()

        dapstmpl = "daps --dc-file={dcfile} --output={output}"

        # Act
        result = await process_deliverable(
            deliverable=deliverable, dapstmpl=dapstmpl, **setup_paths
        )

        # Assert
        assert result is expected_result
        if expected_log:
            assert any(expected_log in record.message for record in caplog.records)


@pytest.mark.asyncio
class TestProcessDoctype:
    """Tests for the process_doctype function."""

    @pytest.fixture
    def mock_context(self, mock_envconfig: Mock) -> DocBuildContext:
        """Provide a mock DocBuildContext with necessary paths."""
        context = Mock(spec=DocBuildContext)
        # Assign the pre-configured mock_envconfig to the context
        context.envconfig = mock_envconfig
        return context

    @pytest.fixture
    def mock_root(self) -> etree._ElementTree:
        """Provide a mock XML root element for testing."""
        return etree.ElementTree(etree.fromstring("<docservconfig/>"))

    @patch.object(metaprocess_pkg, "process_deliverable", new_callable=AsyncMock)
    @patch.object(metaprocess_pkg, "get_deliverable_from_doctype")
    async def test_success_with_deliverables(
        self,
        mock_get_deliverables: Mock,
        mock_process_deliverable: AsyncMock,
        mock_root: etree._ElementTree,
        mock_context: DocBuildContext,
    ):
        """Test successful processing when deliverables are found."""
        doctype = Doctype.from_str("sles/15/en-us")
        # Correctly mock the nested git.url attribute
        mock_deliverable = Mock(
            spec=Deliverable, git=Mock(spec=Repo, url="gh://SUSE/doc-test")
        )
        mock_deliverables = [mock_deliverable, mock_deliverable]
        mock_get_deliverables.return_value = mock_deliverables
        # Ensure the mock returns an awaitable result
        mock_process_deliverable.return_value = True

        result = await process_doctype(
            mock_root, mock_context, doctype, exitfirst=False
        )

        assert not result
        mock_get_deliverables.assert_called_once_with(mock_root, doctype)
        assert mock_process_deliverable.call_count == 2

    @patch.object(metaprocess_pkg, "process_deliverable", new_callable=AsyncMock)
    @patch.object(metaprocess_pkg, "get_deliverable_from_doctype")
    async def test_no_deliverables_found(
        self,
        mock_get_deliverables: Mock,
        mock_process_deliverable: AsyncMock,
        mock_root: etree._ElementTree,
        mock_context: DocBuildContext,
    ):
        """Test behavior when no deliverables are found for the doctype."""
        doctype = Doctype.from_str("sles/15/en-us")
        mock_get_deliverables.return_value = []

        result = await process_doctype(mock_root, mock_context, doctype)

        assert not result
        mock_get_deliverables.assert_called_once_with(mock_root, doctype)
        mock_process_deliverable.assert_not_called()

    @patch.object(metaprocess_pkg, "get_deliverable_from_doctype")
    async def test_missing_paths_in_config_raises_error(
        self,
        mock_get_deliverables: Mock,
        mock_root: etree._ElementTree,
        mock_envconfig: Mock,
    ):
        """Test that an AttributeError is raised if required paths are missing."""
        doctype = Doctype.from_str("sles/15/en-us")
        mock_get_deliverables.return_value = [Mock(spec=Deliverable)]
        context_missing_path = Mock(spec=DocBuildContext)

        # Use the mock_envconfig and then delete the attribute to simulate missing
        del mock_envconfig.paths.repo_dir
        # Ensure other paths are set, even if repo_dir is missing
        mock_envconfig.paths.base_cache_dir = Path("/fake/cache")
        mock_envconfig.paths.meta_cache_dir = Path("/fake/cache/meta")
        mock_envconfig.paths.temp_repo_dir = Path("/fake/temp")
        context_missing_path.envconfig = mock_envconfig

        with pytest.raises(AttributeError):
            await process_doctype(mock_root, context_missing_path, doctype)

    @patch.object(metaprocess_pkg, "process_deliverable", new_callable=AsyncMock)
    @patch.object(metaprocess_pkg, "get_deliverable_from_doctype")
    @patch.object(metaprocess_pkg, "update_repositories", new_callable=AsyncMock)
    async def test_exitfirst_fails_fast(
        self,
        mock_update_repositories: AsyncMock,
        mock_get_deliverables: Mock,
        mock_process_deliverable: AsyncMock,
        mock_root: etree._ElementTree,
        mock_context: DocBuildContext,
    ):
        """When `exitfirst=True`, process_doctype should stop on first failure."""
        doctype = Doctype.from_str("sles/15/en-us")

        # Create two mock deliverables
        d1 = Mock(spec=Deliverable)
        d1.full_id = "sles/15/en-us:DC-ONE"
        d2 = Mock(spec=Deliverable)
        d2.full_id = "sles/15-en-us:DC-TWO"

        mock_get_deliverables.return_value = [d1, d2]

        # First call returns a failing tuple, second would be successful
        mock_process_deliverable.side_effect = [(False, d1), (True, d2)]

        # Prevent update_repositories from attempting real repo work
        mock_update_repositories.return_value = None

        failed = await process_doctype(mock_root, mock_context, doctype, exitfirst=True)

        # Expect the failing deliverable is reported
        assert failed == [d1]


@pytest.mark.asyncio
class TestProcessEmptyDoctypes:
    """Tests for the case when no doctypes are passed to process."""

    @patch.object(metaprocess_pkg, "store_productdocset_json", new_callable=Mock)
    @patch.object(metaprocess_pkg, "collect_files_flat", new_callable=Mock)
    @patch.object(metaprocess_pkg, "create_stitchfile", new_callable=AsyncMock)
    @patch.object(metaprocess_pkg, "process_doctype", new_callable=AsyncMock)
    async def test_process_empty_doctypes(
        self,
        mock_process_doctype: AsyncMock,
        mock_create_stitchfile: AsyncMock,
        mock_collect_files_flat: Mock,
        mock_store_json: Mock,
        mock_context_with_config_dir: DocBuildContext,
    ):
        """Test process function with an empty tuple of doctypes.

        This test ensures that when no doctypes are provided, the process
        correctly uses the default doctype and finds the relevant configuration
        files to proceed with metadata processing.
        """
        # This mock needs to represent the stitched XML config that
        # `collect_files_flat` will traverse. It needs at least one product
        # and docset to avoid the AttributeError.
        xml_string = """
        <docservconfig>
            <product productid="sles">
              <name>SUSE Linux Enterprise Server</name>
              <acronym>SLES</acronym>
              <docset setid="15-SP6"/>
            </product>
        </docservconfig>
        """
        mock_stitch_node = etree.ElementTree(etree.fromstring(xml_string))
        mock_create_stitchfile.return_value = mock_stitch_node

        mock_collect_files_flat.return_value = [
            (Doctype.from_str(DEFAULT_DELIVERABLES), "*", [Path("dummy.xml")])
        ]

        await process(mock_context_with_config_dir, doctypes=())

        # Assert that create_stitchfile was called
        mock_create_stitchfile.assert_called_once()
        # Assert that process_doctype was called with the default doctype
        mock_process_doctype.assert_called()
        # Assert that store_productdocset_json was called
        mock_store_json.assert_called()

    @patch.object(metaprocess_pkg, "store_productdocset_json", new_callable=Mock)
    @patch.object(metaprocess_pkg, "collect_files_flat", new_callable=Mock)
    @patch.object(metaprocess_pkg, "create_stitchfile", new_callable=AsyncMock)
    @patch.object(metaprocess_pkg, "process_doctype", new_callable=AsyncMock)
    async def test_no_doctypes_uses_default(
        self,
        mock_process_doctype: AsyncMock,
        mock_create_stitchfile: AsyncMock,
        mock_collect_files_flat: Mock,
        mock_store_json: Mock,
        mock_context_with_config_dir: DocBuildContext,
    ):
        """Test process uses a default doctype when none are provided.

        This test covers the successful execution path and the logic for handling
        an empty doctypes tuple.
        """
        # Arrange (use the fixture for the context)
        xml_string = """
        <docservconfig>
            <product productid="sles">
              <name>SUSE Linux Enterprise Server</name>
              <acronym>SLES</acronym>
              <docset setid="15-SP6"/>
            </product>
        </docservconfig>
        """
        mock_stitch_node = etree.ElementTree(etree.fromstring(xml_string))

        mock_create_stitchfile.return_value = mock_stitch_node
        mock_process_doctype.return_value = []
        mock_collect_files_flat.return_value = [
            (Doctype.from_str(DEFAULT_DELIVERABLES), "*", [Path("dummy.xml")])
        ]

        # Act and suppress console output during the test
        with patch.object(metaprocess_pkg, "stdout"):
            result = await process(mock_context_with_config_dir, doctypes=tuple())

        # Assert
        assert result == 0
        mock_create_stitchfile.assert_awaited_once()
        mock_store_json.assert_called()
        default_doctype = Doctype.from_str(DEFAULT_DELIVERABLES)
        mock_process_doctype.assert_awaited_once_with(
            mock_stitch_node,
            mock_context_with_config_dir,
            default_doctype,
            exitfirst=False,
            skip_repo_update=False,
        )

    @patch.object(metaprocess_pkg, "store_productdocset_json", new_callable=Mock)
    @patch.object(metaprocess_pkg, "collect_files_flat", new_callable=Mock)
    @patch.object(metaprocess_pkg, "create_stitchfile", new_callable=AsyncMock)
    @patch.object(metaprocess_pkg, "process_doctype", new_callable=AsyncMock)
    async def test_process_reports_failed_deliverables_and_returns_one(
        self,
        mock_process_doctype: AsyncMock,
        mock_create_stitchfile: AsyncMock,
        mock_collect_files_flat: Mock,
        mock_store_json: Mock,
        mock_context_with_config_dir: DocBuildContext,
        deliverable: Deliverable,
        stitchnode: etree._ElementTree,
    ):
        """When any deliverable fails, `process` should report and return 1.

        Use the existing `deliverable` fixture to construct the stitched XML
        instead of an inline XML string.
        """
        # Use stitched node fixture rather than constructing manually
        mock_create_stitchfile.return_value = stitchnode

        # Simulate a failing deliverable returned by process_doctype
        mock_deliverable = Mock(spec=Deliverable)
        mock_deliverable.full_id = (
            f"{deliverable.productid}/{deliverable.docsetid}/{deliverable.lang}:DC-FAIL"
        )
        mock_process_doctype.return_value = [mock_deliverable]

        # collect_files_flat won't be reached when failures exist, but
        # provide an empty list
        mock_collect_files_flat.return_value = []

        # Act: call process and capture console_err output
        with patch.object(metaprocess_pkg, "console_err") as mock_console_err:
            result = await process(mock_context_with_config_dir, doctypes=tuple())

        # Assert: process should return 1 and console_err should have been used
        assert result == 1
        assert mock_console_err.print.called


def test_store_productdocset_json_merges_and_writes(
    mock_context_with_config_dir: DocBuildContext,
    deliverable: Deliverable,
    stitchnode: etree._ElementTree,
):
    """Merge docs from metadata files and write product/docset JSON."""
    # Use the fixture's meta cache dir and create a metadata file there
    meta_cache_dir = mock_context_with_config_dir.envconfig.paths.meta_cache_dir
    meta_file = Path(meta_cache_dir) / "meta1.json"
    meta_file.write_text(json.dumps({"docs": [{"title": "Doc1"}]}), encoding="utf-8")

    doctype = Doctype.from_str(
        f"{deliverable.productid}/{deliverable.docsetid}/{deliverable.lang}"
    )

    # Patch collect_files_flat to return our file (relative path)
    with patch.object(
        metaprocess_pkg,
        "collect_files_flat",
        return_value=[(doctype, deliverable.docsetid, [Path("meta1.json")])],
    ):
        metaprocess_pkg.store_productdocset_json(
            mock_context_with_config_dir, [doctype], stitchnode
        )

    # Assert written JSON exists and contains merged document
    out_file = (
        Path(meta_cache_dir) / deliverable.productid / f"{deliverable.docsetid}.json"
    )
    assert out_file.exists()
    merged = json.loads(out_file.read_text(encoding="utf-8"))
    assert "documents" in merged
    assert merged["documents"][0]["title"] == "Doc1"


def test_store_productdocset_json_warns_on_empty_metadata(
    mock_context_with_config_dir: DocBuildContext,
    deliverable: Deliverable,
    stitchnode: etree._ElementTree,
):
    """If a metadata file is empty ({}), a warning is printed to console_err."""
    meta_cache_dir = mock_context_with_config_dir.envconfig.paths.meta_cache_dir
    meta_file = Path(meta_cache_dir) / "empty.json"
    meta_file.write_text("{}", encoding="utf-8")

    doctype = Doctype.from_str(
        f"{deliverable.productid}/{deliverable.docsetid}/{deliverable.lang}"
    )

    with (
        patch.object(
            metaprocess_pkg,
            "collect_files_flat",
            return_value=[(doctype, deliverable.docsetid, [Path("empty.json")])],
        ),
        patch.object(metaprocess_pkg, "console_err") as mock_console_err,
    ):
        metaprocess_pkg.store_productdocset_json(
            mock_context_with_config_dir, [doctype], stitchnode
        )

    # Expect a warning printed
    assert mock_console_err.print.called


def test_store_productdocset_json_handles_read_error(
    mock_context_with_config_dir: DocBuildContext,
    deliverable: Deliverable,
    stitchnode: etree._ElementTree,
):
    """If reading a metadata file raises, it should be caught and an error printed."""
    meta_cache_dir = mock_context_with_config_dir.envconfig.paths.meta_cache_dir
    bad_file = Path(meta_cache_dir) / "bad.json"
    # Write invalid JSON to cause json.load to raise
    bad_file.write_text("{ not json }", encoding="utf-8")

    doctype = Doctype.from_str(
        f"{deliverable.productid}/{deliverable.docsetid}/{deliverable.lang}"
    )

    with (
        patch.object(
            metaprocess_pkg,
            "collect_files_flat",
            return_value=[(doctype, deliverable.docsetid, [Path("bad.json")])],
        ),
        patch.object(metaprocess_pkg, "console_err") as mock_console_err,
    ):
        metaprocess_pkg.store_productdocset_json(
            mock_context_with_config_dir, [doctype], stitchnode
        )

    assert mock_console_err.print.called


@pytest.mark.parametrize(
    "setup_files, doctype_str, expected_file_count",
    [
        (
            {"en-us/sles/15-SP4": ["DC-file1", "DC-file2", "ignored.xml"]},
            "sles/15-SP4/en-us",
            2,
        ),
        (
            {
                "en-us/sles/15-SP4": ["DC-file-foo", "DC-file-bar"],
                "de-de/sles/15-SP4": ["DC-file-foo", "DC-file-bar"],
            },
            "sles/15-SP4/en-us,de-de",
            4,
        ),
        (
            {},  # No files created
            "sles/15-SP4/en-us",
            0,
        ),
    ],
    ids=["single_lang", "multi_lang", "no_files"],
)
def test_collect_files_flat(
    tmp_path: Path, setup_files, doctype_str, expected_file_count
):
    """Verify that collect_files_flat finds DC-* files correctly."""
    # Arrange
    cache_dir = tmp_path / "cache"
    for path_str, files in setup_files.items():
        dir_path = cache_dir / path_str
        dir_path.mkdir(parents=True, exist_ok=True)
        for f in files:
            (dir_path / f).touch()

    doctypes = [Doctype.from_str(doctype_str)]

    # Act
    results = list(collect_files_flat(doctypes, cache_dir))

    # Assert
    assert len(results) == (1 if expected_file_count > 0 else 0)
    if results:
        _, _, found_files = results[0]
        assert len(found_files) == expected_file_count


@pytest.mark.asyncio
class TestUpdateRepositories:
    """Tests for the update_repositories function."""

    @patch.object(metaprocess_pkg.ManagedGitRepo, "clone_bare", new_callable=AsyncMock)
    async def test_update_repositories_success(
        self, mock_clone_bare: AsyncMock, tmp_path: Path
    ):
        """Verify that update_repositories successfully 'clones' a repo."""
        # Arrange
        mock_deliverable = Mock(spec=Deliverable)
        mock_deliverable.git.url = "gh://SUSE/doc-test"
        mock_deliverable.git.slug = "SUSE-doc-test"
        deliverables = [mock_deliverable]
        repo_dir = tmp_path / "repos"
        mock_clone_bare.return_value = True

        from docbuild.cli.cmd_metadata.metaprocess import update_repositories

        # Act
        await update_repositories(deliverables, repo_dir)

        # Assert
        mock_clone_bare.assert_awaited_once()
        # mock_clone_bare.assert_awaited_once_with(expected_path)

    @patch.object(metaprocess_pkg.ManagedGitRepo, "clone_bare", new_callable=AsyncMock)
    async def test_update_repositories_failed(
        self, mock_clone_bare: AsyncMock, tmp_path: Path, caplog
    ):
        """Verify that update_repositories handles a git clone failure."""
        # Arrange
        mock_deliverable = Mock(spec=Deliverable)
        mock_deliverable.git.url = "gh://SUSE/non-existent-repo"
        mock_deliverable.git.slug = "SUSE-non-existent-repo"
        deliverables = [mock_deliverable]
        repo_dir = tmp_path / "repos"
        mock_clone_bare.return_value = False

        from docbuild.cli.cmd_metadata.metaprocess import update_repositories

        # Mock a failed clone by raising an exception
        # error_message = "fatal: repository not found"
        # mock_clone_bare.side_effect = Exception(error_message)

        # Act
        await update_repositories(deliverables, repo_dir)

        # Assert
        mock_clone_bare.assert_awaited_once()
        assert "Failed to update" in caplog.text
        # assert error_message in caplog.text
