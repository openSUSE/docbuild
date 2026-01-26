import pytest

from docbuild.constants import SERVER_ROLES, SERVER_ROLES_ALIASES
from docbuild.models.serverroles import ServerRole


@pytest.mark.parametrize("role", SERVER_ROLES)
def test_serverrole_with_call(role):
    assert ServerRole(role)


@pytest.mark.parametrize("role", SERVER_ROLES_ALIASES)
def test_serverrole_with_predicate(role):
    assert ServerRole(role)


@pytest.mark.parametrize("role", SERVER_ROLES)
def test_serverrole_with_uppercase(role):
    assert ServerRole(role) == ServerRole[role.upper()]
