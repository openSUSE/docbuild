from unittest.mock import AsyncMock, MagicMock, patch

from lxml import etree
import pytest

from docbuild.models.doctype import Doctype
from docbuild.models.repo import Repo
from docbuild.tasks import check
from docbuild.tasks.check import check_repository_files

STUB_TREE = etree.ElementTree(
    etree.fromstring('<portal><product xml:id="sles"><docset path="16.0"/></product></portal>')
)
"""Minimal portal tree so that wildcard expansion finds ``sles/16.0``."""


@pytest.fixture
def mock_deliverable():
    """Create a mock Deliverable object with required nested attributes."""
    deli = MagicMock()
    deli.xml.product_id = "sles"
    deli.xml.docset_path = "16.0"
    deli.xml.lang = "en-us"
    deli.xml.dcfile = "README.md"

    deli.xml.is_xref = False
    deli.xml.final_target_node = None
    deli.lang_is_default = True
    deli.subdir = ""
    deli.branch = "main"
    deli.git = Repo("gh://org/repo")
    return deli

@patch.object(check, "parse_portal_config", new_callable=AsyncMock)
@patch.object(check, "get_deliverable_from_doctype")
@patch.object(check, "ManagedGitRepo")
async def test_check_repository_files_all_found(
    mock_repo_class, mock_get_deli, mock_parse_portal_config, tmp_path, mock_deliverable
):
    """Test full process when all files exist in the repo."""
    mock_parse_portal_config.return_value = STUB_TREE
    mock_get_deli.return_value = [mock_deliverable]

    mock_repo = AsyncMock()
    mock_repo.clone_bare.return_value = True
    mock_repo.ls_tree.return_value = ["README.md"]
    mock_repo_class.return_value = mock_repo

    main_portal_config = tmp_path / "config.xml"
    main_portal_config.write_text("<xml/>")
    repo_root = tmp_path / "repos"

    result = await check_repository_files(main_portal_config, repo_root, doctypes=None)

    assert result == [("sles/16.0/en-us", "README.md", "gh://org/repo", "found")]
    mock_repo.clone_bare.assert_called_once()
    mock_repo.ls_tree.assert_called_with("main")


@patch.object(check, "parse_portal_config", new_callable=AsyncMock)
@patch.object(check, "get_deliverable_from_doctype")
@patch.object(check, "ManagedGitRepo")
async def test_check_repository_files_missing(
    mock_repo_class, mock_get_deli, mock_parse_portal_config, tmp_path, mock_deliverable
):
    """Test full process when a file is missing in the repo."""
    mock_parse_portal_config.return_value = STUB_TREE
    mock_get_deli.return_value = [mock_deliverable]

    mock_repo = AsyncMock()
    mock_repo.clone_bare.return_value = True
    mock_repo.ls_tree.return_value = ["LICENSE"] # README.md is missing
    mock_repo_class.return_value = mock_repo

    main_portal_config = tmp_path / "config.xml"
    main_portal_config.write_text("<xml/>")
    repo_root = tmp_path / "repos"

    result = await check_repository_files(main_portal_config, repo_root, doctypes=None)

    assert ("sles/16.0/en-us", "README.md", "gh://org/repo", "missing") in result


@patch.object(check, "parse_portal_config", new_callable=AsyncMock)
@patch.object(check, "get_deliverable_from_doctype")
@patch.object(check, "ManagedGitRepo")
async def test_process_git_failure(
    mock_repo_class, mock_get_deli, mock_parse_portal_config, tmp_path, mock_deliverable
):
    """Test coverage for the branch where Git cloning/fetching fails."""
    mock_parse_portal_config.return_value = STUB_TREE
    mock_get_deli.return_value = [mock_deliverable]

    mock_repo = AsyncMock()
    mock_repo.clone_bare.return_value = False # Simulate failure
    mock_repo_class.return_value = mock_repo

    main_portal_config = tmp_path / "config.xml"
    main_portal_config.write_text("<xml/>")
    repo_root = tmp_path / "repos"

    result = await check_repository_files(main_portal_config, repo_root, doctypes=None)

    assert ("sles/16.0/en-us", "README.md", "gh://org/repo", "missing") in result


