from __future__ import annotations

"""
Canonical section mapping utilities.

This module centralizes the normalization of section headings to a
restricted set of canonical keys used by PaperSlicer.

Canonical keys (current):
 - abstract
 - introduction
 - materials_and_methods
 - results
 - discussion
 - conclusions
 - results_and_discussion

We intentionally skip non-content boilerplate (acknowledgements, funding, etc.).
"""

import re
from typing import Optional


# Common non-content sections to exclude from main body mapping
NON_CONTENT_KEYS = {
    "acknowledgements",
    "acknowledgments",
    "funding",
    "conflict_of_interest",
    "conflicts_of_interest",
    "competing_interests",
    "author_contributions",
    "authors_contributions",
    "contributorship",
    "availability_of_data_and_materials",
    "data_availability",
    "ethical_statement",
    "ethics_statement",
    "human_and_animal_rights",
    "patient_consent",
    "consent_for_publication",
    "list_of_abbreviations",
    "abbreviations",
    "orcid",
    "references",
    "bibliography",
}


# Exact (lowercased) title to canonical key
def _sanitize_heading(name: str) -> str:
    s = (name or "").strip().lower()
    # Remove leading pipes/bullets/dashes and numbering like "1.", "3.2.", "ii.", etc.
    s = re.sub(r"^[|>•\-\u2013\u2014\s]+", "", s)  # leading punctuation/bullets
    s = re.sub(r"^(?:[ivxlcdm]+\.|\d+(?:\.\d+)*\.?)[\s\-:]*", "", s, flags=re.I)  # numbering
    # Collapse multiple spaces
    s = re.sub(r"\s+", " ", s)
    return s.strip()


