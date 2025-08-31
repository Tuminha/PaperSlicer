from paperslicer.models import PaperRecord, Meta
from paperslicer.metadata import resolver as res


def test_ensure_abstract_from_crossref(monkeypatch):
    rec = PaperRecord(meta=Meta(source_path="p.pdf", title="T", doi="10.1/abc"), sections={})

    class DummyItem(dict):
        pass

    def fake_get_by_doi(doi, mailto=None, timeout=12):
        return DummyItem({
            "abstract": "<jats:p>Crossref abstract here.</jats:p>",
            "DOI": doi,
            "title": ["Title from Crossref"],
            "container-title": ["Journal from Crossref"],
        })

    monkeypatch.setattr(res.cr, "get_work_by_doi", fake_get_by_doi)
    # Ensure title search is not used
    monkeypatch.setattr(res.cr, "search_by_title", lambda t, mailto=None, timeout=12: None)
    ok = res.ensure_abstract(rec)
    assert ok is True
    assert rec.sections.get("abstract") == "Crossref abstract here."
    assert rec.meta.doi == "10.1/abc"
    assert rec.meta.title in ("T", "Title from Crossref")
    assert rec.meta.journal == "Journal from Crossref"


def test_ensure_abstract_from_pubmed_when_crossref_missing(monkeypatch):
    rec = PaperRecord(meta=Meta(source_path="p.pdf", title="T2", doi="10.2/def"), sections={})
    monkeypatch.setattr(res.cr, "get_work_by_doi", lambda *a, **k: None)
    monkeypatch.setattr(res.cr, "search_by_title", lambda *a, **k: None)
    monkeypatch.setattr(res.pm, "get_abstract", lambda **k: "PubMed abstract text")
    ok = res.ensure_abstract(rec)
    assert ok is True
    assert rec.sections.get("abstract") == "PubMed abstract text"

