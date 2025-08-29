import re
import unicodedata
from typing import Dict, List, Optional


def _ascii(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def _clean(s: str) -> str:
    s = _ascii(s or "").lower()
    # remove leading numbering like "1. ", "I. ", etc.
    s = re.sub(r"^[\s\-–—\divx\.]+\s+", "", s)
    s = s.replace("&", " and ").replace("/", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Canonical → synonyms (cleaned, lowercase, ascii, words joined by spaces)
SECTIONS_MAP: Dict[str, List[str]] = {
    "abstract": [
        "abstract",
        "summary",
    ],
    "introduction": [
        "introduction",
        "background",
        "background and aims",
        "introduction and objectives",
        "introduction and aim",
        "background and objectives",
        "purpose",
        "aim",
        "aims",
        "aims and objectives",
        "objective",
        "objectives",
    ],
    "materials_and_methods": [
        "materials and methods",
        "methods and materials",
        "materials methods",
        "materials and method",
        "method and materials",
        "patients and methods",
        "methodology",
        "methods",
        "method",
        "materials",
        "statistical analysis",
        "statistical analyses",
        "statistics",
    ],
    "results": [
        "results",
        "findings",
        "outcomes",
        "observations",
        "results of",
    ],
    "results_and_discussion": [
        "results and discussion",
        "results discussion",
        "results & discussion",
        "discussion and results",
        "results with discussion",
    ],
    "discussion": [
        "discussion",
    ],
    "conclusions": [
        "conclusions",
        "conclusion",
        "clinical significance",
        "clinical implications",
        "practical implications",
    ],
    "limitations": [
        "limitations",
        "study limitations",
        "strengths and limitations",
    ],
    "ethics": [
        "ethics",
        "ethical approval",
        "ethics statement",
    ],
    "author_contributions": [
        "author contributions",
        "authors contributions",
        "contribution of authors",
    ],
    "data_availability": [
        "data availability",
        "availability of data",
        "data and materials availability",
    ],
    "abbreviations": [
        "abbreviations",
        "abbreviation",
        "nomenclature",
        "glossary",
    ],
    "trial_registration": [
        "trial registration",
        "clinical trial registration",
        "registration",
    ],
    "acknowledgements": [
        "acknowledgements",
        "acknowledgments",
        "acknowledgement",
    ],
    "funding": [
        "funding",
        "funding statement",
    ],
    "conflicts_of_interest": [
        "conflict of interest",
        "conflicts of interest",
        "competing interests",
    ],
    "references": [
        "references",
        "bibliography",
    ],
    "supplementary": [
        "supplementary material",
        "supplementary data",
        "supporting information",
    ],
}


def canonicalize(header: str) -> Optional[str]:
    """Return canonical section id if header matches known synonyms, else None."""
    h = _clean(header)
    if not h:
        return None
    for canon, variants in SECTIONS_MAP.items():
        for v in variants:
            vv = _clean(v)
            # match exact or startswith (to catch "introduction and ...")
            if h == vv or h.startswith(vv + " ") or vv.startswith(h + " "):
                return canon
    # Additional heuristics
    if h.startswith("introduction") or h.startswith("background"):
        return "introduction"
    if "materials" in h and "methods" in h:
        return "materials_and_methods"
    if h.startswith("methods") or h.startswith("methodology"):
        return "materials_and_methods"
    if h.startswith("results and discussion"):
        return "results_and_discussion"
    if h.startswith("results"):
        return "results"
    if h.startswith("discussion"):
        return "discussion"
    if h.startswith("conclusion") or h.startswith("clinical significance"):
        return "conclusions"
    if h.startswith("acknowledg"):
        return "acknowledgements"
    if h.startswith("funding"):
        return "funding"
    if "conflict" in h or "competing" in h:
        return "conflicts_of_interest"
    if h.startswith("reference") or h == "bibliography":
        return "references"
    if h.startswith("supplementary") or "supporting information" in h:
        return "supplementary"
    return None


def is_heading_of(header: str, canonical: str) -> bool:
    return canonicalize(header) == canonical
