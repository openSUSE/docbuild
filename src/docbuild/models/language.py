"""Language model for representing language codes."""

from functools import cached_property, total_ordering
from typing import Any, ClassVar

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator
from pydantic.config import ConfigDict

from ..constants import ALLOWED_LANGUAGES


@total_ordering
class LanguageCode(BaseModel):
    """The language in the format language-country (all lowercase).

    It accepts also an underscore as a separator instead of a dash.
    Use "*" to denote "ALL" languages
    """

    language: str = Field(
        title='The natural language',
        description=(
            'A natural language in the format ll-cc, '
            "whereas 'll' is the language and 'cc' the country "
            'both in lowercase letters. '
            "The special syntax '*' denotes every language."
        ),
        examples=['en-us', 'de-de'],
        frozen=True,
    )
    """The natural language in the format ll-cc, where 'll' is the
    language and 'cc' the country."""

    model_config = ConfigDict(frozen=True)
    """Configuration for the model, should be a dictionary
    conforming to Pydantic's :class:`~pydantic.config.ConfigDict`."""

    ALLOWED_LANGS: ClassVar[frozenset] = frozenset(
        {'*'} | ALLOWED_LANGUAGES,
    )
    """Class variable containing all allowed languages."""

    @model_validator(mode='before')
    @classmethod
    def _convert_str_to_dict(cls, data: Any) -> Any:
        """Allow initializing LanguageCode from a plain string."""
        if isinstance(data, str):
            return {'language': data}
        return data

    def __str__(self) -> str:
        """Implement str(self)."""
        return f'{self.language}'

    def __repr__(self) -> str:
        """Implement repr(self)."""
        return f'{self.__class__.__name__}(language={str(self)!r})'

    def __eq__(self, other: 'object|str|LanguageCode') -> bool:
        """Implement self == other.

        The comparison does NOT break the principle of equality:
        * Reflexive: a == b
        * Symmetric: a == b <=> b == a
        * Transitive: if a == b and b == c, then a == c

        If you need to check for wildcar logic, use matches()
        """
        if isinstance(other, LanguageCode):
            return self.language == other.language
        elif isinstance(other, str):
            return self.language == other
        return NotImplemented

    def __lt__(self, other: 'object|str|LanguageCode') -> bool:
        """Implement self < other.

        Special properties:
        - "*" is always the "smallest" language
        - If self contains "*" and the other not, return True
        - If self and the other contains "*", return False
        """
        if isinstance(other, LanguageCode):
            other_value = other.language
        elif isinstance(other, str):
            other_value = other
        else:
            return NotImplemented

        # "*" is always smallest
        if self.language == '*':
            return other_value != '*'
        if other_value == '*':
            return False

        # Perform string comparison after handling the wildcard case
        return self.language < other_value

    def __hash__(self) -> int:
        """Implement hash(self).

        For using 'in sets' or as dict keys
        """
        return hash(self.language)

    def matches(self, other: 'LanguageCode | str') -> bool:
        """Return True if this LanguageCode matches the other, considering wildcards.

        The string '*' matches any language:

        >>> LanguageCode("*").matches("de-de")
        True
        >>> LanguageCode("de-de").matches("*")
        True
        """
        other_value = str(other)
        return (
            self.language == '*' or other_value == '*' or self.language == other_value
        )

    @field_validator('language', mode='before')
    @classmethod
    def _normalize_language_separator(cls, value: str) -> str:
        """Normalize separator from _ to -."""
        if isinstance(value, str):
            return value.replace('_', '-')
        return value

    @field_validator('language')
    @classmethod
    def validate_language(cls, value: str) -> str:
        """Check if the passed language adheres to the allowed language."""
        if value not in cls.ALLOWED_LANGS:
            raise ValueError(
                (
                    f"Invalid language code '{value}'. "
                    f'Expected one of {", ".join(sorted(cls.ALLOWED_LANGS))}'
                ),
            )
        return value

    @cached_property
    def _parts(self) -> tuple[str, str] | tuple[str]:
        """Split the `language` code into language and country.

        This method parses the :attr:`language` string into its parts
        and caches the result per instance to avoid redundant parsing operations.

        :returns: A tuple containing:
          - ``(language, country)`` if both parts are present.
          - ``('*',)`` if the language code is ``"*"``
        """
        if self.language == '*':
            return ('*',)

        # Use split('-') as the separator is already normalized
        parts = self.language.split('-')
        return (parts[0], parts[1]) if len(parts) > 1 else (parts[0],)

    @computed_field(
        repr=False,
        title='The language part of the language code',
        examples=['en', 'de', 'ja'],
    )
    def lang(self) -> str:
        """Extract the language part of the language code (property)."""
        return self._parts[0]

    @computed_field(
        repr=False,
        title='The country part of the language code',
        examples=['us', 'de', 'jp'],
    )
    def country(self) -> str:
        """Extract the country part of the language code (property)."""
        return self._parts[1] if len(self._parts) > 1 else '*'
