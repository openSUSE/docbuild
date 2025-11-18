from itertools import chain, combinations

import pytest

from docbuild.constants import ALLOWED_LIFECYCLES
from docbuild.models.lifecycle import LifecycleFlag


@pytest.mark.parametrize('lifecycle', ALLOWED_LIFECYCLES)
def test_valid_lifecycles(lifecycle):
    instance = getattr(LifecycleFlag, lifecycle)
    assert instance.name == lifecycle


def test_unknown_lifecycle():
    instance = LifecycleFlag.unknown
    assert instance.name == 'unknown'
    assert instance.value == 0
    instance = LifecycleFlag(0)
    assert instance.name == 'unknown'


def test_lifecycle_flag_from_str_with_empty_string():
    instance = LifecycleFlag.from_str('')
    assert instance == LifecycleFlag.unknown
    assert instance.name == 'unknown'
    assert instance.value == 0


def all_non_empty_combinations(items):
    return chain.from_iterable(combinations(items, r) for r in range(1, len(items) + 1))


@pytest.mark.parametrize(
    'input_str',
    ['|'.join(combo) for combo in all_non_empty_combinations(ALLOWED_LIFECYCLES)],
)
def test_lifecycle_flag_from_str(input_str):
    lifecycle = LifecycleFlag.from_str(input_str)  # type: ignore

    assert set(i.name for i in lifecycle) == set(input_str.split('|'))


@pytest.mark.parametrize(
    'input_str',
    ['|'.join(combo) for combo in all_non_empty_combinations(ALLOWED_LIFECYCLES)],
)
def test_contains_for_lifecycle(input_str):
    lifecycle = LifecycleFlag.from_str(input_str)
    assert input_str in lifecycle


def test_contains_with_invalidvalue_for_lifecycle():
    with pytest.raises(ValueError):
        assert 'nonexistent' in LifecycleFlag.beta


def test_contains_with_lifecycle_for_lifecycle():
    assert LifecycleFlag.beta == LifecycleFlag.beta


def test_non_string_non_flag_returns_not_implemented():
    lifecycle = LifecycleFlag.from_str('supported')
    assert (42 in lifecycle) is False  # triggers fallback, returns False


def test_contains_other_lifecycle_flag():
    lifecycle = LifecycleFlag.from_str('supported|beta')
    other_lifecycle = LifecycleFlag.from_str('beta')

    # Should return True as `beta` is in `supported|beta`
    assert other_lifecycle in lifecycle
