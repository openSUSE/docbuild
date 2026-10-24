import pytest

from docbuild.constants import ENV_ROLES, ENV_ROLES_ALIASES
from docbuild.models.envroles import EnvRole


@pytest.mark.parametrize("role", ENV_ROLES)
def test_envrole_with_call(role):
    assert EnvRole(role)


@pytest.mark.parametrize("role", ENV_ROLES_ALIASES)
def test_envrole_with_predicate(role):
    assert EnvRole(role)


@pytest.mark.parametrize("role", ENV_ROLES)
def test_envrole_with_uppercase(role):
    assert EnvRole(role) == EnvRole[role.upper()]
