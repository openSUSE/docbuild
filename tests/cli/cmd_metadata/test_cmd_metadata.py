"""Unit tests for metadata command helper functions."""

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from lxml import etree
import pytest

from docbuild.cli.cmd_metadata import metaprocess as metaprocess_pkg
from docbuild.cli.cmd_metadata.metaprocess import (
    get_deliverable_from_doctype,
    process,
    process_deliverable,
    process_doctype,
)
from docbuild.cli.context import DocBuildContext
from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype


@pytest.fixture
def xmlconfig(request) -> etree.ElementTree:
    """Parse an XML string into an ElementTree.

    Can be used with or without @pytest.mark.parametrize.
    If used with parametrize, it expects the XML string as the parameter.
    If used without, it provides a default empty <config/> tree.
    """
    xml_string = None
    if hasattr(request, 'param'):
        xml_string = request.param

    if not xml_string:
        xml_string = '<docservconfig/>'
    root = etree.fromstring(xml_string)
    return etree.ElementTree(root)


@pytest.fixture
def mock_context_with_config_dir(tmp_path: Path) -> DocBuildContext:
    """Provide a mock DocBuildContext with a valid config_dir."""
    context = Mock(spec=DocBuildContext)
    config_dir = tmp_path / 'config'
    config_dir.mkdir()
    (config_dir / 'dummy.xml').write_text(
        '<docservconfig/>'
    )  # Ensure at least one XML file exists
    context.envconfig = {'paths': {'config_dir': str(config_dir)}}
    return context


# @pytest.mark.parametrize(
#     'xmlconfig',
#     [None],
#     ids=['empty'],
#     indirect=True,
# )
def test_for_xmlconfig(xmlconfig):
    """Verify the xmlconfig fixture parses XML correctly."""
    print('>>> xmlconfig:', xmlconfig.getroot().tag)


@pytest.mark.parametrize(
    'xmlconfig',
    [
        # Verify deliverables are correctly extracted for a specific doctype.
        """
    <docservconfig>
      <product productid="sles">
        <docset setid="15-SP7" lifecycle="supported">
          <version>15-SP7</version>
          <builddocs>
             <git remote="https://github.com/SUSE/doc-sle.git"/>
             <language default="1" lang="en-us">
                <branch>main</branch>
                <deliverable category="installation-upgrade">
                    <dc>DC-SLES-deployment</dc>
                    <format epub="0" html="0" pdf="1" single-html="1"/>
               </deliverable>
             </language>
            <language lang="de-de">
                <branch>main</branch>
                <subdir>l10n/sles/de-de</subdir>
                <deliverable>
                    <dc>DC-SLES-deployment</dc>
                </deliverable>
            </language>
          </builddocs>
        </docset>
      </product>
    </docservconfig>
    """
    ],
    ids=['xmldata'],
    indirect=True,
)
def test_get_deliverable_from_doctype_success(xmlconfig):
    """Verify deliverables are correctly extracted for a specific doctype."""
    # Arrange
    mock_context = Mock(spec=DocBuildContext)
    doctype = Doctype.from_str('sles/15-SP7/en-us')

    # Act
    deliverables = get_deliverable_from_doctype(xmlconfig, mock_context, doctype)

    # Assert
    assert len(deliverables) == 1
    assert all(isinstance(d, Deliverable) for d in deliverables)


def test_xmlconfig_no_param_provides_default(xmlconfig):
    """Verify the xmlconfig fixture works without being parametrized."""
    assert xmlconfig is not None
    root = xmlconfig.getroot()
    assert root.tag == 'docservconfig'
    assert len(root) == 0


@pytest.mark.parametrize(
    'xmlconfig',
    [None, ''],
    ids=['none-param', 'empty-string-param'],
    indirect=True,
)
def test_xmlconfig_falsy_params_provide_default(xmlconfig):
    """Verify the xmlconfig fixture provides a default for falsy params."""
    assert xmlconfig is not None
    root = xmlconfig.getroot()
    assert root.tag == 'docservconfig'
    assert len(root) == 0


