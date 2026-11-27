"""Unit tests for docbuild.tasks.build.runner."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from lxml import etree  # type: ignore
import pytest
import yaml

from docbuild.cli.defaults import DEFAULT_ENV_CONFIG
from docbuild.exceptions import NoDeliverablesError
from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
import docbuild.tasks.build.runner as build_runner
from docbuild.tasks.build.runner import (
    build_format,
    generate_llmstxt,
    process,
    process_doctype,
    process_single_deliverable,
)
from docbuild.tasks.worktrees import process_with_shared_worktrees
from docbuild.utils.sync import RsyncOptions


class SortableMock(Mock):
    """A Mock that supports sorting by the full_id attribute."""

    def __lt__(self, other: object) -> bool:
        return str(getattr(self, "full_id", "")) < str(getattr(other, "full_id", ""))


@pytest.fixture
def empty_xml_root() -> etree._ElementTree:
    """Return a minimal empty ElementTree."""
    return etree.ElementTree(etree.fromstring("<docservconfig/>"))


@pytest.mark.asyncio
async def test_build_format_no_dcfile(tmp_path: Path) -> None:
    """Test that missing DC file safely raises error."""
    mock_d = Mock(spec=Deliverable, full_id="test:DC")
    mock_d.xml.dcfile = None

    with pytest.raises(AssertionError, match=r"Deliverable must have a DC file\."):
        await build_format(mock_d, "html", tmp_path, tmp_path, "daps -d {dcfile} html")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("stdout", "stderr", "expected"),
    [
        ("", "Build crashed", "Build crashed"),
        ("Validation failed", "", "Validation failed"),
        (
            "Validation details\nInvalid document",
            "Build crashed",
            "Validation details\nInvalid document\nBuild crashed",
        ),
        ("", "", "No output captured."),
    ],
    ids=["stderr", "stdout", "both-streams", "no-output"],
)
async def test_build_format_failure(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    stdout: str,
    stderr: str,
    expected: str,
) -> None:
    """Include all captured DAPS diagnostics and the failure exit code."""
    mock_d = Mock(spec=Deliverable, full_id="test:DC")
    mock_d.xml.dcfile = "DC-test"
    mock_d.xml.translations = {"en-us"}

    with patch.object(build_runner, "run_command", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = Mock(returncode=1, stdout=stdout, stderr=stderr)

        success, err = await build_format(
            mock_d, "html", tmp_path, tmp_path, "daps -d {dcfile} --builddir {builddir} html"
        )
        assert success is False
        assert err == expected
        assert expected in caplog.text
        assert "exit code 1" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("translations", "expected_parameter"),
    [
        ({"en-us"}, "canonicals.hreflangs=en-us"),
        ({"en-us", "de-de"}, "'canonicals.hreflangs=de-de en-us'"),
    ],
    ids=["single-language", "multiple-languages"],
)
async def test_build_format_default_template_has_no_runtime_braces(
    translations: set[str], expected_parameter: str
) -> None:
    """Verify build templates receive runtime values."""
    mock_d = Mock(spec=Deliverable, full_id="test:DC")
    mock_d.xml.dcfile = "DC-test"
    mock_d.xml.translations = translations
    cwd = Path(".")
    build_dir = Path("build")
    template = str(DEFAULT_ENV_CONFIG["build"]["daps"]["html"]).replace(
        "{build.daps.command}", "daps"
    )

    with patch.object(build_runner, "run_command", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="Build OK", stderr="")

        success, _ = await build_format(
            mock_d,
            "html",
            cwd,
            build_dir,
            template,
        )

    assert success is True
    mock_run.assert_awaited_once_with(
        [
            "daps",
            "--builddir",
            "build",
            "-d",
            "DC-test",
            "html",
                "--stringparam",
                expected_parameter,
            ],
        cwd=cwd,
    )


@pytest.mark.parametrize(
    "rsync_options", [None, RsyncOptions(exclude=[]), RsyncOptions(exclude=["*.tmp"])]
)
@pytest.mark.asyncio
async def test_process_single_deliverable_success(tmp_path: Path, rsync_options: RsyncOptions | None) -> None:
    """Test successful build execution and rsync for a single deliverable."""
    mock_deliverable = Mock(
        spec=Deliverable,
        full_id="sles/15:TEST",
        subdir="subdir",
        format={"html": True, "pdf": False},
        branch="main",
    )
    mock_deliverable.xml.dcfile = "DC-test"
    mock_deliverable.xml.product_id = "sles"
    mock_deliverable.xml.docset_path = "15"
    mock_deliverable.xml.lang = "en-us"
    mock_deliverable.xml.translations = {"en-us", "de-de"}
    mock_deliverable.make_safe_name.return_value = "safe_sles_15_TEST"

    daps_tmpls = {"html": "daps -d {dcfile} --builddir {builddir} {format}"}

    with (
        patch.object(build_runner, "run_command", new_callable=AsyncMock) as mock_run,
        patch.object(build_runner, "rsync", new_callable=AsyncMock) as mock_rsync,
    ):
        mock_run.return_value = Mock(returncode=0, stdout="Build OK", stderr="")
        mock_rsync.return_value = Mock(returncode=0, stdout="Sync OK", stderr="")

        success, _ = await process_single_deliverable(
            mock_deliverable,
            tmp_path,
            tmp_path,
            tmp_path / "target",
            "{{product}}/{{docset}}/{{lang}}",
            daps_tmpls,
            rsync_options=rsync_options,
        )

        assert success is True
        mock_run.assert_called_once()
        mock_rsync.assert_called_once()

        expected_target = tmp_path / "target/sles/15/en-us/html"
        assert expected_target.is_dir()

        # rsync still receives the build directory and the local target
        src, dest = mock_rsync.call_args.args
        src_path = Path(src)
        assert src_path.is_absolute()
        assert src_path.parts[-1].endswith("_html")
        assert dest == expected_target
        assert mock_rsync.call_args.kwargs == {"content_only": True, "options": rsync_options}


@pytest.mark.asyncio
@patch("docbuild.tasks.worktrees.ManagedGitRepo", autospec=True)
async def test_process_with_shared_worktrees_success(
    mock_mgr_class: Mock, tmp_path: Path
) -> None:
    """Test the reusable grouping abstraction creates worktrees and executes the pipeline."""
    mock_d = SortableMock(spec=Deliverable, full_id="sles/15:A", branch="main")
    mock_d.git.url = "https://git.test"
    mock_d.make_safe_name.return_value = "safe"

    mock_mgr_instance = mock_mgr_class.return_value
    mock_mgr_instance.create_worktree = AsyncMock()

    async def dummy_process(d: Deliverable, wt: Path) -> tuple[bool, Deliverable]:
        return True, d

    failed = await process_with_shared_worktrees(
        [mock_d],
        tmp_path,
        tmp_path,
        max_workers=2,
        semaphore=asyncio.Semaphore(2),
        process_single_func=dummy_process,
    )

    assert failed == []
    mock_mgr_instance.create_worktree.assert_called_once()


@pytest.mark.asyncio
async def test_process_doctype_build(
    empty_xml_root: etree._ElementTree, tmp_path: Path
) -> None:
    """Test process_doctype pipeline for build task."""
    doctype = Doctype.from_str("sles/15/en-us")
    d1 = SortableMock(
        spec=Deliverable,
        full_id="sles/15:A",
        subdir="",
        branch="main",
        format={"html": True},
    )
    d1.xml.is_dc = True
    d1.xml.is_xref = False
    d1.xml.dcfile = "DC-test"
    d1.git = None
    daps_tmpls = {"html": "daps {format}"}

    with (
        patch.object(build_runner, "get_deliverable_from_doctype", return_value=[d1]),
        patch.object(build_runner, "process_with_shared_worktrees", new_callable=AsyncMock) as mock_group_build,
        patch.object(build_runner, "update_repositories", new_callable=AsyncMock) as mock_update,
    ):
        mock_group_build.return_value = []
        failed = await process_doctype(
            root=empty_xml_root,
            doctype=doctype,
            repo_dir=tmp_path,
            tmp_repo_dir=tmp_path,
            tmp_build_base_dir=tmp_path,
            target_base_dir=tmp_path / "target",
            target_dir_dyn="{product}",
            max_workers=2,
            semaphore=asyncio.Semaphore(2),
            daps_tmpls=daps_tmpls,
            skip_repo_update=False,
            rsync_options=RsyncOptions(exclude=["*.tmp"]),
        )

        assert failed == []
        mock_group_build.assert_called_once()
        mock_update.assert_called_once()


@pytest.mark.asyncio
async def test_process_doctype_without_deliverables_raises(
    empty_xml_root: etree._ElementTree,
    tmp_path: Path,
) -> None:
    """Raise and skip the build when a doctype matches no deliverables."""
    doctype = Doctype.from_str("sles/16.0/en-us")

    with (
        patch.object(build_runner, "process_with_shared_worktrees", new_callable=AsyncMock) as mock_group_build,
        patch.object(build_runner, "update_repositories", new_callable=AsyncMock) as mock_update,
        pytest.raises(NoDeliverablesError, match=r"sles/16\.0"),
    ):
        await process_doctype(
            root=empty_xml_root,
            doctype=doctype,
            repo_dir=tmp_path,
            tmp_repo_dir=tmp_path,
            tmp_build_base_dir=tmp_path,
            target_base_dir=tmp_path / "target",
            target_dir_dyn="{product}",
            max_workers=1,
            semaphore=asyncio.Semaphore(1),
            daps_tmpls={},
        )

    mock_group_build.assert_not_called()
    mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_process_without_deliverables_fails(tmp_path: Path) -> None:
    """Return a non-zero exit code and print an error for unmatched doctypes."""
    doctypes = [Doctype.from_str("sles/16.0/en-us"), Doctype.from_str("sles/16.1/en-us")]

    async def fake_process_doctype(root: object, dt: Doctype, *args: object, **kwargs: object) -> list:
        if "16.0" in str(dt):
            raise NoDeliverablesError(str(dt))
        return []

    with (
        patch.object(build_runner, "parse_portal_config", new_callable=AsyncMock),
        patch.object(build_runner, "process_doctype", side_effect=fake_process_doctype) as mock_pd,
        patch.object(build_runner, "report_unmatched_doctypes") as mock_report,
    ):
        result = await process(
            tmp_path, tmp_path, tmp_path, tmp_path,
            tmp_path / "target", "{product}",
            1, doctypes, {},
        )

    assert result == 1
    assert mock_pd.call_count == 2
    mock_report.assert_called_once_with([doctypes[0]])


@pytest.mark.asyncio
async def test_process_entry_point(tmp_path: Path) -> None:
    """Test the main process() orchestration function."""
    doctype = Doctype.from_str("sles/15/en-us")
    daps_tmpls = {"html": "daps html"}

    with (
        patch.object(build_runner, "parse_portal_config", new_callable=AsyncMock),
        patch.object(build_runner, "process_doctype", new_callable=AsyncMock) as mock_pd,
    ):
        mock_pd.return_value = []
        result = await process(
            tmp_path, tmp_path, tmp_path, tmp_path,
            tmp_path / "target", "{product}",
            1, [doctype], daps_tmpls,
            rsync_options=RsyncOptions(exclude=[]),
        )
        assert result == 0
        assert mock_pd.call_args.kwargs["rsync_options"].exclude == []

        mock_pd.return_value = [Mock(spec=Deliverable)]
        result = await process(
            tmp_path, tmp_path, tmp_path, tmp_path,
            tmp_path / "target", "{product}",
            1, [doctype], daps_tmpls
        )
        assert result == 1


@pytest.fixture
def llms_deliverable() -> Deliverable:
        """Return an XML-backed deliverable for LLM frontmatter tests."""
        root = etree.fromstring("""
                <portal schemaversion="7.0">
                    <product xml:id="sles">
                        <name>SUSE Linux Enterprise Server</name>
                        <docset xml:id="sles-16.1" path="16.1">
                            <version>16.1</version>
                            <resources>
                                <locale lang="en-us">
                                    <branch>main</branch>
                                    <deliverable xml:id="test-deliverable">
                                        <dc file="DC-test"><format html="1"/></dc>
                                    </deliverable>
                                </locale>
                            </resources>
                        </docset>
                    </product>
                </portal>
        """)
        node = root.find(".//deliverable")
        assert node is not None
        return Deliverable(node)


@pytest.mark.asyncio
async def test_generate_llmstxt_yaml_frontmatter_extraction(
        tmp_path: Path, llms_deliverable: Deliverable
) -> None:
    """Test YAML frontmatter extraction, relative path URL building, and date handling."""
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # Create nested HTML file to verify rel_path.as_posix() in URL
    html_file = target_dir / "en-us" / "sles" / "16.1" / "html" / "books" / "chapter.html"
    html_file.parent.mkdir(parents=True, exist_ok=True)

    html_content = """<!DOCTYPE html>
    <html>
    <head>
        <script type="application/ld+json">
        {
            "name": "Dynamic Chapter Title",
            "description": "Dynamic chapter description.",
            "dateModified": "2026-02-15T12:00:00Z"
        }
        </script>
    </head>
    <body><h1>Test Content</h1><p>Some text</p></body>
    </html>"""
    html_file.write_text(html_content, encoding="utf-8")

    await generate_llmstxt(
            deliverable=llms_deliverable,
            target_base_dir=target_dir,
            build_llmstxt=True,
            llmstxt_dir="docs",
            canonical_domain="https://doc.example.com",
        )

    md_file = target_dir / "docs" / "en-us" / "sles" / "16.1" / "html" / "books" / "chapter.md"
    assert md_file.exists()

    content = md_file.read_text(encoding="utf-8")
    assert content.startswith("---")

    frontmatter_raw = content.split("---")[1]
    data = yaml.safe_load(frontmatter_raw)

    assert data["title"] == "Dynamic Chapter Title"
    assert data["description"] == "Dynamic chapter description."
    assert "source_url" not in data
    assert data["product"] == "SUSE Linux Enterprise Server"
    assert data["version"] == "16.1"
    assert "language" not in data
    assert data["dateModified"] == "2026-02-15T12:00:00Z"
    assert "generator" not in data
    assert "deliverable_id" not in data


@pytest.mark.asyncio
@pytest.mark.parametrize(
        ("category", "expected"),
        [
                ("administration", ["administration"]),
                ("administration security", ["administration", "security"]),
                (None, []),
        ],
        ids=["single", "multiple", "missing"],
)
async def test_generate_llmstxt_assigned_categories(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    category: str | None,
    expected: list[str],
) -> None:
        """Serialize assigned category IDs, not product category XML elements."""
        root = etree.fromstring("""
                <docservconfig>
                    <product xml:id="sles">
                        <categories>
                            <category>
                                <language xml:id="administration"><title>Administration</title></language>
                                <language xml:id="security"><title>Security</title></language>
                                <language xml:id="unused"><title>Unused</title></language>
                            </category>
                        </categories>
                        <docset xml:id="sles-16.1" path="16.1">
                        <version>16.1</version>
                            <resources>
                                <locale lang="en-us">
                                    <branch>main</branch>
                                    <deliverable><dc file="DC-test"/></deliverable>
                                </locale>
                            </resources>
                        </docset>
                    </product>
                </docservconfig>
        """)
        node = root.find(".//deliverable")
        assert node is not None
        if category is not None:
                node.set("category", category)
        html_file = tmp_path / "en-us" / "sles" / "16.1" / "html" / "index.html"
        html_file.parent.mkdir(parents=True, exist_ok=True)
        html_file.write_text(
                "<html><head><title>Test</title></head><body>Content</body></html>",
                encoding="utf-8",
        )

        caplog.set_level("DEBUG", logger="docbuild.tasks.metadata.prebuilt")
        await generate_llmstxt(
            deliverable=Deliverable(node),
            target_base_dir=tmp_path,
            build_llmstxt=True,
            llmstxt_dir="docs",
        )

        content = (tmp_path / "docs" / "en-us" / "sles" / "16.1" / "html" / "index.md").read_text(encoding="utf-8")
        data = yaml.safe_load(content.split("---")[1])
        if expected:
                assert data["categories"] == expected
        else:
                assert "categories" not in data
        assert "/docs/en-us/sles/16.1/html/index.md" in html_file.read_text(encoding="utf-8")
        assert "/docs/en-us/sles/16.1/html/index.md" in (tmp_path / "docs" / "llms.txt").read_text(encoding="utf-8")
        assert f"No JSON-LD block found in {html_file}" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("html_head", "expected_warning"),
    [
        ("", "No JSON-LD block found"),
        (
            '<script type="application/ld+json">{invalid json</script>',
            "Invalid JSON-LD",
        ),
        (
            '<script type="application/ld+json">["not", "a", "dict"]</script>',
            "is not a JSON object",
        ),
        (
            '<script type="application/ld+json">{"name": "Only Name"}</script>',
            "Missing JSON-LD field(s) description, dateCreated, dateModified, datePublished",
        ),
        (
            '<script type="application/ld+json">{"name": 123}</script>',
            "Invalid JSON-LD fields",
        ),
        (
            '<script type="application/ld+json">{"name": "Valid", "dateModified": "not-a-date"}</script>',
            "Invalid JSON-LD fields",
        ),
    ],
    ids=["no-json-ld", "invalid-json-ld", "non-object-json-ld", "missing-fields", "invalid-field-type", "invalid-date-format"],
)
async def test_generate_llmstxt_warns_on_missing_or_invalid_json_ld(
    tmp_path: Path,
    llms_deliverable: Deliverable,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    html_head: str,
    expected_warning: str,
) -> None:
    """Warn via logger and Rich stderr when JSON-LD metadata is missing or incomplete."""
    target_dir = tmp_path / "target"
    html_file = target_dir / "en-us" / "sles" / "16.1" / "html" / "index.html"
    html_file.parent.mkdir(parents=True, exist_ok=True)
    html_file.write_text(
        f"<!DOCTYPE html><html><head>{html_head}</head><body><h1>Index</h1></body></html>",
        encoding="utf-8",
    )

    with caplog.at_level("WARNING", logger="docbuild.tasks.build.llms.generator"):
        await generate_llmstxt(
            deliverable=llms_deliverable,
            target_base_dir=target_dir,
            build_llmstxt=True,
            llmstxt_dir="docs",
        )

    assert expected_warning in caplog.text
    stderr = " ".join(capsys.readouterr().err.split())
    assert "Warning" in stderr
    assert expected_warning in stderr


@pytest.mark.asyncio
async def test_generate_llmstxt_frontmatter_omits_missing_date(
    tmp_path: Path, llms_deliverable: Deliverable
) -> None:
    """Test that build_date is omitted from frontmatter if dateModified is absent."""
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    html_file = target_dir / "en-us" / "sles" / "16.1" / "html" / "index.html"
    html_file.parent.mkdir(parents=True, exist_ok=True)
    html_content = """<!DOCTYPE html>
    <html>
    <head>
        <script type="application/ld+json">
        {
            "name": "Title Without Date"
        }
        </script>
    </head>
    <body><h1>Index</h1></body>
    </html>"""
    html_file.write_text(html_content, encoding="utf-8")

    await generate_llmstxt(
            deliverable=llms_deliverable,
            target_base_dir=target_dir,
            build_llmstxt=True,
            llmstxt_dir="docs",
        )

    md_file = target_dir / "docs" / "en-us" / "sles" / "16.1" / "html" / "index.md"
    assert md_file.exists()

    content = md_file.read_text(encoding="utf-8")
    frontmatter_raw = content.split("---")[1]
    data = yaml.safe_load(frontmatter_raw)

    assert data["title"] == "Title Without Date"
    assert "build_date" not in data
