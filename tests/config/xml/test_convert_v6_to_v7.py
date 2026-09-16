from importlib import resources
from pathlib import Path
import tempfile

from lxml import etree
import pytest

from docbuild.constants import XML_NS

XSLT_RESOURCE = resources.files("docbuild.config.xml").joinpath(
    "data", "convert-v6-to-v7.xsl"
)


@pytest.fixture
def xslt_transformer():
    """Load and compile the v6-to-v7 migration stylesheet."""
    with resources.as_file(XSLT_RESOURCE) as xslt_path:
        xslt_doc = etree.parse(str(xslt_path))
        return etree.XSLT(xslt_doc)


def test_prebuilt_multi_url_migration(xslt_transformer):
    """Test that prebuilt deliverables with multiple URLs (HTML and PDF) are not dropped."""
    v6_xml = etree.XML("""<docservconfig>
      <product productid="suma" schemaversion="6.0">
        <docset lifecycle="supported" setid="5.0">
          <version>5.0</version>
          <external>
            <link category="core-doc" linkid="retail">
              <language lang="en-us" default="1" title="Retail Guide">
                <url format="html" href="/suma/5.0/en/suse-manager/retail/retail-overview.html"/>
                <url format="pdf" href="/suma/5.0/en/pdf/suse_manager_retail_guide.pdf"/>
              </language>
            </link>
          </external>
        </docset>
      </product>
    </docservconfig>""")

    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = str(Path(tmpdir)) + "/"
        _ = xslt_transformer(
            v6_xml,
            outputdir=etree.XSLT.strparam(outdir),
            outputfile=etree.XSLT.strparam("portal.xml"),
        )
        result_tree = etree.parse(str(Path(tmpdir) / "portal.xml"))

        # Deliverable must exist and be of type "prebuilt"
        deliverables = result_tree.xpath("//deliverable[@type='prebuilt']")
        assert len(deliverables) == 1
        deliv = deliverables[0]

        # ID should be scoped to product and docset
        deliv_id = deliv.attrib.get(f"{{{XML_NS}}}id")
        assert deliv_id.startswith("suma.5.0.")

        # Prebuilt element should contain both HTML and PDF urls
        urls = deliv.xpath(".//prebuilt/url")
        assert len(urls) == 2
        formats = [u.attrib.get("format") for u in urls]
        assert "html" in formats
        assert "pdf" in formats


def test_prebuilt_unique_ids_across_docsets(xslt_transformer):
    """Test that links sharing the same target URL across docsets get unique IDs."""
    v6_xml = etree.XML("""<docservconfig>
      <product productid="suse-edge" schemaversion="6.0">
        <docset lifecycle="supported" setid="3.6">
          <version>3.6</version>
          <external>
            <link category="container">
              <language lang="en-us" default="1" title="SUSE Storage (Longhorn)">
                <url format="html" href="/cloudnative/storage/1.11/en/longhorn-documentation.html"/>
              </language>
            </link>
          </external>
        </docset>
      </product>
      <product productid="suse-telco" schemaversion="6.0">
        <docset lifecycle="supported" setid="3.6">
          <version>3.6</version>
          <external>
            <link category="container">
              <language lang="en-us" default="1" title="SUSE Storage (Longhorn)">
                <url format="html" href="/cloudnative/storage/1.11/en/longhorn-documentation.html"/>
              </language>
            </link>
          </external>
        </docset>
      </product>
    </docservconfig>""")

    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = str(Path(tmpdir)) + "/"
        _ = xslt_transformer(
            v6_xml,
            outputdir=etree.XSLT.strparam(outdir),
            outputfile=etree.XSLT.strparam("portal.xml"),
        )
        result_tree = etree.parse(str(Path(tmpdir) / "portal.xml"))

        deliverables = result_tree.xpath("//deliverable[@type='prebuilt']")
        assert len(deliverables) == 2

        ids = [d.attrib.get(f"{{{XML_NS}}}id") for d in deliverables]
        # IDs must be unique
        assert len(ids) == len(set(ids))
        assert any(i.startswith("suse-edge.3.6.") for i in ids)
        assert any(i.startswith("suse-telco.3.6.") for i in ids)


