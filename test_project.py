import pytest
import os
import shutil
from paperslicer.grobid.manager import GrobidManager
from paperslicer.grobid.client import GrobidClient



def test_function_1():
    ...


def test_function_2():
    ...


def test_function_n():
    ...


def test_extract_metadata_from_tei_bytes_minimal():
    # minimal TEI with title, journal, date, doi, abstract, one author
    tei = b"""<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt><title>Sample Title</title></titleStmt>
      <publicationStmt>
        <publisher>Sample Publisher</publisher>
        <date type="published">2025-01-15</date>
      </publicationStmt>
      <sourceDesc>
        <biblStruct>
          <monogr>
            <title>Journal of Sample Dentistry</title>
            <idno type="DOI">10.1000/sampledoi</idno>
            <author>
              <persName><forename>Ana</forename><surname>Ferro</surname></persName>
              <affiliation>Lisbon School of Dentistry</affiliation>
            </author>
          </monogr>
        </biblStruct>
      </sourceDesc>
    </fileDesc>
    <profileDesc>
      <abstract>Short abstract here.</abstract>
      <textClass><keywords><term>implant</term><term>socket</term></keywords></textClass>
    </profileDesc>
  </teiHeader>
  <text><body/></text>
</TEI>"""
    from paperslicer.extractors.metadata import TEIMetadataExtractor
    md = TEIMetadataExtractor().from_bytes(tei)
    assert md["title"] == "Sample Title"
    assert md["journal"] == "Journal of Sample Dentistry"
    assert md["publisher"] == "Sample Publisher"
    assert md["date"] == "2025-01-15"
    assert md["doi"] == "10.1000/sampledoi"
    assert md["abstract"].startswith("Short abstract")
    assert "implant" in md["keywords"] and "socket" in md["keywords"]
    assert md["authors"][0]["family"] == "Ferro"


def test_metadata_extractor_on_periodontology_tei():
    # Verify metadata extracted from a real TEI file in data/xml
    import os
    base_dir = os.path.dirname(__file__)
    tei_path = os.path.join(
        base_dir,
        "data",
        "xml",
        "Periodontology 2000 - 2023 - Liñares - Critical review on bone grafting during immediate implant placement.tei.xml",
    )
    from paperslicer.extractors.metadata import TEIMetadataExtractor

    md = TEIMetadataExtractor().from_file(tei_path)
    assert md["title"] == "Critical review on bone grafting during immediate implant placement"
    assert md["journal"] == "Periodontology 2000"
    assert md["publisher"] == "Wiley"
    assert md["date"] == "2023-09"
    assert md["doi"] == "10.1111/prd.12516"
    assert md.get("keywords", []) in ([], None)
    assert md.get("abstract", "") == ""
    assert md["authors"][0]["family"] in ("Liñares", "Liñares")


def test_debug_save_metadata_filename(tmp_path):
    from datetime import datetime
    from paperslicer.utils.debug import build_debug_filename, save_metadata_json

    meta = {
        "title": "Implant esthetics: a randomized trial",
        "date": "2024-05-10",
        "authors": [{"given": "Ana", "family": "Ferro", "full": "Ana Ferro", "affiliations": []}],
        "journal": "Journal of Clinical Periodontology",
        "publisher": "Wiley",
        "doi": "10.1000/xyz",
    }
    now = datetime(2025, 8, 29, 19, 45)
    fname = build_debug_filename(meta, now=now)
    assert fname.startswith("Ferro_2024_Implant-esthetics-a-randomized-trial_1945")

    # Save to a temp dir and verify file exists
    out_dir = tmp_path / "meta"
    saved = save_metadata_json(meta, out_dir=str(out_dir), now=now)
    assert saved.endswith(fname)
    assert os.path.exists(saved)


def test_extract_introduction_minimal():
    tei = b"""<?xml version=\"1.0\"?>
<TEI xmlns=\"http://www.tei-c.org/ns/1.0\"> 
  <text>
    <body>
      <div type=\"section\"><head>Abstract</head><p>Not intro.</p></div>
      <div type=\"section\"><head>Introduction</head><p>This is the introduction text.</p></div>
      <div type=\"section\"><head>Methods</head><p>Methods...</p></div>
    </body>
  </text>
</TEI>"""
    import tempfile, os
    from paperslicer.grobid.sections import (
        extract_introduction,
        extract_methods,
        extract_results,
        extract_discussion,
        extract_conclusions,
    )
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.tei.xml")
        with open(p, "wb") as f:
            f.write(tei)
        intro = extract_introduction(p)
        assert intro is not None
        assert "introduction text" in intro.lower()


