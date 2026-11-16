"""Mail notification subsystem for Docbuild."""

from .models import FailureCollector, FailureRecord
from .sender import notify_build_failures, send_email

__all__ = [
    "FailureCollector",
    "FailureRecord",
    "notify_build_failures",
    "send_email",
]
