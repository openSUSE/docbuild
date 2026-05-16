from collections.abc import Callable
import copy

from lxml import etree, objectify
import pytest

from docbuild.config.xml.checks import (
    check_dc_in_language,
    check_duplicated_format_in_extralinks,
    check_duplicated_url_in_extralinks,
    check_enabled_format,
    check_format_subdeliverable,
    check_lang_code_in_desc,
    check_lang_code_in_docset,
    check_lang_code_in_extralinks,
    check_subdeliverable_in_deliverable,
    check_unsupported_language_code,
    dc_identifier,
    docset_id,
    register_check,
)

# This is a non-namespace ElementMaker for creating XML elements.
E = objectify.ElementMaker(annotate=False, namespace=None, nsmap=None)


# @pytest.fixture(autouse=True)
# def clear_registry():
#     if hasattr(register_check, 'registry'):
#         # Clear the registry before each test to avoid state leakage
#         register_check.registry.clear()


@pytest.fixture
def xmlnode() -> etree._Element:
    """Minimal portal-like structure aligned with current schema semantics."""
    return etree.fromstring(
        """<portal schemaversion="7.0">
            <categories>
                <category lang="en-us">
                    <language id="cat.root" title="Root"/>
                </category>
            </categories>
            <productfamilies>
                <item id="family1">Family 1</item>
            </productfamilies>
            <series>
                <item id="series1">Series 1</item>
            </series>
            <product id="product1" series="series1" family="family1">
                <name>Product 1</name>
                <maintainers>
                    <contact>docs@example.invalid</contact>
                </maintainers>
                <docset id="docset1" lifecycle="supported">
                    <version>1.0</version>
                    <resources>
                        <git remote="https://example.invalid/repo.git"/>
                        <locale lang="en-us">
                            <branch>main</branch>
                            <deliverable id="deli-1" type="dc">
                                <dc file="DC-TEST-ONE">
                                    <format html="1" pdf="0" single-html="0" epub="0"/>
                                    <subdeliverable>book-1</subdeliverable>
                                </dc>
                            </deliverable>
                        </locale>
                    </resources>
                    <external>
                        <link>
                            <url lang="en-us" href="https://example.invalid/docs" format="html"/>
                            <descriptions>
                                <desc lang="en-us"/>
                            </descriptions>
                        </link>
                    </external>
                </docset>
            </product>
        </portal>""",
        parser=None,
    )


# @pytest.fixture(autouse=True)
# def ensure_logger_handler():
#     logger = logging.getLogger(LOGGERNAME)
#     handler = logging.StreamHandler()
#     try:
#         if logger.handlers:
#             logger.handlers.clear()  # Clear existing handlers to avoid duplicates
#         handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
#         logger.addHandler(handler)
#         logger.setLevel(logging.CRITICAL)
#         logger.propagate = True
#         yield

#     finally:
#         logger.removeHandler(handler)


# -----------------------
def assert_results(string, messages: list[str]) -> None:
    assert any(string in msg for msg in messages)


# -----------------------
def test_check_in_registry():
    """Test that the check functions are registered correctly."""
    assert len(register_check.registry) > 0, "No checks registered"
    for func in register_check.registry:
        assert callable(func), f"{func.__name__} is not callable"
        assert func.__name__.startswith("check_"), (
            f'{func.__name__} does not start with "check_"'
        )


# ----
def test_check_dc_in_language(xmlnode):
    assert check_dc_in_language(xmlnode)


def test_check_dc_in_language_double_dc(xmlnode):
    language = xmlnode.find(".//resources/locale")
    first_child = language.find("deliverable")

    # Append the first deliverable
    new_deli = copy.deepcopy(first_child)
    language.append(new_deli)

    result = check_dc_in_language(xmlnode)
    success, messages = result.success, result.messages
    assert not success
    assert_results("non-unique values", messages)
    assert_results("DC-TEST-ONE", messages)
    assert_results("docset=docset1 language=en-us", messages)


