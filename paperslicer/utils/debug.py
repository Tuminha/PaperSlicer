import json
import os
import re
import unicodedata
from datetime import datetime
from typing import Dict, Optional


def _ascii_slug(s: str, max_len: int = 80) -> str:
    if not s:
        return "unknown"
    # Normalize and strip accents
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    # Replace non-alnum with spaces, then collapse to hyphens
    s = re.sub(r"[^A-Za-z0-9]+", "-", s)
    s = s.strip("-")
    if not s:
        s = "unknown"
    return s[:max_len]


def _year_from_date(date_str: Optional[str]) -> str:
    if not date_str:
        return "unknown"
    m = re.search(r"(19|20)\d{2}", date_str)
    return m.group(0) if m else "unknown"


def build_debug_filename(meta: Dict, now: Optional[datetime] = None) -> str:
    """Return a filename like: <author>_<year>_<title>_<HHMM>.json"""
    first_author = ""
    if meta.get("authors"):
        a0 = meta["authors"][0] or {}
        first_author = a0.get("family") or a0.get("given") or a0.get("full") or ""
    author_slug = _ascii_slug(first_author, max_len=40)
    year = _year_from_date(meta.get("date"))
    title_slug = _ascii_slug(meta.get("title") or "", max_len=80)
    ts = (now or datetime.now()).strftime("%H%M")
    return f"{author_slug}_{year}_{title_slug}_{ts}.json"


def save_metadata_json(meta: Dict, out_dir: str = "out/meta", now: Optional[datetime] = None) -> str:
    os.makedirs(out_dir, exist_ok=True)
    fname = build_debug_filename(meta, now=now)
    path = os.path.join(out_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return path

