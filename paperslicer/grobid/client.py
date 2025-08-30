import os
import pathlib
from typing import Optional, Tuple
import requests

DEFAULT_URL = "http://localhost:8070"

class GrobidClient:
    """
    Minimal HTTP client for GROBID.
    - is_available(): quick health check (returns True/False)
    - process_fulltext(pdf_path): returns TEI XML bytes for a PDF
    """
    def __init__(self, base_url: Optional[str] = None, timeout: int = 120):
        # Use env var if provided, else default localhost
        self.base_url = (base_url or os.getenv("GROBID_URL") or DEFAULT_URL).rstrip("/")
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            r = requests.get(self.base_url, timeout=2)
            return r.status_code < 500
        except Exception:
            return False

    def process_fulltext(
        self,
        pdf_path: str,
        consolidate_header: int = 1,
        consolidate_citations: int = 1,
        include_raw_affils: int = 1,
        save_dir: Optional[str] = None,
        basename: Optional[str] = None,
        tei_coordinates: Optional[str] = "fig,table",
    ) -> Tuple[bytes, Optional[str]]:
        """
        Calls /api/processFulltextDocument and returns TEI XML (bytes).
        Raises requests.HTTPError on failure.
        """
        url = f"{self.base_url}/api/processFulltextDocument"
        with open(pdf_path, "rb") as fh:
            files = {"input": fh}
            data = {
                "consolidateHeader": str(consolidate_header),
                "consolidateCitations": str(consolidate_citations),
                "includeRawAffiliations": str(include_raw_affils),
            }
            if tei_coordinates:
                data["teiCoordinates"] = tei_coordinates
            r = requests.post(url, files=files, data=data, timeout=self.timeout)
        r.raise_for_status()
        tei_bytes = r.content
        saved_path: Optional[str] = None

        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            stem = basename or pathlib.Path(pdf_path).stem
            saved_path = os.path.join(save_dir, f"{stem}.tei.xml")
            with open(saved_path, "wb") as out:
                out.write(tei_bytes)

        return tei_bytes, saved_path
