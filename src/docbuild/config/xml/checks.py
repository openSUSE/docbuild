"""Contain different checks against the XML config."""
# TODO: Use docbuild.models.deliverable.Deliverable class for checks?

from collections import Counter
from collections.abc import Generator
from dataclasses import dataclass, field

from lxml import etree

from ...constants import ALLOWED_LANGUAGES
from ...utils.convert import convert2bool
from ...utils.decorators import factory_registry

# log = logging.getLogger(LOGGERNAME)


@dataclass
class CheckResult:
    """Result of a validation check."""

    success: bool
    messages: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        """Return True if the check was successful, False otherwise."""
        return self.success


register_check = factory_registry()


@register_check
def check_dc_in_language(tree: etree._Element | etree._ElementTree) -> CheckResult:
    """Make sure each DC appears only once within a language.

    .. code-block:: xml

        <language lang="en-us" default="1">
            <deliverable>
                <dc>DC-foo</dc>
                <format html="1" pdf="1" single-html="0"/>
            </deliverable>
            <deliverable>
                <dc>DC-foo</dc>
                <format html="1" pdf="1" single-html="0"/>
            </deliverable>
        </language>

    :param tree: The XML tree to check.
    :return: CheckResult with success status and any error messages.
    """
    messages = []
    for language in tree.findall(".//language", namespaces=None):
        dc_values = [d.findtext("dc") for d in language.findall("deliverable")]
        if len(dc_values) != len(set(dc_values)):
            duplicates = [
                item for item, count in Counter(dc_values).items() if count > 1
            ]
            setid = language.getparent().getparent().get("setid", "n/a")
            langcode = language.get("lang", "n/a")
            message = (
                f"Some dc elements within a language have non-unique values. "
                f"Check for occurrences of the following duplicated dc "
                f"elements in docset={setid} language={langcode}: "
                f"{', '.join(duplicates)}"
            )
            messages.append(message)
            # log.critical(message)

    return CheckResult(success=len(messages) == 0, messages=messages)


