"""Utility functions for merging Doctype instances."""

from collections.abc import Sequence
from itertools import chain

from ..models.doctype import Doctype
from ..models.language import LanguageCode


def _merge_docsets(ds1: Sequence[str], ds2: Sequence[str]) -> list[str]:
    """Merge two docset lists, ensuring no duplicates and sorted order.

    :param ds1: First list of docsets.
    :param ds2: Second list of docsets.
    :return: Merged list of docsets.
    """
    return sorted(set(chain(ds1, ds2)))  # sorted(set(ds1 + ds2))


def _merge_langs(
    langs1: Sequence[LanguageCode],
    langs2: Sequence[LanguageCode],
) -> list[LanguageCode]:
    """Merge two lists of LanguageCode objects.

    Ensuring no duplicates and sorted order.

    :param langs1: First list of LanguageCode objects.
    :param langs2: Second list of LanguageCode objects.
    :return: Merged sorted list of LanguageCode objects.
    """
    if '*' in langs1 or '*' in langs2:
        return [LanguageCode(language='*')]
    return sorted(set(chain(langs1, langs2)))  # sorted(set(langs1 + langs2))


def _dedup_doctypes(doctypes: Sequence[Doctype]) -> list[Doctype]:
    """Remove duplicate Doctype objects from a list, preserving order.

    :param doctypes: List of Doctype objects to deduplicate.
    :return: Deduplicated list of Doctype objects or an empty list if input is empty.
    """
    # Use explicit equality to force coverage tool to see this branch
    if doctypes == []:
        return []
    deduped = []
    for d in doctypes:
        if d not in deduped:
            deduped.append(d)
    return deduped


def _split_wildcard_docset(dt1: Doctype, dt2: Doctype) -> list[Doctype] | None:
    """Merge a wildcard docset with a specific docset if product and lifecycle match.

    Returns a list of merged Doctypes if applicable, otherwise None.

    :param dt1: First Doctype instance.
    :param dt2: Second Doctype instance.
    :return: List of merged Doctypes or None if no merging is possible.
    """
    if ('*' in dt1.docset and '*' not in dt2.docset) or (
        '*' in dt2.docset and '*' not in dt1.docset
    ):
        wildcard, specific = (dt1, dt2) if '*' in dt1.docset else (dt2, dt1)
        wildcard_langs = set(wildcard.langs)
        specific_langs = set(specific.langs)
        common_langs = wildcard_langs & specific_langs
        extra_langs = specific_langs - wildcard_langs
        if common_langs:
            merged = [
                Doctype(
                    product=wildcard.product,
                    docset=['*'],
                    lifecycle=wildcard.lifecycle,
                    langs=sorted(common_langs),
                ),
            ]
            if extra_langs:
                merged.append(
                    Doctype(
                        product=specific.product,
                        docset=[d for d in specific.docset if d != '*'],
                        lifecycle=specific.lifecycle,
                        langs=sorted(extra_langs),
                    ),
                )
            return merged
    return None


def merge_doctypes(*doctypes: Doctype) -> list[Doctype]:  # noqa: C901
    """Merge a list of Doctype instances into a minimal set of non-redundant entries.

    Strategy:
        - For each incoming Doctype `dt`, compare it to the existing `result` list.
        - If any existing Doctype can absorb `dt`, extend its docset/langs as needed.
        - If `dt` can absorb an existing one, replace it.
        - Otherwise, keep both.
        - Wildcards ("*") are treated as "contains all" and will cause merging
          if overlap exists.
        - ``docset`` and ``langs`` are always sorted lists.

    Examples:
        - ``foo/1,2/en-us + foo/*/en-us`` => ``foo/*/en-us``
        - ``foo/1,2/* + foo/1/en-us`` => ``foo/1,2/*``
        - ``foo/1,2/en-us + bar/1,2/en-us`` => ``foo/1,2/en-us, bar/1,2/en-us``
        - ``foo/1/en-us + foo/2/*`` => ``foo/1/en-us', 'foo/2/*``
        - ``foo/1/en-us,de-de + foo/2/*`` => ``foo/1/en-us,de-de, foo/2/*``

    """
    result: list[Doctype] = []
    for dt in doctypes:
        merged = False
        new_result = []
        for existing in result:
            if dt.product == existing.product and dt.lifecycle == existing.lifecycle:
                # Use helper for wildcard/specific docset split
                split = _split_wildcard_docset(existing, dt)
                if split is not None:
                    new_result.extend(split)
                    merged = True
                    continue

                if existing == dt:
                    # Exact match, keep only one
                    new_result.append(existing)
                    merged = True

                elif dt in existing:  # existing.__contains__(dt)
                    # existing absorbs dt, merge docset/langs
                    docset = _merge_docsets(existing.docset, dt.docset)
                    langs = _merge_langs(existing.langs, dt.langs)
                    merged_doctype = Doctype(
                        product=existing.product,
                        docset=docset,
                        lifecycle=existing.lifecycle,
                        langs=langs,
                    )
                    new_result.append(merged_doctype)
                    merged = True

                elif existing in dt:  # dt.__contains__(existing)
                    # dt absorbs existing, merge docset/langs
                    docset = _merge_docsets(existing.docset, dt.docset)
                    langs = _merge_langs(existing.langs, dt.langs)
                    merged_doctype = Doctype(
                        product=dt.product,
                        docset=docset,
                        lifecycle=dt.lifecycle,
                        langs=langs,
                    )
                    new_result.append(merged_doctype)
                    merged = True

                elif existing.docset == dt.docset:
                    # Same docset, merge langs
                    langs = _merge_langs(existing.langs, dt.langs)
                    merged_doctype = Doctype(
                        product=existing.product,
                        docset=existing.docset,
                        lifecycle=existing.lifecycle,
                        langs=langs,
                    )
                    new_result.append(merged_doctype)
                    merged = True

                elif existing.langs == dt.langs:
                    # Same langs, merge docset
                    docset = _merge_docsets(existing.docset, dt.docset)
                    merged_doctype = Doctype(
                        product=existing.product,
                        docset=docset,
                        lifecycle=existing.lifecycle,
                        langs=existing.langs,
                    )
                    new_result.append(merged_doctype)
                    merged = True

                else:
                    new_result.append(existing)

            else:
                new_result.append(existing)

        if not merged:
            new_result.append(dt)
        result = _dedup_doctypes(new_result)

    return _dedup_doctypes(result)