@pytest.mark.parametrize(
    'xmlconfig',
    [
        """
    <docservconfig>
      <product productid="sles">
        <docset setid="15-sp6">
          <builddocs>
            <language lang="en-us">
              <!-- No deliverables here -->
            </language>
          </builddocs>
        </docset>
      </product>
    </docservconfig>
    """
    ],
    indirect=True,
)
def test_get_deliverable_from_doctype_no_deliverables(xmlconfig):
    """Verify an empty list is returned when a language has no deliverables."""
    # Arrange
    mock_context = Mock(spec=DocBuildContext)
    doctype = Doctype.from_str('sles/15-sp6/en-us')

    # Act
    with patch('docbuild.cli.cmd_metadata.console_out'):
        deliverables = get_deliverable_from_doctype(xmlconfig, mock_context, doctype)

    # Assert
    assert deliverables == []


@pytest.mark.parametrize(
    'xmlconfig',
    [
        """
    <docservconfig>
      <product productid="sles">
        <docset setid="15-sp6">
          <builddocs>
            <language lang="en-us">
              <deliverable id="d1" git_name="repo1" dc_file="file1.xml" />
            </language>
          </builddocs>
        </docset>
      </product>
    </docservconfig>
    """
    ],
    indirect=True,
)
def test_get_deliverable_from_doctype_no_match(xmlconfig):
    """Verify an empty list is returned when the doctype doesn't match any node."""
    # Arrange
    mock_context = Mock(spec=DocBuildContext)
    # This doctype does not exist in the XML
    doctype = Doctype.from_str('sles/1.0/en-us')

    # Act
    with patch('docbuild.cli.cmd_metadata.console_out'):
        # with patch.object(cmd_metadata, 'console_out')
        deliverables = get_deliverable_from_doctype(xmlconfig, mock_context, doctype)

    # Assert
    assert deliverables == []


