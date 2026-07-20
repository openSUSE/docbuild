"""Manifest assembly helpers for metadata extraction results."""

from collections.abc import Sequence
import json
import os
from pathlib import Path
import tempfile

from ...models.deliverable import Deliverable
from ...models.deliverable.paths import DeliverablePaths
from ...models.language import LanguageCode
from ...models.manifest import (
    Archive,
    Category,
    Description,
    Document,
    DocumentFormat,
    Manifest,
)


def build_document_for_deliverable(
    deliverable: Deliverable,
    metadata_payload: dict[str, object],
    *,
    lang: str | LanguageCode | None = None,
) -> Document:
    """Build a normalized document from a deliverable metadata payload.

    :param deliverable: Deliverable to process.
    :param metadata_payload: Parsed metadata payload.
    :param lang: Optional language override for translated deliverables.
    :return: Normalized document instance.
    :raises ValueError: When no document payload is available.
    """
    lang_value = lang if lang is not None else deliverable.xml.lang
    lang_code = (
        lang_value
        if isinstance(lang_value, LanguageCode)
        else LanguageCode(language=str(lang_value))
    )
    lang_text = str(lang_code)
    dcfile = deliverable.xml.dcfile or ""
    document = Document.from_metadata_payload(
        metadata_payload,
        dcfile=dcfile,
        lang=lang_text,
    )
    if not document.docs:
        raise ValueError("Metadata payload missing document data.")

    rootid = document.docs[0].rootid
    document.docs[0].dcfile = dcfile
    document.docs[0].lang = lang_text
    document.docs[0].rootid = rootid
    paths = DeliverablePaths(deliverable.xml, rootid=rootid, lang=lang_code)
    fmt = deliverable.format
    doc_format = DocumentFormat(html=paths.html_path)
    if fmt.get("pdf"):
        doc_format.pdf = paths.pdf_path
    if fmt.get("single-html"):
        doc_format.single_html = paths.singlehtml_path

    document.docs[0].format = doc_format
    return document


def write_manifest_json(json_path: Path, manifest: Manifest) -> None:
    """Write a manifest JSON file atomically.

    :param json_path: Destination JSON file path.
    :param manifest: Manifest data to serialize.
    """
    json_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    payload = manifest.model_dump(by_alias=True)

    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(json_path.parent),
            delete=False,
            prefix=f".{json_path.stem}.",
            suffix=".tmp",
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)
            json.dump(payload, tmp_file, indent=2, ensure_ascii=False)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

        if json_path.exists():
            tmp_path.chmod(json_path.stat().st_mode)

        tmp_path.replace(json_path)

        dir_fd = os.open(str(json_path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        tmp_path = None

    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


def build_document_from_deliverable(deliverable: Deliverable) -> Document | None:
    """Return the document stored for the deliverable."""
    document = getattr(deliverable, "document", None)
    if isinstance(document, Document):
        return document
    return None


def merge_document_docs(target: Document, source: Document) -> None:
    """Merge document variants from another document into the target."""
    existing_langs = {doc.lang for doc in target.docs if doc.lang}
    for doc in source.docs:
        if doc.lang and doc.lang in existing_langs:
            continue
        target.docs.append(doc)
        if doc.lang:
            existing_langs.add(doc.lang)


def compile_manifest(
    product: str,
    docset: str,
    deliverables: Sequence[Deliverable],
) -> Manifest | None:
    """Compile a manifest for a product and docset from deliverables.

    :param product: Product identifier.
    :param docset: Docset identifier.
    :param deliverables: Deliverables with parsed metadata.
    :return: Manifest instance or ``None`` when no data is available.
    """
    if not deliverables:
        return None

    representative = deliverables[0]
    Category.reset_rank()
    descriptions = list(Description.from_xml_node(representative))
    categories = list(Category.from_xml_node(representative))

    name_node = representative.xml.product_node.find("name")
    acronym_node = representative.xml.product_node.find("acronym")
    productname = name_node.text if name_node is not None and name_node.text else product
    acronym = acronym_node.text if acronym_node is not None and acronym_node.text else product
    lifecycle = representative.xml.docset_node.attrib.get("lifecycle") or ""

    documents_by_key: dict[str, Document] = {}
    archives: list[Archive] = []
    for deliverable in deliverables:
        document = build_document_from_deliverable(deliverable)
        if document is None:
            continue

        doc_key = ""
        if document.docs:
            doc_key = document.docs[0].dcfile or ""
        if not doc_key:
            doc_key = deliverable.xml.dcfile or deliverable.full_id
        if doc_key in documents_by_key:
            merge_document_docs(documents_by_key[doc_key], document)
        else:
            documents_by_key[doc_key] = document
        rootid = document.docs[0].rootid if document.docs else ""
        paths = DeliverablePaths(deliverable.xml, rootid=rootid)
        archives.append(
            Archive(
                lang=deliverable.xml.lang,
                default=deliverable.lang_is_default,
                zip=paths.zip_path,
            )
        )

    if not documents_by_key:
        return None

    payload = {
        "productname": productname,
        "acronym": acronym,
        "version": docset,
        "lifecycle": lifecycle,
        "hide-productname": False,
        "descriptions": descriptions,
        "categories": categories,
        "documents": list(documents_by_key.values()),
        "archives": archives,
    }
    return Manifest.model_validate(payload)
