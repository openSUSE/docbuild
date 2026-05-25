"""Translation metadata for deliverables."""

from dataclasses import dataclass

from ..language import LanguageCode


@dataclass(frozen=True)
class TranslationInfo:
    """Translation metadata for a ref locale."""

    lang: LanguageCode
    branch: str | None = None
    subdir: str | None = None