@patch.object(check, "parse_portal_config", new_callable=AsyncMock)
@patch.object(check, "get_deliverable_from_doctype")
async def test_process_no_deliverables_found(mock_get_deli, mock_parse_portal_config, tmp_path):
    """Test path where stitch tree returns no deliverables."""
    mock_parse_portal_config.return_value = MagicMock()
    mock_get_deli.return_value = [] # No deliverables

    main_portal_config = tmp_path / "config.xml"
    main_portal_config.write_text("<xml/>")
    repo_root = tmp_path / "repos"

    result = await check_repository_files(main_portal_config, repo_root, doctypes=None)
    assert result == []


@patch.object(check, "parse_portal_config", new_callable=AsyncMock)
async def test_process_no_xml_files(mock_parse_portal_config, tmp_path):
    """Verify behavior when the main portal config is missing."""
    main_portal_config = tmp_path / "missing.xml"
    repo_root = tmp_path / "repos"

    result = await check_repository_files(main_portal_config, repo_root, doctypes=None)
    assert result == []
    mock_parse_portal_config.assert_not_awaited()


@patch.object(check, "parse_portal_config", new_callable=AsyncMock)
@patch.object(check, "get_deliverable_from_doctype")
@patch.object(check, "ManagedGitRepo")
async def test_check_repository_files_with_explicit_doctypes(
    mock_repo_class, mock_get_deli, mock_parse_portal_config, tmp_path, mock_deliverable
):
    """Test coverage for providing explicit doctypes instead of defaulting."""
    mock_parse_portal_config.return_value = STUB_TREE
    mock_get_deli.return_value = [mock_deliverable]

    mock_repo = AsyncMock()
    mock_repo.clone_bare.return_value = True
    mock_repo.ls_tree.return_value = ["README.md"]
    mock_repo_class.return_value = mock_repo

    main_portal_config = tmp_path / "config.xml"
    main_portal_config.write_text("<xml/>")

    # Passing an actual list bypasses the "if not doctypes:" block
    explicit_doctypes = [Doctype.from_str("sles/16.0/en-us")]

    result = await check_repository_files(
        main_portal_config, tmp_path / "repos", doctypes=explicit_doctypes
    )

    assert [status for *_, status in result] == ["found"]


PORTAL_XML = """<portal>
  <product xml:id="sles" path="sles">
    <name>SUSE Linux Enterprise Server</name>
    <acronym>SLES</acronym>
    <docset xml:id="sles-16-0" path="16.0">
      <resources>
        <git remote="gh://suse/doc-modular"/>
        <locale lang="en-us">
          <branch>main</branch>
          <deliverable><dc file="DC-keg"/><format html="1"/></deliverable>
          <deliverable><dc file="DC-SLE"/><format html="1"/></deliverable>
          <deliverable><xref linkend="sles"/></deliverable>
        </locale>
        <locale lang="de-de">
          <branch>de-branch</branch>
          <subdir>de</subdir>
        </locale>
      </resources>
    </docset>
  </product>
</portal>
"""


@pytest.fixture
def portal_config(tmp_path):
    """Write the sample portal config and return its path."""
    path = tmp_path / "portal.xml"
    path.write_text(PORTAL_XML)
    return path


@pytest.fixture
def mock_git(monkeypatch):
    """Replace ManagedGitRepo with a mock that lists two files on any branch."""
    repo = AsyncMock()
    repo.clone_bare.return_value = True
    repo.has_branch.return_value = True
    repo.ls_tree.return_value = ["DC-keg", "DC-SLE", "de/DC-keg"]
    monkeypatch.setattr(check, "ManagedGitRepo", MagicMock(return_value=repo))
    return repo


async def test_translation_checked_on_locale_branch(portal_config, tmp_path, mock_git):
    """Translations use the locale's branch and subdir and derive from English."""
    doctypes = [Doctype.from_str("sles/16.0/de-de")]

    result = await check_repository_files(portal_config, tmp_path, doctypes)

    assert result == [
        ("sles/16.0/de-de", "DC-keg", "gh://suse/doc-modular", "found"),
        ("sles/16.0/de-de", "DC-SLE", "gh://suse/doc-modular", "skipped"),
    ]
    mock_git.has_branch.assert_called_with("de-branch")
    mock_git.ls_tree.assert_called_with("de-branch")


async def test_wildcard_language_is_expanded(portal_config, tmp_path, mock_git):
    """A ``*`` language is expanded to the locales of the portal."""
    doctypes = [Doctype.from_str("sles/16.0/*")]

    result = await check_repository_files(portal_config, tmp_path, doctypes)

    identifiers = {identifier for identifier, *_ in result}
    assert identifiers == {"sles/16.0/en-us", "sles/16.0/de-de"}


