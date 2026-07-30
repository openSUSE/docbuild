"""Metadata processing tasks.

Public API for the metadata task package. Import :func:`process` to run the
full metadata extraction pipeline, or :func:`process_doctype` for a single
doctype.
"""

from .runner import process, process_doctype

__all__ = ["process", "process_doctype"]