EXACT_MAP = {
    # Core
    "abstract": "abstract",
    "introduction": "introduction",
    "background": "introduction",
    "methods": "materials_and_methods",
    "materials": "materials_and_methods",
    "materials and methods": "materials_and_methods",
    "materials & methods": "materials_and_methods",
    "methods and materials": "materials_and_methods",
    "patients and methods": "materials_and_methods",
    "subjects and methods": "materials_and_methods",
    "study design": "materials_and_methods",
    "experimental procedures": "materials_and_methods",
    "data analysis": "materials_and_methods",
    "statistical analysis": "materials_and_methods",
    "statistical methods": "materials_and_methods",
    "statistics": "materials_and_methods",
    "sample size calculation": "materials_and_methods",
    "power analysis": "materials_and_methods",
    "sample size determination": "materials_and_methods",
    "eligibility criteria": "materials_and_methods",
    "inclusion criteria": "materials_and_methods",
    "exclusion criteria": "materials_and_methods",
    "inclusion and exclusion criteria": "materials_and_methods",
    "participants": "materials_and_methods",
    "study population": "materials_and_methods",
    "sample preparation": "materials_and_methods",
    "specimen preparation": "materials_and_methods",
    "radiographic analysis": "materials_and_methods",
    "radiographic analyses": "materials_and_methods",
    "clinical examination": "materials_and_methods",
    "clinical examinations": "materials_and_methods",
    "evaluation of volume loss": "materials_and_methods",
    "scanning": "materials_and_methods",
    "drink selection": "materials_and_methods",
    "microscope positioning and use": "materials_and_methods",
    "flap incision and elevation": "materials_and_methods",
    "root apex positioning": "materials_and_methods",
    "root end resection, curettage, and inspection": "materials_and_methods",
    "suturing": "materials_and_methods",
    "suture removal": "materials_and_methods",
    "outcome measure": "materials_and_methods",
    "outcome measures": "materials_and_methods",
    "randomization and blinding": "materials_and_methods",
    "design": "materials_and_methods",
    "sample and setting": "materials_and_methods",
    "protocol and registration": "materials_and_methods",
    "data charting and synthesis": "materials_and_methods",
    "in vivo studies": "materials_and_methods",
    "medical preparations": "materials_and_methods",
    "patient preparation": "materials_and_methods",
    "surgical area preparation": "materials_and_methods",
    "surgical procedures": "materials_and_methods",
    # Intro-like
    "research question": "introduction",
    "current medical therapy": "introduction",
    # Discussion / Conclusions-like
    "interpretation of key findings": "discussion",
    "agreements and disagreements with other studies or reviews": "discussion",
    "clinical management": "discussion",
    "grading the certainty of evidence": "discussion",
    "certainty of evidence": "discussion",
    "summary of key findings": "conclusions",
    "summary of main findings": "conclusions",
    "possible applications of research and future research directions": "conclusions",
    "clinical considerations and practical recommendations": "conclusions",
    "search strategy": "materials_and_methods",
    "study selection": "materials_and_methods",
    "data extraction": "materials_and_methods",
    "quality assessment": "materials_and_methods",
    "methodological quality": "materials_and_methods",
    "risk of bias": "materials_and_methods",
    "risk of bias assessment": "materials_and_methods",
    "indications": "materials_and_methods",
    "contraindications": "materials_and_methods",
    "systemic conditions": "materials_and_methods",
    "local conditions": "materials_and_methods",
    "preoperative examination": "materials_and_methods",
    "history and preoperative examination": "materials_and_methods",
    "results": "results",
    "discussion": "discussion",
    "limitations": "discussion",
    "strengths and limitations": "discussion",
    "conclusion": "conclusions",
    "conclusions": "conclusions",
    "clinical significance": "conclusions",
    "results and discussion": "results_and_discussion",
    "results & discussion": "results_and_discussion",
    # Boilerplate (kept here for normalization then filtered via NON_CONTENT_KEYS)
    "acknowledgements": "acknowledgements",
    "acknowledgments": "acknowledgments",
    "funding": "funding",
    "conflict of interest": "conflict_of_interest",
    "conflicts of interest": "conflicts_of_interest",
    "competing interests": "competing_interests",
    "authors' contributions": "author_contributions",
    "author contributions": "author_contributions",
    "availability of data and materials": "availability_of_data_and_materials",
    "data availability": "data_availability",
    "ethical statement": "ethical_statement",
    "ethics statement": "ethics_statement",
    "human and animal rights": "human_and_animal_rights",
    "consent for publication": "consent_for_publication",
    "list of abbreviations": "list_of_abbreviations",
    "abbreviations": "abbreviations",
    "references": "references",
    "bibliography": "bibliography",
    # --- Added batch from unmapped_head_frequencies ---
    "evaluation of ph": "materials_and_methods",
    "volume loss test": "materials_and_methods",
    "volume loss evaluation": "materials_and_methods",
    "pathological examination": "materials_and_methods",
    "postoperative management postoperative reactions": "materials_and_methods",
    "efficacy evaluation": "materials_and_methods",
    "medical records": "materials_and_methods",
    "included studies": "materials_and_methods",
    "evaluation of titratable acidity": "materials_and_methods",
    "animals": "materials_and_methods",
    "surgical interventions": "materials_and_methods",
    "primary outcome": "materials_and_methods",
    "secondary outcomes": "materials_and_methods",
    "histological preparation": "materials_and_methods",
    "analysis": "materials_and_methods",
    "histomorphometric analysis": "materials_and_methods",
    "circularly polarized light microscopy analysis": "materials_and_methods",
    "examiner calibration": "materials_and_methods",
    "clinical measurements": "materials_and_methods",
    "protocol registration number": "materials_and_methods",
    "protocol registration": "materials_and_methods",
    "screening of articles": "materials_and_methods",
    "bayesian meta-analysis": "materials_and_methods",
    "wound healing parameter evaluation": "materials_and_methods",
    "study and control samples": "materials_and_methods",
    "research systematics": "materials_and_methods",
    "gcf collection": "materials_and_methods",
    "levelling and alignment": "materials_and_methods",
    "surgical procedure": "materials_and_methods",
    "biochemical analysis": "materials_and_methods",
    "fe model creation": "materials_and_methods",
    "loading procedure": "materials_and_methods",
    "experimental setup": "materials_and_methods",
    "morphological surface and cross-sectional analysis": "materials_and_methods",
    "compositional analysis": "materials_and_methods",
    "functional group analysis": "materials_and_methods",
    "ph analysis": "materials_and_methods",
    "calcium ion release": "materials_and_methods",
    "preparation of bis-gma/tegdma composites": "materials_and_methods",
    "material testing conditions": "materials_and_methods",
    "flexural properties": "materials_and_methods",
    "compressive strength": "materials_and_methods",
    "scanning electron microscopy": "materials_and_methods",
    "calcium (ca 2+ ) and phosphate (po4 3-) release": "materials_and_methods",
    "cell cytotoxicity": "materials_and_methods",
    "mechanical performance 1. flexural strength": "materials_and_methods",
    "evaluation of surface roughness": "materials_and_methods",
    "periapical image processing": "materials_and_methods",
    "analysis of periapical images by ai model": "materials_and_methods",
    "information sources": "materials_and_methods",
    "intervention (i)": "materials_and_methods",
    "comparator or control group (c)": "materials_and_methods",
    "outcomes (o)": "materials_and_methods",
    "study design (s)": "materials_and_methods",
    "selection of studies": "materials_and_methods",
    "patient selection": "materials_and_methods",
    "vacuum plasma surface treatment": "materials_and_methods",
    "predictor and outcome variables": "materials_and_methods",
    "design and data collection": "materials_and_methods",
    "measures": "materials_and_methods",
    "the design of the questionnaire": "materials_and_methods",
    "the studied group": "materials_and_methods",
    "research protocol and search queries": "materials_and_methods",
    "review question": "introduction",
    "a brief history of artificial intelligence and its applications in dentistry": "introduction",
    "legislative context": "introduction",
    "grade approach": "discussion",
    "comparison with previous research": "discussion",
    "implications/significance of the study": "discussion",
    "main outcome of the study": "results",
    "outcomes": "results",
    "vertical bone gain": "results",
    "horizontal bone gain": "results",
    "other complications": "results",
    "clinical outcomes": "results",
    "colour maps of implantation torque values": "results",
    "comparison of measurements between implants": "results",
    "correlation": "results",
    "success rates": "results",
    "survival rates": "results",
    "complication rates": "results",
    "analysis of subdomain-diagnosis": "results",
    "analysis of subdomain-treatment planning": "results",
    "analysis of subdomain-feedback": "results",
    "case report": "results",
    "follow-up": "results",
}


