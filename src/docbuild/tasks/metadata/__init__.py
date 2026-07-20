"""Metadata task entry points and reusable helpers."""

from .collect import collect_dynamic_metadata
from .discovery import get_deliverables_for_doctype, iter_doctype_groups
from .manifest import (
    build_document_for_deliverable,
    compile_manifest,
    write_manifest_json,
)
from .progress import report_failed_deliverables, run_metadata_progress
from .service import process, process_doctype_group

__all__ = [
    "build_document_for_deliverable",
    "collect_dynamic_metadata",
    "compile_manifest",
    "get_deliverables_for_doctype",
    "iter_doctype_groups",
    "process",
    "process_doctype_group",
    "report_failed_deliverables",
    "run_metadata_progress",
    "write_manifest_json",
]
