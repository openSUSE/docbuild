"""Unit tests for docbuild.tasks.metadata.daps."""

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from lxml import etree  # type: ignore
import pytest

from docbuild.models.deliverable import Deliverable
import docbuild.tasks.metadata.daps as daps_pkg
from docbuild.tasks.metadata.daps import (
    get_daps_command,
    process_deliverable,
    update_metadata_json,
)


@pytest.fixture
def deliverable() -> Deliverable:
    """Provide a Deliverable built from a minimal docservconfig XML."""
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


def test_get_daps_command(tmp_path: Path):
    """Verify get_daps_command correctly interpolates the template."""
    worktree = tmp_path / "worktree"
    dcfile = worktree / "DC-test"
    output = tmp_path / "out.json"
    tmpl = "daps --builddir={builddir} --dc={dcfile} --output={output}"

    result = get_daps_command(worktree, dcfile, output, tmpl)

    assert result == [
        "daps",
        f"--builddir={worktree}",
        f"--dc={dcfile}",
        f"--output={output}",
    ]


def test_update_metadata_json_sets_category_at_document_level(
    deliverable: Deliverable,
    tmp_path: Path,
):
    """Category is written on the outer document object, not inside docs[0]."""
    outputjson = tmp_path / "metadata.json"
    outputjson.write_text("{}", encoding="utf-8")

    mock_json_data = {
        "docs": [{"format": {}, "lang": ""}],
    }

    with patch.object(daps_pkg, "edit_json") as mock_edit_json:
        mock_edit_json.return_value.__enter__.return_value = mock_json_data
        update_metadata_json(outputjson, deliverable)

    assert mock_json_data.get("category") == deliverable.xml.categoryid
    assert "category" not in mock_json_data["docs"][0]


def test_update_metadata_json_no_pdf(tmp_path: Path):
    """When pdf is not in the format dict, "pdf" key is not added (line 50->52 branch)."""
    outputjson = tmp_path / "metadata.json"
    outputjson.write_text("{}", encoding="utf-8")

    d = MagicMock()
    d.format = {"html": "1"}  # no pdf key
    d.xml.dcfile = "DC-FOO"
    d.xml.lang = "en-us"
    d.xml.categoryid = None
    d.paths.html_path = "/html"

    mock_json_data = {"docs": [{"format": {}, "lang": ""}]}

    with patch.object(daps_pkg, "edit_json") as mock_edit_json:
        mock_edit_json.return_value.__enter__.return_value = mock_json_data
        update_metadata_json(outputjson, d)

    assert "pdf" not in mock_json_data["docs"][0]["format"]


def test_update_metadata_json_with_single_html(tmp_path: Path):
    """When single-html is set, "single-html" key is written to format (line 53)."""
    outputjson = tmp_path / "metadata.json"
    outputjson.write_text("{}", encoding="utf-8")

    d = MagicMock()
    d.format = {"html": "1", "single-html": "1"}
    d.xml.dcfile = "DC-FOO"
    d.xml.lang = "en-us"
    d.xml.categoryid = None
    d.paths.html_path = "/html"
    d.paths.singlehtml_path = "/single-html"

    mock_json_data = {"docs": [{"format": {}, "lang": ""}]}

    with patch.object(daps_pkg, "edit_json") as mock_edit_json:
        mock_edit_json.return_value.__enter__.return_value = mock_json_data
        update_metadata_json(outputjson, d)

    assert mock_json_data["docs"][0]["format"]["single-html"] == "/single-html"


def test_update_metadata_json_with_category(tmp_path: Path):
    """When categoryid is set, it is written to jsonconfig (line 58)."""
    outputjson = tmp_path / "metadata.json"
    outputjson.write_text("{}", encoding="utf-8")

    d = MagicMock()
    d.format = {}
    d.xml.dcfile = "DC-FOO"
    d.xml.lang = "en-us"
    d.xml.categoryid = "cat.administration"
    d.paths.html_path = "/html"

    mock_json_data = {"docs": [{"format": {}, "lang": ""}]}

    with patch.object(daps_pkg, "edit_json") as mock_edit_json:
        mock_edit_json.return_value.__enter__.return_value = mock_json_data
        update_metadata_json(outputjson, d)

    assert mock_json_data.get("category") == "cat.administration"


