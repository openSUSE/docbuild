from collections.abc import Generator
from pathlib import Path

from lxml import etree
import pytest

from docbuild.models.deliverable import Deliverable
from docbuild.models.metadata import Metadata

DATADIR = Path(__file__).absolute().parent.parent / "data"


@pytest.fixture
def node() -> etree._ElementTree:
    """Fixture to create a mock XML node for testing."""
    node = etree.fromstring(
        """
    <product productid="sles" schemaversion="6.0">
        <name>SUSE Linux Enterprise Server</name>
        <acronym>SLES</acronym>
        <categories>
            <category categoryid="about">
                <language lang="en-us" default="1" title="About"/>
            </category>
        </categories>
        <!-- desc -->
        <docset lifecycle="supported" setid="15-SP6">
            <version>15 SP6</version>
            <!-- <canonical>sles/15-SP6</canonical> -->
            <builddocs>
                <git remote="https://github.com/SUSE/doc-sle.git"/>
                <language default="1" lang="en-us">
                    <branch>maintenance/SLE15SP6</branch>
                    <deliverable category="administration">
                        <dc>DC-SLES-administration</dc>
                        <format epub="0" html="0" pdf="1" single-html="1"/>
                    </deliverable>
                    <deliverable category="installation-upgrade">
                        <dc>DC-SLES-deployment</dc>
                        <format epub="0" html="0" pdf="1" single-html="1"/>
                    </deliverable>
                    <deliverable category="installation-upgrade">
                        <dc>DC-SLES-raspberry-pi</dc>
                        <format epub="0" html="1" pdf="1" single-html="1"/>
                    </deliverable>
                </language>
                <language lang="de-de" translation-type="list">
                    <!-- <branch>maintenance/SLE15SP6</branch> -->
                    <subdir>l10n/sles/de-de</subdir>
                    <deliverable>
                        <dc>DC-SLES-administration</dc>
                    </deliverable>
                    <deliverable>
                        <dc>DC-SLES-deployment</dc>
                    </deliverable>
                </language>
            </builddocs>
        </docset>
    </product>""",
        parser=None,
    )
    return node.getroottree()  # .getiterator("deliverable")


def get_deliverables(node, *, lang: str = "en-us"):
    """Get all deliverable elements from the XML node."""
    yield from node.xpath(
        (
            # Works for product nodes that is a root element and
            # those that is under another element:
            "(/product | /docservconfig/product)"
            f"/docset/builddocs/language[@lang={lang!r}]/deliverable"
        ),
    )


@pytest.fixture
def deliverable(node: etree._ElementTree) -> Generator[etree._Element, None, None]:
    """Fixture to yield English deliverable elements from the XML node."""
    return get_deliverables(node)


@pytest.fixture
def deliverable_de(node: etree._Element) -> Generator[etree._Element, None, None]:
    """Fixture to yield German deliverable elements from the XML node."""
    return get_deliverables(node, lang="de-de")


@pytest.fixture
def firstnode(deliverable: etree._Element) -> etree._Element:
    return Deliverable(next(deliverable))


# ---------------------
def test_deliverable_productid(firstnode: Deliverable):
    assert firstnode.productid == "sles"


def test_deliverable_docsetid(firstnode: Deliverable):
    assert firstnode.docsetid == "15-SP6"


def test_deliverable_lang(firstnode: Deliverable):
    assert firstnode.lang == "en-us"


def test_deliverable_language(firstnode: Deliverable):
    assert firstnode.language == "en"


def test_deliverable_product_docset(firstnode: Deliverable):
    assert firstnode.product_docset == "sles/15-SP6"


def test_deliverable_pdlang(firstnode: Deliverable):
    assert firstnode.pdlang == "sles/15-SP6/en-us"


def test_deliverable_pdlangdc(firstnode: Deliverable):
    assert firstnode.pdlangdc == "sles/15-SP6/en-us:DC-SLES-administration"


def test_deliverable_full_id(firstnode: Deliverable):
    assert firstnode.full_id == (
        "sles/15-SP6/maintenance_SLE15SP6/en-us:DC-SLES-administration"
    )


def test_deliverable_lang_is_default(firstnode: Deliverable):
    assert firstnode.lang_is_default is True


def test_deliverable_docsuite(firstnode: Deliverable):
    assert firstnode.docsuite == "sles/15-SP6/en-us:DC-SLES-administration"


