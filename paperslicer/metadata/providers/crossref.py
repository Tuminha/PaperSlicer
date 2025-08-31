from __future__ import annotations
import os
import re
import html
from typing import Optional, Dict, Any
import requests


CR_API = "https://api.crossref.org"


def _user_agent(mailto: Optional[str]) -> str:
    mt = mailto or os.getenv("CROSSREF_MAILTO")
    if mt:
        return f"PaperSlicer/0.1 (mailto: {mt})"
    return "PaperSlicer/0.1"


def _strip_tags(s: str) -> str:
    # Crossref abstracts are often JATS XML; remove tags and unescape entities
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return html.unescape(s)


def get_work_by_doi(doi: str, mailto: Optional[str] = None, timeout: int = 12) -> Optional[Dict[str, Any]]:
    doi = doi.strip()
    if not doi:
        return None
    url = f"{CR_API}/works/{requests.utils.quote(doi)}"
    try:
        r = requests.get(url, headers={"User-Agent": _user_agent(mailto)}, timeout=timeout)
        if r.status_code != 200:
            return None
        data = r.json()
        return data.get("message")
    except Exception:
        return None


def search_by_title(title: str, mailto: Optional[str] = None, timeout: int = 12) -> Optional[Dict[str, Any]]:
    if not title:
        return None
    try:
        r = requests.get(
            f"{CR_API}/works",
            params={"query.title": title, "rows": 1},
            headers={"User-Agent": _user_agent(mailto)},
            timeout=timeout,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        items = (data.get("message") or {}).get("items") or []
        return items[0] if items else None
    except Exception:
        return None


def extract_abstract(item: Dict[str, Any]) -> Optional[str]:
    if not item:
        return None
    raw = item.get("abstract")
    if isinstance(raw, str) and raw.strip():
        return _strip_tags(raw)
    return None

