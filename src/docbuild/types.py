"""Common domain type aliases for docbuild."""

from typing import Any, Literal

type FormatType = Literal["html", "pdf", "single-html"]
type FormatDict = dict[FormatType, str]
type JsonDict = dict[str, Any]
type CheckResultTuple = tuple[str, str, str]
