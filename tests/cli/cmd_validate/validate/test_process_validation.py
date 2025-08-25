import shutil
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import docbuild.cli.cmd_validate.process as process_mod
from docbuild.cli.context import DocBuildContext


def is_jing_installed():
    return shutil.which("jing") is not None


async def test_run_command():
    """Test the run_command function."""
    command = ['echo', 'Hello, World!']

    returncode, stdout, stderr = await process_mod.run_command(*command)

    assert returncode == 0, f'Expected return code 0, got {returncode}'
    assert stdout.strip() == 'Hello, World!', f'Unexpected stdout: {stdout}'
    assert stderr == '', f'Unexpected stderr: {stderr}'


@pytest.mark.skipif(not is_jing_installed(), reason="jing command not found")
async def test_validate_rng_with_rng_suffix(tmp_path: Path):
    """Test validate_rng with a schema file having a .rng suffix."""
    xmlfile = tmp_path / Path('file.xml')
    xmlfile.write_text("""<root/>""")

    rng_schema = tmp_path / Path('schema.rng')
    rng_schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
  <start><element name="root"><text/></element></start>
</grammar>""")

    returncode, _ = await process_mod.validate_rng(xmlfile, rng_schema)

    assert returncode, f'Expected True, got {returncode}'


@pytest.mark.skipif(not is_jing_installed(), reason="jing command not found")
async def test_validate_rng_with_invalid_xml(tmp_path: Path):
    """Test validate_rng with an invalid XML file."""
    xmlfile = tmp_path / Path('file.xml')
    xmlfile.write_text("""<wrong_root/>""")

    rng_schema = tmp_path / Path('schema.rng')
    rng_schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start><element name="root"><text/></element></start>
</grammar>""")

    returncode, message = await process_mod.validate_rng(xmlfile, rng_schema)
    assert returncode is False, f'Expected False, got {returncode}'
    assert 'error: element "wrong_root"' in message


@pytest.mark.skipif(not is_jing_installed(), reason="jing command not found")
async def test_validate_rng_without_xinclude(tmp_path: Path):
    """Test validate_rng with xinclude set to False."""
    xmlfile = tmp_path / Path('file.xml')
    xmlfile.write_text("""<root/>""")

    rng_schema = tmp_path / Path('schema.rng')
    rng_schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start><element name="root"><text/></element></start>
</grammar>""")

    returncode, _ = await process_mod.validate_rng(xmlfile, rng_schema, xinclude=False)

    assert returncode, f'Expected True, got {returncode}'


@pytest.mark.skipif(not is_jing_installed(), reason="jing command not found")
async def test_validate_rng_with_invalid_xml_without_xinclude(tmp_path: Path):
    """Test validate_rng with xinclude set to False."""
    xmlfile = tmp_path / Path('file.xml')
    xmlfile.write_text("""<wrong_root/>""")

    rng_schema = tmp_path / Path('schema.rng')
    rng_schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start><element name="root"><text/></element></start>
</grammar>""")

    returncode, message = await process_mod.validate_rng(
        xmlfile, rng_schema, xinclude=False
    )

    assert returncode is False, f'Expected False, got {returncode}'
    assert 'element "wrong_root" not allowed anywhere' in message


async def test_validate_rng_jing_failure():
    """Test validate_rng when jing fails."""
    xmlfile = MagicMock(spec=Path)
    rng_schema = MagicMock(spec=Path)
    xmlfile.__str__.return_value = '/mocked/path/to/file.xml'
    rng_schema.__str__.return_value = '/mocked/path/to/schema.rng'

    with patch.object(
        process_mod,
        'run_command',
        new=AsyncMock(return_value=(1, 'Error in jing', '')),
    ) as mock_run_command:
        success, output = await process_mod.validate_rng(
            xmlfile, rng_schema_path=rng_schema, xinclude=False
        )

        assert not success, 'Expected validation to fail.'
        assert output == 'Error in jing', f'Unexpected output: {output}'

        mock_run_command.assert_called_once_with('jing', str(rng_schema), str(xmlfile))


async def test_validate_rng_command_not_found():
    """Test validate_rng when a command is not found and has a filename."""
    xmlfile = MagicMock(spec=Path)
    rng_schema = MagicMock(spec=Path)
    xmlfile.__str__.return_value = '/mocked/path/to/file.xml'
    rng_schema.__str__.return_value = '/mocked/path/to/schema.rng'

    error = FileNotFoundError(2, 'No such file or directory')
    error.filename = 'jing'

    with patch.object(
        process_mod, 'run_command', new_callable=AsyncMock, side_effect=error
    ):
        success, output = await process_mod.validate_rng(
            xmlfile, rng_schema_path=rng_schema, xinclude=False
        )

    assert not success, 'Expected validation to fail.'
    assert output == 'jing command not found. Please install it to run validation.'


async def test_validate_rng_command_not_found_no_filename():
    """Test validate_rng when FileNotFoundError has no filename attribute."""
    xmlfile = MagicMock(spec=Path)
    rng_schema = MagicMock(spec=Path)
    error = FileNotFoundError(2, 'No such file or directory')
    error.filename = None

    with patch.object(
        process_mod, 'run_command', new_callable=AsyncMock, side_effect=error
    ):
        success, output = await process_mod.validate_rng(
            xmlfile, rng_schema, xinclude=False
        )

    assert not success, 'Expected validation to fail.'
    assert (
        output == 'xmllint/jing command not found. Please install it to run validation.'
    )


async def test_process_file_with_validation_issues(capsys, tmp_path):
    with patch.object(
        process_mod,
        'validate_rng',
        new=AsyncMock(return_value=(False, 'Validation error')),
    ) as mock_validate_rng:
        dir_path = tmp_path / 'path' / 'to'
        dir_path.mkdir(parents=True)
        xmlfile = dir_path / 'file.xml'
        xmlfile.touch()

        mock_context = Mock(spec=DocBuildContext)
        mock_context.verbose = 2
        mock_context.validation_method = 'jing'  # <-- Use 'jing' or 'lxml'

        result = await process_mod.process_file(xmlfile, mock_context, 40)

        assert result == 10  # RNG validation failure code



async def test_process_file_with_xmlsyntax_error(capsys, tmp_path):
    dir_path = tmp_path / 'path' / 'to'
    dir_path.mkdir(parents=True)
    xmlfile = dir_path / 'file.xml'
    xmlfile.write_text("""<root><invalid></root>""")

    mock_context = Mock(spec=DocBuildContext)
    mock_context.verbose = 2
    mock_context.validation_method = 'jing'  

    with (
        patch.object(
            process_mod.etree,
            'parse',
            new=Mock(
                side_effect=process_mod.etree.XMLSyntaxError(
                    'XML syntax error', None, 0, 0, 'fake.xml'
                )
            ),
        ) as mock_etree_parse,
        patch.object(
            process_mod, 'validate_rng', new=AsyncMock(return_value=(True, ''))
        ) as mock_validate_rng,
    ):
        result = await process_mod.process_file(xmlfile, mock_context, 40)

    assert result == 20
