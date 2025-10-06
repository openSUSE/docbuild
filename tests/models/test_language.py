from pydantic import ValidationError
import pytest

from docbuild.constants import ALLOWED_LANGUAGES
from docbuild.models.language import LanguageCode


@pytest.mark.parametrize('language', sorted(ALLOWED_LANGUAGES))
def test_valid_language(language):
    lang, country = language.split('-')
    thelang = LanguageCode(language=language)
    assert thelang.language == language
    assert thelang.lang == lang
    assert thelang.country == country


def test_wildcard_language():
    thelang = LanguageCode(language='*')
    assert thelang.language == '*'
    assert thelang.lang == '*'
    assert thelang.country == '*'


def test_unknown_language():
    with pytest.raises(ValidationError, match='validation error'):
        LanguageCode(language='de-ch')


def test_language_with_underscore():
    thelang = LanguageCode(language='de_de')
    assert thelang.language == 'de-de'
    assert thelang.lang == 'de'
    assert thelang.country == 'de'


def test_str_in_language():
    thelang = LanguageCode(language='de_de')
    assert str(thelang) == 'de-de'


def test_repr_in_language():
    thelang = LanguageCode(language='de-de')
    assert repr(thelang) == "LanguageCode(language='de-de')"


def test_compare_two_uneqal_languages():
    lang1 = LanguageCode(language='en-us')
    lang2 = LanguageCode(language='de-de')
    assert lang1 != lang2
    assert lang2 != lang1


def test_compare_two_eqal_languages():
    lang1 = LanguageCode(language='de-de')
    lang2 = LanguageCode(language='de-de')
    assert lang1 == lang2
    assert lang2 == lang1


def test_compare_with_all_language():
    lang1 = LanguageCode(language='*')
    lang2 = LanguageCode(language='de-de')
    assert lang1 != lang2
    assert lang2 != lang1


def test_compare_with_one_language_and_with_different_object():
    lang1 = LanguageCode(language='*')
    lang2 = object()
    assert lang1 != lang2


def test_language_code_is_frozen():
    lang = LanguageCode(language='en-us')

    with pytest.raises(ValidationError, match='.*frozen_instance.*'):
        lang.language = 'de-de'


def test_language_code_is_hashable():
    lang = LanguageCode(language='en-us')
    s = {lang}
    assert lang in s


def test_compare_languagecode_with_str():
    lang1 = LanguageCode(language='de-de')
    lang2 = 'de-de'
    assert lang1 == lang2
    assert lang2 == lang1


@pytest.mark.parametrize(
    'languages,expected',
    [
        # 1
        (('en-us', 'de-de'), ('de-de', 'en-us')),
        # 2
        (('zh-cn', 'de-de'), ('de-de', 'zh-cn')),
        # 3
        (
            ('pt-br', 'es-es', 'ja-jp', 'fr-fr', 'ko-kr'),
            ('es-es', 'fr-fr', 'ja-jp', 'ko-kr', 'pt-br'),
        ),
        # 4 Special case with "*": ALL comes always first
        (('en-us', '*', 'de-de'), ('*', 'de-de', 'en-us')),
    ],
)
def test_sorting_languages(languages, expected):
    languages = sorted([LanguageCode(language=lang) for lang in languages])
    assert languages == [LanguageCode(language=lang) for lang in expected]


def test_compare_two_langs():
    lang1 = LanguageCode(language='de-de')
    lang2 = 'en-us'
    assert lang1 < lang2


def test_compare_two_langs_with_asterisk():
    lang1 = LanguageCode(language='*')
    lang2 = LanguageCode(language='de-de')
    assert lang1 < lang2


def test_compare_two_asterisks():
    lang1 = LanguageCode(language='*')
    lang2 = LanguageCode(language='*')
    assert not lang1 < lang2


def test_compare_with_unknown_type():
    lang1 = LanguageCode(language='de-de')
    lang2 = object()
    with pytest.raises(TypeError):
        assert lang1 < lang2


def test_language_matches():
    lang1 = LanguageCode(language='de-de')
    assert lang1.matches('*')