def test_deliverable_branch(firstnode: Deliverable):
    assert firstnode.branch == "maintenance/SLE15SP6"


def test_deliverable_branch_german(deliverable_de: etree._Element):
    firstnode = Deliverable(next(deliverable_de))
    assert firstnode.branch == "maintenance/SLE15SP6"


def test_deliverable_no_branch_found(node: etree._ElementTree):
    branch = node.xpath(
        "/product/docset/builddocs/language[@lang='en-us']/branch",
    )
    # Remove the branch element to simulate no branch found
    if branch:
        branch[0].getparent().remove(branch[0])

    deliverables = get_deliverables(node)
    with pytest.raises(ValueError, match="No branch found for this deliverable"):
        deli = Deliverable(next(deliverables))
        deli.branch  # noqa: B018 This should raise an error


def test_deliverable_subdir(firstnode: Deliverable):
    assert firstnode.subdir == ""


def test_deliverable_no_subdir_found(deliverable_de: etree._Element):
    deli = Deliverable(next(deliverable_de))
    assert deli.subdir == "l10n/sles/de-de"


def test_deliverable_git(firstnode: Deliverable):
    assert firstnode.git.url == "https://github.com/suse/doc-sle.git"


def test_deliverable_no_git_found(node: etree._ElementTree):
    git = node.xpath(
        "/product/docset[1]/builddocs/git",
    )
    # Remove the git element to simulate no error
    if git:
        git[0].getparent().remove(git[0])

    deliverables = get_deliverables(node)
    with pytest.raises(ValueError, match="No git remote found"):
        deli = Deliverable(next(deliverables))
        deli.git  #  noqa: B018 This should raise an error


def test_deliverable_dcfile(firstnode: Deliverable):
    assert firstnode.dcfile == "DC-SLES-administration"


def test_deliverable_basefile(firstnode: Deliverable):
    assert firstnode.basefile == "SLES-administration"


def test_deliverable_format(firstnode: Deliverable):
    assert firstnode.format == {
        "epub": False,
        "html": False,
        "pdf": True,
        "single-html": True,
    }


def test_deliverable_no_format_found(node: etree._ElementTree):
    format_elem = node.xpath(
        "/product/docset/builddocs/language[@lang='en-us']/deliverable[1]/format",
    )
    # Remove the format element to simulate no error
    if format_elem:
        format_elem[0].getparent().remove(format_elem[0])

    deliverables = get_deliverables(node)
    with pytest.raises(ValueError, match="No format found for"):
        deli = Deliverable(next(deliverables))
        deli.format  #  noqa: B018 This should raise an error


def test_deliverable_node(firstnode: Deliverable):
    assert firstnode.node is not None


def test_deliverable_productname(firstnode: Deliverable):
    assert firstnode.productname == "SUSE Linux Enterprise Server"


def test_deliverable_acronym(firstnode: Deliverable):
    assert firstnode.acronym == "SLES"


def test_deliverable_no_acronym_found(node: etree._ElementTree):
    acronym_elem = node.xpath(
        "/product/acronym",
    )
    # Remove the acronym element to simulate no error
    if acronym_elem:
        acronym_elem[0].getparent().remove(acronym_elem[0])

    deliverables = get_deliverables(node)
    deli = Deliverable(next(deliverables))
    assert deli.acronym == ""


def test_deliverable_version(firstnode: Deliverable):
    assert firstnode.version == "15 SP6"


def test_deliverable_lifecycle(firstnode: Deliverable):
    assert firstnode.lifecycle == "supported"


def test_deliverable_relpath(firstnode: Deliverable):
    assert firstnode.relpath == "en-us/sles/15-SP6"


def test_deliverable_repo_path(firstnode: Deliverable):
    assert firstnode.repo_path == Path("https___github_com_suse_doc_sle_git")


def test_deliverable_zip_path(firstnode: Deliverable):
    assert firstnode.zip_path == "en-us/sles/15-SP6/sles-15-SP6-en-us.zip"


def test_deliverable_html_path(firstnode: Deliverable):
    assert firstnode.html_path == "/sles/15-SP6/html/SLES-administration/"


def test_deliverable_base_format_path(deliverable_de: etree._Element):
    deli = Deliverable(next(deliverable_de))
    deli.meta = Metadata(
        rootid="foo",
        # productid="sles",
        # docsetid="15-SP6",
        # lang="de-de"
    )
    assert deli.html_path == "/de-de/sles/15-SP6/html/foo/"


