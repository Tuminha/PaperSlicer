from __future__ import annotations
from typing import Optional

from paperslicer.models import PaperRecord
from .providers import crossref as cr
from .providers import pubmed as pm


def ensure_abstract(rec: PaperRecord, mailto: Optional[str] = None) -> bool:
    """
    Ensure rec.sections['abstract'] exists by consulting Crossref and PubMed if needed.
    Returns True if abstract present at the end, False otherwise.
    """
    abstract = (rec.sections or {}).get("abstract") or ""
    if abstract and len(abstract) >= 30:
        return True

    doi = (rec.meta.doi or "").strip() if rec.meta else ""
    title = (rec.meta.title or "").strip() if rec.meta else ""

    # Try Crossref
    item = None
    if doi:
        item = cr.get_work_by_doi(doi, mailto=mailto)
    if item is None and title:
        item = cr.search_by_title(title, mailto=mailto)
    if item is not None:
        cr_abs = cr.extract_abstract(item)
        if cr_abs and len(cr_abs) >= 30:
            rec.sections["abstract"] = cr_abs
            # Fill missing DOI/title/journal if absent
            if rec.meta:
                rec.meta.doi = rec.meta.doi or item.get("DOI")
                tit = item.get("title")
                if not rec.meta.title and isinstance(tit, list) and tit:
                    rec.meta.title = tit[0]
                cont = item.get("container-title")
                if isinstance(cont, list) and cont and not rec.meta.journal:
                    rec.meta.journal = cont[0]
            return True

    # Try PubMed
    pm_abs = pm.get_abstract(doi=doi or None, title=title or None)
    if pm_abs and len(pm_abs) >= 30:
        rec.sections["abstract"] = pm_abs
        return True

    return (rec.sections.get("abstract") or "") != ""

