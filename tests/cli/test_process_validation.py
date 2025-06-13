from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from docbuild.cli import process_validation
from docbuild.cli.context import DocBuildContext
from docbuild.cli.process_validation import run_command, validate_rng


async def test_run_command():
    """Test the run_command function."""
    # Use a simple command that is guaranteed to exist
    command = ['echo', 'Hello, World!']

    returncode, stdout, stderr = await run_command(*command)

    # Assert the return code is 0 (success)
    assert returncode == 0, f'Expected return code 0, got {returncode}'

    # Assert the stdout contains the expected output
    assert stdout.strip() == 'Hello, World!', f'Unexpected stdout: {stdout}'

    # Assert stderr is empty
    assert stderr == '', f'Unexpected stderr: {stderr}'


async def test_validate_rng_with_rng_suffix(tmp_path: Path):
    """Test validate_rng with a schema file having a .rng suffix."""
    xmlfile = tmp_path / Path('file.xml')
    xmlfile.write_text("""<root/>""")

    rng_schema = tmp_path / Path('schema.rng')
    rng_schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
  <start><element name="root"><text/></element></start>
</grammar>""")

    returncode, _ = await validate_rng(xmlfile, rng_schema)

    assert returncode, f'Expected True, got {returncode}'


async def test_validate_rng_with_invalid_xml(tmp_path: Path):
    """Test validate_rng with an invalid XML file."""
    xmlfile = tmp_path / Path('file.xml')
    xmlfile.write_text("""<wrong_root/>""")

    rng_schema = tmp_path / Path('schema.rng')
    rng_schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start><element name="root"><text/></element></start>
</grammar>""")

    returncode, message = await validate_rng(xmlfile, rng_schema)
    assert returncode is False, f'Expected False, got {returncode}'
    assert 'error: element "wrong_root"' in message


async def test_validate_rng_without_xinclude(tmp_path: Path):
    """Test validate_rng with xinclude set to False."""
    xmlfile = tmp_path / Path('file.xml')
    xmlfile.write_text("""<root/>""")

    rng_schema = tmp_path / Path('schema.rng')
    rng_schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start><element name="root"><text/></element></start>
</grammar>""")

    returncode, _ = await validate_rng(xmlfile, rng_schema, xinclude=False)

    assert returncode, f'Expected True, got {returncode}'


async def test_validate_rng_with_invalid_xml_without_xinclude(tmp_path: Path):
    """Test validate_rng with xinclude set to False."""
    xmlfile = tmp_path / Path('file.xml')
    xmlfile.write_text("""<wrong_root/>""")

    rng_schema = tmp_path / Path('schema.rng')
    rng_schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start><element name="root"><text/></element></start>
</grammar>""")

    returncode, message = await validate_rng(xmlfile, rng_schema, xinclude=False)

    assert returncode is False, f'Expected False, got {returncode}'
    assert 'element "wrong_root" not allowed anywhere' in message


async def test_validate_rng_jing_failure():
    """Test validate_rng when jing fails."""
    # Mock the Path objects to simulate valid file paths
    xmlfile = MagicMock(spec=Path)
    rng_schema = MagicMock(spec=Path)
    xmlfile.__str__.return_value = '/mocked/path/to/file.xml'
    rng_schema.__str__.return_value = '/mocked/path/to/schema.rng'

    # Mock the run_command method to simulate jing failure
    with patch.object(
        process_validation,
        'run_command',
        new=AsyncMock(return_value=(1, 'Error in jing', '')),
    ) as mock_run_command:
        success, output = await validate_rng(
            xmlfile, rng_schema_path=rng_schema, xinclude=False
        )

        # Assert that validation fails
        assert not success, 'Expected validation to fail.'
        assert output == 'Error in jing', f'Unexpected output: {output}'

        # Verify that jing was called with the correct arguments
        mock_run_command.assert_called_once_with('jing', str(rng_schema), str(xmlfile))


async def test_validate_rng_command_not_found():
    """Test validate_rng when a command is not found and has a filename."""
    # This test covers the `e.filename` part of the `or` expression
    # on the target line.
    xmlfile = MagicMock(spec=Path)
    rng_schema = MagicMock(spec=Path)
    xmlfile.__str__.return_value = '/mocked/path/to/file.xml'
    rng_schema.__str__.return_value = '/mocked/path/to/schema.rng'

    error = FileNotFoundError(2, 'No such file or directory')
    error.filename = 'jing'

    with patch.object(
        process_validation, 'run_command', new_callable=AsyncMock, side_effect=error
    ):
        success, output = await validate_rng(
            xmlfile, rng_schema_path=rng_schema, xinclude=False
        )

    assert not success, 'Expected validation to fail.'
    assert output == 'jing command not found. Please install it to run validation.'


async def test_validate_rng_command_not_found_no_filename():
    """Test validate_rng when FileNotFoundError has no filename attribute."""
    # This test covers the fallback part of the `or` expression
    # on the target line.
    xmlfile = MagicMock(spec=Path)
    rng_schema = MagicMock(spec=Path)
    error = FileNotFoundError(2, 'No such file or directory')
    error.filename = None

    with patch.object(
        process_validation, 'run_command', new_callable=AsyncMock, side_effect=error
    ):
        success, output = await validate_rng(xmlfile, rng_schema, xinclude=False)

    assert not success, 'Expected validation to fail.'
    assert (
        output == 'xmllint/jing command not found. Please install it to run validation.'
    )


async def test_process_file_with_validation_issues(capsys):
    """Test process_file with validation issues."""
    with patch.object(
        process_validation,
        'validate_rng',
        new=AsyncMock(return_value=(False, 'Validation error')),
    ) as mock_validate_rng:
        xmlfile = MagicMock(spec=Path, name='test.xml')
        xmlfile.__str__.return_value = 'path/to/file.xml'
        xmlfile.parts = ('path', 'to', 'file.xml')

        mock_context = Mock(spec=DocBuildContext)

        result = await process_validation.process_file(xmlfile, mock_context, 40)

        assert result != 0, (
            'Expected process_file to return 10 due to validation issues.'
        )
        # mock_validate_rng.assert_called_once_with(xmlfile, rng_schema_path=rng_schema, xinclude=True)
        mock_validate_rng.assert_awaited_once()

    captured = capsys.readouterr()
    assert 'RNG validation => failed' in captured.err
    assert 'Validation error' in captured.err


async def test_process_file_with_xmlsyntax_error(capsys):
    """Test process_file with XML syntax error."""
    xmlfile = MagicMock(spec=Path, name='test.xml')
    xmlfile.__str__.return_value = 'path/to/file.xml'
    xmlfile.parts = ('path', 'to', 'file.xml')
    xmlfile.exists.return_value = True
    xmlfile.is_file.return_value = True
    xmlfile.read_text.return_value = """<root><invalid></root>"""

    mock_context = Mock(spec=DocBuildContext)

    with (
        patch.object(
            process_validation.etree,
            'parse',
            new=Mock(
                side_effect=process_validation.etree.XMLSyntaxError(
                    'XML syntax error', code=None, line=0, column=0, filename='fake.xml'
                )
            ),
        ) as mock_etree_parse,
        patch.object(
            process_validation, 'validate_rng', new=AsyncMock(return_value=(True, ''))
        ) as mock_validate_rng,
    ):
        result = await process_validation.process_file(xmlfile, mock_context, 40)

        assert result != 0, (
            'Expected process_file to return 10 due to XML syntax error.'
        )
        mock_validate_rng.assert_awaited_once()
        capture = capsys.readouterr()
        assert 'XML syntax error' in capture.err