@pytest.mark.parametrize(
    "scenario,expected_success,expected_messages",
    [
        ("baseline", True, []),
        (
            "duplicate_format",
            False,
            ["Duplicated format attributes found", "docset=docset1"],
        ),
        ("extra_pdf", True, []),
        ("extra_no_format_attr", True, []),
        ("unknown_language", True, []),
    ],
)
def test_check_duplicated_format_in_extralinks_cases(
    xmlnode, scenario: str, expected_success: bool, expected_messages: list[str]
):
    """Test duplicated format checks across baseline and edge cases."""
    link = xmlnode.find(".//external/link")

    if scenario == "duplicate_format":
        link.append(
            E.url(
                lang="en-us",
                format="html",
                href="https://documentation.suse.com/sle-micro/6.0/duplicate-format",
            )
        )
    elif scenario == "extra_pdf":
        link.append(E.url(lang="en-us", format="pdf", href="https://example.com/pdf"))
    elif scenario == "extra_no_format_attr":
        link.append(E.url(lang="en-us", href="https://example.com/no-fmt"))
    elif scenario == "unknown_language":
        link.append(E.url(format="pdf", href="https://example.com"))

    result = check_duplicated_format_in_extralinks(xmlnode)
    assert result.success is expected_success
    for msg in expected_messages:
        assert_results(msg, result.messages)


@pytest.mark.parametrize(
    "scenario,expected_success,expected_messages",
    [
        ("baseline", True, []),
        ("duplicate_href_append", False, ["non-unique href values", "href"]),
        (
            "duplicate_href_insert",
            False,
            ["non-unique href values", "language=en-us", "https://example.invalid/docs"],
        ),
        ("missing_href", True, []),
        ("unknown_lang", True, []),
    ],
)
def test_check_duplicated_url_in_extralinks_cases(
    xmlnode, scenario: str, expected_success: bool, expected_messages: list[str]
):
    """Test duplicated URL checks across baseline and edge cases."""
    link = xmlnode.find(".//external/link")

    if scenario == "duplicate_href_append":
        link.append(E.url(lang="en-us", format="pdf", href="https://example.invalid/docs"))
    elif scenario == "duplicate_href_insert":
        link.insert(1, E.url(lang="en-us", href="https://example.invalid/docs", format="html"))
    elif scenario == "missing_href":
        link.append(E.url(lang="en-us", format="pdf"))
    elif scenario == "unknown_lang":
        link.append(E.url(format="pdf", href="https://other-url.com"))

    result = check_duplicated_url_in_extralinks(xmlnode)
    assert result.success is expected_success
    for msg in expected_messages:
        assert_results(msg, result.messages)


@pytest.mark.parametrize(
    "scenario,expected_success,expected_messages",
    [
        ("baseline", True, []),
        (
            "deliverable_disabled_formats",
            False,
            ["No enabled format", "deliverable=DC-fake-deliverable", "docset=docset1"],
        ),
        (
            "dc_with_disabled_formats",
            False,
            ["deliverable=DC-TEST-TWO", "docset=docset1"],
        ),
        ("no_format_element", True, []),
        ("direct_format_disabled", False, ["direct-format"]),
    ],
)
def test_check_enabled_format_cases(
    xmlnode, scenario: str, expected_success: bool, expected_messages: list[str]
):
    """Test enabled format checks across baseline and edge cases."""
    locale = xmlnode.find(".//resources/locale")

    if scenario == "deliverable_disabled_formats":
        locale.append(
            E.deliverable(
                E.dc("DC-fake-deliverable"),
                E.format(**{"html": "0", "pdf": "0", "single-html": "0", "epub": "0"}),
            )
        )
    elif scenario == "dc_with_disabled_formats":
        locale.append(
            E.deliverable(
                E.dc(
                    E.format(**{"html": "0", "pdf": "0", "single-html": "0", "epub": "0"}),
                    file="DC-TEST-TWO",
                ),
                id="deli-2",
                type="dc",
            )
        )
    elif scenario == "no_format_element":
        locale.append(E.deliverable(E.dc("DC-no-format"), id="no-fmt"))
    elif scenario == "direct_format_disabled":
        locale.append(
            E.deliverable(
                E.format(html="0", pdf="0", epub="0", **{"single-html": "0"}),
                id="direct-format",
            )
        )

    result = check_enabled_format(xmlnode)
    assert result.success is expected_success
    for msg in expected_messages:
        assert_results(msg, result.messages)


# ----
def test_check_format_subdeliverable(xmlnode):
    assert check_format_subdeliverable(xmlnode)


