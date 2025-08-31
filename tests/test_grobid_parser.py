import os
from paperslicer.grobid.parser import tei_to_record


def _sample_tei() -> bytes:
    return ("""
    <TEI xmlns=\"http://www.tei-c.org/ns/1.0\">
      <teiHeader>
        <fileDesc>
          <titleStmt>
            <title>Sample Title</title>
          </titleStmt>
          <sourceDesc>
            <biblStruct>
              <analytic>
                <author><persName><forename>A</forename><surname>B</surname></persName></author>
              </analytic>
              <monogr><title>Journal Name</title></monogr>
              <idno type=\"DOI\">10.1234/abc</idno>
            </biblStruct>
          </sourceDesc>
        </fileDesc>
        <profileDesc>
          <abstract>This is an abstract in the TEI.</abstract>
        </profileDesc>
      </teiHeader>
      <text>
        <body>
          <div><head>Introduction</head><p>Intro content.</p></div>
          <div><head>Methods</head><p>Method content.</p></div>
          <div><head>Results</head><p>Results content.</p></div>
          <div><head>Conclusion</head><p>Conclusion content.</p></div>
          <figure><label>Fig 1</label><figDesc>Figure 1 desc.</figDesc></figure>
          <table><head><label>Table 1</label> Table 1 desc.</head></table>
        </body>
      </text>
    </TEI>
    """).encode("utf-8")


def test_tei_to_record_basic_mapping():
    tei = _sample_tei()
    rec = tei_to_record(tei, pdf_path="/path/to/file.pdf")
    assert rec.meta.title == "Sample Title"
    assert rec.meta.journal == "Journal Name"
    assert rec.meta.doi == "10.1234/abc"
    assert "abstract" in rec.sections and "TEI".lower() not in rec.sections["abstract"].lower()  # plain text
    # Section canonicalization
    assert "introduction" in rec.sections
    assert "materials_and_methods" in rec.sections
    assert "results" in rec.sections
    assert "conclusions" in rec.sections
    # Media capture
    assert len(rec.figures) >= 1
    assert len(rec.tables) >= 1

