"""Manifest and product/docset JSON building for metadata."""

from collections.abc import Sequence
import itertools
import json
import logging
from pathlib import Path
from typing import Literal

from lxml import etree  # type: ignore
from pydantic import ValidationError
from rich.console import Console

from ...models.deliverable import Deliverable
from ...models.doctype import Doctype
from ...models.language import LanguageCode
from ...models.manifest import Archive, Category, Description, Document, Manifest
from .deliverables import get_deliverable_from_doctype

log = logging.getLogger(__name__)
stdout = Console()


def apply_parity_fixes(descriptions: list, categories: list) -> None:
    """Apply wording and HTML parity fixes for legacy JSON consistency.

    :param descriptions: List of Description objects to patch.
    :param categories: List of Category objects to patch.
    """
    for desc in descriptions:
        desc.description = desc.description.replace("& ", "&amp; ")

    for cat in categories:
        for trans in cat.translations:
            trans.title = trans.title.replace("&", "&amp;")


def merge_documents_by_dcfile(documents: list[Document]) -> list[Document]:
    """Merge per-language Document entries that share the same DC file.

    All language variants of the same DC file are collapsed into one
    :class:`~docbuild.models.manifest.Document` entry whose ``docs`` list
    contains every translation. The final order of documents is determined
    by the document order of the English deliverables.

    Within each document, the ``en-us`` entry is placed first and marked
    ``default=True``; other languages follow in alphabetical order.
    The ``tasks``, ``products`` and other outer fields are taken from the
    ``en-us`` entry when present, otherwise from the first entry found.

    :param documents: Flat list of per-language Document objects.
    :return: Merged list with at most one Document per DC file.
    """
    # Preserve insertion order; key = dcfile
    groups: dict[str, Document] = {}

    # Separate English from other languages to establish a baseline order
    en_docs = [doc for doc in documents if doc.docs and doc.docs[0].lang == "en-us"]
    other_docs = [doc for doc in documents if doc.docs and doc.docs[0].lang != "en-us"]

    # 1. Establish order based on English deliverables first
    for doc in en_docs:
        dcfile = doc.docs[0].dcfile
        groups.setdefault(dcfile, doc)

    # 2. Merge in other languages
    for doc in other_docs:
        dcfile = doc.docs[0].dcfile
        if dcfile not in groups:
            # This document has no English version; append it to the end
            groups[dcfile] = doc
        else:
            # Merge translations into the existing English-ordered entry
            if not groups[dcfile].category and doc.category:
                groups[dcfile].category = doc.category
            groups[dcfile].docs.extend(doc.docs)

    # 3. Sort the translations within each merged document
    for merged in groups.values():
        en_translations = [d for d in merged.docs if d.lang == "en-us"]
        other_translations = sorted(
            [d for d in merged.docs if d.lang != "en-us"],
            key=lambda d: d.lang or "",
        )
        for d in en_translations:
            d.default = True
        merged.docs = en_translations + other_translations

    return list(groups.values())


def load_documents_from_deliverables(
    deliverables: list[Deliverable],
    meta_cache_dir: Path,
) -> list[Document]:
    """Load JSON metadata and return validated Document models from deliverables.

    This function iterates through a list of :class:`~docbuild.models.deliverable.Deliverable`
    objects, finds their corresponding ``DC-*.json`` files in the metadata
    cache, loads the JSON, and validates it into a
    :class:`~docbuild.models.manifest.Document` model.

    Deliverables are skipped if they don't have a ``dcfile`` or if the
    corresponding file does not exist in the cache.

    :param deliverables: A list of Deliverable objects to process.
    :param meta_cache_dir: The base path to the metadata cache directory.
    :return: A list of validated Document models.
    """
    loaded_docs = []
    for d in deliverables:
        if not d.xml.dcfile:
            continue

        actual_file = meta_cache_dir / d.paths.relpath / d.xml.dcfile

        if not actual_file.is_file():
            continue

        stdout.print(f"  | {actual_file.stem} [{d.xml.lang}]", markup=False)
        try:
            with actual_file.open(encoding="utf-8") as fh:
                loaded_doc_data = json.load(fh)

            if not loaded_doc_data:
                log.error("Empty metadata file %s", actual_file)
                continue

            # This yields a Document model with a single translation in its .docs list
            loaded_docs.append(Document.model_validate(loaded_doc_data))

        except (json.JSONDecodeError, ValidationError, OSError) as e:
            log.error("Error processing metadata file %s: %s", actual_file, e)
    return loaded_docs


def merge_descriptions_with_treatment(
    product_descriptions: list[Description],
    docset_descriptions: list[Description],
    treatment: Literal["append", "prepend", "replace"] = "replace",
) -> list[Description]:
    """Merge product and docset descriptions according to treatment policy.

    :param product_descriptions: Descriptions from the product scope.
    :param docset_descriptions: Descriptions from the docset scope.
    :param treatment: How docset descriptions interact with product descriptions.
    :return: Merged descriptions list.
    """
    if not docset_descriptions:
        return [d.model_copy(deep=True) for d in product_descriptions]

    if treatment == "replace":
        return [d.model_copy(deep=True) for d in docset_descriptions]

    product_by_lang = {str(d.lang): d for d in product_descriptions}
    docset_by_lang = {str(d.lang): d for d in docset_descriptions}

    ordered_langs = [str(d.lang) for d in product_descriptions]
    ordered_langs.extend(
        str(d.lang) for d in docset_descriptions if str(d.lang) not in product_by_lang
    )

    merged: list[Description] = []
    for lang in ordered_langs:
        p_desc = product_by_lang.get(lang)
        d_desc = docset_by_lang.get(lang)

        if p_desc and d_desc:
            if treatment == "prepend":
                text = f"{d_desc.description}{p_desc.description}"
            else:
                text = f"{p_desc.description}{d_desc.description}"
            merged.append(
                Description(
                    lang=lang,
                    default=p_desc.default or d_desc.default,
                    description=text,
                )
            )
        elif d_desc:
            merged.append(d_desc.model_copy(deep=True))
        elif p_desc:
            merged.append(p_desc.model_copy(deep=True))

    return merged