@pytest.mark.parametrize(
    "formats",
    [
        # 0
        {"pdf": "1", "epub": "0"},
        # 1
        {"pdf": "0", "epub": "1"},
        # 2
        {"pdf": "1", "epub": "1"},
    ],
)
def test_format_subdeliverable(formats, xmlnode, caplog):
    """Test that the check_format_subdeliverable function works as expected."""
    # Add a subdeliverable with no formats enabled
    language = xmlnode.find(".//resources/locale")
    dct_formats = {"html": "1", "single-html": "0"} | formats
    new_deli = E.deliverable(
        E.dc("DC-fake-subdeliverable"),
        E.format(**dct_formats),
        E.subdeliverable("book-subdeliverable"),
    )
    language.append(new_deli)

    result = check_format_subdeliverable(xmlnode)
    success, messages = result.success, result.messages
    assert not success
    assert_results("deliverable that has subdeliverables", messages)
    assert_results("deliverable=DC-fake-subdeliverable", messages)
    assert_results("docset=docset1", messages)
    assert_results("language=en-us", messages)


def test_format_subdeliverable_no_format(xmlnode, caplog):
    language = xmlnode.find(".//resources/locale")
    # dct_formats = {'html': '1', 'single-html': '0'} | formats
    new_deli = E.deliverable(
        E.dc("DC-fake-subdeliverable"),
        # E.format(**dct_formats),
        E.subdeliverable("book-subdeliverable"),
    )
    language.append(new_deli)

    result = check_format_subdeliverable(xmlnode)
    success, _ = result.success, result.messages
    assert success


def test_check_lang_code_in_desc_duplicate_lang(xmlnode):
    desc = xmlnode.find(".//external/link/descriptions/desc")
    new_desc = E.desc(lang="en-us", default="1", title="Fake title")
    desc.addnext(new_desc)

    result = check_lang_code_in_desc(xmlnode)
    success, messages = result.success, result.messages
    assert not success
    assert_results("have non-unique lang", messages)
    assert_results("Found duplicates:", messages)


def test_check_lang_code_in_docset_duplicate_lang(xmlnode):
    docset = xmlnode.find(".//docset/resources/locale")
    new_locale = E.locale(E.branch("main"), lang="en-us", default="1")
    docset.addnext(new_locale)

    result = check_lang_code_in_docset(xmlnode)
    success, messages = result.success, result.messages
    assert not success
    assert_results("have non-unique lang", messages)
    assert_results("Found duplicates:", messages)


# ----
def test_check_lang_code_in_extralinks(xmlnode):
    """Test that the check_lang_code_in_extralinks function works as expected."""
    assert check_lang_code_in_extralinks(xmlnode)


def test_check_lang_code_in_extralinks_duplicate_lang(xmlnode):
    """Test that the check_lang_code_in_extralinks function works as expected."""
    link = xmlnode.find(".//external/link")
    duplicate_url = E.url(
        lang="en-us",
        format="pdf",
        href="https://documentation.suse.com/sle-micro/6.0/extra",
    )
    link.append(duplicate_url)

    result = check_lang_code_in_extralinks(xmlnode)
    success, messages = result.success, result.messages
    assert not success
    assert_results("have non-unique lang", messages)
    assert_results("Found duplicates:", messages)


# ----
def test_check_subdeliverable_in_deliverable():
    node = etree.fromstring(
        """
        <product product="fake" schemaversion="6.0">
            <name>Fake Doc</name>
            <acronym>fake</acronym>
            <docset id="ds1" lifecycle="supported">
                <resources>
                    <locale lang="en-us" default="1">
                        <branch>main</branch>
                        <deliverable id="d1" type="dc">
                            <dc file="DC-fake-all">
                            <subdeliverable>book-1</subdeliverable>
                            </dc>
                        </deliverable>
                    </locale>
                </resources>
            </docset>
        </product>
        """,
        parser=None,
    )
    assert check_subdeliverable_in_deliverable(node)


