import os
from typing import Optional, Dict, Any
from lxml import etree
import requests


class CrossrefClient:
    def __init__(self, mailto: Optional[str] = None, timeout: int = 10):
        self.base = "https://api.crossref.org"
        self.timeout = timeout
        mail = mailto or os.getenv("CROSSREF_MAILTO") or "you@example.com"
        self.headers = {"User-Agent": f"PaperSlicer/0.1 (mailto:{mail})"}

    def by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        try:
            r = requests.get(f"{self.base}/works/{doi}", headers=self.headers, timeout=self.timeout)
            if r.status_code == 200:
                return r.json().get("message", {})
        except Exception:
            return None
        return None

    def by_title(self, title: str) -> Optional[Dict[str, Any]]:
        try:
            params = {"query.title": title, "rows": 1}
            r = requests.get(f"{self.base}/works", params=params, headers=self.headers, timeout=self.timeout)
            if r.status_code == 200:
                items = r.json().get("message", {}).get("items", [])
                return items[0] if items else None
        except Exception:
            return None
        return None

    @staticmethod
    def to_meta(msg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not msg:
            return {}
        md: Dict[str, Any] = {}
        title_list = msg.get("title") or []
        md["title"] = " ".join(title_list) if isinstance(title_list, list) else title_list
        cont = msg.get("container-title") or [None]
        md["journal"] = cont[0] if isinstance(cont, list) else cont
        md["publisher"] = msg.get("publisher")
        md["doi"] = msg.get("DOI")
        issued = msg.get("issued", {}).get("date-parts", [[]])
        if issued and issued[0]:
            parts = issued[0]
            md["date"] = "-".join(str(p) for p in parts)
        else:
            md["date"] = None
        authors = []
        for a in msg.get("author", []) or []:
            affs = [af.get("name") for af in (a.get("affiliation", []) or []) if af.get("name")]
            given = a.get("given") or ""
            family = a.get("family") or ""
            authors.append({
                "given": given,
                "family": family,
                "full": " ".join([given, family]).strip(),
                "affiliations": affs,
            })
        md["authors"] = authors
        # Abstract: Crossref may include JATS XML in a string under 'abstract'
        abs_raw = msg.get("abstract")
        abstract: Optional[str] = None
        if isinstance(abs_raw, str) and abs_raw.strip():
            try:
                wrapper = f"<root>{abs_raw}</root>"
                root = etree.fromstring(wrapper.encode("utf-8"))
                abstract = " ".join(" ".join(p.split()) for p in root.itertext()).strip()
            except Exception:
                # Fallback: strip tags crudely
                import re
                text = re.sub(r"<[^>]+>", " ", abs_raw)
                abstract = " ".join(text.split()).strip() or None
        md["abstract"] = abstract
        md["keywords"] = msg.get("subject") or []
        return md
