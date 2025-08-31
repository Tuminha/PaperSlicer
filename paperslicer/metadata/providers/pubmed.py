from __future__ import annotations
import os
from typing import Optional, Dict, Any, List
import requests
from lxml import etree


EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _params_base() -> Dict[str, str]:
    p: Dict[str, str] = {"retmode": "json"}
    api_key = os.getenv("PUBMED_API_KEY")
    if api_key:
        p["api_key"] = api_key
    return p


def _esearch_term(doi: Optional[str], title: Optional[str]) -> Optional[str]:
    if doi:
        return f"{doi}[DOI]"
    if title:
        return f"\"{title}\"[Title]"
    return None


def find_pmid(doi: Optional[str] = None, title: Optional[str] = None, timeout: int = 12) -> Optional[str]:
    term = _esearch_term(doi, title)
    if not term:
        return None
    try:
        params = {"db": "pubmed", "term": term, **_params_base()}
        r = requests.get(f"{EUTILS}/esearch.fcgi", params=params, timeout=timeout)
        if r.status_code != 200:
            return None
        data = r.json()
        ids = ((data.get("esearchresult") or {}).get("idlist") or [])
        return ids[0] if ids else None
    except Exception:
        return None


def fetch_abstract_by_pmid(pmid: str, timeout: int = 12) -> Optional[str]:
    if not pmid:
        return None
    try:
        params = {"db": "pubmed", "id": pmid, "retmode": "xml"}
        api_key = os.getenv("PUBMED_API_KEY")
        if api_key:
            params["api_key"] = api_key
        r = requests.get(f"{EUTILS}/efetch.fcgi", params=params, timeout=timeout)
        if r.status_code != 200:
            return None
        root = etree.fromstring(r.content)
        # //Abstract/AbstractText possibly multiple
        texts: List[str] = []
        for el in root.xpath("//Abstract/AbstractText"):
            t = " ".join((el.text or "").split())
            if t:
                texts.append(t)
        if texts:
            return "\n\n".join(texts)
        return None
    except Exception:
        return None


def get_abstract(doi: Optional[str] = None, title: Optional[str] = None, timeout: int = 12) -> Optional[str]:
    pmid = find_pmid(doi=doi, title=title, timeout=timeout)
    if not pmid:
        return None
    return fetch_abstract_by_pmid(pmid, timeout=timeout)