def test_check_subdeliverable_in_deliverable_duplicate_subdeliverable():
    node = etree.fromstring(
        """
        <product id="fake" schemaversion="6.0">
            <name>Fake Doc</name>
            <acronym>fake</acronym>
            <docset id="ds1" lifecycle="supported">
                <resources>
                    <locale lang="en-us" default="1">
                        <branch>main</branch>
                        <deliverable>
                            <dc file="DC-fake-all">
                            <subdeliverable>book-1</subdeliverable>
                            <subdeliverable>book-1</subdeliverable><!-- Duplicate -->
                            </dc>
                        </deliverable>
                    </locale>
                </resources>
            </docset>
        </product>
        """,
        parser=None,
    )

    result = check_subdeliverable_in_deliverable(node)
    success, messages = result.success, result.messages
    assert not success
    assert_results("book-1", messages)
    assert_results("docset=ds1/language=en-us", messages)


def test_check_dc_in_language_v7_duplicate_dc(xmlnode):
    locale = xmlnode.find(".//resources/locale")
    first_deli = locale.find("deliverable")
    locale.append(copy.deepcopy(first_deli))

    result = check_dc_in_language(xmlnode)
    assert not result.success
    assert_results("DC-TEST-ONE", result.messages)
    assert_results("docset=docset1 language=en-us", result.messages)


def test_check_lang_code_in_docset_v7_duplicate_locale_lang(xmlnode):
    resources = xmlnode.find(".//resources")
    duplicate_locale = E.locale(E.branch("main"), lang="en-us")
    resources.append(duplicate_locale)

    result = check_lang_code_in_docset(xmlnode)
    assert not result.success
    assert_results("non-unique lang attributes", result.messages)
    assert_results("docset=docset1", result.messages)


def test_check_lang_code_in_extralinks_v7_duplicate_url_lang(xmlnode):
    link = xmlnode.find(".//external/link")
    duplicate = E.url(lang="en-us", href="https://example.invalid/other", format="pdf")
    link.insert(1, duplicate)

    result = check_lang_code_in_extralinks(xmlnode)
    assert not result.success
    assert_results("duplicate external/link/url/@lang", result.messages)


def test_check_subdeliverable_in_deliverable_v7_duplicate_subdeliverable(xmlnode):
    dc = xmlnode.find(".//resources/locale/deliverable/dc")
    dc.append(E.subdeliverable("book-1"))

    result = check_subdeliverable_in_deliverable(xmlnode)
    assert not result.success
    assert_results("book-1", result.messages)
    assert_results("docset=docset1/language=en-us", result.messages)


@pytest.mark.parametrize(
    "langs,expected_success,expected_messages",
    [
        ([], True, []),
        (["de-at"], False, ["de-at", "not supported"]),
        (["de-at", "en-nz"], False, ["de-at", "en-nz", "not supported"]),
    ],
)
def test_check_unsupported_language_code_cases(
    xmlnode,
    langs: list[str],
    expected_success: bool,
    expected_messages: list[str],
):
    """Test supported and unsupported language scenarios."""
    locale = xmlnode.find(".//resources/locale")
    for lang in langs:
        locale.addnext(E.locale(E.branch("main"), lang=lang))

    result = check_unsupported_language_code(xmlnode)
    assert result.success is expected_success
    for msg in expected_messages:
        assert_results(msg, result.messages)


def test_check_lang_code_in_desc_with_duplicates(xmlnode):
    """Test detection of duplicate lang attributes in desc elements."""
    desc_parent = xmlnode.find(".//desc/..")
    if desc_parent is not None:
        duplicate_desc = E.desc(title="Duplicate", lang="en-us")
        desc_parent.append(duplicate_desc)

    result = check_lang_code_in_desc(xmlnode)
    assert not result.success
    assert_results("non-unique lang attributes", result.messages)


def test_check_dc_in_language_with_deliverable_no_dc(xmlnode):
    """Test deliverable without dc element."""
    language = xmlnode.find(".//resources/locale")
    # Add deliverable without dc
    no_dc_deli = E.deliverable(E.format(html="1"), id="no-dc-1")
    language.append(no_dc_deli)

    result = check_dc_in_language(xmlnode)
    assert result.success


def test_check_format_subdeliverable_default_false(xmlnode):
    """Test subdeliverable with format attributes defaulting to false."""
    language = xmlnode.find(".//resources/locale")
    new_deli = E.deliverable(
        E.dc("DC-test", E.format(), E.subdeliverable("book")),
        id="test-1",
    )
    language.append(new_deli)

    result = check_format_subdeliverable(xmlnode)
    # Should pass since no pdf/epub is explicitly set to true
    assert result.success


