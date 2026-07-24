"""Tests for metadata manifest helpers."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import docbuild.tasks.metadata.manifest as manifest_mod
from docbuild.tasks.metadata.manifest import (
    build_document_for_deliverable,
    compile_manifest,
    write_manifest_json,
)


class TestManifestHelpers:
    """Tests for manifest and document helper functions."""

    def test_build_document_for_deliverable_raises_without_docs(self, deliverable) -> None:
        """Reject metadata payloads that do not contain document entries."""
        with (
            patch.object(
                manifest_mod.Document,
                "from_metadata_payload",
                return_value=SimpleNamespace(docs=[]),
            ),
            pytest.raises(ValueError),
        ):
            build_document_for_deliverable(deliverable, {})

    def test_build_document_for_deliverable_sets_single_html(
        self,
        deliverable_single_html,
    ) -> None:
        """Populate optional single HTML output when the format is enabled."""
        document = build_document_for_deliverable(
            deliverable_single_html,
            {"docs": [{"rootid": "doc-root", "title": "Doc"}]},
            lang="de-de",
        )

        assert document.docs[0].lang == "de-de"
        assert document.docs[0].format.single_html is not None
        assert document.docs[0].format.pdf is not None

    def test_build_document_for_deliverable_without_optional_formats(
        self,
        deliverable,
    ) -> None:
        """Keep optional output paths unset when their formats are disabled."""
        deliverable.__dict__["format"] = {
            "html": True,
            "pdf": False,
            "single-html": False,
        }

        document = build_document_for_deliverable(
            deliverable,
            {"docs": [{"rootid": "doc-root", "title": "Doc"}]},
        )

        assert document.docs[0].format.pdf is None
        assert document.docs[0].format.single_html is None

    def test_build_document_from_deliverable_returns_none_for_non_document(self) -> None:
        """Return None when an object does not expose a valid Document."""
        deliverable_mock = SimpleNamespace(document="invalid")
        assert manifest_mod.build_document_from_deliverable(deliverable_mock) is None

    def test_merge_document_docs_skips_duplicate_languages(self, deliverable) -> None:
        """Avoid appending duplicate language variants during merges."""
        target = build_document_for_deliverable(
            deliverable,
            {"docs": [{"rootid": "root-a", "title": "Doc A"}]},
        )
        source = build_document_for_deliverable(
            deliverable,
            {"docs": [{"rootid": "root-b", "title": "Doc B"}]},
        )

        manifest_mod.merge_document_docs(target, source)
        assert len(target.docs) == 1

    def test_write_manifest_json_overwrites_existing_file(
        self,
        tmp_path: Path,
        deliverable,
    ) -> None:
        """Replace an existing manifest file while preserving atomic write behavior."""
        deliverable.document = build_document_for_deliverable(
            deliverable,
            {"docs": [{"rootid": "doc-root", "title": "Doc"}]},
        )
        manifest = compile_manifest(
            deliverable.xml.productid,
            deliverable.xml.docsetid,
            [deliverable],
        )
        assert manifest is not None
        out_file = tmp_path / "manifest.json"
        out_file.write_text("{}", encoding="utf-8")

        write_manifest_json(out_file, manifest)

        payload = json.loads(out_file.read_text(encoding="utf-8"))
        assert payload["documents"][0]["docs"][0]["title"] == "Doc"

    def test_compile_manifest_skips_missing_documents(self, deliverable) -> None:
        """Ignore deliverables that do not expose a parsed document."""
        deliverable_with_doc = type(deliverable)(deliverable._node)
        deliverable_with_doc.document = build_document_for_deliverable(
            deliverable_with_doc,
            {"docs": [{"rootid": "doc-root", "title": "Doc"}]},
        )

        manifest = compile_manifest(
            deliverable.xml.productid,
            deliverable.xml.docsetid,
            [deliverable, deliverable_with_doc],
        )

        assert manifest is not None
        assert len(manifest.documents) == 1

    def test_compile_manifest_fallback_doc_key_and_merge_docs(self, deliverable) -> None:
        """Fallback to deliverable key and merge docs for duplicate document keys."""
        first = type(deliverable)(deliverable._node)
        second = type(deliverable)(deliverable._node)

        first.document = build_document_for_deliverable(
            first,
            {"docs": [{"rootid": "root-en", "title": "Doc EN"}]},
            lang="en-us",
        )
        second.document = build_document_for_deliverable(
            second,
            {"docs": [{"rootid": "root-de", "title": "Doc DE"}]},
            lang="de-de",
        )

        first.document.docs[0].dcfile = ""
        second.document.docs[0].dcfile = ""

        manifest = compile_manifest(
            deliverable.xml.productid,
            deliverable.xml.docsetid,
            [first, second],
        )

        assert manifest is not None
        assert len(manifest.documents) == 1
        assert len(manifest.documents[0].docs) == 2


def test_write_manifest_json_cleans_temp_file_on_write_error(
    tmp_path: Path,
    deliverable,
) -> None:
    """Remove temporary files when writing the manifest fails mid-flight."""
    deliverable.document = build_document_for_deliverable(
        deliverable,
        {"docs": [{"rootid": "doc-root", "title": "Doc"}]},
    )
    manifest = compile_manifest(
        deliverable.xml.productid,
        deliverable.xml.docsetid,
        [deliverable],
    )
    assert manifest is not None

    out_file = tmp_path / "manifest.json"

    with (
        patch.object(manifest_mod.json, "dump", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError),
    ):
        write_manifest_json(out_file, manifest)

    leftovers = list(out_file.parent.glob(f".{out_file.stem}.*.tmp"))
    assert leftovers == []


@pytest.mark.asyncio
async def test_compile_manifest_writes_json(tmp_path: Path, deliverable) -> None:
    """Write manifest JSON for a compiled document list."""
    metadata_payload: dict[str, object] = {
        "docs": [{"rootid": "doc-root", "title": "Doc1"}]
    }
    document = build_document_for_deliverable(deliverable, metadata_payload)
    deliverable.document = document

    manifest = compile_manifest(
        deliverable.xml.productid,
        deliverable.xml.docsetid,
        [deliverable],
    )
    assert manifest is not None

    out_file = tmp_path / "manifest.json"
    write_manifest_json(out_file, manifest)

    merged = json.loads(out_file.read_text(encoding="utf-8"))
    assert merged["documents"][0]["docs"][0]["title"] == "Doc1"
    assert merged["hide-productname"] is False


def test_compile_manifest_missing_documents_returns_none(deliverable) -> None:
    """Return None when no deliverable documents are present."""
    manifest = compile_manifest(
        deliverable.xml.productid,
        deliverable.xml.docsetid,
        [deliverable],
    )
    assert manifest is None


def test_compile_manifest_empty_deliverables_returns_none() -> None:
    """Return None when no deliverables are provided."""
    manifest = compile_manifest("sles", "15-sp6", [])
    assert manifest is None
