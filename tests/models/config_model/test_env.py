"""Unit tests for the EnvConfig Pydantic models."""

from pathlib import Path
from typing import Any
import os
from unittest.mock import Mock

import pytest
from pydantic import ValidationError, HttpUrl, IPvAnyAddress
from ipaddress import IPv4Address

from docbuild.models.config_model.env import EnvConfig, Env_Server
import docbuild.config.app as config_app_mod 


# --- Fixture Setup ---

def _mock_successful_placeholder_resolver(data: dict[str, Any]) -> dict[str, Any]:
    """Mocks the placeholder resolver to return a guaranteed clean, resolved dictionary."""

    resolved_data = data.copy()
    
    # Define resolved paths based on the EnvConfig structure
    tmp_general = '/var/tmp/docbuild/doc-example-com'
    
    resolved_data['paths']['config_dir'] = '/etc/docbuild'
    resolved_data['paths']['root_config_dir'] = '/etc/docbuild'
    resolved_data['paths']['jinja_dir'] = '/etc/docbuild/jinja-doc-suse-com'
    resolved_data['paths']['server_rootfiles_dir'] = '/etc/docbuild/server-root-files-doc-suse-com'
    resolved_data['paths']['repo_dir'] = '/var/cache/docbuild/repos/permanent-full/'
    resolved_data['paths']['temp_repo_dir'] = '/var/cache/docbuild/repos/temporary-branches/'
    resolved_data['paths']['base_cache_dir'] = '/var/cache/docserv'
    resolved_data['paths']['base_server_cache_dir'] = '/var/cache/docserv/doc-example-com'
    resolved_data['paths']['meta_cache_dir'] = '/var/cache/docbuild/doc-example-com/meta'
    resolved_data['paths']['base_tmp_dir'] = '/var/tmp/docbuild'
    resolved_data['paths']['tmp']['tmp_base_dir'] = '/var/tmp/docbuild'
    resolved_data['paths']['tmp']['tmp_path'] = tmp_general
    resolved_data['paths']['tmp']['tmp_deliverable_path'] = tmp_general + '/deliverable'
    resolved_data['paths']['tmp']['tmp_metadata_dir'] = tmp_general + '/metadata'
    resolved_data['paths']['tmp']['tmp_build_dir'] = tmp_general + '/build/{{product}}-{{docset}}-{{lang}}'
    resolved_data['paths']['tmp']['tmp_out_path'] = tmp_general + '/out'
    resolved_data['paths']['tmp']['log_path'] = tmp_general + '/log'
    resolved_data['paths']['tmp']['tmp_deliverable_name'] = '{{product}}_{{docset}}_{{lang}}_XXXXXX'
    resolved_data['paths']['target']['target_path'] = 'doc@10.100.100.100:/srv/docs'
    resolved_data['paths']['target']['backup_path'] = Path('/data/docbuild/external-builds/')
    
    # Ensure mandatory top-level fields (like 'build') are present 
    resolved_data.setdefault(
        'build', 
        {'daps': {'command': 'daps', 'meta': 'daps meta'}, 'container': {'container': 'registry.example.com/container'}}
    )

    return resolved_data


@pytest.fixture(autouse=True)
def mock_placeholder_resolution(monkeypatch):
    """Mocks the replace_placeholders utility used inside EnvConfig."""

    monkeypatch.setattr(
        config_app_mod,
        'replace_placeholders', 
        _mock_successful_placeholder_resolver
    )


@pytest.fixture
def mock_valid_raw_env_data(tmp_path: Path) -> dict[str, Any]:
    """
    Provides a minimal, valid dictionary representing env.toml data (using aliases).
    Includes ALL mandatory path fields and a nested xslt-params structure.
    """

    nested_xslt_params = {
        'external': {'js': {'onlineonly': '/docserv/res/extra.js'}},
        'show': {'edit': {'link': 1}},
        'twittercards': {'twitter': {'account': '@SUSE'}},
        'generate': {'json-ld': 1},
        'search': {'description': {'length': 118}},
        'socialmedia': {'description': {'length': 65}},
    }
    
    return {
        'server': {
            'name': 'doc-example-com',
            'role': 'production',
            'host': '127.0.0.1',
            'enable_mail': True,
        },
        'config': {
            'default_lang': 'en-us',
            'languages': ['en-us', 'de-de'],
            'canonical_url_domain': 'https://docs.example.com',
        },
        'paths': {
            'config_dir': str(tmp_path / 'config'),
            'root_config_dir': '/etc/docbuild',
            'jinja_dir': '/etc/docbuild/jinja',
            'server_rootfiles_dir': '/etc/docbuild/rootfiles',
            'base_server_cache_dir': '/var/cache/docserv/server',
            'base_tmp_dir': '/var/tmp/docbuild',
            'repo_dir': '/var/cache/docbuild/repos/permanent-full/',
            'temp_repo_dir': '/var/cache/docbuild/repos/temporary-branches/',
            'base_cache_dir': '/var/cache/docserv',
            'meta_cache_dir': '/var/cache/docbuild/doc-example-com/meta',
            
            'tmp': {
                'tmp_base_dir': '/var/tmp/docbuild',
                'tmp_dir': '{tmp_base_dir}/doc-example-com', 
                'tmp_deliverable_dir': '{tmp_dir}/deliverable/',
                'tmp_build_dir': '{tmp_dir}/build/{{product}}-{{docset}}-{{lang}}',
                'tmp_out_dir': '{tmp_dir}/out/',
                'log_dir': '{tmp_dir}/log',
                'tmp_metadata_dir': '{tmp_dir}/metadata', 
                'tmp_deliverable_name': '{{product}}_{{docset}}_{{lang}}_XXXXXX',
            },
            'target': {
                'target_dir': 'doc@10.100.100.100:/srv/docs',
                'backup_dir': Path('/data/docbuild/external-builds/'),
            }
        },
        'build': {
            'daps': {'command': 'daps', 'meta': 'daps meta'},
            'container': {'container': 'registry.example.com/container'},
        },
        'xslt-params': nested_xslt_params, # <-- Use nested structure
    }


