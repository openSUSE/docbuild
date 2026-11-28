"""Custom exceptions for docbuild."""


class NoDeliverablesError(LookupError):
    """Raised when a doctype matches no deliverables in the portal config."""
