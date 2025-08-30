import os
from typing import Optional, Dict, Any, List
import requests
from lxml import etree


class PubMedClient:
    def __init__(self, timeout: int = 10, api_key: Optional[str] = None):
        self.esearch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        self.esummary = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        self.efetch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        self.timeout = timeout
        self.api_key = api_key or os.getenv("PUBMED_API_KEY")

    def _params(self, base: Dict[str, Any]) -> Dict[str, Any]:
        if self.api_key:
            base = dict(base)
            base["api_key"] = self.api_key
        return base

    def id_by_title(self, title: str) -> Optional[str]:
        params = self._params({"db": "pubmed", "term": title, "retmode": "json", "retmax": "1"})
        try:
            r = requests.get(self.esearch, params=params, timeout=self.timeout)
            if not r.ok:
                return None
            ids = r.json().get("esearchresult", {}).get("idlist", [])
            return ids[0] if ids else None
        except Exception:
            return None

    def abstract_by_id(self, pmid: str) -> Optional[str]:
        params = self._params({"db": "pubmed", "id": pmid, "retmode": "xml"})
        try:
            r = requests.get(self.efetch, params=params, timeout=self.timeout)
            if not r.ok:
                return None
            parser = etree.XMLParser(recover=True)
            root = etree.fromstring(r.content, parser)
            # Join possibly multiple AbstractText nodes, include Label if present
            texts: List[str] = []
            for node in root.findall(".//Abstract/AbstractText"):
                label = node.get("Label") or node.get("NlmCategory")
                content = (" ".join(node.itertext())).strip()
                if label and content:
                    texts.append(f"{label}: {content}")
                elif content:
                    texts.append(content)
            if not texts:
                return None
            return "\n\n".join(texts)
        except Exception:
            return None

    def doi_by_id(self, pmid: str) -> Optional[str]:
        params = self._params({"db": "pubmed", "id": pmid, "retmode": "xml"})
        try:
            r = requests.get(self.efetch, params=params, timeout=self.timeout)
            if not r.ok:
                return None
            parser = etree.XMLParser(recover=True)
            root = etree.fromstring(r.content, parser)
            doi_node = root.find(".//ArticleIdList/ArticleId[@IdType='doi']")
            return doi_node.text.strip() if doi_node is not None and doi_node.text else None
        except Exception:
            return None

    def keywords_by_id(self, pmid: str) -> List[str]:
        params = self._params({"db": "pubmed", "id": pmid, "retmode": "xml"})
        try:
            r = requests.get(self.efetch, params=params, timeout=self.timeout)
            if not r.ok:
                return []
            parser = etree.XMLParser(recover=True)
            root = etree.fromstring(r.content, parser)
            kws: List[str] = []
            for kw in root.findall(".//KeywordList/Keyword"):
                if kw.text:
                    txt = " ".join(kw.text.split()).strip()
                    if txt:
                        kws.append(txt)
            return kws
        except Exception:
            return []

    def summary_by_id(self, pmid: str) -> Optional[Dict[str, Any]]:
        params = self._params({"db": "pubmed", "id": pmid, "retmode": "json"})
        try:
            r = requests.get(self.esummary, params=params, timeout=self.timeout)
            if not r.ok:
                return None
            res = r.json().get("result", {})
            rec = res.get(pmid)
            if not rec:
                return None
            md = {
                "title": rec.get("title"),
                "journal": rec.get("fulljournalname"),
                "date": rec.get("pubdate"),
                "authors": [{
                    "full": a.get("name", ""),
                    "given": "",
                    "family": "",
                    "affiliations": [],
                } for a in rec.get("authors", [])],
                "doi": None,
                "publisher": None,
                "keywords": [],
                "abstract": None,
            }
            # Try to pull DOI if present in identifiers
            ids = rec.get("articleids") or []
            for item in ids:
                if item.get("idtype") == "doi" and item.get("value"):
                    md["doi"] = item["value"]
                    break
            return md
        except Exception:
            return None
