import os
from typing import List, Optional
from lxml import etree

from paperslicer.grobid.client import GrobidClient

DEFAULT_TEI_DIR = os.getenv("TEI_SAVE_DIR", "data/xml")


class GrobidIngestor:
    """
    Generate TEI XML for one PDF or a directory of PDFs.
    Saves to TEI_SAVE_DIR (default: data/xml) unless overridden.
    Returns list of saved TEI paths.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        tei_dir: Optional[str] = None,
        skip_existing: bool = True,
        validate_existing: bool = True,
    ):
        self.client = GrobidClient(base_url=base_url)
        self.tei_dir = tei_dir or DEFAULT_TEI_DIR
        self.skip_existing = skip_existing
        self.validate_existing = validate_existing
        os.makedirs(self.tei_dir, exist_ok=True)

    def _expected_tei_path(self, pdf_path: str) -> str:
        import pathlib
        stem = pathlib.Path(pdf_path).stem
        return os.path.join(self.tei_dir, f"{stem}.tei.xml")

    def _is_valid_tei(self, tei_path: str) -> bool:
        if not os.path.isfile(tei_path) or os.path.getsize(tei_path) <= 0:
            return False
        if not self.validate_existing:
            return True
        try:
            parser = etree.XMLParser(recover=True)
            root = etree.parse(tei_path, parser).getroot()
            # basic sanity: root tag endswith 'TEI'
            return root.tag.endswith('TEI')
        except Exception:
            return False

    def ingest_pdf(self, pdf_path: str) -> str:
        # Skip if TEI already exists and looks valid
        expected = self._expected_tei_path(pdf_path)
        if self.skip_existing and self._is_valid_tei(expected):
            return expected

        # If refresh requested but GROBID is not available, fall back to existing TEI if valid
        if not self.client.is_available():
            if self._is_valid_tei(expected):
                return expected
            raise RuntimeError("GROBID not available and no valid TEI exists for: " + pdf_path)

        tei_bytes, saved_path = self.client.process_fulltext(
            pdf_path,
            save_dir=self.tei_dir,
            basename=os.path.splitext(os.path.basename(pdf_path))[0],
        )
        if not saved_path:
            # Shouldn't happen when save_dir is provided, but fallback just in case
            import pathlib

            stem = pathlib.Path(pdf_path).stem
            saved_path = os.path.join(self.tei_dir, f"{stem}.tei.xml")
            with open(saved_path, "wb") as fh:
                fh.write(tei_bytes)
        return saved_path

    def ingest_path(self, path: str) -> List[str]:
        if os.path.isfile(path) and path.lower().endswith(".pdf"):
            return [self.ingest_pdf(path)]

        saved: List[str] = []
        for dp, _, files in os.walk(path):
            for f in files:
                if f.lower().endswith(".pdf"):
                    saved.append(self.ingest_pdf(os.path.join(dp, f)))
        return saved
