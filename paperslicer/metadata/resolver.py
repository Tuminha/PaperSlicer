from typing import Dict, Optional

from paperslicer.extractors.metadata import TEIMetadataExtractor
from paperslicer.metadata.providers.crossref import CrossrefClient
from paperslicer.metadata.providers.pubmed import PubMedClient


def _norm(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = s.strip()
    return s or None


def merge(primary: Dict, secondary: Dict) -> Dict:
    """Fill missing primary fields from secondary; keep primary if non-empty."""
    out = dict(primary)
    for k, v in secondary.items():
        if k not in out or out[k] in (None, "", [], {}):
            out[k] = v
    return out


class MetadataResolver:
    def __init__(self, mailto: str = "you@example.com"):
        self.tei = TEIMetadataExtractor()
        self.crossref = CrossrefClient(mailto=mailto)
        self.pubmed = PubMedClient()

    def resolve_from_tei(self, tei_path: str) -> Dict:
        base = self.tei.from_file(tei_path)

        # Crossref
        cr = None
        if _norm(base.get("doi")):
            cr_msg = self.crossref.by_doi(base["doi"])  # type: ignore[arg-type]
            cr = self.crossref.to_meta(cr_msg) if cr_msg else None
        else:
            if _norm(base.get("title")):
                cr_msg = self.crossref.by_title(base["title"])  # type: ignore[arg-type]
                cr = self.crossref.to_meta(cr_msg) if cr_msg else None

        out = merge(base, cr or {})

        # PubMed for abstract/summary/doi/keywords if still missing critical fields
        need_abstract = not _norm(out.get("abstract"))
        need_keywords = (not out.get("keywords")) or out.get("keywords") == []
        need_doi = not _norm(out.get("doi"))
        if (need_abstract or need_keywords or need_doi) and _norm(out.get("title")):
            pmid = self.pubmed.id_by_title(out["title"])  # type: ignore[arg-type]
            if pmid:
                enrich: Dict = {}
                if need_abstract:
                    abst = self.pubmed.abstract_by_id(pmid)
                    if abst:
                        enrich["abstract"] = abst
                summ = self.pubmed.summary_by_id(pmid) or {}
                enrich = merge(enrich, summ)
                if need_doi and not _norm(enrich.get("doi")):
                    doi = self.pubmed.doi_by_id(pmid)
                    if doi:
                        enrich["doi"] = doi
                if need_keywords:
                    kws = self.pubmed.keywords_by_id(pmid)
                    if kws:
                        enrich["keywords"] = kws
                out = merge(out, enrich)

        # Normalize empties
        for k, v in list(out.items()):
            if v in ("", [], {}):
                out[k] = None if k != "keywords" else []
        if out.get("keywords") is None:
            out["keywords"] = []

        # Normalize date to YYYY or YYYY-MM or YYYY-MM-DD with zero padding when parts present
        date = out.get("date")
        if isinstance(date, str) and date:
            parts = date.replace("/", "-").split("-")
            try:
                if len(parts) == 1 and parts[0].isdigit():
                    out["date"] = parts[0]
                elif len(parts) == 2 and all(p.isdigit() for p in parts):
                    y, m = parts
                    out["date"] = f"{int(y):04d}-{int(m):02d}"
                elif len(parts) >= 3:
                    y, m, d = parts[:3]
                    out["date"] = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
            except Exception:
                pass

        return out
