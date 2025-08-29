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


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker not available")
def test_grobid_manager_does_not_crash_when_trying_to_start():
    mgr = GrobidManager()
    # We don’t assert True here (CI environments vary). Just ensure it doesn’t raise.
    try:
        mgr.start(wait_ready_s=1)  # short wait
    except Exception as e:
        pytest.fail(f"Manager.start raised unexpectedly: {e}")