async def test_missing_translation_branch_is_skipped(portal_config, tmp_path, mock_git):
    """A missing translation branch skips translations and fails English files."""
    mock_git.has_branch.return_value = False
    doctypes = [Doctype.from_str("sles/16.0/de-de")]

    result = await check_repository_files(portal_config, tmp_path, doctypes)

    assert {status for *_, status in result} == {"skipped"}
    mock_git.ls_tree.assert_not_called()


async def test_linked_product_is_listed(portal_config, tmp_path, mock_git):
    """A reference to a product is listed with the ``linked`` status."""
    doctypes = [Doctype.from_str("sles/16.0/en-us")]

    result = await check_repository_files(portal_config, tmp_path, doctypes)

    assert ("sles/16.0/en-us", "sles", "", "linked") in result
    assert ("sles/16.0/en-us", "DC-keg", "gh://suse/doc-modular", "found") in result


async def test_inaccessible_repository_fails_english(portal_config, tmp_path, mock_git):
    """An unreachable repository reports English files as missing."""
    mock_git.clone_bare.return_value = False
    doctypes = [Doctype.from_str("sles/16.0/en-us")]

    result = await check_repository_files(portal_config, tmp_path, doctypes)

    assert ("sles/16.0/en-us", "DC-keg", "gh://suse/doc-modular", "missing") in result
    mock_git.ls_tree.assert_not_called()


async def test_deliverables_without_dc_or_repository_are_ignored(tmp_path, mock_git):
    """Prebuilt deliverables and deliverables without a repository are not checked."""
    config = tmp_path / "portal.xml"
    config.write_text(
        """<portal>
  <product xml:id="sles" path="sles">
    <acronym>SLES</acronym>
    <docset xml:id="sles-16-0" path="16.0">
      <resources>
        <locale lang="en-us">
          <branch>main</branch>
          <deliverable><prebuilt/></deliverable>
          <deliverable><dc file="DC-SLE"/></deliverable>
        </locale>
      </resources>
    </docset>
  </product>
</portal>"""
    )

    result = await check_repository_files(
        config, tmp_path, [Doctype.from_str("sles/16.0/en-us")]
    )

    assert result == []
    mock_git.clone_bare.assert_not_called()


async def test_translation_without_any_branch_is_skipped(tmp_path, mock_git):
    """A translation without a branch is skipped instead of aborting the check."""
    config = tmp_path / "portal.xml"
    config.write_text(
        """<portal>
  <product xml:id="sles" path="sles">
    <acronym>SLES</acronym>
    <docset xml:id="sles-16-0" path="16.0">
      <resources>
        <git remote="gh://suse/doc-modular"/>
        <locale lang="en-us">
          <deliverable><dc file="DC-SLE"/></deliverable>
        </locale>
        <locale lang="de-de"/>
      </resources>
    </docset>
  </product>
</portal>"""
    )

    result = await check_repository_files(
        config, tmp_path, [Doctype.from_str("sles/16.0/de-de")]
    )

    assert result == []


PREBUILT_XML = """<portal>
  <product xml:id="cloudnative" path="cloudnative">
    <acronym>CN</acronym>
    <docset xml:id="rancher-manager" path="rancher-manager">
      <resources>
        <locale lang="en-us">
          <branch>main</branch>
          <deliverable type="prebuilt">
            <prebuilt>
              <url format="html" href="/en/cloudnative/rancher-manager/html/guide/index.html"/>
            </prebuilt>
          </deliverable>
        </locale>
      </resources>
    </docset>
  </product>
</portal>
"""


async def test_prebuilt_found_and_missing(tmp_path):
    """Prebuilt deliverables are checked for their HTML file below prebuilt_dir."""
    config = tmp_path / "portal.xml"
    config.write_text(PREBUILT_XML)
    prebuilt_dir = tmp_path / "prebuilt"
    html = prebuilt_dir / "en/cloudnative/rancher-manager/html/guide/index.html"
    html.parent.mkdir(parents=True)
    html.write_text("<html/>")
    doctypes = [Doctype.from_str("cloudnative/rancher-manager/en-us")]

    found = await check_repository_files(config, tmp_path, doctypes, prebuilt_dir)
    assert found == [
        (
            "cloudnative/rancher-manager/en-us",
            "/en/cloudnative/rancher-manager/html/guide/index.html",
            "",
            "found",
        )
    ]

    missing = await check_repository_files(config, tmp_path, doctypes, tmp_path / "none")
    assert [status for *_, status in missing] == ["missing"]
