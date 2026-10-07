"""Centralized Rich console instances for docbuild CLI output and errors."""

from rich.console import Console

from .theme import DOCBUILD_THEME

console: Console = Console(theme=DOCBUILD_THEME)
"""Shared Rich console for standard output."""

console_err: Console = Console(stderr=True, theme=DOCBUILD_THEME)
"""Shared Rich console for standard error and diagnostics."""

console_out: Console = console
"""Alias for `console` when explicit stdout/stderr symmetry is preferred."""
