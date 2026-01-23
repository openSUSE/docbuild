from io import StringIO

import pytest

import docbuild.models.metadata as metadata_module


def test_metadata_read_full(monkeypatch):
    fake_content = """# Example metadata file
productname=[15 SP6]SUSE Linux Enterprise Server
title = Example Title
subtitle = Example Subtitle
seo-title = Example SEO Title
seo-social-descr = Example Social Description
seo-description = Example Description
date = 2023-10-01
rootid = root123
series = Linux"""

    def fake_open(self, *args, **kwargs):
        return StringIO(fake_content)

    monkeypatch.setattr(metadata_module.Path, "open", fake_open)

    meta = metadata_module.Metadata()
    meta.read("dummy/path")
    assert meta.title == "Example Title"
    assert meta.subtitle == "Example Subtitle"
    assert meta.seo_title == "Example SEO Title"
    assert meta.seo_social_descr == "Example Social Description"
    assert meta.seo_description == "Example Description"
    assert meta.dateModified == "2023-10-01"
    assert meta.rootid == "root123"
    assert meta.series == "Linux"
    assert meta.products == [
        {"name": "SUSE Linux Enterprise Server", "versions": ["15 SP6"]}
    ]


@pytest.mark.parametrize(
    "option, key, value",
    [
        ("series", "series", None),
        ("date", "dateModified", ""),
        ("subtitle", "subtitle", ""),
        ("seo-title", "seo_title", None),
        ("seo-social-descr", "seo_social_descr", ""),
        ("seo-description", "seo_description", ""),
        ("rootid", "rootid", None),
        ("tasks", "tasks", []),
        ("productname", "products", []),
        ("task", "tasks", [""]),
    ],
)
def test_metadata_without_key(option, key, value, monkeypatch):
    fake_content = f"""# Example metadata file\n{option} =\n"""

    def fake_open(self, *args, **kwargs):
        return StringIO(fake_content)

    monkeypatch.setattr(metadata_module.Path, "open", fake_open)

    meta = metadata_module.Metadata()
    meta.read("dummy/path")
    assert getattr(meta, key) == value