@pytest.mark.parametrize(
    "num_locales",
    [
        1,   # Single locale - success
        2,   # Two unique locales - success
    ],
)
def test_check_lang_code_in_docset_unique_langs(xmlnode, num_locales):
    """Test docset with unique language codes."""
    docset = xmlnode.find(".//docset")
    resources = docset.find("resources")

    for i in range(1, num_locales):
        new_locale = E.locale(E.branch(f"branch{i}"), lang="de-de")
        resources.append(new_locale)

    result = check_lang_code_in_docset(xmlnode)
    assert result.success or num_locales <= 1


# ---- Tests for subdeliverable_in_deliverable with empty text ----
def test_check_subdeliverable_in_deliverable_empty_text(xmlnode):
    """Test subdeliverable with empty text content."""
    language = xmlnode.find(".//resources/locale")
    deli = language.find("deliverable")
    dc = deli.find("dc")
    sub = E.subdeliverable("")
    dc.append(sub)

    result = check_subdeliverable_in_deliverable(xmlnode)
    assert result.success


# ---- Tests for _dc_identifier edge cases ----
@pytest.mark.parametrize(
    "deliverable_xml,expected_identifier",
    [
        ('<deliverable id="deli-1"><dc file="DC-TEST">text</dc></deliverable>', "DC-TEST"),
        ('<deliverable id="deli-1"><dc>DC-FROM-TEXT</dc></deliverable>', "DC-FROM-TEXT"),
        ('<deliverable id="deli-2"><dc/></deliverable>', "deli-2"),
        ('<deliverable><format/></deliverable>', "n/a"),
    ],
)
def test_dc_identifier_cases(deliverable_xml: str, expected_identifier: str):
    """Test dc_identifier helper across common edge cases."""
    deliverable = etree.fromstring(deliverable_xml)
    assert dc_identifier(deliverable) == expected_identifier


def test_check_lang_code_in_desc_no_lang_attr(xmlnode):
    """Test desc elements without lang attribute."""
    desc_parent = xmlnode.find(".//desc/..")
    if desc_parent is not None:
        no_lang_desc = E.desc(title="No Lang")
        desc_parent.append(no_lang_desc)

    result = check_lang_code_in_desc(xmlnode)
    assert result.success


def test_check_format_subdeliverable_html_only(xmlnode):
    """Test subdeliverable with only HTML format enabled (allowed)."""
    language = xmlnode.find(".//resources/locale")
    new_deli = E.deliverable(
        E.dc("DC-html-only", E.format(html="1", pdf="0", epub="0", **{"single-html": "0"})),
        E.subdeliverable("book"),
        id="html-only",
    )
    language.append(new_deli)

    result = check_format_subdeliverable(xmlnode)
    assert result.success


@pytest.mark.parametrize(
    "node_xml,expected_docset_id",
    [
        (
            '<docset id="custom-set"><resources><locale lang="en"/></resources></docset>',
            "custom-set",
        ),
        ('<locale lang="en"/>', "n/a"),
    ],
)
def test_check_docset_id_cases(node_xml: str, expected_docset_id: str):
    """Test _docset_id helper."""
    node = etree.fromstring(node_xml)
    locale = node.find(".//locale") if node.tag == "docset" else node
    assert docset_id(locale) == expected_docset_id


def test_check_dc_in_language_multiple_failures():
    node = etree.fromstring(
        """
        <root>
            <docset id="1">
                <resources>
                    <locale lang="en-us"><deliverable><dc file="A"/></deliverable><deliverable><dc file="A"/></deliverable></locale>
                    <locale lang="de-de"><deliverable><dc file="B"/></deliverable><deliverable><dc file="B"/></deliverable></locale>
                </resources>
            </docset>
        </root>
        """
    )
    assert not check_dc_in_language(node).success