def test_external_gated_link_migration(xslt_transformer):
    """Test that gated links with https:// URLs are migrated to <external><link gated="true">."""
    v6_xml = etree.XML("""<docservconfig>
      <product productid="cloudnative" schemaversion="6.0">
        <docset lifecycle="supported" setid="virtualization">
          <version>SUSE Virtualization</version>
          <external>
            <link category="administration" gated="true">
              <language lang="en-us" default="1" title="SUSE VM Migration Toolkit">
                <url format="html" href="https://scc.suse.com/rancher-docs/rancherprime/latest/en/suse-virtualization/forklift-addon.html"/>
              </language>
            </link>
            <link category="administration">
              <language lang="en-us" default="1" title="SUSE Rancher Prime Integration">
                <url format="html" href="/cloudnative/virtualization/latest/en/rancher/rancher-integration.html"/>
              </language>
            </link>
            <link category="core-doc">
              <language lang="en-us" default="1" title="External Partner Link">
                <url format="html" href="https://docs.example.com/"/>
              </language>
            </link>
          </external>
        </docset>
      </product>
    </docservconfig>""")

    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = str(Path(tmpdir)) + "/"
        _ = xslt_transformer(
            v6_xml,
            outputdir=etree.XSLT.strparam(outdir),
            outputfile=etree.XSLT.strparam("portal.xml"),
        )
        result_tree = etree.parse(str(Path(tmpdir) / "portal.xml"))

        # The relative link is a prebuilt deliverable inside locale
        prebuilt_delivs = result_tree.xpath(
            "//resources/locale[@lang='en-us']/deliverable[@type='prebuilt']"
        )
        assert len(prebuilt_delivs) == 1
        assert (
            prebuilt_delivs[0].findtext(".//prebuilt/title")
            == "SUSE Rancher Prime Integration"
        )

        # The https:// links must be placed in <docset>/<external>/<link>
        external_links = result_tree.xpath("//docset/external/link")
        assert len(external_links) == 2

        # Verify the gated link preserves gated="true" and category
        gated_links = result_tree.xpath("//docset/external/link[@gated='true']")
        assert len(gated_links) == 1
        gated_link = gated_links[0]
        assert gated_link.attrib.get("category") == "cat.administration"
        assert (
            gated_link.find(".//url")
            .attrib.get("href")
            .startswith("https://scc.suse.com/")
        )
        assert (
            gated_link.findtext(".//descriptions/desc/title")
            == "SUSE VM Migration Toolkit"
        )


def test_prebuilt_translated_empty_locale_no_xrefs(xslt_transformer):
    """Test that prebuilt translated deliverables get an empty <locale> without xrefs."""
    v6_xml = etree.XML("""<docservconfig>
      <product productid="suma" schemaversion="6.0">
        <docset lifecycle="supported" setid="5.0">
          <version>5.0</version>
          <internal>
            <ref product="suma" docset="5.0" dc="DC-internal-ref"/>
          </internal>
          <external>
            <link category="core-doc" linkid="retail">
              <language lang="en-us" default="1" title="Retail Guide">
                <url format="html" href="/suma/5.0/en/suse-manager/retail/retail-overview.html"/>
              </language>
            </link>
            <link category="admin-doc" linkid="admin">
              <language lang="en-us" default="1" title="Admin Guide">
                <url format="html" href="/suma/5.0/en/suse-manager/admin/admin-overview.html"/>
              </language>
              <language lang="ja-jp" title="Admin Guide JA">
                <url format="html" href="/suma/5.0/ja/suse-manager/admin/admin-overview.html"/>
              </language>
              <language lang="zh-cn" title="Admin Guide ZH">
                <url format="html" href="/suma/5.0/zh/suse-manager/admin/admin-overview.html"/>
              </language>
            </link>
          </external>
        </docset>
      </product>
    </docservconfig>""")

    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = str(Path(tmpdir)) + "/"
        _ = xslt_transformer(
            v6_xml,
            outputdir=etree.XSLT.strparam(outdir),
            outputfile=etree.XSLT.strparam("portal.xml"),
        )
        result_tree = etree.parse(str(Path(tmpdir) / "portal.xml"))

        locales = result_tree.xpath("//resources/locale")
        locale_langs = [loc.attrib.get("lang") for loc in locales]
        assert locale_langs == ["en-us", "ja-jp", "zh-cn"]

        # English locale has deliverables (2 prebuilts) and 1 xref; no path attribute
        en_locale = locales[0]
        assert en_locale.attrib.get("path") is None
        prebuilt_delivs = en_locale.xpath("./deliverable[@type='prebuilt']")
        assert len(prebuilt_delivs) == 2
        xref_delivs = en_locale.xpath("./deliverable[@type='xref']")
        assert len(xref_delivs) == 1

        # Translated locales (ja-jp, zh-cn) must be empty: branch only, no deliverables, no xrefs
        ja_locale = locales[1]
        assert ja_locale.attrib.get("path") == "ja"
        assert ja_locale.findtext("branch") == "main"
        assert len(ja_locale.xpath("./deliverable")) == 0

        zh_locale = locales[2]
        # SUMA overrides zh-cn to zh_CN via _transformation-map
        assert zh_locale.attrib.get("path") == "zh_CN"
        assert zh_locale.findtext("branch") == "main"
        assert len(zh_locale.xpath("./deliverable")) == 0