def configured_languages_from_docset(docsetnode: etree._Element) -> list[LanguageCode]:
    """Return configured locale languages from a docset node.

    :param docsetnode: A ``<docset>`` XML node from the stitched portal config.
    :return: Ordered unique list of configured LanguageCode values.
    """
    resources = docsetnode.find("resources")
    if resources is None:
        return []

    languages: list[LanguageCode] = []
    seen: set[str] = set()

    for locale_node in resources.findall("locale"):
        lang = (locale_node.attrib.get("lang") or "").strip()
        if not lang or lang in seen:
            continue
        languages.append(LanguageCode(language=lang))
        seen.add(lang)

    return languages


def store_productdocset_json(
    doctypes: Sequence[Doctype],
    stitchnode: etree._ElementTree,
    meta_cache_dir: Path,
    json_cache_dir: Path,
) -> None:
    """Build and store a aggregated JSON manifest for each product/docset.

    This function orchestrates the creation of the final JSON manifest files.
    The process is as follows:

    1.  All :class:`~docbuild.models.deliverable.Deliverable` objects are
        retrieved from the stitched XML based on the input doctypes.
    2.  Deliverables are grouped by the product and docset they belong to.
    3.  For each group, the corresponding ``DC-*.json`` metadata files are loaded
        from the cache into :class:`~docbuild.models.manifest.Document` models.
    4.  These per-language documents are merged into unified document entries.
    5.  A final :class:`~docbuild.models.manifest.Manifest` is assembled with
        all associated data (descriptions, categories, etc.) and written to
        the JSON cache.

    :param doctypes: A sequence of :class:`~docbuild.models.doctype.Doctype`
        objects to filter which deliverables to include.
    :param stitchnode: The stitched XML tree containing all configuration.
    :param meta_cache_dir: Path to the metadata cache directory where ``DC-*.json``
        files are stored.
    :param json_cache_dir: Path to the output directory for the final JSON
        manifests.
    """
    # 1. Get all deliverable objects from the stitched XML, honoring doctype filters
    resolved_doctypes = [dt for doctype in doctypes for dt in doctype.iter_doctypes(stitchnode.getroot())]
    all_deliverables = []
    for dt in resolved_doctypes:
        all_deliverables.extend(get_deliverable_from_doctype(stitchnode, dt))

    # 2. Group deliverables by the product/docset they belong to
    keyfunc = lambda d: (d.xml.productid, d.xml.docsetid)  # noqa: E731
    all_deliverables.sort(key=keyfunc)  # groupby requires a sorted sequence

    for (product_id, docset_id), group in itertools.groupby(all_deliverables, key=keyfunc):
        if not product_id or not docset_id:
            continue

        deliverables_in_group = list(group)

        # 3. Load the corresponding DC-*.json files from cache for this group
        documents = load_documents_from_deliverables(deliverables_in_group, meta_cache_dir)
        if not documents:
            log.warning("No valid metadata files found for %s/%s", product_id, docset_id)
            continue

        # 4. Merge the per-language documents into unified entries by dcfile
        merged_documents = merge_documents_by_dcfile(documents)

        # 5. Extract shared manifest data (descriptions, categories, etc.)
        # We can get this from the first deliverable in the group
        first_deliv = deliverables_in_group[0]
        productnode = first_deliv.xml.product_node
        docsetnode = first_deliv.xml.docset_node

        product_descriptions = list(Description.from_xml_node(productnode))
        docset_descriptions = list(Description.from_xml_node(docsetnode))
        descriptions_node = docsetnode.find("descriptions")
        treatment = "replace"
        if descriptions_node is not None:
            treatment = descriptions_node.attrib.get("treatment", treatment)
        descriptions = merge_descriptions_with_treatment(
            product_descriptions,
            docset_descriptions,
            treatment=treatment if treatment in {"append", "prepend", "replace"} else "replace",
        )

        # Global (portal-level) categories first, then local (product-level) ones
        categories = list(Category.from_xml_node(stitchnode.getroot()))
        global_ids = {c.id for c in categories}
        categories += [
            c for c in Category.from_xml_node(productnode) if c.id not in global_ids
        ]
        configured_languages = configured_languages_from_docset(docsetnode)
        archives = [
            Archive(lang=lang, product=product_id, docset=docset_id)
            for lang in configured_languages
        ]

        apply_parity_fixes(descriptions, categories)

        # 6. Assemble and save the final manifest for this product/docset
        manifest = Manifest(
            productname=productnode.find("name").text,
            acronym=product_id,
            version=docset_id,
            lifecycle=docsetnode.attrib.get("lifecycle") or "",
            hide_productname=False,
            descriptions=descriptions,
            categories=categories,
            documents=merged_documents,
            archives=archives,
        )

        jsondir = json_cache_dir / product_id
        jsondir.mkdir(parents=True, exist_ok=True)
        jsonfile = jsondir / f"{docset_id}.json"

        json_data = manifest.model_dump(by_alias=True)
        with jsonfile.open("w", encoding="utf-8") as jf:
            json.dump(json_data, jf, indent=2, ensure_ascii=False)

        stdout.print(f" > Result: {jsonfile}")
        Category.reset_rank()