def test_deliverable_base_format_path_rootid_none(deliverable_de: etree._Element):
    deli = Deliverable(next(deliverable_de))
    deli.meta = Metadata(
        rootid=None,
        # productid="sles",
        # docsetid="15-SP6",
        # lang="de-de"
    )
    # If rootid is None, fallback to the deliverable's basefile
    assert deli.html_path == ("/de-de/sles/15-SP6/html/SLES-administration/")


def test_deliverable_singlehtml_path(firstnode: Deliverable):
    assert firstnode.singlehtml_path == "/sles/15-SP6/single-html/SLES-administration/"


def test_deliverable_pdf_path(firstnode: Deliverable):
    assert firstnode.pdf_path == "/sles/15-SP6/pdf/SLES-administration_en.pdf"


def test_deliverable_pdf_path_german(deliverable_de: etree._Element):
    deli = Deliverable(next(deliverable_de))
    assert deli.pdf_path == "/de-de/sles/15-SP6/pdf/SLES-administration_de.pdf"


def test_deliverable_product_node(firstnode: Deliverable):
    assert firstnode.product_node is not None


def test_deliverable_docset_node(firstnode: Deliverable):
    assert firstnode.docset_node is not None


def test_deliverable_metafile(firstnode: Deliverable):
    assert firstnode.metafile is None


def test_deliverable_metafile_setter(firstnode: Deliverable):
    firstnode.metafile = "metafile"
    assert firstnode.metafile is not None


def test_deliverable_meta(firstnode: Deliverable):
    assert firstnode.meta is None


def test_deliverable_meta_setter_wrong_type(firstnode: Deliverable):
    with pytest.raises(TypeError, match="Expected type Metadata, but got"):
        firstnode.meta = "not-a-metadata-instance"


def test_deliverable_hash(firstnode: Deliverable):
    assert hash(firstnode) == hash(firstnode.full_id)


def test_deliverable_repr(firstnode: etree._Element):
    assert repr(firstnode) == (
        "Deliverable(productid='sles', docsetid='15-SP6', lang='en-us', "
        "branch='maintenance/SLE15SP6', dcfile='DC-SLES-administration')"
    )


def test_deliverable_to_dict(firstnode: Deliverable):
    with pytest.raises(NotImplementedError):
        firstnode.to_dict()


def test_deliverable_group_from_product(node: etree._ElementTree):
    deli = Deliverable(next(get_deliverables(node)))
    assert len(list(deli.categories)) == 1


def test_deliverable_group_from_root():
    doc = """<docservconfig>
        <categories>
            <category categoryid="about">
                <language lang="en-us" default="1" title="About"/>
            </category>
        </categories>
        <product productid="sles" schemaversion="6.0">
            <docset lifecycle="supported" setid="15-SP6">
                <builddocs>
                    <git remote="https://github.com/SUSE/doc-sle.git"/>
                    <language default="1" lang="en-us">
                        <branch>maintenance/SLE15SP6</branch>
                        <deliverable category="administration">
                            <dc>DC-SLES-administration</dc>
                        </deliverable>
                    </language>
                </builddocs>
            </docset>
        </product>
    </docservconfig>
    """
    node = etree.fromstring(doc, parser=None).getroottree()
    deli = Deliverable(next(get_deliverables(node)))
    assert len(list(deli.categories_from_root)) == 1


def test_deliverable_all_groups():
    doc = """<docservconfig>
        <categories>
            <category categoryid="about">
                <language lang="en-us" default="1" title="About"/>
            </category>
        </categories>
        <product productid="sles" schemaversion="6.0">
            <category>
                <language lang="en-us" default="1" title="Hello World"/>
            </category>
            <docset lifecycle="supported" setid="15-SP6">
                <builddocs>
                    <git remote="https://github.com/SUSE/doc-sle.git"/>
                    <language default="1" lang="en-us">
                        <branch>maintenance/SLE15SP6</branch>
                        <deliverable category="administration">
                            <dc>DC-SLES-administration</dc>
                        </deliverable>
                    </language>
                </builddocs>
            </docset>
        </product>
    </docservconfig>
    """
    node = etree.fromstring(doc, parser=None).getroottree()
    deli = Deliverable(next(get_deliverables(node)))
    assert len(list(deli.all_categories)) == 2