def test_builddocs_with_prebuilt_translated_empty_locale_no_xrefs(xslt_transformer):
    """Test builddocs docsets with translated prebuilts produce empty <locale> without xrefs."""
    v6_xml = etree.XML("""<docservconfig>
      <product productid="suma" schemaversion="6.0">
        <docset lifecycle="supported" setid="5.0">
          <version>5.0</version>
          <builddocs>
            <git remote="https://github.com/example/repo.git"/>
            <language lang="en-us" default="1">
              <branch>main</branch>
              <deliverable>
                <dc>DC-guide</dc>
                <format html="1"/>
              </deliverable>
            </language>
            <language lang="de-de">
              <branch>maint-de</branch>
            </language>
          </builddocs>
          <internal>
            <ref product="suma" docset="5.0" dc="DC-internal-ref"/>
          </internal>
          <external>
            <link category="core-doc" linkid="retail">
              <language lang="en-us" default="1" title="Retail Guide">
                <url format="html" href="/suma/5.0/en/suse-manager/retail/retail-overview.html"/>
              </language>
              <language lang="de-de" title="Retail Guide DE">
                <url format="html" href="/suma/5.0/de/suse-manager/retail/retail-overview.html"/>
              </language>
              <language lang="ja-jp" title="Retail Guide JA">
                <url format="html" href="/suma/5.0/ja/suse-manager/retail/retail-overview.html"/>
              </language>
            </link>
          </external>
        </docset>
      </product>
    </docservconfig>""")

    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = str(Path(tmpdir)) + "/"
        _ = xslt_transformer(
            v6_xml,
            outputdir=etree.XSLT.strparam(outdir),
            outputfile=etree.XSLT.strparam("portal.xml"),
        )
        result_tree = etree.parse(str(Path(tmpdir) / "portal.xml"))

        locales = result_tree.xpath("//resources/locale")
        locale_langs = [loc.attrib.get("lang") for loc in locales]
        assert "en-us" in locale_langs
        assert "de-de" in locale_langs
        assert "ja-jp" in locale_langs

        # English locale has deliverables (dc + prebuilt) and 1 xref
        en_locale = result_tree.xpath("//resources/locale[@lang='en-us']")[0]
        assert len(en_locale.xpath("./deliverable[@type='dc']")) == 1
        assert len(en_locale.xpath("./deliverable[@type='prebuilt']")) == 1
        assert len(en_locale.xpath("./deliverable[@type='xref']")) == 1

        # Translated locales (de-de, ja-jp) must be empty: branch only, no deliverables, no xrefs
        for lang in ("de-de", "ja-jp"):
            trans_locale = result_tree.xpath(f"//resources/locale[@lang='{lang}']")[0]
            assert trans_locale.find("branch") is not None
            assert len(trans_locale.xpath("./deliverable")) == 0