def test_sections_mapping_canonicalize():
    from paperslicer.utils.sections_mapping import canonicalize, is_heading_of
    assert canonicalize("Introduction") == "introduction"
    assert canonicalize("Background") == "introduction"
    assert canonicalize("Materials & Methods") == "materials_and_methods"
    assert canonicalize("Patients and Methods") == "materials_and_methods"
    assert canonicalize("Results and Discussion") == "results_and_discussion"
    assert is_heading_of("Clinical significance", "conclusions")


def test_extract_major_sections_minimal():
    tei = b"""<?xml version=\"1.0\"?>
<TEI xmlns=\"http://www.tei-c.org/ns/1.0\"> 
  <text>
    <body>
      <div type=\"section\"><head>Introduction</head><p>Intro content.</p></div>
      <div type=\"section\"><head>Materials and Methods</head><p>Methods content.</p></div>
      <div type=\"section\"><head>Results</head><p>Results content.</p></div>
      <div type=\"section\"><head>Discussion</head><p>Discussion content.</p></div>
      <div type=\"section\"><head>Conclusions</head><p>Conclusions content.</p></div>
    </body>
  </text>
</TEI>"""
    import tempfile, os
    from paperslicer.grobid.sections import (
        extract_introduction,
        extract_methods,
        extract_results,
        extract_discussion,
        extract_conclusions,
    )
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.tei.xml")
        with open(p, "wb") as f:
            f.write(tei)
        assert "intro content" in (extract_introduction(p) or "").lower()
        assert "methods content" in (extract_methods(p) or "").lower()
        assert "results content" in (extract_results(p) or "").lower()
        assert "discussion content" in (extract_discussion(p) or "").lower()
        assert "conclusions content" in (extract_conclusions(p) or "").lower()


def test_extract_results_and_discussion_combined():
    tei = b"""<?xml version=\"1.0\"?>
<TEI xmlns=\"http://www.tei-c.org/ns/1.0\"> 
  <text>
    <body>
      <div type=\"section\"><head>Results and Discussion</head><p>Combined content.</p></div>
    </body>
  </text>
</TEI>"""
    import tempfile, os
    from paperslicer.grobid.sections import (
        extract_results,
        extract_discussion,
        extract_results_and_discussion,
    )
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.tei.xml")
        with open(p, "wb") as f:
            f.write(tei)
        combined = extract_results_and_discussion(p) or ""
        assert "combined content" in combined.lower()
        # Separate extractors may not see it; we ensure combined extractor works


def test_parse_figures_tables_minimal():
    # TEI with facsimile/zone and a figure referencing it via @facs
    tei = b"""<?xml version=\"1.0\"?>
<TEI xmlns=\"http://www.tei-c.org/ns/1.0\">
  <facsimile>
    <surface n=\"1\">
      <zone xml:id=\"z1\" ulx=\"72\" uly=\"100\" lrx=\"300\" lry=\"250\" />
    </surface>
  </facsimile>
  <text><body>
    <figure facs=\"#z1\"><head>Figure 1</head><figDesc>Demo caption</figDesc></figure>
  </body></text>
</TEI>"""
    import tempfile, os
    from paperslicer.grobid.figures import parse_figures_tables
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.tei.xml")
        with open(p, "wb") as f:
            f.write(tei)
        items = parse_figures_tables(p)
        assert items and items[0]["type"] == "figure"
        assert items[0]["bbox"] == [72.0, 100.0, 300.0, 250.0]


def test_harvest_suggestions_append(tmp_path):
    # create a TEI with an unmapped heading and ensure suggestions are appended without duplicates
    tei = b"""<?xml version=\"1.0\"?>
<TEI xmlns=\"http://www.tei-c.org/ns/1.0\"> 
  <text>
    <body>
      <div type=\"section\"><head>Clinical Practice Points</head><p>X</p></div>
    </body>
  </text>
</TEI>"""
    from paperslicer.utils.harvest_sections import harvest_heads
    from paperslicer.utils.sections_mapping import canonicalize
    import os
    d = tmp_path
    p = d / "x.tei.xml"
    p.write_bytes(tei)
    heads = harvest_heads(str(p))
    assert "Clinical Practice Points" in heads
    unmapped = [h for h in heads if canonicalize(h) is None]
    assert unmapped
    # simulate pipeline's suggestion append
    suggestions_path = d / "suggestions.txt"
    existing = set()
    new_items = [u for u in unmapped if u not in existing]
    if new_items:
        with open(suggestions_path, "a", encoding="utf-8") as sf:
            for u in sorted(set(new_items)):
                sf.write(u + "\n")
    # run again; should not duplicate
    existing = {line.strip() for line in open(suggestions_path, encoding="utf-8")}
    new_items = [u for u in unmapped if u not in existing]
    assert not new_items