@register_check
def check_duplicated_categoryid(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Check that categoryid is unique within a product.

    .. code-block:: xml

        <category categoryid="container"> ... </category>
        <category categoryid="container"> ... </category>

    :param tree: The XML tree to check.
    :return: CheckResult with success status and any error messages.
    """
    categoryids = [
        cat.get("categoryid") for cat in tree.findall(".//category", namespaces=None)
    ]
    if len(categoryids) != len(set(categoryids)):
        duplicates = [item for item, count in Counter(categoryids).items() if count > 1]
        message = (
            "Some category elements have non-unique categoryid values: "
            f"{', '.join(duplicates)}"
        )
        # log.critical(message)
        return CheckResult(success=False, messages=[message])
    return CheckResult(success=True, messages=[])


@register_check
def check_duplicated_format_in_extralinks(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Check that format attributes in extralinks are unique.

    .. code-block:: xml

        <external>
          <link>
            <language>
              <url href="https://example.com/page1" format="html" lang="en-us"/>
              <url href="https://example.com/page1.pdf" format="pdf" lang="en-us"/>
              <!-- Duplicate format: -->
              <url href="https://example.com/page1_again" format="html" lang="en-us"/>
            </language>
          </link>
        </external>

    :param tree: The XML tree to check.
    :return: CheckResult with success status and any error messages.
    """
    messages = []
    for language in tree.findall("./docset/external/link/language", namespaces=None):
        formats = language.xpath("./url/@format")
        docset = language.xpath("ancestor::docset/@setid")[0]
        duplicates = [item for item, count in Counter(formats).items() if count > 1]

        if duplicates:
            message = (
                f"Duplicated format attributes found in external/link/language/url "
                f"in docset={docset}: {', '.join(duplicates)}"
            )
            messages.append(message)
            # log.critical(message)

    return CheckResult(success=len(messages) == 0, messages=messages)


@register_check
def check_duplicated_linkid(tree: etree._Element | etree._ElementTree) -> CheckResult:
    """Check that linkid is unique within an external element.

    .. code-block:: xml

        <external>
          <link linkid="fake-link">
            <language>
              <url href="https://example.com/page1" format="html" lang="en-US"/>
            </language>
          </link>
          <link linkid="fake-link"> <!-- Duplicate linkid -->
            <language>
              <url href="https://example.com/page2" format="html" lang="en-US"/>
            </language>
          </link>
        </external>

    :param tree: The XML tree to check.
    :return: CheckResult with success status and any error messages.
    """
    messages = []

    # Check each docset separately
    for docset in tree.findall(".//docset", namespaces=None):
        setid = docset.get("setid", "unknown")
        linkids = [
            link.get("linkid")
            for link in docset.findall("./external/link", namespaces=None)
            if link.get("linkid") is not None
        ]

        duplicates = [item for item, count in Counter(linkids).items() if count > 1]
        if duplicates:
            message = (
                f"Some link elements have non-unique linkid values in "
                f"docset={setid}: {', '.join(duplicates)}"
            )
            messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages)


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
            <language lang="en-US">
              <url href="https://example.com/page1" lang="en-US"/>
            </language>
          </link>
          <link>
            <language lang="en-US">
              <url href="https://example.com/page1" lang="en-US"/><!-- Duplicate -->
            </language>
          </link>
        </external>

    :param tree: The XML tree to check.
    :return: CheckResult with success status and any error messages.
    """
    messages = []

    # Group URLs by language
    for language in tree.findall(".//external/link/language", namespaces=None):
        lang_code = language.get("lang", "unknown")
        urls = [url.get("href") for url in language.findall("url", namespaces=None)]

        duplicates = [item for item, count in Counter(urls).items() if count > 1]
        if duplicates:
            docset = (
                language.xpath("ancestor::docset/@setid")[0]
                if language.xpath("ancestor::docset/@setid")
                else "unknown"
            )
            message = (
                "Some url elements have non-unique href values in "
                f"language={lang_code} for docset={docset}: {', '.join(duplicates)}"
            )
            messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages)


@register_check
def check_enabled_format(tree: etree._Element | etree._ElementTree) -> CheckResult:
    """Check if at least one format is enabled.

    .. code-block:: xml

        <deliverable>
          <dc>DC-fake-doc</dc>
          <!-- All formats here are disabled: -->
          <format epub="0" html="0" pdf="0" single-html="0"/>
        </deliverable>

    :param tree: The XML tree to check.
    :return: CheckResult with success status and any error messages.
    """
    messages = []
    for fmt in tree.findall(".//deliverable/format", namespaces=None):
        format_issues = [convert2bool(value) for value in fmt.attrib.values()]
        if not any(format_issues):
            docset = fmt.xpath("ancestor::docset/@setid")[0]
            deli = fmt.find("../dc")
            deli_text = deli.text  # if deli is not None else 'n/a'
            message = (
                f"No enabled format found in docset={docset} "
                f"for deliverable={deli_text}"
            )
            messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages)


@register_check
def check_format_subdeliverable(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Make sure that deliverables with subdeliverables have only HTML formats enabled.

    .. code-block:: xml

         <deliverable>
            <dc>DC-fake-all</dc>
            <!-- PDF enabled, but subdeliverables present: -->
            <format epub="0" html="1" pdf="1" single-html="1" />
            <subdeliverable> ... </subdeliverable>
         </deliverable>

    :param tree: The XML tree to check.
    :return: True if all subdeliverables have at least one enabled format,
        False otherwise.
    """
    messages = []
    for deli in tree.findall(".//deliverable", namespaces=None):
        subdeli = deli.find("subdeliverable")
        if subdeli is not None:
            formats = deli.find("format")
            if formats is None:
                # Create "fake" <format> element if it doesn't exist:
                formats = etree.Element("format", attrib=None, nsmap=None)

            pdf = convert2bool(formats.attrib.get("pdf", False))
            epub = convert2bool(formats.attrib.get("epub", False))

            if any([pdf, epub]):
                setid = deli.xpath("ancestor::docset/@setid")[0]
                dc = deli.findtext("dc", default="n/a")
                language = deli.xpath("ancestor::language/@lang")[0]
                message = (
                    "A deliverable that has subdeliverables has PDF or EPUB "
                    "enabled as a format: "
                    f"docset={setid}/language={language}/deliverable={dc} "
                    "but no enabled format is present"
                )
                messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages)


