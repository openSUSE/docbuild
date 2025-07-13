from typing import Any
import re

import pytest

from docbuild.config.app import (
    CircularReferenceError,
    PlaceholderResolutionError,
    PlaceholderResolver,
    replace_placeholders,
)


def test_replace_placeholders():
    config = {
        'server': {'name': 'example.com', 'url': 'https://{server.name}'},
        'paths': {
            'config_dir': '/etc/myapp',
            'tmp': {'tmp_base_dir': '/tmp/myapp'},
            'full_tmp_path': '{paths.tmp.tmp_base_dir}/session',
        },
        'logging': {
            'log_dir': '{paths.config_dir}/logs',
            'tmp_base_dir': '/var/tmp',
            # Should resolve within this section if key exists:
            'temp_dir': '{tmp_base_dir}',
        },
    }

    expected = {
        'server': {'name': 'example.com', 'url': 'https://example.com'},
        'paths': {
            'config_dir': '/etc/myapp',
            'tmp': {'tmp_base_dir': '/tmp/myapp'},
            'full_tmp_path': '/tmp/myapp/session',
        },
        'logging': {
            'log_dir': '/etc/myapp/logs',
            'tmp_base_dir': '/var/tmp',
            'temp_dir': '/var/tmp',
        },
    }

    result = replace_placeholders(config)
    assert result == expected, f'Expected {expected}, but got {result}'


def test_missing_key_in_current_section():
    config = {
        'database': {
            'host': 'localhost',
            # 'user' is missing in this section
            'url': 'postgres://{user}@{host}/mydb',
        },
        'user': 'admin',
    }

    with pytest.raises(
        PlaceholderResolutionError,
        match=re.escape(
            "While resolving '{user}' in 'url': key 'user' "
            'not found in current section.',
        ),
    ):
        replace_placeholders(config)


def test_unresolved_key_in_config():
    config = {
        'server': {'name': 'example.com', 'url': 'https://{server.name}'},
        'paths': {
            'config_dir': '/etc/myapp',
            'tmp': {'tmp_base_dir': '/tmp/myapp'},
            # 'session' is missing in this section
            'full_tmp_path': '{paths.tmp.session}/session',
        },
    }

    with pytest.raises(
        PlaceholderResolutionError,
        match=re.escape(
            "While resolving '{paths.tmp.session}' in 'full_tmp_path': missing key "
            "'session' in path 'paths.tmp.session'.",
        ),
    ):
        replace_placeholders(config)


def test_placeholders_in_list():
    config = {
        'paths': {
            'config_dir': '/etc/myapp',
        },
        'resources': {
            'files': [
                '{paths.config_dir}/app.yaml',
                '{paths.config_dir}/db.yaml',
                'static/style.css',
            ],
        },
    }

    expected = {
        'paths': {
            'config_dir': '/etc/myapp',
        },
        'resources': {
            'files': ['/etc/myapp/app.yaml', '/etc/myapp/db.yaml', 'static/style.css'],
        },
    }

    result = replace_placeholders(config)
    assert result == expected, f'Expected {expected}, but got {result}'


def test_literal_values_are_untouched():
    config = {
        'defaults': {'enabled': True, 'retries': 3, 'timeout': 5.5, 'optional': None},
    }

    expected = {
        'defaults': {'enabled': True, 'retries': 3, 'timeout': 5.5, 'optional': None},
    }

    result = replace_placeholders(config)
    assert result == expected, f'Expected {expected}, but got {result}'


def test_placeholder_path_is_not_dict():
    config = {
        'server': {'name': 'myserver', 'ip': '127.0.0.1'},
        'paths': {
            'tmp': 'not_a_dict',
            'path': '{paths.tmp.value}',  # .value should fail
        },
    }

    with pytest.raises(
        PlaceholderResolutionError,
        match=re.escape(
            "While resolving '{paths.tmp.value}' in 'path': 'paths.tmp.value' is not "
            'a dictionary (got type str).',
        ),
    ):
        replace_placeholders(config)