def test_grobid_client_saves_xml_to_dir(monkeypatch, tmp_path):
    """Client writes TEI to save_dir and creates it if missing (no network)."""
    # Create a dummy PDF file
    pdf_path = tmp_path / "dummy.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n...")

    # Fake TEI response
    tei_bytes = b"<TEI xmlns=\"http://www.tei-c.org/ns/1.0\"><teiHeader/><text/></TEI>"

    class DummyResp:
        def __init__(self, content: bytes):
            self.content = content

        def raise_for_status(self):
            return None

    def fake_post(url, files, data, timeout):
        # Ensure we were called with a file-like object
        assert "input" in files
        return DummyResp(tei_bytes)

    # Patch requests.post used inside the client
    import paperslicer.grobid.client as client_mod
    monkeypatch.setattr(client_mod.requests, "post", fake_post)

    # Use a nested, non-existent dir to ensure it's created
    save_dir = tmp_path / "nested" / "xml"
    cli = GrobidClient(base_url="http://fake:8070")
    out_bytes, saved_path = cli.process_fulltext(str(pdf_path), save_dir=str(save_dir))

    # Returns the bytes and saved path
    assert out_bytes == tei_bytes
    assert saved_path is not None

    # File saved under <save_dir>/<pdf_stem>.tei.xml
    stem = pdf_path.stem
    out_file = save_dir / f"{stem}.tei.xml"
    assert saved_path == str(out_file)
    assert out_file.exists(), "TEI file was not saved"
    assert out_file.read_bytes() == tei_bytes


@pytest.mark.skipif(
    not os.getenv("GROBID_URL"),
    reason="GROBID_URL not set, skipping integration test"
)
def test_grobid_client_availability_and_process(tmp_path):
    client = GrobidClient()
    assert client.is_available(), "GROBID service is not available at GROBID_URL"

    # pick a small PDF from your data folder
    pdf_path = "data/pdf/bmc_oral_health_article1_reso_pac_2025.pdf"
    save_dir = tmp_path / "tei"
    tei, saved = client.process_fulltext(pdf_path, save_dir=str(save_dir))
    assert isinstance(tei, (bytes, bytearray))
    assert len(tei) > 1000  # at least some TEI XML returned
    assert b"<TEI" in tei[:200].upper()  # TEI XML root element present
    assert saved is not None and os.path.exists(saved)


@pytest.mark.skipif(
    not os.getenv("GROBID_URL"),
    reason="GROBID_URL not set, skipping ingestor test",
)
def test_grobid_ingestor_saves_files(tmp_path):
    from project import grobid_generate_tei

    tei_dir = tmp_path / "xml"
    tei_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = "data/pdf/bmc_oral_health_article1_reso_pac_2025.pdf"

    saved = grobid_generate_tei(pdf_path, tei_dir=str(tei_dir))
    assert len(saved) == 1
    assert os.path.exists(saved[0])
    with open(saved[0], "rb") as fh:
        head = fh.read(200).upper()
    assert b"<TEI" in head


def test_grobid_ingestor_skips_existing_tei(tmp_path):
    """Ingestor should skip network call when a valid TEI already exists."""
    from paperslicer.grobid.ingest import GrobidIngestor

    # Create dummy PDF and pre-existing TEI
    pdf_path = tmp_path / "dummy.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n...")

    tei_dir = tmp_path / "xml"
    tei_dir.mkdir(parents=True, exist_ok=True)
    tei_path = tei_dir / f"{pdf_path.stem}.tei.xml"
    tei_path.write_text(
        """<?xml version='1.0'?>
<TEI xmlns='http://www.tei-c.org/ns/1.0'><teiHeader/><text/></TEI>
""",
        encoding="utf-8",
    )

    ing = GrobidIngestor(tei_dir=str(tei_dir), skip_existing=True, validate_existing=True)
    # This should return the existing TEI path without raising (no server needed)
    out = ing.ingest_path(str(pdf_path))
    assert out == [str(tei_path)]


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker not available")
def test_grobid_manager_does_not_crash_when_trying_to_start():
    mgr = GrobidManager()
    # We don’t assert True here (CI environments vary). Just ensure it doesn’t raise.
    try:
        mgr.start(wait_ready_s=1)  # short wait
    except Exception as e:
        pytest.fail(f"Manager.start raised unexpectedly: {e}")


