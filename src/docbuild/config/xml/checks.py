"""Contain different checks against the XML config."""
# TODO: Use docbuild.models.deliverable.Deliverable class for checks?

from collections import Counter
from dataclasses import dataclass, field

from lxml import etree

from ...constants import ALLOWED_LANGUAGES
from ...utils.convert import convert2bool
from ...utils.decorators import factory_registry
from .semantic_xpath import semantic_xpath

# log = logging.getLogger(LOGGERNAME)


@dataclass
class CheckResult:
    """Result of a validation check."""

    success: bool
    messages: list[str] = field(default_factory=list)
    xpath: str | None = None

    def __bool__(self) -> bool:
        """Return True if the check was successful, False otherwise."""
        return self.success


register_check = factory_registry()


def docset_id(node: etree._Element) -> str:
    """Return a stable docset identifier for error messages."""
    ids = node.xpath("ancestor-or-self::docset/@id")
    return ids[0] if ids else "n/a"


def dc_identifier(deliverable: etree._Element) -> str:
    """Return a DC identifier from legacy or current schema representation."""
    dc_node = deliverable.find("dc")
    if dc_node is None:
        return deliverable.get("id", "n/a")

    file_attr = dc_node.get("file")
    if file_attr:
        return file_attr

    text = (dc_node.text or "").strip()
    return text if text else deliverable.get("id", "n/a")


@register_check
def check_dc_in_language(tree: etree._Element | etree._ElementTree) -> CheckResult:
    """Make sure each DC appears only once within a language.

    .. code-block:: xml

        <locale lang="en-us">
            <branch>main</branch>
            <deliverable id="deli-1" type="dc">
                <dc file="DC-foo">
                    <format html="1" pdf="0" single-html="0" epub="0"/>
                </dc>
            </deliverable>
            <deliverable id="deli-2" type="dc">
                <dc file="DC-foo">
                    <format html="1" pdf="0" single-html="0" epub="0"/>
                </dc>
            </deliverable>
        </locale>

    :param tree: The XML tree to check.
    :return: CheckResult with success status and any error messages.
    """
    messages = []
    first_xpath: str | None = None
    language_nodes = list(tree.findall(".//docset/resources/locale", namespaces=None))
    for language in language_nodes:
        dc_values = []
        for deliverable in language.findall("deliverable"):
            dc_node = deliverable.find("dc")
            if dc_node is None:
                continue
            dc_value = dc_node.get("file").strip()
            dc_values.append(dc_value)

        if len(dc_values) != len(set(dc_values)):
            duplicates = [
                item for item, count in Counter(dc_values).items() if count > 1
            ]
            setid = docset_id(language)
            langcode = language.get("lang", "n/a")
            if first_xpath is None:
                first_xpath = semantic_xpath(language)
            message = (
                f"Some dc elements within a language have non-unique values. "
                f"Check for occurrences of the following duplicated dc "
                f"elements in docset={setid} language={langcode}: "
                f"{', '.join(duplicates)}"
            )
            messages.append(message)
            # log.critical(message)

    return CheckResult(success=len(messages) == 0, messages=messages, xpath=first_xpath)


@register_check
def check_duplicated_format_in_extralinks(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Check that format attributes in extralinks are unique.

    .. code-block:: xml

       <external>
           <link>
                <url lang="en-us" href="https://example.com/page1" format="html"/>
                <url lang="en-us" href="https://example.com/page1.pdf" format="pdf"/>
                <!-- Duplicate format: -->
                <url lang="en-us" href="https://example.com/page1-again" format="html"/>
                <descriptions>
                    <desc lang="en-us"/>
                </descriptions>
           </link>
       </external>

    :param tree: The XML tree to check.
    :return: CheckResult with success status and any error messages.
    """
    messages = []
    first_xpath: str | None = None
    link_nodes = tree.findall(".//docset/external/link", namespaces=None)
    for link in link_nodes:
        grouped_formats: dict[str, list[str]] = {}
        for url in link.findall("url", namespaces=None):
            language_code = url.get("lang", "unknown")
            fmt = url.get("format")
            if fmt:
                grouped_formats.setdefault(language_code, []).append(fmt)

        for language_code, formats in grouped_formats.items():
            duplicates = [item for item, count in Counter(formats).items() if count > 1]

            if duplicates:
                if first_xpath is None:
                    first_xpath = semantic_xpath(link)
                message = (
                    "Duplicated format attributes found in external/link/url "
                    f"for language={language_code} in docset={docset_id(link)}: "
                    f"{', '.join(duplicates)}"
                )
                messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages, xpath=first_xpath)


@register_check
def check_duplicated_url_in_extralinks(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Check that url attributes in extralinks are unique within each language.

    Make sure each URL appears only once within a given language in external
    links section.

    .. code-block:: xml

       <external>
           <link>
               <url lang="en-us" href="https://example.com/page1" format="html"/>
               <url lang="en-us" href="https://example.com/page1" format="pdf"/>
               <descriptions>
                  <desc lang="en-us"/>
               </descriptions>
           </link>
       </external>

    :param tree: The XML tree to check.
    :return: CheckResult with success status and any error messages.
    """
    messages = []
    first_xpath: str | None = None

    # Group URLs by language in current schema (<link><url lang=.../></link>).
    for link in tree.findall(".//external/link", namespaces=None):
        grouped_values: dict[str, list[str]] = {}
        for url in link.findall("url", namespaces=None):
            lang_code = url.get("lang", "unknown")
            value = url.get("href") or (url.text or "").strip()
            if value:
                grouped_values.setdefault(lang_code, []).append(value)

        for lang_code, values in grouped_values.items():
            duplicates = [item for item, count in Counter(values).items() if count > 1]
            if duplicates:
                if first_xpath is None:
                    first_xpath = semantic_xpath(link)
                message = (
                    "Some url elements have non-unique href values in "
                    f"language={lang_code} for docset={docset_id(link)}: "
                    f"{', '.join(duplicates)}"
                )
                messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages, xpath=first_xpath)


