import copy

from lxml import etree, objectify
import pytest

from docbuild.config.xml.checks import (
    check_dc_in_language,
    check_duplicated_categoryid,
    check_duplicated_format_in_extralinks,
    check_duplicated_linkid,
    check_duplicated_url_in_extralinks,
    check_enabled_format,
    check_format_subdeliverable,
    check_lang_code_in_category,
    check_lang_code_in_desc,
    check_lang_code_in_docset,
    check_lang_code_in_extralinks,
    check_lang_code_in_overridedesc,
    check_subdeliverable_in_deliverable,
    check_translation_deliverables,
    check_valid_languages,
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
    return etree.fromstring(
        """<product product="fake" schemaversion="6.0">
            <name>Fake Doc</name>
            <acronym>fake</acronym>
            <category categoryid="container">
                <language lang="en-us" default="1" title="Containerization"/>
            </category>
            <desc default="1" lang="en-us">
              <title>A fake title</title>
              <p>This is a fake description.</p>
            </desc>
            <docset setid="1" lifecycle="supported">
                <version>1.0</version>
                <overridedesc treatment="append">
                    <desc default="1" lang="en-us">
                        <p>Doc fake addition</p>
                    </desc>
                </overridedesc>
                <builddocs>
                    <git remote="https://github.com/SUSE/doc-fakedoc.git"/>
                    <language lang="en-us" default="1">
                        <deliverable>
                            <dc>DC-GNOME-getting-started</dc>
                            <format html="1" pdf="1" single-html="0"/>
                        </deliverable>
                    </language>
                </builddocs>
                <external>
                    <link category="additional" linkid="fake-link">
                        <language lang="en-us" default="1"
                            title="SL Micro 6.0 Documentation">
                            <url format="html"
                            href="https://documentation.suse.com/sle-micro/6.0/"/>
                        </language>
                    </link>
               </external>
            </docset>
        </product>""",
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
    language = xmlnode.find(".//builddocs/language")
    first_child = language[0] if language is not None and len(language) > 0 else None

    # Append the first deliverable
    new_deli = copy.deepcopy(first_child)
    language.append(new_deli)

    result = check_dc_in_language(xmlnode)
    success, messages = result.success, result.messages
    assert not success
    assert_results("non-unique values", messages)
    assert_results("DC-GNOME-getting-started", messages)
    assert_results("docset=1 language=en-us", messages)


# ----
def test_check_duplicated_categoryid(xmlnode):
    assert check_duplicated_categoryid(xmlnode)


def test_check_duplicated_categoryid_with_duplicates(xmlnode):
    # Add a second category with the same categoryid
    new_category = E.category(categoryid="container")
    # we don't care about the order yet:
    xmlnode.append(new_category)

    result = check_duplicated_categoryid(xmlnode)
    success, messages = result.success, result.messages
    assert not success
    assert_results("non-unique categoryid values", messages)
    assert_results("container", messages)


# ----
def test_check_duplicated_format_in_extralinks(xmlnode):
    assert check_duplicated_format_in_extralinks(xmlnode)


def test_check_duplicated_format_in_extralinks_with_duplicates(xmlnode):
    language = xmlnode.find(".//external/link/language")
    first_child = language[0] if language is not None and len(language) > 0 else None

    new_url = copy.deepcopy(first_child)
    language.append(new_url)

    result = check_duplicated_format_in_extralinks(xmlnode)
    success, messages = result.success, result.messages
    assert not success
    assert_results("Duplicated format attributes found", messages)
    assert_results("docset=1", messages)


# ----
def test_check_duplicated_linkid(xmlnode):
    assert check_duplicated_linkid(xmlnode)


def test_check_duplicated_linkid_with_duplicates(xmlnode):
    """Test that duplicate linkid values within the same docset are detected."""
    # Add a second link with the same linkid within the same external element
    external = xmlnode.find(".//external")
    new_link = etree.Element("link", attrib={"linkid": "fake-link"}, nsmap=None)

    # Add a language element to make it a valid link structure
    language = etree.SubElement(new_link, "language", attrib=None, nsmap=None)
    language.set("lang", "en-us")
    url = etree.SubElement(language, "url", attrib=None, nsmap=None)
    url.set("href", "https://example.com/duplicate")
    url.set("format", "html")

    external.append(new_link)

    result = check_duplicated_linkid(xmlnode)
    success, messages = result.success, result.messages
    assert not success
    assert_results("non-unique linkid values", messages)
    assert_results("fake-link", messages)
    assert_results("docset=1", messages)


# ----
def test_check_duplicated_url_in_extralinks(xmlnode):
    assert check_duplicated_url_in_extralinks(xmlnode)


def test_check_duplicated_url_in_extralinks_with_duplicates(xmlnode):
    language = xmlnode.find(".//external/link/language")
    first_child = language[0] if language is not None and len(language) > 0 else None

    new_url = copy.deepcopy(first_child)
    # new_url.set('href', 'https://documentation.suse.com/sle-micro/6.0/')
    language.append(new_url)

    result = check_duplicated_url_in_extralinks(xmlnode)
    success, messages = result.success, result.messages
    assert not success
    assert_results("non-unique href values", messages)
    assert_results("href", messages)


# ----
def test_check_enabled_format(xmlnode):
    assert check_enabled_format(xmlnode)


def test_check_enabled_format_with_atleast_one(xmlnode):
    language = xmlnode.find(".//builddocs/language")
    # Add a new deliverable with no formats enabled
    new_deli = E.deliverable(
        E.dc("DC-fake-deliverable"),
        E.format(**{"html": "0", "pdf": "0", "single-html": "0", "epub": "0"}),
    )
    language.append(new_deli)

    result = check_enabled_format(xmlnode)
    success, messages = result.success, result.messages
    assert not success
    assert_results("No enabled format", messages)
    assert_results("deliverable=DC-fake-deliverable", messages)
    assert_results("docset=1", messages)


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
    language = xmlnode.find(".//builddocs/language")
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
    assert_results("docset=1", messages)
    assert_results("language=en-us", messages)


def test_format_subdeliverable_no_format(xmlnode, caplog):
    language = xmlnode.find(".//builddocs/language")
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


# ----
def test_check_lang_code_in_category(xmlnode):
    assert check_lang_code_in_category(xmlnode)


def test_check_lang_code_in_category_duplicate_lang(xmlnode):
    category = xmlnode.find("./category")
    new_language = E.language(lang="en-us", default="1", title="Containerization")
    category.append(new_language)

    result = check_lang_code_in_category(xmlnode)
    success, messages = result.success, result.messages
    assert not success
    assert_results("have non-unique lang", messages)
    assert_results("category 'container'", messages)


# ----
def test_check_lang_code_in_desc(xmlnode):
    assert check_lang_code_in_desc(xmlnode)


def test_check_lang_code_in_desc_duplicate_lang(xmlnode):
    desc = xmlnode.find("./desc")
    new_desc = E.desc(lang="en-us", default="1", title="Fake title")
    desc.addnext(new_desc)

    result = check_lang_code_in_desc(xmlnode)
    success, messages = result.success, result.messages
    assert not success
    assert_results("have non-unique lang", messages)
    assert_results("Found duplicates:", messages)


# ----
def test_check_lang_code_in_docset(xmlnode):
    assert check_lang_code_in_docset(xmlnode)


def test_check_lang_code_in_docset_duplicate_lang(xmlnode):
    docset = xmlnode.find("./docset/builddocs/language")
    new_language = E.language(lang="en-us", default="1")
    docset.addnext(new_language)

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
    language = xmlnode.find(".//external/link/language")
    new_language = E.language(lang="en-us", default="1", title="Fake title")
    language.addnext(new_language)

    result = check_lang_code_in_extralinks(xmlnode)
    success, messages = result.success, result.messages
    assert not success
    assert_results("have non-unique lang", messages)
    assert_results("Found duplicates:", messages)


# ----
def test_check_lang_code_in_overridedesc(xmlnode):
    assert check_lang_code_in_overridedesc(xmlnode)


def test_check_lang_code_in_overridedesc_duplicate_lang(xmlnode):
    overridedesc = xmlnode.find(".//overridedesc/desc")
    new_desc = E.desc(lang="en-us", default="1", title="Fake title")
    overridedesc.addnext(new_desc)

    result = check_lang_code_in_overridedesc(xmlnode)
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
        <docset setid="1" lifecycle="supported">
            <builddocs>
                <language lang="en-us" default="1">
                    <deliverable>
                        <dc>DC-fake-all</dc>
                        <subdeliverable>book-1</subdeliverable>
                    </deliverable>
                </language>
            </builddocs>
        </docset>
    </product>
    """,
        parser=None,
    )
    assert check_subdeliverable_in_deliverable(node)


def test_check_subdeliverable_in_deliverable_duplicate_subdeliverable():
    node = etree.fromstring(
        """
    <product product="fake" schemaversion="6.0">
        <name>Fake Doc</name>
        <acronym>fake</acronym>
        <docset setid="1" lifecycle="supported">
            <builddocs>
                <language lang="en-us" default="1">
                    <deliverable>
                        <dc>DC-fake-all</dc>
                        <subdeliverable>book-1</subdeliverable>
                        <subdeliverable>book-1</subdeliverable><!-- Duplicate -->
                    </deliverable>
                </language>
            </builddocs>
        </docset>
    </product>
    """,
        parser=None,
    )

    result = check_subdeliverable_in_deliverable(node)
    success, messages = result.success, result.messages
    assert not success
    assert_results("book-1", messages)
    assert_results("docset=1/language=en-us", messages)


# ---
def test_check_translation_deliverables(xmlnode):
    assert check_translation_deliverables(xmlnode)


def test_check_translation_deliverables_invalid(xmlnode, caplog):
    # Add a deliverable with a non-translation DC
    language = xmlnode.find("./docset/builddocs/language")
    builddocs = language.getparent()
    builddocs.remove(language)

    new_deli_en_us = E.language(
        E.deliverable(
            E.dc("DC-fake-all"),
            E.format(html="1", pdf="1", single_html="0"),
            E.subdeliverable("book-1"),
        ),
        default="1",
        lang="en-us",
    )
    new_deli_de_de = E.language(
        E.deliverable(
            E.dc("DC-fake-all"),
            # no format!
            E.subdeliverable("book-2"),  # is not available in en-us
        ),
        lang="de-de",
    )
    builddocs.append(new_deli_en_us)
    builddocs.append(new_deli_de_de)
    # print(etree.tostring(xmlnode, pretty_print=True, encoding="unicode"))

    result = check_translation_deliverables(xmlnode)
    success, messages = result.success, result.messages
    assert not success
    assert_results("DC-fake-all", messages)
    assert_results("The subdeliverable 'book-2'", messages)
    assert_results("docset=1/language=de-de/deliverable=DC-fake-all", messages)


def test_check_translation_deliverables_valid_with_subdeliverables(xmlnode):
    # First remove the existing language node
    # and add a new one with valid deliverables.
    # This is to simulate a valid case with multiple languages and subdeliverables.
    language = xmlnode.find("./docset/builddocs/language")
    builddocs = language.getparent()
    builddocs.remove(language)

    new_deli_en_us = E.language(
        E.deliverable(
            E.dc("DC-fake-all"),
            E.format(html="1", pdf="1", single_html="0"),
            E.subdeliverable("book-1"),
        ),
        default="1",
        lang="en-us",
    )
    new_deli_de_de = E.language(
        E.deliverable(
            E.dc("DC-fake-all"),
            # no format!
            E.subdeliverable("book-1"),
        ),
        lang="de-de",
    )
    builddocs.append(new_deli_en_us)
    builddocs.append(new_deli_de_de)
    # print(etree.tostring(xmlnode, pretty_print=True, encoding='unicode'))

    assert check_translation_deliverables(xmlnode)


# ----
def test_check_valid_languages(xmlnode):
    assert check_valid_languages(xmlnode)


def test_check_valid_languages_invalid_language(xmlnode):
    # Add an invalid language code
    language = xmlnode.find(".//builddocs/language")
    new_language = E.language(lang="invalid-lang", default="1")
    language.addnext(new_language)

    result = check_valid_languages(xmlnode)
    success, messages = result.success, result.messages
    assert not success
    assert_results("invalid language code", messages)
    assert_results("invalid-lang", messages)
    assert_results("docset=1", messages)
