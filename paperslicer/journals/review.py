from __future__ import annotations
from typing import Iterable
from paperslicer.models import PaperRecord
from paperslicer.utils.sections_mapping import canonical_section_name


CORE = {"abstract", "introduction", "materials_and_methods", "results", "discussion", "conclusions", "results_and_discussion"}


def should_apply(rec: PaperRecord) -> bool:
    t = (rec.meta.title or "").lower()
    j = (rec.meta.journal or "").lower()
    # Heuristics: review in title, or certain journals, or typical review sections in other_sections
    if "review" in t or "systematic" in t or "meta-analysis" in t or "periodontology 2000" in j:
        return True
    if rec.other_sections:
        heads = " ".join(h.lower() for h in rec.other_sections.keys())
        if any(k in heads for k in ["search strategy", "study selection", "data extraction", "risk of bias", "quality assessment"]):
            return True
    return False


def apply(rec: PaperRecord) -> PaperRecord:
    """
    Augment review/consensus papers:
    - Map method-like other sections into materials_and_methods
    - If discussion is weak/missing, aggregate other sections into discussion as a fallback
    - Keep original other_sections (do not delete), but enrich canonical ones
    """
    # 1) Map method-like others into methods
    for head, text in list(rec.other_sections.items()):
        key = canonical_section_name(head)
        if key == "materials_and_methods":
            if "materials_and_methods" in rec.sections:
                rec.sections["materials_and_methods"] += "\n\n" + text
            else:
                rec.sections["materials_and_methods"] = text

    # 2) If discussion absent or too short, aggregate remaining others into discussion
    disc = rec.sections.get("discussion") or ""
    if len(disc) < 300 and rec.other_sections:
        agg = []
        for head, text in rec.other_sections.items():
            # Skip items we mapped to methods above
            if canonical_section_name(head) == "materials_and_methods":
                continue
            agg.append(f"{head}\n{text}")
        if agg:
            payload = "\n\n".join(agg)
            if disc:
                rec.sections["discussion"] = disc + "\n\n" + payload
            else:
                rec.sections["discussion"] = payload
    return rec

