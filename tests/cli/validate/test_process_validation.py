from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import docbuild.cli.cmd_validate.process as process_mod
import docbuild.cli.commands as commands_mod
from docbuild.cli.context import DocBuildContext


async def test_validate_rng_with_rng_suffix(tmp_path: Path):
    """Test validate_rng with a schema file having a .rng suffix."""
    xmlfile = tmp_path / Path('file.xml')
    xmlfile.write_text("""<root/>""")

    rng_schema = tmp_path / Path('schema.rng')
    rng_schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
    <grammar xmlns="http://relaxng.org/ns/structure/1.0">
        <start><element name="root"><text/></element></start>
    </grammar>""")

    result = await process_mod.validate_rng(xmlfile, rng_schema)
    assert result.returncode == 0, f'Expected return code 0, got {result.returncode}'


async def test_validate_rng_with_invalid_xml(tmp_path: Path):
    """Test validate_rng with an invalid XML file."""
    xmlfile = tmp_path / Path('file.xml')
    xmlfile.write_text("""<wrong_root/>""")

    rng_schema = tmp_path / Path('schema.rng')
    rng_schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
    <grammar xmlns="http://relaxng.org/ns/structure/1.0">
        <start><element name="root"><text/></element></start>
    </grammar>""")

    result = await process_mod.validate_rng(xmlfile, rng_schema)
    assert result.returncode != 0, f'Expected non-zero return code, got {result.returncode}'
    assert 'error: element "wrong_root"' in result.stdout or result.stderr


async def test_validate_rng_without_xinclude(tmp_path: Path):
    """Test validate_rng with xinclude set to False."""
    xmlfile = tmp_path / Path('file.xml')
    xmlfile.write_text("""<root/>""")

    rng_schema = tmp_path / Path('schema.rng')
    rng_schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
    <grammar xmlns="http://relaxng.org/ns/structure/1.0">
        <start><element name="root"><text/></element></start>
    </grammar>""")

    result = await process_mod.validate_rng(xmlfile, rng_schema, xinclude=False)
    assert result.returncode == 0, f'Expected return code 0, got {result.returncode}'


async def test_validate_rng_with_invalid_xml_without_xinclude(tmp_path: Path):
    """Test validate_rng with xinclude set to False."""
    xmlfile = tmp_path / Path('file.xml')
    xmlfile.write_text("""<wrong_root/>""")

    rng_schema = tmp_path / Path('schema.rng')
    rng_schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
    <grammar xmlns="http://relaxng.org/ns/structure/1.0">
        <start><element name="root"><text/></element></start>
    </grammar>""")

    result = await process_mod.validate_rng(
        xmlfile, rng_schema, xinclude=False
    )
    assert result.returncode != 0, f'Expected non-zero return code, got {result.returncode}'
    assert 'element "wrong_root" not allowed anywhere' in result.stdout or result.stderr


async def test_validate_rng_jing_failure():
    """Test validate_rng when jing fails."""
    # Mock the Path objects to simulate valid file paths
    xmlfile = MagicMock(spec=Path)
    rng_schema = MagicMock(spec=Path)
    xmlfile.__str__.return_value = '/mocked/path/to/file.xml'
    rng_schema.__str__.return_value = '/mocked/path/to/schema.rng'

    # Mock the run_command method to simulate jing failure
    with patch.object(
        process_mod,
        'run_command',
        new=AsyncMock(
            return_value=CompletedProcess(
                args=['jing', str(rng_schema), str(xmlfile)],
                returncode=1, stderr='Error in jing', stdout=''
            )
        ),
    ) as mock_run_command:
        result = await process_mod.validate_rng(
            xmlfile, rng_schema_path=rng_schema, xinclude=False
        )
        # Assert that validation fails
        assert result.returncode != 0, 'Expected validation to fail.'
        assert result.stdout == 'Error in jing' or result.stderr == 'Error in jing'
        # Verify that jing was called with the correct arguments
        mock_run_command.assert_called_once_with(
            'jing', str(rng_schema), str(xmlfile), stdout=-1, stderr=-1
        )


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
        result = await process_mod.validate_rng(
            xmlfile, rng_schema_path=rng_schema, xinclude=False
        )
    assert result.returncode == 127, 'Expected validation to fail.'
    assert result.stderr == 'jing command not found. Please install it to run validation.'


async def test_validate_rng_command_not_found_no_filename():
    """Test validate_rng when FileNotFoundError has no filename attribute."""
    xmlfile = MagicMock(spec=Path)
    rng_schema = MagicMock(spec=Path)
    error = FileNotFoundError(2, 'No such file or directory')
    error.filename = None

    with patch.object(
        process_mod, 'run_command', new_callable=AsyncMock, side_effect=error
    ):
        result = await process_mod.validate_rng(
            xmlfile, rng_schema, xinclude=False
        )
    assert result.returncode == 127, 'Expected validation to fail.'
    assert (
        result.stderr == 'xmllint/jing command not found. Please install it to run validation.'
    )


async def test_process_file_with_validation_issues(capsys, tmp_path):
    """Test process_file with validation issues."""
    # Use a real file path to avoid issues with Path(MagicMock)
    dir_path = tmp_path / 'path' / 'to'
    dir_path.mkdir(parents=True)
    xmlfile = dir_path / 'file.xml'
    xmlfile.touch()

    with patch.object(
        process_mod,
        'validate_rng',
        new=AsyncMock(
            return_value=CompletedProcess(
                args=['jing', ],
                returncode=1,
                stderr='Error in jing',
                stdout='',
            )
        ),
    ) as mock_validate_rng:
        mock_context = Mock(spec=DocBuildContext)
        mock_context.verbose = 2  # to get output with details

        result = await process_mod.process_file(xmlfile, mock_context, 40)

        assert result != 0, (
            'Expected process_file to return 10 due to validation issues.'
        )
        mock_validate_rng.assert_awaited_once_with(xmlfile)

    captured = capsys.readouterr()
    assert 'to/file.xml' in captured.err
    assert 'RNG validation' in captured.err


async def test_process_file_with_xmlsyntax_error(capsys, tmp_path):
    """Test process_file with XML syntax error."""
    # Use a real file path to avoid issues with Path(MagicMock)
    dir_path = tmp_path / 'path' / 'to'
    dir_path.mkdir(parents=True)
    xmlfile = dir_path / 'file.xml'
    xmlfile.write_text("""<root><invalid></root>""")

    mock_context = Mock(spec=DocBuildContext)
    mock_context.verbose = 2

    with (
        patch.object(
            process_mod.etree,
            'parse',
            new=Mock(
                side_effect=process_mod.etree.XMLSyntaxError(
                    'XML syntax error', None, 0, 0, 'fake.xml'
                )
            ),
        ),
        patch.object(
            process_mod, 'validate_rng',
            new=AsyncMock(return_value=CompletedProcess(
                args=['jing'],
                returncode=0,
                stdout='',
                stderr='',
                )
            ),
        ) as mock_validate_rng,
    ):
        result = await process_mod.process_file(xmlfile, mock_context, 40)

        assert result != 0, (
            'Expected process_file to return 20 due to XML syntax error.'
        )
        mock_validate_rng.assert_awaited_once_with(xmlfile)
        capture = capsys.readouterr()
        assert 'to/file.xml' in capture.err
        assert 'XML syntax error' in capture.err