@register_check
def check_lang_code_in_category(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Ensure that each language code appears only once within <category>.

    .. code-block:: xml

        <category categoryid="container">
            <language lang="en-us" title="..." />
            <language lang="en-us" title="..."/> <!-- Duplicate -->
        </category>

    :param tree: The XML tree to check.
    :return: True if all lang attributes in categories are valid, False otherwise.
    """
    messages = []
    for category in tree.findall(".//category", namespaces=None):
        langs = [lng.attrib.get("lang") for lng in category.iterchildren("language")]
        duplicates = [item for item, count in Counter(langs).items() if count > 1]

        if duplicates:
            catid = category.get("categoryid", "n/a")
            message = (
                f"Some of the name translation of category {catid!r} "
                "have non-unique lang attributes. "
                f"Found duplicates: {', '.join(duplicates)}"
            )
            messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages)


@register_check
def check_lang_code_in_desc(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Ensure that each language code appears only once within <desc>.

    .. code-block:: xml

        <product>
           <!-- ... -->
           <desc lang="en-us">...</desc>
           <desc lang="en-us">...</desc> <!-- Duplicate -->
        </product>

    :param tree: The XML tree to check.
    :return: True if all lang attributes in desc are valid, False otherwise.
    """
    langs = [
        desc.attrib.get("lang") for desc in tree.findall("./desc", namespaces=None)
    ]
    duplicates = [item for item, count in Counter(langs).items() if count > 1]

    if duplicates:
        xpath_lang = " or ".join([f'@lang="{lang}"' for lang in duplicates])
        titles = tree.xpath(f".//desc[{xpath_lang}]/@title")
        message: str = (
            "Some <desc> elements have non-unique lang attributes. "
            f"Found duplicates: {', '.join(duplicates)} for titles: "
            f"{', '.join(titles)}"
        )
        return CheckResult(success=False, messages=[message])

    return CheckResult(success=True, messages=[])


@register_check
def check_lang_code_in_docset(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Ensure that each language code appears only once within <docset>.

    .. code-block:: xml

        <docset setid="..." lifecycle="...">
            <!-- ... -->
            <builddocs>
                <git remote="..." />
                <language lang="en-us" default="1">...</language>
                <language lang="en-us" default="1">...</language> <!-- Duplicate -->
            </builddocs>
        </external>

    :param tree: The XML tree to check.
    :return: True if all lang attributes in extralinks are valid, False otherwise.
    """
    messages = []
    for docset in tree.findall(".//docset", namespaces=None):
        langs = [
            lng.attrib.get("lang")
            for lng in docset.findall("./builddocs/language", namespaces=None)
        ]
        duplicates = [item for item, count in Counter(langs).items() if count > 1]

        if duplicates:
            setid = docset.get("setid", "n/a")
            message = (
                "Some language elements within a set have non-unique lang attributes "
                f"In docset={setid}, check for duplicate builddocs/language. "
                f"Found duplicates: {', '.join(duplicates)}"
            )
            messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages)


@register_check
def check_lang_code_in_extralinks(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Ensure that each language code appears only once within <external>.

    .. code-block:: xml

        <external>
            <link>
                <language lang="en-us" default="1">...</language>
                <language lang="en-us" default="1">...</language> <!-- Duplicate -->
            </link>
        </external>

    :param tree: The XML tree to check.
    :return: True if all lang attributes in extralinks are valid, False otherwise.
    """
    messages = []
    for link in tree.findall(".//external/link", namespaces=None):
        langs = [lng.attrib.get("lang") for lng in link.findall("language")]
        duplicates = [item for item, count in Counter(langs).items() if count > 1]

        if duplicates:
            docsetid = link.xpath("ancestor::docset/@setid")[0]
            message = (
                "Some language elements within a link have non-unique lang attributes. "
                f"In docset={docsetid}, check for duplicate external/link/language. "
                f"Found duplicates: {', '.join(duplicates)}"
            )
            messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages)


@register_check
def check_lang_code_in_overridedesc(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Ensure that each language code appears only once within <overridedesc>.

    .. code-block:: xml

        <overridedesc>
            <language lang="en-us" default="1">...</language>
            <language lang="en-us" default="1">...</language> <!-- Duplicate -->
        </overridedesc>

    :param tree: The XML tree to check.
    :return: True if all lang attributes in overridedesc are valid, False otherwise.
    """
    messages = []
    for node in tree.findall(".//docset/overridedesc", namespaces=None):
        langs = [
            lng.attrib.get("lang") for lng in node.findall("./desc", namespaces=None)
        ]
        duplicates = [item for item, count in Counter(langs).items() if count > 1]

        if duplicates:
            message = (
                "Some language elements within overridedesc have non-unique "
                f"lang attributes. Found duplicates: {', '.join(duplicates)}"
            )
            messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages)


@register_check
def check_subdeliverable_in_deliverable(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Check that site section is present in the XML tree.

    .. code-block:: xml

        <deliverable>
            <dc>DC-fake-doc</dc>
            <subdeliverable>sub-1</subdeliverable>
            <subdeliverable>sub-2</subdeliverable>
            <subdeliverable>sub-1</subdeliverable> <!-- Duplicate -->
        </deliverable>

    :param tree: The XML tree to check.
    :return: True if site/section is present, False otherwise.
    """
    messages = []
    for deliverables in tree.iter("deliverable"):
        subdelis = [
            node.text
            for node in deliverables.findall("subdeliverable", namespaces=None)
        ]
        duplicates = [item for item, count in Counter(subdelis).items() if count > 1]

        if duplicates:
            setid = deliverables.xpath("ancestor::docset/@setid")[0]
            language = deliverables.xpath("ancestor::language/@lang")[0]
            message = (
                "Some subdeliverable elements within a deliverable have non-unique "
                "values. "
                f"In docset={setid}/language={language}, "
                f"found duplicates: {', '.join(duplicates)}"
            )
            messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages)


@register_check
def check_translation_deliverables(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Check that deliverables have translations in all languages.

    Make sure that deliverables defined in translations are a subset
    of the deliverables defined in the default language.

    .. code-block:: xml

        <language default="1" lang="en-us">
            <branch>main</branch>
            <deliverable>
            <dc>DC-SLES-all</dc>
            <format epub="0" html="1" pdf="0" single-html="0"/>
            <subdeliverable>book-rmt</subdeliverable>
            </deliverable>
        </language>
        <language  lang="de-de">
            <branch>main</branch>
            <deliverable>
            <dc>DC-SLES-all</dc>
            <!-- This subdeliverable is not present in the default language: -->
            <subdeliverable>book-abc</subdeliverable>
            </deliverable>
        </language>

    :param tree: The XML tree to check.
    :return: True if all deliverables have translations in all languages,
        False otherwise.
    """
    messages = []
    for deliverable in tree.xpath(
        "./docset/builddocs/language["
        "  not(@default) or not(@default='true' or @default='1')"
        "]/deliverable",
        namespaces=None,
    ):
        current_dc = deliverable.findtext("dc")
        for subdeli in deliverable.iterchildren("subdeliverable"):
            current_subdeli = subdeli.text
            xpath = (
                "ancestor::builddocs/language[@default='1' or @default='true']/"
                f"descendant::deliverable[dc={current_dc!r}]/"
                f"subdeliverable[. = {subdeli.text!r}]"
            )

            # We expect that a subdeliverable in translation contains the same
            # subdeliverable in the default language deliverable.
            if not deliverable.xpath(xpath, namespaces=None):
                setid = deliverable.xpath("ancestor::docset/@setid")[0]
                lang = deliverable.xpath("ancestor::language/@lang")[0]
                message = (
                    f"The subdeliverable {current_subdeli!r} is configured for "
                    f"docset={setid}/language={lang}/deliverable={current_dc} "
                    "but not for same deliverable of the default language. "
                    "Documents configured for translation languages must be a "
                    "subset of the documents configured for the default language."
                )
                messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages)


@register_check
def check_valid_languages(
    tree: etree._Element | etree._ElementTree,
) -> CheckResult:
    """Check that all languages are valid.

    .. code-block:: xml

        <language lang="en-us" default="1">...</language>
        <language lang="invalid-lang" default="0">...</language> <!-- Invalid -->

    :param tree: The XML tree to check.
    :return: CheckResult with success status and any error messages.
    """

    def iter_lang_attrib() -> Generator[tuple[etree._Element, str], None, None]:
        for node in tree.iter(tag=None):  # "desc", "language"
            lang = node.attrib.get("lang")
            if lang:
                yield node, lang

    messages = []
    for node, lang in iter_lang_attrib():
        if lang not in ALLOWED_LANGUAGES:
            setid = node.xpath("ancestor-or-self::docset/@setid")[0]
            message = (
                f"In docset={setid}, invalid language code found: {lang}. "
                f"Valid codes are: {', '.join(ALLOWED_LANGUAGES)}"
            )
            messages.append(message)

    return CheckResult(success=len(messages) == 0, messages=messages)
