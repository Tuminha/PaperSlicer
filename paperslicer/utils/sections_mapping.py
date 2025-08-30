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
    # Important: put combined sections before individual ones to avoid shadowing
    "results_and_discussion": [
        "results and discussion",
        "results discussion",
        "results & discussion",
        "discussion and results",
        "results with discussion",
    ],
    "abstract": [
        "abstract",
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
        "material and methods",
        "material and method",
        "material methods",
        "method and materials",
        "patients and methods",
        "subjects and methods",
        "methodology",
        "methods",
        "method",
        "materials",
        "statistical analysis",
        "statistical analyses",
        "statistics",
        # Systematic review methods subheads
        "study selection",
        "eligibility criteria",
        "inclusion criteria",
        "inclusion and exclusion criteria",
        "information sources and search strategy",
        "search strategy",
        "data extraction",
        "risk of bias assessment",
        "risk of bias",
        "data synthesis",
        "sample size calculation",
        "sample size",
        # Procedure-specific steps
        "sample preparation",
        "drink selection",
        "scanning",
        "volume loss test",
        "volume loss evaluation",
        "evaluation of volume loss",
        "evaluation of ph",
        "evaluation of titratable acidity",
        "preoperative examination",
        "history and preoperative examination",
        "preoperative preparations",
        "medical preparations",
        "patient preparation",
        "surgical area preparation",
        "surgical procedures",
        "microscope positioning and use",
        "ultrasonic tips",
        "electrolytic cleaning",
        "rotating brushes",
        "air powder abrasive",
        "air-powder abrasive",
        "flap incision and elevation",
        "root apex positioning",
        "root end resection, curettage, and inspection",
        "pathological examination",
        "suturing",
        "suture removal",
        "postoperative management",
        "postoperative reactions",
        "indications",
        "contraindications",
        "systemic conditions",
        "local conditions",
    ],
    "results": [
        "results",
        "findings",
        "outcomes",
        "observations",
        "results of",
        "meta analysis",
        "meta-analysis",
        "included studies",
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
        "summary",
        "summary and conclusions",
        "summary and decision-making process",
        "summary and decision making process",
        "concluding remarks",
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
        "institutional review board statement",
        "informed consent statement",
        "informed consent",
        "consent for publication",
        "human and animal rights",
        "human rights",
    ],
    "author_contributions": [
        "author contributions",
        "authors contributions",
        "authors contribution",
        "contribution of authors",
    ],
    "data_availability": [
        "data availability",
        "availability of data",
        "data and materials availability",
        "data availability statement",
    ],
    "abbreviations": [
        "abbreviations",
        "abbreviation",
        "nomenclature",
        "glossary",
        "list of abbreviations",
        "abbreviations list",
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
        "financial support",
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
        "additional information",
    ],
    # Additional canonical buckets to reduce unmapped noise
    "keywords": [
        "keywords",
        "key words",
        "list of keywords",
    ],
    "declarations": [
        "declarations",
    ],
    "publisher_note": [
        "publisher's note",
        "publishers note",
        "publisher note",
    ],
}


def canonicalize(header: str) -> Optional[str]:
    """Return canonical section id if header matches known synonyms, else None.

    Strategy:
    1) Exact match across all variants
    2) Starts-with match where header begins with the variant (e.g., "introduction and aims")
    Avoid mapping a short header to a longer variant that merely starts with it (e.g.,
    "results" must not map to "results and discussion").
    """
    # Clean and also make a compact version with spaces removed to handle
    # headings with artificial spacing like "INTRODUC TI ON"
    h = _clean(header)
    hc = h.replace(" ", "")
    if not h:
        return None
    # Pass 1: exact equality wins
    for canon, variants in SECTIONS_MAP.items():
        for v in variants:
            vv = _clean(v)
            if h == vv or hc == vv.replace(" ", ""):
                return canon
    # Pass 2: header starts with a known variant (e.g., "introduction and objectives")
    for canon, variants in SECTIONS_MAP.items():
        for v in variants:
            vv = _clean(v)
            if h.startswith(vv + " ") or hc.startswith(vv.replace(" ", "")):
                return canon
    # Additional heuristics
    if h.startswith("introduction") or hc.startswith("introduction") or h.startswith("background"):
        return "introduction"
    if "materials" in h and "methods" in h:
        return "materials_and_methods"
    if h.startswith("methods") or h.startswith("methodology"):
        return "materials_and_methods"
    if h.startswith("results and discussion") or hc.startswith("resultsanddiscussion"):
        return "results_and_discussion"
    if h.startswith("results"):
        return "results"
    if h.startswith("discussion") or hc.startswith("discussion"):
        return "discussion"
    if h.startswith("conclusion") or hc.startswith("conclusion") or h.startswith("clinical significance"):
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
