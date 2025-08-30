from __future__ import annotations

from typing import Optional, List, Dict
import copy
import re
from lxml import etree

from paperslicer.grobid.sections import TEI_NS
from paperslicer.utils.sections_mapping import canonicalize


class Periodontology2000Handler:
    """Heuristics tailored for 'Periodontology 2000' review-style articles.

    Goals (conservative, domain-agnostic):
    - Prefer populating 'discussion' (not 'results') when the body consists of topical sections
      without explicit Results/Discussion heads.
    - Avoid pulling disclaimers (e.g., ORCID, data availability, contributions) into augmented text.
    """

    EXCLUDE_CANON = {
        "data_availability",
        "acknowledgements",
        "conflicts_of_interest",
        "author_contributions",
        "funding",
        "trial_registration",
        "keywords",
        "supplementary",
        "publisher_note",
        "declarations",
    }

    EXCLUDE_SUBSTR = {
        "orcid",
        "data availability",
        "conflict of interest",
        "competing interest",
        "author contribution",
        "acknowledg",
        "funding",
        "trial registration",
        "publisher's note",
        "publisher note",
    }

    @staticmethod
    def is_match(root: etree._Element, md: Dict[str, object] | None = None) -> bool:
        # Prefer TEI header journal title
        j = root.find(".//tei:sourceDesc//tei:monogr//tei:title", TEI_NS)
        jtitle = (j.text or "").strip().lower() if j is not None and j.text else ""
        if "periodontology 2000" in jtitle:
            return True
        # Fallback to metadata dict
        if md:
            jt = (md.get("journal") or "").strip().lower() if isinstance(md.get("journal"), str) else ""
            return "periodontology 2000" in jt
        return False

    @staticmethod
    def _clean_text(el: etree._Element) -> str:
        cp = copy.deepcopy(el)
        for ref in cp.findall('.//tei:ref[@type="bibr"]', TEI_NS):
            par = ref.getparent()
            if par is not None:
                par.remove(ref)
        for h in cp.findall('.//tei:head', TEI_NS):
            par = h.getparent()
            if par is not None:
                par.remove(h)
        s = "\n\n".join(" ".join(x.split()) for x in ["".join(cp.itertext())])
        s = re.sub(r"\[(?:\s*\d+(?:\s*[-–]\s*\d+)?\s*(?:,\s*\d+(?:\s*[-–]\s*\d+)?)*)\]", "", s)
        s = re.sub(r"\n+\d+\n+", "\n\n", s)
        s = re.sub(r"(?m)^\|\s*", "", s)
        return s.strip()

    def aggregate_body_between(self, root: etree._Element) -> str:
        divs = root.findall(".//tei:text//tei:div", TEI_NS)
        def head_of(d: etree._Element) -> str:
            h = d.find("./tei:head", TEI_NS)
            return "".join(h.itertext()) if h is not None else ""
        # boundaries
        intro_idx: Optional[int] = None
        end_idx: Optional[int] = None
        for i, dv in enumerate(divs):
            canon = canonicalize(head_of(dv))
            if intro_idx is None and canon == "introduction":
                intro_idx = i
            if canon in ("conclusions", "references") and end_idx is None:
                end_idx = i
        start = (intro_idx + 1) if intro_idx is not None else 0
        stop = end_idx if end_idx is not None else len(divs)
        parts: List[str] = []
        for i in range(max(0, start), max(start, min(stop, len(divs)))):
            dv = divs[i]
            htxt = head_of(dv)
            canon = canonicalize(htxt)
            hclean = (htxt or "").lower()
            if canon in self.EXCLUDE_CANON:
                continue
            if any(sub in hclean for sub in self.EXCLUDE_SUBSTR):
                continue
            # keep only unmapped or general topical sections
            if canon is None or canon == "limitations":
                txt = self._clean_text(dv)
                if txt:
                    parts.append(txt)
        return "\n\n".join(parts).strip()

    def apply(self, md_plus: Dict[str, object], tei_path: str) -> List[str]:
        """Mutates md_plus in place; returns names of sections affected."""
        try:
            root = etree.parse(tei_path, etree.XMLParser(recover=True)).getroot()
        except Exception:
            return []
        if not self.is_match(root, md_plus):
            return []

        changed: List[str] = []
        # Prefer a discussion-only augmentation when results/discussion are missing
        have_results = bool((md_plus.get("results") or "").strip())
        have_disc = bool((md_plus.get("discussion") or "").strip())
        # Use existing augmented aggregate if present; else compute
        agg = (md_plus.get("augmented_results_and_discussion") or "").strip()
        if not agg:
            agg = self.aggregate_body_between(root)
        if agg:
            if not have_disc:
                md_plus["augmented_results_and_discussion"] = agg
                md_plus["discussion"] = (md_plus.get("discussion") or "") or agg
                changed.append("discussion")
            # If generic review-mode already stuffed results with the same aggregate, prefer clearing it
            r = (md_plus.get("results") or "")
            if isinstance(r, str) and r.strip() == agg.strip():
                md_plus["results"] = ""
                if not have_results:
                    # results was empty already; don't mark changed
                    pass
                else:
                    changed.append("results")
        return changed