def canonical_section_name(name: str) -> str:
    n = _sanitize_heading(name)
    if not n:
        return ""
    # Exact matches first
    if n in EXACT_MAP:
        return EXACT_MAP[n]
    # Composite and fuzzy matches
    # e.g., "results and discussion" variants
    if "results" in n and "discussion" in n:
        return "results_and_discussion"
    # Methods family including methodologic phrases
    if any(k in n for k in [
        "method", "methodology", "statistic", "power analysis", "sample size",
        "eligibility", "inclusion", "exclusion", "sample preparation", "specimen preparation",
        "participants", "population", "search strategy", "study selection", "data extraction",
        "quality assessment", "methodological quality", "risk of bias", "preoperative",
        "indication", "contraindication", "systemic condition", "local condition",
        "outcome measure", "randomization", "blinding", "charting", "synthesis",
    ]):
        return "materials_and_methods"
    # Intro-like
    if any(k in n for k in ["introduc", "aim", "objective", "objectives", "purpose", "background"]):
        return "introduction"
    # Conclusions-like
    if "conclusion" in n or "clinical significance" in n:
        return "conclusions"
    # Results-like
    if "result" in n:
        return "results"
    # Discussion-like
    if "discussion" in n or "limitation" in n:
        return "discussion"
    # Fallback: normalize spaces
    return n.replace(" ", "_")


def is_non_content(key: str) -> bool:
    return key in NON_CONTENT_KEYS