@pytest.mark.parametrize(
    'xmlconfig',
    [
        """
    <docservconfig>
      <product productid="sles">
        <docset setid="15-sp6">
          <builddocs>
            <language lang="en-us">
              <deliverable>
                <dc>DC-SLE-Micro-5.5-admin</dc>
                <format html="1" pdf="1" single-html="0"/>
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
                 <format html="1" pdf="1" single-html="0"/>
              </deliverable>
              <deliverable>
                <dc>DC-Micro-5.5-cockpit</dc>
                <format html="1" pdf="1" single-html="0"/>
              </deliverable>
            </language>
          </builddocs>
        </docset>
      </product>
    </docservconfig>
    """
    ],
    indirect=True,
)
def test_get_deliverable_from_doctype_with_wildcard(xmlconfig):
    """Verify deliverables are correctly extracted using a wildcard doctype."""
    # Arrange
    mock_context = Mock(spec=DocBuildContext)
    doctype = Doctype.from_str('//en-us')  # Wildcard for product and docset

    # Act
    deliverables = get_deliverable_from_doctype(xmlconfig, mock_context, doctype)

    # Assert
    assert len(deliverables) == 3
    deliverable_ids = {d.docsuite for d in deliverables}
    assert deliverable_ids == {
        'other/1.0/en-us:DC-Micro-5.4-cockpit',
        'other/1.0/en-us:DC-Micro-5.5-cockpit',
        'sles/15-sp6/en-us:DC-SLE-Micro-5.5-admin',
    }


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
                </deliverable>
             </language>
          </builddocs>
        </docset>
      </product>
    </docservconfig>
    """
    root = etree.fromstring(xml_string)
    deliverable_node = root.find('.//deliverable')
    return Deliverable(deliverable_node)


async def test_metadata_process_empty_context_envconfig():
    context = Mock(spec=DocBuildContext)
    context.envconfig = None

    with pytest.raises(ValueError):
        await process(context, doctypes=tuple())


@pytest.mark.asyncio
class TestProcessDeliverable:
    """Tests for the process_deliverable function."""

    @pytest.fixture
    def mock_subprocess(self) -> Iterator[AsyncMock]:
        """Fixture to mock asyncio.create_subprocess_exec."""
        with patch(
            'docbuild.cli.cmd_metadata.asyncio.create_subprocess_exec',
            new_callable=AsyncMock,
        ) as mock:
            yield mock

    @pytest.fixture
    def setup_paths(self, tmp_path: Path, deliverable: Deliverable) -> dict:
        """Set up common paths and directories for tests."""
        paths = {
            'repo_dir': tmp_path / 'repos',
            'temp_repo_dir': tmp_path / 'temp_repos',
            'base_cache_dir': tmp_path / 'cache',
            'meta_cache_dir': tmp_path / 'cache' / 'metadata',
        }
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)

        # Create a fake bare repo for the success/failure paths
        (paths['repo_dir'] / deliverable.git.slug).mkdir()
        return paths

    async def test_success(
        self, deliverable: Deliverable, setup_paths: dict, mock_subprocess: AsyncMock
    ):
        """Test successful processing of a deliverable."""
        # Arrange
        clone_proc = AsyncMock(returncode=0)
        clone_proc.communicate.return_value = (b'', b'')
        daps_proc = AsyncMock(returncode=0)
        daps_proc.communicate.return_value = (b'', b'')
        mock_subprocess.side_effect = [clone_proc, daps_proc]

        dapstmpl = 'daps --dc-file={dcfile} --output-file={output}'

        # Act
        result = await process_deliverable(
            deliverable=deliverable, dapstmpl=dapstmpl, **setup_paths
        )

        # Assert
        assert result is True
        assert mock_subprocess.call_count == 2

    async def test_bare_repo_not_found(
        self, deliverable: Deliverable, tmp_path: Path, caplog
    ):
        """Test failure when the bare repository does not exist."""
        # Arrange
        paths = {
            'repo_dir': tmp_path / 'repos',  # Don't create the slug subdir
            'temp_repo_dir': tmp_path / 'temp_repos',
            'base_cache_dir': tmp_path / 'cache',
            'meta_cache_dir': tmp_path / 'cache' / 'metadata',
        }
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)

        # Act
        result = await process_deliverable(
            deliverable=deliverable, dapstmpl='', **paths
        )

        # Assert
        assert result is False
        # assert "Bare repository not found" in caplog.text

    async def test_git_clone_fails(
        self,
        deliverable: Deliverable,
        setup_paths: dict,
        mock_subprocess: AsyncMock,
        caplog,
    ):
        """Test failure when the git clone command fails."""
        clone_proc = AsyncMock(returncode=128)
        clone_proc.communicate.return_value = (b'', b'fatal: repository not found')
        mock_subprocess.return_value = clone_proc

        result = await process_deliverable(
            deliverable=deliverable, dapstmpl='', **setup_paths
        )

        assert result is False
        # assert "Failed to clone" in caplog.text
        # assert "fatal: repository not found" in caplog.text

    async def test_daps_command_fails(
        self,
        deliverable: Deliverable,
        setup_paths: dict,
        mock_subprocess: AsyncMock,
        caplog,
    ):
        """Test failure when the DAPS command fails."""
        clone_proc = AsyncMock(returncode=0)
        clone_proc.communicate.return_value = (b'', b'')
        daps_proc = AsyncMock(returncode=1)
        daps_proc.communicate.return_value = (b'', b'DAPS error: file not found')
        mock_subprocess.side_effect = [clone_proc, daps_proc]

        result = await process_deliverable(
            deliverable=deliverable, dapstmpl='daps', **setup_paths
        )

        assert result is False
        # assert "DAPS command failed" in caplog.text
        # assert "DAPS error: file not found" in caplog.text


@pytest.mark.asyncio
class TestProcessDoctype:
    """Tests for the process_doctype function."""

    @pytest.fixture
    def mock_context(self, tmp_path: Path) -> DocBuildContext:
        """Provide a mock DocBuildContext with necessary paths."""
        context = Mock(spec=DocBuildContext)
        context.envconfig = {
            'build': {'daps': {'meta': 'daps-command-template'}},
            'paths': {
                'repo_dir': tmp_path / 'repos',
                'base_cache_dir': tmp_path / 'cache',
                'meta_cache_dir': tmp_path / 'cache' / 'metadata',
                'temp_repo_dir': tmp_path / 'temp_repos',
            },
        }
        return context

    @pytest.fixture
    def mock_root(self) -> etree._ElementTree:
        """Provide a mock XML root element for testing."""
        return etree.ElementTree(etree.fromstring('<docservconfig/>'))

    @patch.object(metaprocess_pkg, 'process_deliverable', new_callable=AsyncMock)
    @patch.object(metaprocess_pkg, 'get_deliverable_from_doctype')
    async def test_success_with_deliverables(
        self,
        mock_get_deliverables: Mock,
        mock_process_deliverable: AsyncMock,
        mock_root: etree._ElementTree,
        mock_context: DocBuildContext,
    ):
        """Test successful processing when deliverables are found."""
        doctype = Doctype.from_str('sles/15/en-us')
        mock_deliverables = [Mock(spec=Deliverable), Mock(spec=Deliverable)]
        mock_get_deliverables.return_value = mock_deliverables
        mock_process_deliverable.return_value = True

        result = await process_doctype(mock_root, mock_context, doctype)

        assert result is True
        mock_get_deliverables.assert_called_once_with(mock_root, mock_context, doctype)
        assert mock_process_deliverable.call_count == 2

    @patch.object(metaprocess_pkg, 'process_deliverable', new_callable=AsyncMock)
    @patch.object(metaprocess_pkg, 'get_deliverable_from_doctype')
    async def test_no_deliverables_found(
        self,
        mock_get_deliverables: Mock,
        mock_process_deliverable: AsyncMock,
        mock_root: etree._ElementTree,
        mock_context: DocBuildContext,
    ):
        """Test behavior when no deliverables are found for the doctype."""
        doctype = Doctype.from_str('sles/15/en-us')
        mock_get_deliverables.return_value = []

        result = await process_doctype(mock_root, mock_context, doctype)

        assert result is True
        mock_get_deliverables.assert_called_once_with(mock_root, mock_context, doctype)
        mock_process_deliverable.assert_not_called()

    @patch.object(metaprocess_pkg, 'get_deliverable_from_doctype')
    async def test_missing_paths_in_config_raises_error(
        self, mock_get_deliverables: Mock, mock_root: etree._ElementTree
    ):
        """Test that a ValueError is raised if required paths are missing."""
        doctype = Doctype.from_str('sles/15/en-us')
        mock_get_deliverables.return_value = [Mock(spec=Deliverable)]
        context_missing_path = Mock(spec=DocBuildContext)
        context_missing_path.envconfig = {
            'build': {'daps': {'meta': 'daps-command'}},
            'paths': {'base_cache_dir': '/fake/cache'},  # Missing other paths
        }

        with pytest.raises(ValueError, match='Missing required paths in configuration'):
            await process_doctype(mock_root, context_missing_path, doctype)


@pytest.mark.asyncio
class TestProcessEmptyDoctypes:
    """Tests for the case when no doctypes are passed to process."""

    @patch.object(metaprocess_pkg, 'create_stitchfile', new_callable=AsyncMock)
    @patch.object(metaprocess_pkg, 'process_doctype', new_callable=AsyncMock)
    async def test_process_empty_doctypes(
        self,
        mock_process_doctype: AsyncMock,
        mock_create_stitchfile: AsyncMock,
        mock_context_with_config_dir: DocBuildContext,
    ):
        """Test process function with an empty tuple of doctypes."""
        mock_stitch_node = etree.ElementTree(etree.Element('docservconfig'))
        mock_create_stitchfile.return_value = mock_stitch_node

        await process(mock_context_with_config_dir, doctypes=())

        # Assert that create_stitchfile was called
        mock_create_stitchfile.assert_called_once()
        # Assert that process_doctype was called with the default doctype
        mock_process_doctype.assert_called()

    async def test_no_config_dir_raises_error(self):
        """Test process raises ValueError if config_dir is missing from paths."""
        context = Mock(spec=DocBuildContext)
        context.envconfig = {'paths': {}}  # No config_dir in paths

        with pytest.raises(
            ValueError, match='Could not get a value from envconfig.paths.config_dir'
        ):
            await process(context, doctypes=tuple())

    @patch.object(metaprocess_pkg, 'create_stitchfile', new_callable=AsyncMock)
    @patch.object(metaprocess_pkg, 'process_doctype', new_callable=AsyncMock)
    async def test_no_doctypes_uses_default(
        self,
        mock_process_doctype: AsyncMock,
        mock_create_stitchfile: AsyncMock,
        tmp_path: Path,
    ):
        """Test process uses a default doctype when none are provided.

        This test covers the successful execution path and the logic for handling
        an empty doctypes tuple.
        """
        # Arrange
        context = Mock(spec=DocBuildContext)
        config_dir = tmp_path / 'config'
        config_dir.mkdir()
        context.envconfig = {'paths': {'config_dir': str(config_dir)}}

        mock_stitch_node = etree.ElementTree(etree.Element('docservconfig'))
        mock_create_stitchfile.return_value = mock_stitch_node
        mock_process_doctype.return_value = True

        # Act and suppress console output during the test
        with patch.object(metaprocess_pkg, 'console_out'):
            result = await process(context, doctypes=tuple())

        # Assert
        assert result == 0
        mock_create_stitchfile.assert_awaited_once()
        default_doctype = Doctype.from_str('//en-us')
        mock_process_doctype.assert_awaited_once_with(
            mock_stitch_node, context, default_doctype
        )
