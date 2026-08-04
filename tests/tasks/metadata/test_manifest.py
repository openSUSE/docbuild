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


def test_configured_languages_from_docset_preserves_order_and_uniqueness() -> None:
    """Extract configured locale languages in order while removing duplicates."""
    docset_node = etree.fromstring(
        """
        <docset>
          <resources>
            <locale lang="en-us"/>
            <locale lang="de-de"/>
            <locale lang="en-us"/>
            <locale lang=""/>
            <locale/>
            <locale lang="fr-fr"/>
          </resources>
        </docset>
        """
    )

    languages = configured_languages_from_docset(docset_node)

    assert [str(lang) for lang in languages] == ["en-us", "de-de", "fr-fr"]
