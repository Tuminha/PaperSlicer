from paperslicer.pipeline import Pipeline


def _tei_bytes() -> bytes:
    return ("""
    <TEI xmlns=\"http://www.tei-c.org/ns/1.0\">
      <teiHeader>
        <fileDesc>
          <titleStmt><title>Pipeline Title</title></titleStmt>
          <sourceDesc>
            <biblStruct>
              <analytic/>
              <monogr><title>Pipeline Journal</title></monogr>
              <idno type=\"DOI\">10.55/xyz</idno>
            </biblStruct>
          </sourceDesc>
        </fileDesc>
        <profileDesc><abstract>TEI abstract.</abstract></profileDesc>
      </teiHeader>
      <text><body><div><head>Introduction</head><p>text</p></div></body></text>
    </TEI>
    """).encode("utf-8")


def test_pipeline_uses_grobid_and_resolves_abstract(monkeypatch, tmp_path):
    # Pretend GROBID is available
    from paperslicer import grobid as gmod

    class DummyMgr:
        def is_available(self, timeout_s: float = 1.0) -> bool:
            return True

        def start(self, *a, **k):
            return True

    monkeypatch.setattr(gmod.manager, "GrobidManager", lambda *a, **k: DummyMgr())

    class DummyCli:
        def process_fulltext(self, pdf_path: str, save_dir=None, **kwargs):
            p = tmp_path / "x.tei.xml"
            p.write_bytes(_tei_bytes())
            return _tei_bytes(), str(p)

    monkeypatch.setattr(gmod.client, "GrobidClient", lambda *a, **k: DummyCli())

    # Track resolver call
    called = {"ok": False}

    def fake_ensure(rec, mailto=None):
        called["ok"] = True
        return True

    from paperslicer.metadata import resolver as res
    monkeypatch.setattr(res, "ensure_abstract", fake_ensure)

    pipe = Pipeline(try_start_grobid=False, xml_save_dir=str(tmp_path), export_images=False)
    rec = pipe.process("/path/to/file.pdf")
    assert rec.meta.title == "Pipeline Title"
    assert "introduction" in rec.sections
    assert called["ok"] is True

