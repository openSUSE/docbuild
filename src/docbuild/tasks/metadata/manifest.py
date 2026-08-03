"""Manifest and product/docset JSON building for metadata."""

from collections.abc import Sequence
import json
import logging
from pathlib import Path

from lxml import etree  # type: ignore
from pydantic import ValidationError
from rich.console import Console

from docbuild.models.doctype import Doctype
from docbuild.models.manifest import Category, Description, Document, Manifest

from .deliverables import collect_files_flat

log = logging.getLogger(__name__)
stdout = Console()


def apply_parity_fixes(descriptions: list, categories: list) -> None:
    """Apply wording and HTML parity fixes for legacy JSON consistency.

    :param descriptions: List of Description objects to patch.
    :param categories: List of Category objects to patch.
    """
    # TODO: These strings are hard-coded for legacy parity but should be moved to
    # Docserv config files to allow for proper translation and localization.
    legacy_tail = (
        "<p>The default view of this page is the ```Table of Contents``` sorting order. "
        "To search for a particular document, you can narrow down the results using the "
        "```Filter as you type``` option. It dynamically filters the document titles and "
        "descriptions for what you enter.</p>"
    )
    for desc in descriptions:
        if legacy_tail not in desc.description:
            desc.description += legacy_tail
        desc.description = desc.description.replace("& ", "&amp; ")

    for cat in categories:
        for trans in cat.translations:
            trans.title = trans.title.replace("&", "&amp;")


def merge_documents_by_dcfile(documents: list[Document]) -> list[Document]:
    """Merge per-language Document entries that share the same DC file.

    All language variants of the same DC file are collapsed into one
    :class:`~docbuild.models.manifest.Document` entry whose ``docs`` list
    contains every translation.  The ``en-us`` entry is placed first and
    marked ``default=True``; other languages follow in alphabetical order.
    The ``tasks``, ``products`` and other outer fields are taken from the
    ``en-us`` entry when present, otherwise from the first entry found.

    :param documents: Flat list of per-language Document objects.
    :return: Merged list with at most one Document per DC file.
    """
    # Preserve insertion order; key = dcfile
    groups: dict[str, Document] = {}

    for doc in documents:
        if not doc.docs:
            continue
        dcfile = doc.docs[0].dcfile
        if dcfile not in groups:
            groups[dcfile] = doc
        else:
            if not groups[dcfile].category and doc.category:
                groups[dcfile].category = doc.category
            groups[dcfile].docs.extend(doc.docs)

    for merged in groups.values():
        en_docs = [d for d in merged.docs if d.lang == "en-us"]
        other_docs = sorted(
            [d for d in merged.docs if d.lang != "en-us"],
            key=lambda d: d.lang or "",
        )
        for d in en_docs:
            d.default = True
        merged.docs = en_docs + other_docs

    return list(groups.values())


def load_and_validate_documents(
    files: list[Path],
    meta_cache_dir: Path,
    manifest: Manifest,
) -> None:
    """Load JSON metadata files and append validated Document models to the manifest.

    :param files: List of paths to metadata JSON files.
    :param meta_cache_dir: Base directory for resolving relative paths.
    :param manifest: The Manifest object to populate with loaded documents.
    """
    for f in files:
        actual_file = f if f.is_absolute() else meta_cache_dir / f

        if not actual_file.is_file():
            continue

        # Extract language from first path component relative to meta_cache_dir
        try:
            lang = actual_file.relative_to(meta_cache_dir).parts[0]
        except (ValueError, IndexError):
            lang = ""
        stdout.print(f"  | {f.stem} [{lang}]", markup=False)
        try:
            with actual_file.open(encoding="utf-8") as fh:
                loaded_doc_data = json.load(fh)

            if not loaded_doc_data:
                log.error("Empty metadata file %s", f)
                continue

            try:
                doc_model = Document.model_validate(loaded_doc_data)
            except ValidationError:
                continue
            manifest.documents.append(doc_model)

        except (json.JSONDecodeError, ValidationError, OSError) as e:
            log.error("Error processing metadata file %s: %s", actual_file, e)


def store_productdocset_json(
    doctypes: Sequence[Doctype],
    stitchnode: etree._ElementTree,
    meta_cache_dir: Path,
    json_cache_dir: Path,
) -> None:
    """Collect all JSON files for product/docset and create a single file.

    :param doctypes: Sequence of Doctype objects.
    :param stitchnode: The stitched XML tree.
    :param meta_cache_dir: Path to the metadata cache directory.
    :param json_cache_dir: Path to the JSON cache directory.
    """
    for doctype, docset, files in collect_files_flat(doctypes, meta_cache_dir):
        product = doctype.product.value
        version_str = str(docset)

        productxpath = f"./{doctype.product_xpath_segment()}"
        productnode = stitchnode.find(productxpath)
        docsetxpath = f"./{doctype.docset_xpath_segment(docset)}"
        docsetnode = productnode.find(docsetxpath)

        descriptions = list(Description.from_xml_node(productnode))

        # Global (portal-level) categories first, then local (product-level) ones
        categories = list(Category.from_xml_node(stitchnode.getroot()))
        global_ids = {c.id for c in categories}
        categories += [
            c for c in Category.from_xml_node(productnode)
            if c.id not in global_ids
        ]

        apply_parity_fixes(descriptions, categories)

        manifest = Manifest(
            productname=productnode.find("name").text,
            acronym=(
                productnode.find("acronym").text
                if productnode.find("acronym") is not None
                else product
            ),
            version=version_str,
            lifecycle=docsetnode.attrib.get("lifecycle") or "",
            hide_productname=False,
            descriptions=descriptions,
            categories=categories,
            documents=[],
            archives=[],
        )

        load_and_validate_documents(files, meta_cache_dir, manifest)
        manifest.documents = merge_documents_by_dcfile(manifest.documents)

        jsondir = json_cache_dir / product
        jsondir.mkdir(parents=True, exist_ok=True)
        jsonfile = jsondir / f"{docset}.json"

        json_data = manifest.model_dump(by_alias=True)
        with jsonfile.open("w", encoding="utf-8") as jf:
            json.dump(json_data, jf, indent=2, ensure_ascii=False)

        stdout.print(f" > Result: {jsonfile}")
        Category.reset_rank()