def test_locale_path_cloudnative_and_sles(xslt_transformer):
    """Test that CloudNative uses short code 'zh' while non-prebuilt products omit path."""
    v6_xml = etree.XML("""<docservconfig>
      <product productid="cloudnative" schemaversion="6.0">
        <docset lifecycle="supported" setid="latest">
          <version>latest</version>
          <external>
            <link category="core-doc">
              <language lang="en-us" default="1" title="Cloud Guide">
                <url format="html" href="/cloudnative/en/guide.html"/>
              </language>
              <language lang="zh-cn" title="Cloud Guide ZH">
                <url format="html" href="/cloudnative/zh/guide.html"/>
              </language>
            </link>
          </external>
        </docset>
      </product>
      <product productid="sles" schemaversion="6.0">
        <docset lifecycle="supported" setid="15-SP5">
          <version>15 SP5</version>
          <builddocs>
            <git remote="https://github.com/example/repo.git"/>
            <language lang="en-us" default="1">
              <branch>main</branch>
              <deliverable><dc>DC-1</dc><format html="1"/></deliverable>
            </language>
            <language lang="de-de">
              <branch>main</branch>
              <deliverable><dc>DC-1</dc><format html="1"/></deliverable>
            </language>
          </builddocs>
        </docset>
      </product>
    </docservconfig>""")

    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = str(Path(tmpdir)) + "/"
        _ = xslt_transformer(
            v6_xml,
            outputdir=etree.XSLT.strparam(outdir),
            outputfile=etree.XSLT.strparam("portal.xml"),
        )
        result_tree = etree.parse(str(Path(tmpdir) / "portal.xml"))

        # CloudNative zh-cn gets path="zh" (default language part)
        cn_zh = result_tree.xpath(
            "//product[@xml:id='cloudnative']//resources/locale[@lang='zh-cn']"
        )[0]
        assert cn_zh.attrib.get("path") == "zh"

        # SLES non-English locale has no path attribute
        sles_de = result_tree.xpath(
            "//product[@xml:id='sles']//resources/locale[@lang='de-de']"
        )[0]
        assert sles_de.attrib.get("path") is None


def test_docset_with_only_internal_refs_gets_resources(xslt_transformer):
    """Test that a docset with only <internal> (no builddocs, no external) produces <resources>."""
    v6_xml = etree.XML("""<docservconfig>
      <product productid="trd" schemaversion="6.0">
        <docset lifecycle="supported" setid="ai">
          <version includes-productname="true">Artificial Intelligence</version>
          <descriptions treatment="prepend">
            <desc lang="en-us">
              <p>Documents published in this area focus on AI-based solutions.</p>
            </desc>
          </descriptions>
          <internal>
            <ref product="trd" docset="clearml" dc="DC-rc_suse-ai_clearml" titleformat="title subtitle"/>
            <ref product="trd" docset="contributors" dc="DC-suse-trd_contrib-guide" titleformat="title subtitle"/>
          </internal>
        </docset>
      </product>
    </docservconfig>""")

    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = str(Path(tmpdir)) + "/"
        _ = xslt_transformer(
            v6_xml,
            outputdir=etree.XSLT.strparam(outdir),
            outputfile=etree.XSLT.strparam("portal.xml"),
        )
        result_tree = etree.parse(str(Path(tmpdir) / "portal.xml"))

        # <resources> and <locale lang="en-us"> must be generated
        locales = result_tree.xpath("//product[@xml:id='trd']//resources/locale[@lang='en-us']")
        assert len(locales) == 1
        assert locales[0].findtext("branch") == "main"

        # The <internal> references must be converted to <deliverable type="xref">
        xrefs = locales[0].xpath("./deliverable[@type='xref']")
        assert len(xrefs) == 2
        linkends = [x.find("ref").attrib.get("linkend") for x in xrefs]
        assert "trd.clearml.dc-rc_suse-ai_clearml" in linkends
        assert "trd.contributors.dc-suse-trd_contrib-guide" in linkends

