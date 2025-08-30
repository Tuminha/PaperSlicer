import os
import re
import unicodedata
import hashlib
from typing import Dict, Optional


def _slug(text: Optional[str], max_len: int = 80) -> str:
    if not text:
        return "unknown"
    s = unicodedata.normalize("NFKD", text)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    if not s:
        s = "unknown"
    return s[:max_len]


def _year_from_date(date_str: Optional[str]) -> str:
    if not date_str:
        return "unknown"
    m = re.search(r"(19|20)\d{2}", date_str)
    return m.group(0) if m else "unknown"


def build_media_outdir(media_root: str, meta: Dict, pdf_path: str) -> str:
    """Build a tidy media output directory path using metadata.

    media/<year>/<journal>/<author>_<year>_<shorttitle>_<hash>/
    """
    year = _year_from_date(meta.get("date"))
    journal = _slug(meta.get("journal"), max_len=60)
    title = _slug(meta.get("title"), max_len=80)
    first_author = "unknown"
    authors = meta.get("authors") or []
    if authors:
        a0 = authors[0] or {}
        first_author = a0.get("family") or a0.get("given") or a0.get("full") or "unknown"
    author_slug = _slug(first_author, max_len=40).upper()
    h = hashlib.sha1((pdf_path or "").encode("utf-8")).hexdigest()[:8]
    leaf = f"{author_slug}_{year}_{title}_{h}"
    outdir = os.path.join(media_root, year, journal, leaf)
    return outdir