def test_chained_placeholder_resolution():
    data = {
        'paths': {
            'tmp': {
                'tmp_base_dir': '/tmp/docbuild',
                'tmp_dir': '{tmp_base_dir}/doc-example-com',
                'tmp_deliverable_dir': '{tmp_dir}/deliverable/',
            },
        },
    }

    result: dict[str, Any] = replace_placeholders(data)
    tmp = result['paths']['tmp']
    assert tmp['tmp_base_dir'] == '/tmp/docbuild'
    assert tmp['tmp_dir'] == '/tmp/docbuild/doc-example-com'
    assert tmp['tmp_deliverable_dir'] == '/tmp/docbuild/doc-example-com/deliverable/'


def test_too_many_nested_placeholder_expansions():
    data = {
        'section': {
            'a': '{b}',
            'b': '{a}',
        },
    }
    with pytest.raises(
        CircularReferenceError, match='Too many nested placeholder expansions'
    ):
        replace_placeholders(data)


def test_chained_cross_section_placeholders():
    config = {
        'build': {
            'output': '{paths.tmp_deliverable_dir}',
        },
        'paths': {
            'tmp_base_dir': '/tmp/docbuild',
            'tmp_dir': '{tmp_base_dir}/doc-example-com',
            'tmp_deliverable_dir': '{paths.tmp_dir}/deliverable/',
        },
    }

    result = replace_placeholders(config)
    assert result['build']['output'] == '/tmp/docbuild/doc-example-com/deliverable/'


def test_escaped_braces():
    config = {'section': {'key': 'This is a literal brace: {{not_a_placeholder}}'}}
    result = replace_placeholders(config)
    assert result['section']['key'] == 'This is a literal brace: {not_a_placeholder}'


def test_replace_placeholders_max_recursion_error():
    """Test that max recursion depth is enforced."""
    # Create a config with circular references that will cause infinite recursion
    config = {
        'a': '{b}',
        'b': '{c}',
        'c': '{d}',
        'd': '{e}',
        'e': '{f}',
        'f': '{g}',
        'g': '{h}',
        'h': '{i}',
        'i': '{j}',
        'j': '{k}',
        'k': '{a}',  # Circular reference back to 'a'
    }

    # This should raise ValueError due to max recursion depth
    with pytest.raises(
        CircularReferenceError, match='Too many nested placeholder expansions in key'
    ):
        replace_placeholders(config, max_recursion_depth=5)


def test_replace_placeholders_list_with_non_processable_items():
    """Test that list items that are not dict/list/str are skipped."""
    config = {
        'mixed_list': [
            'string_item',  # This will be processed (str)
            42,  # This will be skipped (int)
            3.14,  # This will be skipped (float)
            True,  # This will be skipped (bool)
            None,  # This will be skipped (NoneType)
            {'nested': 'dict'},  # This will be processed (dict)
            [1, 2, 3],  # This will be processed (list)
        ]
    }

    # This should process without error, skipping non-string/dict/list items
    result = replace_placeholders(config)

    # The structure should remain the same since no placeholders to replace
    assert result == config
    assert result['mixed_list'][1] == 42  # int unchanged
    assert result['mixed_list'][2] == 3.14  # float unchanged
    assert result['mixed_list'][3] is True  # bool unchanged
    assert result['mixed_list'][4] is None  # None unchanged


def test_placeholder_resolution_error_is_keyerror():
    """Test that PlaceholderResolutionError is a subclass of KeyError."""
    config = {
        'section': {
            'value': '{missing_key}',
        },
    }

    # Should be catchable as both PlaceholderResolutionError and KeyError
    with pytest.raises(PlaceholderResolutionError):
        replace_placeholders(config)

    with pytest.raises(KeyError):
        replace_placeholders(config)


def test_placeholder_wrong_type():
    config = 42
    assert replace_placeholders(config) == 42, 'Non-dict input should return unchanged'


def test_get_container_name_with_none_key():
    """Test _get_container_name when _current_key is None."""
    config = {'test': 'value'}
    resolver = PlaceholderResolver(config)

    # Initially _current_key is None
    assert resolver._current_key is None

    # This should return 'unknown'
    container_name = resolver._get_container_name()
    assert container_name == 'unknown'
