from datetime import date

from docbuild.models.manifest import Document


def test_document_from_metadata_payload_full() -> None:
    payload = {
        "docs": [
            {
                "title": "Example Title",
                "subtitle": "Example Subtitle",
                "description": "Example Description",
                "dateModified": "2023-10-01",
                "rootid": "root123",
            }
        ],
        "seo-title": "Example SEO Title",
        "seo-social-descr": "Example Social Description",
        "seo-description": "Example SEO Description",
        "series": "Linux",
        "tasks": ["Task A"],
        "products": [
            {
                "name": "SUSE Linux Enterprise Server",
                "versions": ["15 SP6"],
            }
        ],
    }

    document = Document.from_metadata_payload(
        payload,
        dcfile="DC-Doc",
        lang="en-us",
    )

    assert document.docs[0].title == "Example Title"
    assert document.docs[0].subtitle == "Example Subtitle"
    assert document.docs[0].description == "Example Description"
    assert document.docs[0].rootid == "root123"
    assert document.docs[0].datemodified == date(2023, 10, 1)
    assert document.docs[0].dcfile == "DC-Doc"
    assert document.docs[0].lang == "en-us"
    assert document.tasks == ["Task A"]
    assert document.products[0].name == "SUSE Linux Enterprise Server"
    assert document.products[0].versions == ["15 SP6"]


def test_document_from_metadata_payload_defaults() -> None:
    payload = {
        "docs": [{"title": "Doc"}],
        "description": "Fallback description",
        "task": "",
        "productname": "",
    }

    document = Document.from_metadata_payload(
        payload,
        dcfile="DC-Doc",
        lang="en-us",
    )

    assert document.docs[0].description == "Fallback description"
    assert document.tasks == []
    assert document.products == []
