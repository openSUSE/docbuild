"""Reusable status messages for consistent docbuild CLI output."""

from dataclasses import dataclass
import os
import sys

from rich.console import Console
from rich.text import Text

from .theme import ThemeTag

NO_SYMBOLS_ENV_VAR = "DOCBUILD_NO_SYMBOLS"
"""Environment variable that disables status symbols.

Symbols stay enabled when the variable is unset or set to ``0``, ``false``,
``no``, ``off``, or an empty string. Any other value disables them.
"""

_SYMBOLS_ENABLED_VALUES = frozenset({"", "0", "false", "no", "off"})
"""Values of :data:`NO_SYMBOLS_ENV_VAR` that keep symbols enabled."""

_app_symbols_enabled: bool = True
"""Application-config default for status symbols."""


def set_symbols_enabled(enabled: bool) -> None:
    """Set the application-config default for status symbols.

    The :data:`NO_SYMBOLS_ENV_VAR` environment variable still takes
    precedence over this value.
    """
    global _app_symbols_enabled
    _app_symbols_enabled = enabled


def symbols_enabled() -> bool:
    """Return whether status symbols are enabled.

    Symbols are enabled by default. The application configuration can change
    the default through :func:`set_symbols_enabled`; setting
    :data:`NO_SYMBOLS_ENV_VAR` takes precedence over that value.
    """
    value = os.environ.get(NO_SYMBOLS_ENV_VAR)
    if value is not None:
        return value.strip().lower() in _SYMBOLS_ENABLED_VALUES
    return _app_symbols_enabled


def _stdout_encoding() -> str | None:
    """Return the encoding of standard output, if it is known."""
    return getattr(sys.stdout, "encoding", None)


@dataclass(frozen=True, slots=True)
class Message:
    """A reusable CLI label with a semantic style and optional symbol."""

    label: str
    style: ThemeTag
    symbol: str | None = None

    def __str__(self) -> str:
        """Return the plain label without styling or decoration."""
        return self.label

    def _build_text(self, encoding: str | None, symbols: bool | None) -> Text:
        """Build styled text and omit the symbol when it cannot be encoded."""
        show_symbols = symbols_enabled() if symbols is None else symbols
        symbol = self.symbol if show_symbols else None

        if symbol and encoding:
            try:
                symbol.encode(encoding)
            except UnicodeEncodeError:
                symbol = None

        content = f"{symbol} {self.label}" if symbol else self.label
        return Text(content, style=self.style.value)

    def render(
        self,
        *,
        console: Console | None = None,
        symbols: bool | None = None,
    ) -> Text:
        """Build styled text, omitting an unencodable symbol if needed.

        :param console: Optional console used to check whether the destination
            encoding can represent the symbol.
        :param symbols: Whether to include the symbol. When ``None``, the
            shared :func:`symbols_enabled` setting is used.
        :returns: Styled text containing the label and optional symbol.
        """
        encoding = console.encoding if console is not None else None
        return self._build_text(encoding, symbols)

    def __rich__(self) -> Text:
        """Return styled text for Rich to print directly."""
        return self._build_text(_stdout_encoding(), None)


OK = Message("OK", ThemeTag.SUCCESS, symbol="✓")
"""Successful operation."""

ERROR = Message("Error", ThemeTag.ERROR, symbol="✗")
"""Failed operation."""

WARNING = Message("Warning", ThemeTag.WARNING, symbol="⚠")
"""Non-fatal problem or caution."""

INFO = Message("Info", ThemeTag.INFO)
"""Informational label."""

VALID = Message("Valid", ThemeTag.SUCCESS, symbol="✓")
"""Valid configuration or input."""

INVALID = Message("Invalid", ThemeTag.ERROR, symbol="✗")
"""Invalid configuration or input."""

SKIPPED = Message("Skipped", ThemeTag.WARNING, symbol="→")
"""Operation intentionally not performed."""

MISSING = Message("Missing", ThemeTag.ERROR, symbol="✗")
"""Required item that was not found."""