@register_check
def check_enabled_format(tree: etree._Element | etree._ElementTree) -> CheckResult:
    """Check if at least one format is enabled.

    .. code-block:: xml

       <deliverable id="deli-1" type="dc">
         <dc file="DC-fake-doc">
            <!-- All formats here are disabled: -->
            <format epub="0" html="0" pdf="0" single-html="0"/>
         </dc>
       </deliverable>

    :param tree: The XML tree to check.
    :return: CheckResult with success status and any error messages.
    """
    messages = []
    first_xpath: str | None = None
    for deliverable in tree.findall(".//deliverable", namespaces=None):
        fmt = deliverable.find("format")
        if fmt is None:
            fmt = deliverable.find("dc/format")
        if fmt is None:
            continue

        format_issues = [convert2bool(value) for value in fmt.attrib.values()]
        if not any(format_issues):
            if first_xpath is None:
                first_xpath = semantic_xpath(deliverable)
            docset = docset_id(deliverable)
            deli_text = dc_identifier(deliverable)
            message = (
                f"No enabled format found in docset={docset} "
                f"for deliverable={deli_text}"
            )
            messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages, xpath=first_xpath)


@register_check
def check_format_subdeliverable(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Make sure that deliverables with subdeliverables have only HTML formats enabled.

    .. code-block:: xml

       <deliverable id="deli-1" type="dc">
          <dc file="DC-fake-all">
             <!-- PDF enabled, but subdeliverables present: -->
             <format epub="0" html="1" pdf="1" single-html="1"/>
             <subdeliverable>book-1</subdeliverable>
          </dc>
       </deliverable>

    :param tree: The XML tree to check.
    :return: True if all subdeliverables have at least one enabled format,
        False otherwise.
    """
    messages = []
    first_xpath: str | None = None
    for deli in tree.findall(".//deliverable", namespaces=None):
        subdeliverables = deli.findall("subdeliverable", namespaces=None) + deli.findall(
            "dc/subdeliverable", namespaces=None
        )
        if not subdeliverables:
            continue

        formats = deli.find("format")
        if formats is None:
            formats = deli.find("dc/format")
        if formats is None:
            # Create "fake" <format> element if it doesn't exist:
            formats = etree.Element("format", attrib=None, nsmap=None)

        pdf = convert2bool(formats.attrib.get("pdf", False))
        epub = convert2bool(formats.attrib.get("epub", False))

        if any([pdf, epub]):
            if first_xpath is None:
                first_xpath = semantic_xpath(deli)
            setid = docset_id(deli)
            dc = dc_identifier(deli)
            languages = deli.xpath("ancestor::locale/@lang")
            language = languages[0] if languages else "n/a"
            message = (
                "A deliverable that has subdeliverables has PDF or EPUB "
                "enabled as a format: "
                f"docset={setid}/language={language}/deliverable={dc} "
                "but no enabled format is present"
            )
            messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages, xpath=first_xpath)


@register_check
def check_lang_code_in_desc(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Ensure that each language code appears only once within <desc>.

    .. code-block:: xml

       <descriptions>
            <desc lang="en-us"/>
            <desc lang="en-us"/> <!-- Duplicate -->
       </descriptions>

    :param tree: The XML tree to check.
    :return: True if all lang attributes in desc are valid, False otherwise.
    """
    messages = []
    first_xpath: str | None = None
    parent_to_descs: dict[etree._Element, list[etree._Element]] = {}
    for desc in tree.findall(".//desc", namespaces=None):
        parent = desc.getparent()
        if parent is None:
            continue
        parent_to_descs.setdefault(parent, []).append(desc)

    for desc_nodes in parent_to_descs.values():
        langs = [desc.attrib.get("lang") for desc in desc_nodes if desc.attrib.get("lang")]
        duplicates = [item for item, count in Counter(langs).items() if count > 1]

        if duplicates:
            if first_xpath is None:
                first_xpath = semantic_xpath(desc_nodes[0].getparent())
            titles = [desc.attrib.get("title", "") for desc in desc_nodes]
            message: str = (
                "Some <desc> elements have non-unique lang attributes. "
                f"Found duplicates: {', '.join(duplicates)} for titles: "
                f"{', '.join([title for title in titles if title])}"
            )
            messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages, xpath=first_xpath)