def test_check_duplicated_format_in_extralinks_multiple_failures():
    node = etree.fromstring(
        """
        <portal>
            <docset id="ds1">
                <external>
                    <link>
                        <url lang="en" format="html"/>
                        <url lang="en" format="html"/>
                        <url lang="de" format="pdf"/>
                        <url lang="de" format="pdf"/>
                    </link>
                </external>
            </docset>
        </portal>
        """
    )
    assert not check_duplicated_format_in_extralinks(node).success


def test_check_duplicated_url_in_extralinks_multiple_failures():
    node = etree.fromstring(
        """
        <portal>
           <docset id="ds1">
               <external>
                <link>
                    <url lang="en" href="url1"/>
                    <url lang="en" href="url1"/>
                    <url lang="de" href="url2"/>
                    <url lang="de" href="url2"/>
                </link>
               </external>
           </docset>
        </portal>
        """
    )
    assert not check_duplicated_url_in_extralinks(node).success


def test_check_enabled_format_multiple_failures():
    node = etree.fromstring(
        """
        <docset id="ds1">
            <deliverable id="d1">
              <format html="0" pdf="0" single-html="0" epub="0"/>
            </deliverable>
            <deliverable id="d2">
              <format html="0" pdf="0" single-html="0" epub="0"/>
            </deliverable>
        </docset>
        """
    )
    assert not check_enabled_format(node).success


def test_check_format_subdeliverable_multiple_failures():
    node = etree.fromstring(
        """
        <docset id="ds1">
            <deliverable id="d1">
                <format pdf="1"/>
                <subdeliverable>s1</subdeliverable>
            </deliverable>
            <deliverable id="d2">
                <format epub="1"/>
                <subdeliverable>s2</subdeliverable>
            </deliverable>
        </docset>
        """
    )
    assert not check_format_subdeliverable(node).success


@pytest.mark.parametrize(
    "check_func,node_xml",
    [
        (
            check_lang_code_in_desc,
            """
            <portal>
                <docset id="d1">
                    <external>
                        <link>
                            <descriptions>
                                <desc lang="en-us"/>
                                <desc lang="en-us"/>
                            </descriptions>
                        </link>
                        <link>
                            <descriptions>
                                <desc lang="de-de"/>
                                <desc lang="de-de"/>
                            </descriptions>
                        </link>
                    </external>
                </docset>
            </portal>
            """,
        ),
        (
            check_lang_code_in_docset,
            """
            <portal>
                <docset id="ds1">
                    <resources>
                        <locale lang="en"/>
                        <locale lang="en"/>
                    </resources>
                </docset>
                <docset id="ds2">
                    <resources>
                        <locale lang="de"/>
                        <locale lang="de"/>
                    </resources>
                </docset>
            </portal>
            """,
        ),
        (
            check_lang_code_in_extralinks,
            """
            <docset id="d1">
                <external>
                    <link><url lang="en"/><url lang="en"/></link>
                    <link><url lang="de"/><url lang="de"/></link>
                </external>
            </docset>
            """,
        ),
    ],
)
def test_language_code_checks_multiple_failures(
    check_func: Callable[[etree._Element], object],
    node_xml: str,
):
    node = etree.fromstring(node_xml)
    result = check_func(node)
    assert not result.success
    assert len(result.messages) == 2


def test_check_subdeliverable_in_deliverable_multiple_failures():
    node = etree.fromstring(
        """
        <docset id="d1">
            <deliverable>
            <subdeliverable>a</subdeliverable>
            <subdeliverable>a</subdeliverable>
            </deliverable>
            <deliverable>
            <subdeliverable>b</subdeliverable>
            <subdeliverable>b</subdeliverable>
            </deliverable>
        </docset>
        """
    )
    assert not check_subdeliverable_in_deliverable(node).success


def test_check_lang_code_in_desc_no_parent():
    """Test desc elements without a parent element."""
    from docbuild.config.xml.checks import check_lang_code_in_desc

    class MockElement:
        def __init__(self):
            self.attrib = {}
        def getparent(self):
            return None

    class MockTree:
        def findall(self, path, namespaces=None):
            return [MockElement()]

    result = check_lang_code_in_desc(MockTree())
    assert result.success


def test_check_format_subdeliverable_no_subdeliverable():
    node = etree.fromstring(
        """
        <docset id="ds1">
            <deliverable id="d1"><format pdf="1"/></deliverable>
        </docset>
        """
    )
    assert check_format_subdeliverable(node).success