@pytest.mark.asyncio
class TestProcessDeliverable:
    """Tests for the process_deliverable function."""

    @pytest.fixture
    def mock_subprocess(self) -> Iterator[AsyncMock]:
        """Mock asyncio.create_subprocess_exec inside the daps module."""
        with patch.object(
            daps_pkg.asyncio,
            "create_subprocess_exec",
            new_callable=AsyncMock,
        ) as mock:
            yield mock

    @pytest.fixture
    def setup_paths(self, tmp_path: Path) -> dict:
        """Create directories needed by process_deliverable."""
        paths = {
            "repo_dir": tmp_path / "repos",
            "tmp_repo_dir": tmp_path / "tmp_repos",
            "meta_cache_dir": tmp_path / "cache" / "metadata",
        }
        for p in paths.values():
            p.mkdir(parents=True, exist_ok=True)
        return paths

    @pytest.mark.parametrize(
        "scenario, make_bare_repo, clone_returns, daps_returncode, expected_success, expected_log",
        [
            ("success", True, True, 0, True, None),
            ("bare_repo_not_found", False, True, 0, False, "Bare repository not found"),
            ("clone_fails", True, False, 0, False, "Failed to ensure bare repository"),
            ("daps_fails", True, True, 1, False, "Error processing"),
        ],
        ids=["success", "bare_repo_not_found", "clone_fails", "daps_fails"],
    )
    @patch.object(daps_pkg, "edit_json")
    @patch.object(daps_pkg, "ManagedGitRepo")
    async def test_scenarios(
        self,
        mock_managed_git_repo: Mock,
        mock_edit_json: Mock,
        deliverable: Deliverable,
        setup_paths: dict,
        mock_subprocess: AsyncMock,
        caplog,
        scenario: str,
        make_bare_repo: bool,
        clone_returns: bool,
        daps_returncode: int,
        expected_success: bool,
        expected_log: str | None,
    ):
        """Test success, missing repo, clone failure, and DAPS failure scenarios."""
        mock_repo_instance = AsyncMock()
        mock_managed_git_repo.return_value = mock_repo_instance
        mock_repo_instance.clone_bare.return_value = clone_returns
        mock_repo_instance.create_worktree.return_value = None

        mock_daps_proc = AsyncMock()
        mock_daps_proc.communicate.return_value = (b"", b"")
        mock_daps_proc.returncode = daps_returncode
        mock_subprocess.return_value = mock_daps_proc

        mock_json_data = {"docs": [{"format": {}, "lang": ""}]}
        mock_edit_json.return_value.__enter__.return_value = mock_json_data

        if make_bare_repo:
            (setup_paths["repo_dir"] / deliverable.git.slug).mkdir()

        success, res_deliverable = await process_deliverable(
            deliverable=deliverable,
            repo_dir=setup_paths["repo_dir"],
            tmp_repo_dir=setup_paths["tmp_repo_dir"],
            meta_cache_dir=setup_paths["meta_cache_dir"],
            dapstmpl="daps --dc-file={dcfile} --output={output}",
        )

        assert success is expected_success
        assert res_deliverable == deliverable
        if expected_log:
            assert any(expected_log in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_prebuilt_deliverable_skipped(
        self, tmp_path: Path, deliverable: Deliverable
    ):
        """A deliverable with no DC file (prebuilt) is skipped with success=True."""
        deliverable.xml.dcfile = None  # type: ignore[assignment]

        success, res_deliverable = await process_deliverable(
            deliverable=deliverable,
            repo_dir=tmp_path / "repos",
            tmp_repo_dir=tmp_path / "tmp_repos",
            meta_cache_dir=tmp_path / "cache",
            dapstmpl="daps -d {dcfile} metadata",
        )

        assert success is True
        assert res_deliverable is deliverable

    @patch.object(daps_pkg, "ManagedGitRepo")
    async def test_create_worktree_failure(
        self,
        mock_managed_git_repo: Mock,
        deliverable: Deliverable,
        setup_paths: dict,
        caplog,
    ):
        """When create_worktree raises, the error is wrapped and (False, deliverable)
        is returned (lines 119-120 coverage)."""
        mock_repo_instance = AsyncMock()
        mock_managed_git_repo.return_value = mock_repo_instance
        mock_repo_instance.clone_bare.return_value = True
        mock_repo_instance.create_worktree.side_effect = RuntimeError("git clone failed")

        (setup_paths["repo_dir"] / deliverable.git.slug).mkdir()

        success, res_deliverable = await process_deliverable(
            deliverable=deliverable,
            repo_dir=setup_paths["repo_dir"],
            tmp_repo_dir=setup_paths["tmp_repo_dir"],
            meta_cache_dir=setup_paths["meta_cache_dir"],
            dapstmpl="daps --dc-file={dcfile} --output={output}",
        )

        assert success is False
        assert res_deliverable is deliverable
        assert any("Error processing" in r.message for r in caplog.records)