@register_check
def check_lang_code_in_docset(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Ensure that each language code appears only once within <docset>.

    .. code-block:: xml

       <docset id="docset1" lifecycle="supported">
           <resources>
                <git remote="https://example.invalid/repo.git"/>
                <locale lang="en-us"><branch>main</branch></locale>
                <locale lang="en-us"><branch>main</branch></locale> <!-- Duplicate -->
           </resources>
       </docset>

    :param tree: The XML tree to check.
    :return: True if all lang attributes in extralinks are valid, False otherwise.
    """
    messages = []
    first_xpath: str | None = None
    for docset in tree.findall(".//docset", namespaces=None):
        langs = [
            node.get("lang")
            for node in docset.findall("./resources/locale", namespaces=None)
            if node.get("lang")
        ]
        duplicates = [item for item, count in Counter(langs).items() if count > 1]

        if duplicates:
            if first_xpath is None:
                first_xpath = semantic_xpath(docset)
            setid = docset.get("setid") or docset.get("id", "n/a")
            message = (
                "Some language elements within a set have non-unique lang attributes "
                f"In docset={setid}, check for duplicate resources/locale. "
                f"Found duplicates: {', '.join(duplicates)}"
            )
            messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages, xpath=first_xpath)


# @register_check
def check_lang_code_in_extralinks(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Ensure that each language code appears only once within ``external/link/url``.

    .. code-block:: xml

       <external>
         <link>
            <url lang="en-us" href="https://example.invalid/one" format="html"/>
            <url lang="en-us" href="https://example.invalid/two" format="pdf"/><!-- Wrong: duplicate lang -->
            <descriptions>
                <desc lang="en-us"/>
            </descriptions>
         </link>
       </external>

    :param tree: The XML tree to check.
    :return: CheckResult with success status and any error messages.
    """
    messages = []
    first_xpath: str | None = None
    for link in tree.findall(".//external/link", namespaces=None):
        langs = [
            url.get("lang") for url in link.findall("url", namespaces=None) if url.get("lang")
        ]
        duplicates = [item for item, count in Counter(langs).items() if count > 1]

        if duplicates:
            if first_xpath is None:
                first_xpath = semantic_xpath(link)
            docsetid = docset_id(link)
            message = (
                "Some external/link/url elements have non-unique lang attributes. "
                f"Found duplicates: {', '.join(duplicates)} in docset={docsetid} "
                "(duplicate external/link/url/@lang)"
            )
            messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages, xpath=first_xpath)


@register_check
def check_subdeliverable_in_deliverable(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Check that site section is present in the XML tree.

    .. code-block:: xml

        <deliverable id="deli-1" type="dc">
            <dc file="DC-fake-doc">
                <subdeliverable>sub-1</subdeliverable>
                <subdeliverable>sub-2</subdeliverable>
                <subdeliverable>sub-1</subdeliverable> <!-- Duplicate -->
            </dc>
        </deliverable>

    :param tree: The XML tree to check.
    :return: True if site/section is present, False otherwise.
    """
    messages = []
    first_xpath: str | None = None
    for deliverables in tree.iter("deliverable"):
        sub_nodes = deliverables.findall("subdeliverable", namespaces=None)
        sub_nodes.extend(deliverables.findall("dc/subdeliverable", namespaces=None))
        subdelis = [node.text for node in sub_nodes]
        duplicates = [item for item, count in Counter(subdelis).items() if count > 1]

        if duplicates:
            if first_xpath is None:
                first_xpath = semantic_xpath(deliverables)
            setid = docset_id(deliverables)
            languages = deliverables.xpath("ancestor::locale/@lang")
            language = languages[0] if languages else "n/a"
            message = (
                "Some subdeliverable elements within a deliverable have non-unique "
                "values. "
                f"In docset={setid}/language={language}, "
                f"found duplicates: {', '.join(duplicates)}"
            )
            messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages, xpath=first_xpath)


@register_check
def check_unsupported_language_code(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Check for language codes that match the portal format but are not supported.

    Catches subtle mistakes like ``de-at`` which matches the ``xx-yy`` regex
    but is not in :data:`~docbuild.constants.ALLOWED_LANGUAGES`.

    .. code-block:: xml

        <!-- Valid format but unsupported language: -->
        <locale lang="de-at"><branch>main</branch></locale>

    :param tree: The XML tree to check.
    :return: CheckResult with success status and any error messages.
    """
    messages = []
    first_xpath: str | None = None
    for node in tree.iter():
        lang = node.attrib.get("lang")
        if lang is not None and lang not in ALLOWED_LANGUAGES:
            if first_xpath is None:
                first_xpath = semantic_xpath(node)
            setid = docset_id(node)
            message = (
                f"In docset={setid}, language '{lang}' matches the portal format "
                f"but is not supported. Allowed languages: "
                f"{', '.join(sorted(ALLOWED_LANGUAGES))}"
            )
            messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages, xpath=first_xpath)
