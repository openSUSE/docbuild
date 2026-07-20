"""Shared fixtures for task-layer tests."""

from pathlib import Path
from unittest.mock import Mock

from lxml import etree
import pytest

from docbuild.cli.context import DocBuildContext
from docbuild.models.deliverable import Deliverable


@pytest.fixture
def mock_envconfig(tmp_path: Path) -> Mock:
    """Provide a mock EnvConfig object with task-related paths."""
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
def xmlconfig(request: pytest.FixtureRequest) -> etree.ElementTree:
    """Parse an XML string into an element tree."""
    xml_string = getattr(request, "param", None) or "<docservconfig/>"
    root = etree.fromstring(xml_string)
    return etree.ElementTree(root)


@pytest.fixture
def mock_context_with_config_dir(
    tmp_path: Path,
    mock_envconfig: Mock,
) -> DocBuildContext:
    """Provide a mock DocBuildContext with a valid config dir."""
    context = Mock(spec=DocBuildContext)
    config_dir = tmp_path / "config"
    tmp_metadata_dir = tmp_path / "tmp" / "metadata"

    config_dir.mkdir()
    tmp_metadata_dir.mkdir(parents=True)
    (config_dir / "dummy.xml").write_text("<docservconfig/>")

    mock_envconfig.paths.config_dir = config_dir
    mock_envconfig.paths.main_portal_config = config_dir / "dummy.xml"
    mock_envconfig.paths.meta_cache_dir.mkdir(parents=True)

    mock_tmp = Mock()
    mock_tmp.tmp_metadata_dir = tmp_metadata_dir
    mock_envconfig.paths.tmp = mock_tmp

    context.envconfig = mock_envconfig
    context.appconfig = None
    return context


@pytest.fixture
def deliverable() -> Deliverable:
    """Provide a deliverable with Git, branch, and format information."""
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
def deliverable_single_html() -> Deliverable:
    """Provide a deliverable that enables single HTML output."""
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
                    <dc file="DC-SLES-guides">
                        <format html="1" pdf="1" single-html="1"/>
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
