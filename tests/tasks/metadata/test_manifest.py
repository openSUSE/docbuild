"""Unit tests for docbuild.tasks.metadata.manifest."""

import json
from pathlib import Path
from unittest.mock import patch

from lxml import etree  # type: ignore
import pytest

from docbuild.models.deliverable import Deliverable
from docbuild.models.doctype import Doctype
import docbuild.tasks.metadata.manifest as manifest_pkg
from docbuild.tasks.metadata.manifest import (
    configured_languages_from_docset,
    merge_descriptions_with_treatment,
    store_productdocset_json,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def deliverable() -> Deliverable:
    """Provide a Deliverable built from a minimal docservconfig XML."""
    xml_string = """
    <docservconfig>
      <product id="sles">
        <docset id="sles.15-sp7" path="15-SP7">
          <resources>
             <git remote="https://github.com/SUSE/doc-sle.git"/>
             <locale lang="en-us">
                <branch>main</branch>
                <subdir>l10n/sles/en-us</subdir>
                <deliverable>
                    <dc file="DC-SLES-deployment">
                        <format html="1" pdf="1" single-html="0"/>
                    </dc>
                </deliverable>
             </locale>
          </resources>
        </docset>
      </product>
    </docservconfig>
    """
    root = etree.fromstring(xml_string)
    locale_node = root.find(".//locale")
    return Deliverable(locale_node.find("deliverable"))


@pytest.fixture
def stitchnode(deliverable: Deliverable) -> etree._ElementTree:
    """Minimal stitched docservconfig ElementTree matching the deliverable fixture."""
    prod_node = etree.Element(
        "product",
        id=deliverable.xml.productid,
        productid=deliverable.xml.productid,
    )
    etree.SubElement(prod_node, "name").text = "SUSE Linux Enterprise Server"
    etree.SubElement(prod_node, "acronym").text = "SLES"
    etree.SubElement(
        prod_node,
        "docset",
        id=deliverable.xml.docsetid,
        path=deliverable.xml.docsetid,
        setid=deliverable.xml.docsetid,
        productid=deliverable.xml.productid,
    )
    root = etree.Element("docservconfig")
    root.append(prod_node)
    return etree.ElementTree(root)


@pytest.fixture
def test_dirs(tmp_path: Path) -> dict[str, Path]:
    """Provide mock directories needed for manifest creation."""
    meta_cache_dir = tmp_path / "cache" / "metadata"
    meta_cache_dir.mkdir(parents=True)
    json_cache_dir = tmp_path / "cache" / "json"
    json_cache_dir.mkdir(parents=True)
    return {
        "meta_cache_dir": meta_cache_dir,
        "json_cache_dir": json_cache_dir,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_store_productdocset_json_merges_and_writes(
    test_dirs: dict[str, Path],
    deliverable: Deliverable,
    stitchnode: etree._ElementTree,
):
    """Merge docs from metadata files and write a product/docset JSON file."""
    meta_cache_dir = test_dirs["meta_cache_dir"]
    json_cache_dir = test_dirs["json_cache_dir"]

    meta_file = meta_cache_dir / "meta1.json"
    doc_content = {
        "docs": [
            {
                "title": "Doc1",
                "dcfile": "DC-Doc1.xml",
                "lang": "en-us",
                "description": "A test document.",
                "dateModified": "2024-01-01",
                "format": {"html": "path/to/html"},
            }
        ],
        "category": "cat.administration",
    }
    meta_file.write_text(json.dumps(doc_content), encoding="utf-8")

    doctype = Doctype.from_str(
        f"{deliverable.xml.productid}/{deliverable.xml.docsetid}/{deliverable.xml.lang}"
    )

    with patch.object(
        manifest_pkg,
        "collect_files_flat",
        return_value=[(doctype, deliverable.xml.docsetid, [Path("meta1.json")])],
    ):
        store_productdocset_json(
            doctypes=[doctype],
            stitchnode=stitchnode,
            meta_cache_dir=meta_cache_dir,
            json_cache_dir=json_cache_dir,
        )

    out_file = (
        json_cache_dir
        / deliverable.xml.productid
        / f"{deliverable.xml.docsetid}.json"
    )
    assert out_file.exists()
    merged = json.loads(out_file.read_text(encoding="utf-8"))
    assert "documents" in merged
    assert merged["documents"][0]["docs"][0]["title"] == "Doc1"
    assert merged["documents"][0]["category"] == "cat.administration"
    assert "category" not in merged["documents"][0]["docs"][0]
    assert "hide-productname" in merged


def test_store_productdocset_json_warns_on_empty_metadata(
    test_dirs: dict[str, Path],
    deliverable: Deliverable,
    stitchnode: etree._ElementTree,
):
    """If a metadata file contains an empty object, an error is logged."""
    meta_cache_dir = test_dirs["meta_cache_dir"]
    json_cache_dir = test_dirs["json_cache_dir"]

    (meta_cache_dir / "empty.json").write_text("{}", encoding="utf-8")

    doctype = Doctype.from_str(
        f"{deliverable.xml.productid}/{deliverable.xml.docsetid}/{deliverable.xml.lang}"
    )

    with (
        patch.object(
            manifest_pkg,
            "collect_files_flat",
            return_value=[(doctype, deliverable.xml.docsetid, [Path("empty.json")])],
        ),
        patch.object(manifest_pkg, "log") as mock_log,
    ):
        store_productdocset_json(
            doctypes=[doctype],
            stitchnode=stitchnode,
            meta_cache_dir=meta_cache_dir,
            json_cache_dir=json_cache_dir,
        )

    mock_log.error.assert_called_with("Empty metadata file %s", Path("empty.json"))


def test_store_productdocset_json_handles_read_error(
    test_dirs: dict[str, Path],
    deliverable: Deliverable,
    stitchnode: etree._ElementTree,
):
    """If a metadata file contains invalid JSON, the error is caught and logged."""
    meta_cache_dir = test_dirs["meta_cache_dir"]
    json_cache_dir = test_dirs["json_cache_dir"]

    (meta_cache_dir / "bad.json").write_text("{ not json }", encoding="utf-8")

    doctype = Doctype.from_str(
        f"{deliverable.xml.productid}/{deliverable.xml.docsetid}/{deliverable.xml.lang}"
    )

    with (
        patch.object(
            manifest_pkg,
            "collect_files_flat",
            return_value=[(doctype, deliverable.xml.docsetid, [Path("bad.json")])],
        ),
        patch.object(manifest_pkg, "log") as mock_log,
    ):
        store_productdocset_json(
            doctypes=[doctype],
            stitchnode=stitchnode,
            meta_cache_dir=meta_cache_dir,
            json_cache_dir=json_cache_dir,
        )

    mock_log.error.assert_called()


@pytest.mark.parametrize(
    ("treatment", "docset_lang", "expected_lang", "expected_description"),
    [
        ("append", "en-us", "en-us", "<p>global</p><p>local</p>"),
        ("prepend", "en-us", "en-us", "<p>local</p><p>global</p>"),
        ("replace", "de-de", "de-de", "<p>local</p>"),
    ],
)
def test_merge_descriptions_with_treatment(
    treatment: str,
    docset_lang: str,
    expected_lang: str,
    expected_description: str,
) -> None:
    """Merges descriptions according to append/prepend/replace treatment."""
    product_desc = [
        manifest_pkg.Description(lang="en-us", default=True, description="<p>global</p>")
    ]
    docset_desc = [
        manifest_pkg.Description(lang=docset_lang, default=False, description="<p>local</p>")
    ]

    merged = merge_descriptions_with_treatment(
        product_desc,
        docset_desc,
        treatment=treatment,
    )

    assert len(merged) == 1
    assert str(merged[0].lang) == expected_lang
    assert merged[0].description == expected_description


def test_store_productdocset_json_applies_docset_description_treatment(
    tmp_path: Path,
) -> None:
    """Docset descriptions with treatment=append are merged with product descriptions."""
    xml_string = """
    <docservconfig>
      <product id="sles">
        <name>SUSE Linux Enterprise Server</name>
        <acronym>SLES</acronym>
        <descriptions>
          <desc lang="en-us"><p>Global</p></desc>
        </descriptions>
        <docset id="sles.16.0" path="16.0" lifecycle="supported">
          <descriptions treatment="append">
            <desc lang="en-us"><p>Local</p></desc>
          </descriptions>
          <resources>
            <git remote="https://github.com/SUSE/doc-sle.git"/>
            <locale lang="en-us"/>
          </resources>
        </docset>
      </product>
    </docservconfig>
    """
    stitchnode_local = etree.ElementTree(etree.fromstring(xml_string))
    doctype = Doctype.from_str("sles/16.0/en-us")
    meta_cache_dir = tmp_path / "cache" / "metadata"
    meta_cache_dir.mkdir(parents=True, exist_ok=True)
    json_cache_dir = tmp_path / "cache" / "json"
    json_cache_dir.mkdir(parents=True, exist_ok=True)

    with patch.object(
        manifest_pkg,
        "collect_files_flat",
        return_value=[(doctype, "16.0", [])],
    ):
        store_productdocset_json(
            doctypes=[doctype],
            stitchnode=stitchnode_local,
            meta_cache_dir=meta_cache_dir,
            json_cache_dir=json_cache_dir,
        )

    out_file = json_cache_dir / "sles" / "16.0.json"
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["descriptions"][0]["description"] == "<p>Global</p><p>Local</p>"


def test_store_productdocset_json_expands_docset_wildcard(tmp_path: Path) -> None:
    """A wildcard doctype writes one JSON file per configured docset."""
    xml_string = """
    <docservconfig>
      <product id="appliance">
        <name>Appliance building</name>
        <acronym>appliance</acronym>
        <docset id="appliance.keg-2" path="keg-2" lifecycle="supported">
          <resources>
            <git remote="https://github.com/SUSE-Enceladus/keg.git"/>
            <locale lang="en-us"/>
          </resources>
        </docset>
        <docset id="appliance.kiwi-9" path="kiwi-9" lifecycle="supported">
          <resources>
            <git remote="https://github.com/OSInside/kiwi-suse-doc.git"/>
            <locale lang="en-us"/>
          </resources>
        </docset>
      </product>
    </docservconfig>
    """
    stitchnode_local = etree.ElementTree(etree.fromstring(xml_string))

    meta_cache_dir = tmp_path / "cache" / "metadata"
    json_cache_dir = tmp_path / "cache" / "json"
    json_cache_dir.mkdir(parents=True, exist_ok=True)

    for docset, dcfile, title in (
        ("keg-2", "DC-keg", "Keg"),
        ("kiwi-9", "DC-kiwi", "KIWI"),
    ):
        outdir = meta_cache_dir / "en-us" / "appliance" / docset
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / dcfile).write_text(
            json.dumps(
                {
                    "docs": [
                        {
                            "title": title,
                            "dcfile": f"{dcfile}.xml",
                            "lang": "en-us",
                            "description": f"The {title} guide.",
                            "dateModified": "2024-01-01",
                            "format": {"html": "path/to/html"},
                        }
                    ],
                    "category": "cat.administration",
                }
            ),
            encoding="utf-8",
        )

    store_productdocset_json(
        doctypes=[Doctype.from_str("appliance/*/*")],
        stitchnode=stitchnode_local,
        meta_cache_dir=meta_cache_dir,
        json_cache_dir=json_cache_dir,
    )

    jsondir = json_cache_dir / "appliance"
    assert sorted(p.name for p in jsondir.glob("*.json")) == [
        "keg-2.json",
        "kiwi-9.json",
    ]

    keg = json.loads((jsondir / "keg-2.json").read_text(encoding="utf-8"))
    assert keg["productname"] == "Appliance building"
    assert [doc["docs"][0]["title"] for doc in keg["documents"]] == ["Keg"]


def test_configured_languages_from_docset_preserves_order_and_uniqueness() -> None:
    """Extract configured locale languages in order while removing duplicates."""
    docset_node = etree.fromstring(
        """
        <docset>
          <resources>
            <locale lang="en-us"/>
            <locale lang="de-de"/>
            <locale lang="fr-fr"/>
          </resources>
        </docset>
        """
    )

    languages = configured_languages_from_docset(docset_node)

    assert [str(lang) for lang in languages] == ["en-us", "de-de", "fr-fr"]