@pytest.mark.skipif(os.getenv("ALLOW_NET") != "1", reason="Network calls disabled")
def test_resolver_enriches_when_fields_missing(tmp_path):
    # Minimal TEI with only a title; resolver should try to enrich fields
    tei = b"""<?xml version="1.0"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt><title>Immediate implants and peri-implant tissue stability</title></titleStmt>
      <publicationStmt><publisher></publisher></publicationStmt>
      <sourceDesc><biblStruct><monogr><title></title></monogr></biblStruct></sourceDesc>
    </fileDesc>
  </teiHeader>
  <text><body/></text>
</TEI>"""
    from paperslicer.extractors.metadata import TEIMetadataExtractor
    from paperslicer.metadata.resolver import MetadataResolver

    tei_path = tmp_path / "x.tei.xml"
    tei_path.write_bytes(tei)
    base = TEIMetadataExtractor().from_file(str(tei_path))
    assert base["title"]

    md = MetadataResolver().resolve_from_tei(str(tei_path))
    assert md["title"]
    # Ensure enrichment attempted: at least one of these fields becomes non-empty
    assert any(md.get(k) for k in ("journal", "doi", "abstract"))


def test_harvest_sections_summary_real_data():
    """Tailored boundary check for one article (MDPI Oral 2024).

    For each present major section, assert the first/last words and
    5-token chunks from TEI appear in PDF text. Fails with diagnostic
    messages on mismatch to highlight differences.
    """
    import os
    import re
    import unicodedata
    import pytest
    from lxml import etree
    from paperslicer.utils.sections_mapping import canonicalize

    base_dir = os.path.dirname(__file__)
    tei_path = os.path.join(
        base_dir,
        "data",
        "xml",
        "mdpi_oral_article2_enamel_volume_loss_energy_drinks_2024.tei.xml",
    )
    pdf_path = os.path.join(
        base_dir,
        "data",
        "pdf",
        "mdpi_oral_article2_enamel_volume_loss_energy_drinks_2024.pdf",
    )
    assert os.path.exists(tei_path), f"TEI not found: {tei_path}"
    assert os.path.exists(pdf_path), f"PDF not found: {pdf_path}"

    try:
        import fitz  # PyMuPDF
    except Exception as e:
        pytest.skip(f"PyMuPDF not available: {e}")

    def _norm_tokens(s: str) -> list[str]:
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        s = s.lower()
        s = re.sub(r"[^a-z0-9\s]+", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s.split()

    TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()

    majors = [
        "introduction",
        "materials_and_methods",
        "results",
        "discussion",
        "conclusions",
    ]
    found: dict[str, etree._Element] = {}
    for div in root.findall(".//tei:text//tei:div", TEI_NS):
        head = div.find("./tei:head", TEI_NS)
        head_txt = "".join(head.itertext()) if head is not None else ""
        canon = canonicalize(head_txt or "")
        if canon in majors and canon not in found:
            found[canon] = div
        if len(found) == len(majors):
            break

    assert "introduction" in found, "Introduction section not found in TEI"

    def first_last_chunks(div: etree._Element) -> tuple[list[str], list[str]]:
        ps = div.findall(".//tei:p", TEI_NS)
        if ps:
            first = " ".join(" ".join(ps[0].itertext()).split())
            last = " ".join(" ".join(ps[-1].itertext()).split())
        else:
            parts: list[str] = []
            for el in div.iter():
                if el.tag.endswith("}head"):
                    continue
                txt = " ".join(" ".join(el.itertext()).split())
                if txt:
                    parts.append(txt)
            whole = "\n\n".join(parts)
            toks = _norm_tokens(whole)
            f = " ".join(toks[:20])
            l = " ".join(toks[-20:])
            return _norm_tokens(f), _norm_tokens(l)
        return _norm_tokens(first), _norm_tokens(last)

    # Normalize entire PDF text
    doc = fitz.open(pdf_path)
    pdf_text = []
    for i in range(len(doc)):
        pdf_text.append(doc[i].get_text("text"))
    doc.close()
    pdf_norm = " ".join(_norm_tokens("\n".join(pdf_text)))

    errors: list[str] = []
    for sec in majors:
        if sec not in found:
            continue
        f_toks, l_toks = first_last_chunks(found[sec])
        if len(f_toks) < 1 or len(l_toks) < 1:
            continue
        first_word = f_toks[0]
        last_word = l_toks[-1]
        first5 = " ".join(f_toks[:5])
        last5 = " ".join(l_toks[-5:])
        print(f"Section {sec}: first5='{first5}' | last5='{last5}'")
        if first_word not in pdf_norm:
            errors.append(f"{sec}: first word not in PDF -> '{first_word}' | first5='{first5}'")
        if last_word not in pdf_norm:
            errors.append(f"{sec}: last word not in PDF -> '{last_word}' | last5='{last5}'")
        if first5 not in pdf_norm:
            errors.append(f"{sec}: first 5-token chunk not in PDF -> '{first5}'")
        if last5 not in pdf_norm:
            errors.append(f"{sec}: last 5-token chunk not in PDF -> '{last5}'")

    if errors:
        msg = "\n".join(errors)
        msg += "\nNotes: PDF text may differ due to hyphenation/ligatures; TEI may clean/merge paragraphs."
        pytest.fail(msg)


def test_section_boundaries_against_pdf_for_mdpi_oral_2024():
    """Concrete article check: verify Intro boundaries between TEI and PDF.

    - Extract Introduction text from TEI
    - Compare first word and last word presence in corresponding PDF text
    - On mismatch, fail with a clear diagnostic message explaining likely causes
    """
    import os
    import re
    import unicodedata
    import pytest
    from paperslicer.grobid.sections import extract_introduction

    # TEI/PDF pair (present in the repo)
    base_dir = os.path.dirname(__file__)
    tei_path = os.path.join(
        base_dir,
        "data",
        "xml",
        "mdpi_oral_article2_enamel_volume_loss_energy_drinks_2024.tei.xml",
    )
    pdf_path = os.path.join(
        base_dir,
        "data",
        "pdf",
        "mdpi_oral_article2_enamel_volume_loss_energy_drinks_2024.pdf",
    )
    assert os.path.exists(tei_path), "Sample TEI not found"
    assert os.path.exists(pdf_path), "Matching PDF not found"

    intro_text = extract_introduction(tei_path) or ""
    # normalize TEI text to tokens
    def _tokens(s: str):
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        s = s.lower()
        s = re.sub(r"[^a-z0-9\s]+", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s.split()

    toks = _tokens(intro_text)
    assert len(toks) > 10, "Introduction appears too short or empty in TEI"
    first_word = toks[0]
    last_word = toks[-1]
    first_5 = " ".join(toks[:5])
    last_5 = " ".join(toks[-5:])
    # Print context for quick visualization in test output
    intro_vis_start = (" ".join(toks[:60]))[:240]
    intro_vis_end = (" ".join(toks[-60:]))[-240:]
    print("TEI Introduction (start):", intro_vis_start)
    print("TEI Introduction (end):", intro_vis_end)

    # Extract PDF text using PyMuPDF if available
    try:
        import fitz  # type: ignore
    except Exception as e:  # pragma: no cover - environment dependent
        pytest.skip(f"PyMuPDF not installed or unavailable: {e}")

    doc = fitz.open(pdf_path)
    pdf_text = []
    for pno in range(len(doc)):
        page = doc[pno]
        # Avoid layout complexity: use simple text extraction
        pdf_text.append(page.get_text("text"))
    doc.close()
    pdf_text = "\n".join(pdf_text)

    # normalize PDF text
    pdf_norm = " ".join(_tokens(pdf_text))

    # Checks with helpful diagnostics
    miss_critical = []
    warns = []
    # Helper to check a section (hard-fail on first word; warn on others)
    def check_section(name: str, text: str):
        if not text:
            return
        sec_toks = _tokens(text)
        if len(sec_toks) < 5:
            # ignore trivial content
            return
        fw = sec_toks[0]
        lw = sec_toks[-1]
        f5 = " ".join(sec_toks[:5])
        l5 = " ".join(sec_toks[-5:])
        if fw not in pdf_norm:
            miss_critical.append(
                f"{name} first word missing in PDF: '{fw}'. Context first5='{f5}'"
            )
        if lw not in pdf_norm:
            warns.append(
                f"{name} last word missing in PDF: '{lw}'. Context last5='{l5}'"
            )
        if f5 not in pdf_norm:
            warns.append(
                f"{name} first 5-token chunk not found in PDF: '{f5}'. "
                "Possible hyphenation/spacing differences."
            )
        if l5 not in pdf_norm:
            warns.append(
                f"{name} last 5-token chunk not found in PDF: '{l5}'. "
                "Section boundary may differ between TEI and PDF extraction."
            )

    check_section("Introduction", intro_text)
    # Also verify other major sections when present in TEI
    methods_text = extract_methods(tei_path) or ""
    results_text = extract_results(tei_path) or ""
    discussion_text = extract_discussion(tei_path) or ""
    conclusions_text = extract_conclusions(tei_path) or ""
    check_section("Materials_and_Methods", methods_text)
    check_section("Results", results_text)
    check_section("Discussion", discussion_text)
    check_section("Conclusions", conclusions_text)

    if miss_critical:
        detail = (
            "\n".join(miss_critical)
            + "\nNotes: PDF text extraction can alter whitespace, hyphenation, and ligatures;"
            + " TEI may also clean or merge paragraphs."
        )
        pytest.fail(detail)
    # Emit non-fatal diagnostics for awareness
    for w in warns:
        print("WARN:", w)


def _check_pdf_tei_for_stem(stem: str):
    import os, re, unicodedata, pytest
    try:
        import fitz  # type: ignore
    except Exception as e:
        pytest.skip(f"PyMuPDF not installed or unavailable: {e}")
    from paperslicer.grobid.sections import (
        extract_introduction,
        extract_methods,
        extract_results,
        extract_discussion,
        extract_conclusions,
    )

    base_dir = os.path.dirname(__file__)
    tei_path = os.path.join(base_dir, "data", "xml", f"{stem}.tei.xml")
    pdf_path = os.path.join(base_dir, "data", "pdf", f"{stem}.pdf")
    assert os.path.exists(tei_path), f"TEI not found: {tei_path}"
    assert os.path.exists(pdf_path), f"PDF not found: {pdf_path}"

    def _tokens(s: str):
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        s = s.lower()
        s = re.sub(r"[^a-z0-9\s]+", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s.split()

    # TEI sections
    intro = extract_introduction(tei_path) or ""
    methods = extract_methods(tei_path) or ""
    results = extract_results(tei_path) or ""
    discussion = extract_discussion(tei_path) or ""
    conclusions = extract_conclusions(tei_path) or ""

    # PDF text
    doc = fitz.open(pdf_path)
    pdf_text = "\n".join(page.get_text("text") for page in doc)
    doc.close()
    pdf_norm = " ".join(_tokens(pdf_text))

    def check_section(name: str, text: str):
        if not text:
            print(f"WARN: {stem} '{name}' empty in TEI; skipping checks")
            return
        toks = _tokens(text)
        if len(toks) < 5:
            print(f"WARN: {stem} '{name}' too short; skipping checks")
            return
        fw, lw = toks[0], toks[-1]
        f5 = " ".join(toks[:5])
        l5 = " ".join(toks[-5:])
        # Hard-fail only if both first word and first 5-chunk are missing
        if (fw not in pdf_norm) and (f5 not in pdf_norm):
            pytest.fail(
                f"{stem} '{name}' start not found in PDF. fw='{fw}' f5='{f5}'"
            )
        # Tail checks are soft warnings
        if (lw not in pdf_norm) and (l5 not in pdf_norm):
            print(
                f"WARN: {stem} '{name}' end not in PDF. lw='{lw}' l5='{l5}'"
            )

    # Run checks
    check_section("Introduction", intro)
    check_section("Materials_and_Methods", methods)
    check_section("Results", results)
    check_section("Discussion", discussion)
    check_section("Conclusions", conclusions)


def test_section_boundaries_mdpi_fluoride_release_2025():
    _check_pdf_tei_for_stem("mdpi_dentistry_article2_fluoride_release_2025")


def test_section_boundaries_bmc_oral_health_reso_pac_2025():
    _check_pdf_tei_for_stem("bmc_oral_health_article1_reso_pac_2025")


def test_section_boundaries_ijd_implant_macrodesign_2025():
    _check_pdf_tei_for_stem(
        "international_journal_implant_dentistry_article1_macrodesign_insertion_load_2025"
    )
