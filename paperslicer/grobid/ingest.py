import os
from typing import List, Optional

from paperslicer.grobid.client import GrobidClient

DEFAULT_TEI_DIR = os.getenv("TEI_SAVE_DIR", "data/xml")


class GrobidIngestor:
    """
    Generate TEI XML for one PDF or a directory of PDFs.
    Saves to TEI_SAVE_DIR (default: data/xml) unless overridden.
    Returns list of saved TEI paths.
    """

    def __init__(self, base_url: Optional[str] = None, tei_dir: Optional[str] = None):
        self.client = GrobidClient(base_url=base_url)
        self.tei_dir = tei_dir or DEFAULT_TEI_DIR
        os.makedirs(self.tei_dir, exist_ok=True)

    def ingest_pdf(self, pdf_path: str) -> str:
        tei_bytes, saved_path = self.client.process_fulltext(pdf_path, save_dir=self.tei_dir)
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