# --- Unit Test Cases ---

def test_envconfig_full_success(mock_valid_raw_env_data: dict[str, Any]):
    """Test successful validation of the entire EnvConfig schema."""

    config = EnvConfig.from_dict(mock_valid_raw_env_data)

    assert isinstance(config, EnvConfig)
    
    # Check type coercion for core types
    assert isinstance(config.paths.base_cache_dir, Path)
    
    assert config.paths.tmp.tmp_path.is_absolute()
    assert config.paths.tmp.tmp_path.name == 'doc-example-com'
    
    # Check that the field with runtime placeholders is correctly handled as a string
    assert isinstance(config.paths.tmp.tmp_build_dir, str)

    # Check XSLT params: should now contain the nested structure
    assert 'external' in config.xslt_params
    assert isinstance(config.xslt_params['external'], dict)
    assert config.xslt_params['show']['edit']['link'] == 1


def test_envconfig_type_coercion_ip_host(mock_valid_raw_env_data: dict[str, Any]):
    """Test that the host field handles IPvAnyAddress correctly."""

    data = mock_valid_raw_env_data.copy()
    data['server']['host'] = '192.168.1.1'
    
    config = EnvConfig.from_dict(data)
    
    assert isinstance(config.server.host, IPv4Address) 
    assert str(config.server.host) == '192.168.1.1'


def test_envconfig_strictness_extra_field_forbid(tmp_path: Path):
    """Test that extra fields are forbidden on the top-level EnvConfig model."""

    raw_data = {
        'build': {
            'daps': {'command': 'daps', 'meta': 'daps meta'},
            'container': {'container': 'registry.example.com/container'},
        },
        'server': {'name': 'D', 'role': 'production', 'host': '1.1.1.1', 'enable_mail': True},
        'config': {
            'default_lang': 'en-us', 
            'languages': ['en-us'],
            'canonical_url_domain': 'https://a.b'
        },
        'paths': {
            'config_dir': str(tmp_path / 'config'), 
            'root_config_dir': '/tmp',
            'jinja_dir': '/tmp',
            'server_rootfiles_dir': '/tmp',
            'base_server_cache_dir': '/tmp',
            'base_tmp_dir': '/tmp',
            'repo_dir': '/tmp', 
            'temp_repo_dir': '/tmp', 
            'base_cache_dir': '/tmp',
            'meta_cache_dir': '/tmp',
            
            'tmp': {
                'tmp_base_dir': '/tmp', 
                'tmp_dir': '/tmp',
                'tmp_deliverable_dir': '/tmp/deliverable', 
                'tmp_metadata_dir': '/tmp/metadata',
                'tmp_build_dir': '/tmp/build/{{product}}', 
                'tmp_out_dir': '/tmp/out', 
                'log_dir': '/tmp/log', 
                'tmp_deliverable_name': 'main',
            },
            'target': {
                'target_dir': '/srv', 
                'backup_dir': '/mnt' 
            },
        },
        'xslt-params': {'test': 1}, 
        'typo_section': {'key': 'value'}
    }
    
    with pytest.raises(ValidationError) as excinfo:
        EnvConfig.from_dict(raw_data)
        
    locs = excinfo.value.errors()[0]['loc']
    assert ('typo_section',) == tuple(locs)


def test_envconfig_invalid_role_fails(mock_valid_raw_env_data: dict[str, Any]):
    """Test that an invalid role string is rejected by ServerRole enum."""
    
    data = mock_valid_raw_env_data.copy()
    data['server']['role'] = 'testing_invalid'
    
    with pytest.raises(ValidationError) as excinfo:
        EnvConfig.from_dict(data)
        
    locs = excinfo.value.errors()[0]['loc']
    assert ('server', 'role') == tuple(locs)