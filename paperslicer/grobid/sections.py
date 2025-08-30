from typing import Optional, List, Dict
import copy
import re
from lxml import etree

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}

from paperslicer.utils.sections_mapping import is_heading_of, canonicalize


def _norm_text(s: str) -> str:
    return " ".join((s or "").split()).strip()


def _is_intro_head(head_text: Optional[str]) -> bool:
    return bool(head_text) and is_heading_of(head_text or "", "introduction")


def extract_introduction_from_root(root: etree._Element) -> Optional[str]:
    return _extract_section_from_root(root, canonical="introduction", type_hints=("introduction", "background"))


def extract_introduction(tei_path: str) -> Optional[str]:
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()
    # Try body first
    body = _extract_section_aggregate_from_root(root, canonical="introduction", type_hints=("introduction", "background"))
    if (body or "").strip():
        return body
    # Fallback: introduction under abstract (e.g., heads inside teiHeader/profileDesc/abstract)
    abs_intro = _extract_section_from_abstract(root, canonical="introduction")
    if (abs_intro or "").strip():
        return abs_intro
    # Fallback 2: labeled paragraph inside abstract
    abs_label = _extract_labeled_from_abstract(root, start_labels=("introduction", "background"))
    return abs_label or None


def _extract_section_from_root(
    root: etree._Element,
    canonical: str,
    type_hints: tuple[str, ...] = (),
) -> Optional[str]:
    # Prefer explicit type markers if present
    node = None
    for t in type_hints:
        found = root.find(f".//tei:text//tei:div[@type='{t}']", TEI_NS)
        if found is not None:
            node = found
            break
    if node is None:
        # Otherwise, find first div with a head matching our canonical mapping
        for div in root.findall(".//tei:text//tei:div", TEI_NS):
            head = div.find("./tei:head", TEI_NS)
            head_txt = _norm_text("".join(head.itertext()) if head is not None else "")
            if is_heading_of(head_txt, canonical):
                node = div
                break
    if node is None:
        return None
    # Build cleaned text: remove citation refs and artifacts
    def clean_text(el: etree._Element) -> str:
        # work on a deepcopy to safely remove bibl refs
        cp = copy.deepcopy(el)
        for ref in cp.findall('.//tei:ref[@type="bibr"]', TEI_NS):
            parent = ref.getparent()
            if parent is not None:
                parent.remove(ref)
        # exclude head tags
        for h in cp.findall('.//tei:head', TEI_NS):
            parent = h.getparent()
            if parent is not None:
                parent.remove(h)
        s = "\n\n".join(_norm_text(x) for x in ["".join(cp.itertext())])
        # strip bracketed numeric citations like [1], [2,3], [12-15]
        s = re.sub(r"\[(?:\s*\d+(?:\s*[-–]\s*\d+)?\s*(?:,\s*\d+(?:\s*[-–]\s*\d+)?)*)\]", "", s)
        # remove isolated numbers on their own lines
        s = re.sub(r"\n+\d+\n+", "\n\n", s)
        # remove leading pipe markers on lines
        s = re.sub(r"(?m)^\|\s*", "", s)
        return s.strip()

    text = clean_text(node)
    return text or None


def _extract_section_aggregate_from_root(
    root: etree._Element,
    canonical: str,
    type_hints: tuple[str, ...] = (),
) -> Optional[str]:
    """Concatenate text from all divs matching a canonical section.

    1) Prefer any divs with explicit @type matching hints.
    2) Else, include all divs whose head maps to the canonical id.
    """
    nodes: List[etree._Element] = []
    # 1) explicit types
    for t in type_hints:
        nodes.extend(root.findall(f".//tei:text//tei:div[@type='{t}']", TEI_NS))
    # 2) head mapping
    if not nodes:
        for div in root.findall(".//tei:text//tei:div", TEI_NS):
            head = div.find("./tei:head", TEI_NS)
            head_txt = _norm_text("".join(head.itertext()) if head is not None else "")
            if is_heading_of(head_txt, canonical):
                nodes.append(div)
    if not nodes:
        return None
    parts: List[str] = []
    def node_text(n: etree._Element) -> str:
        cp = copy.deepcopy(n)
        for ref in cp.findall('.//tei:ref[@type="bibr"]', TEI_NS):
            par = ref.getparent()
            if par is not None:
                par.remove(ref)
        for h in cp.findall('.//tei:head', TEI_NS):
            par = h.getparent()
            if par is not None:
                par.remove(h)
        s = "\n\n".join(_norm_text(x) for x in ["".join(cp.itertext())])
        s = re.sub(r"\[(?:\s*\d+(?:\s*[-–]\s*\d+)?\s*(?:,\s*\d+(?:\s*[-–]\s*\d+)?)*)\]", "", s)
        s = re.sub(r"\n+\d+\n+", "\n\n", s)
        s = re.sub(r"(?m)^\|\s*", "", s)
        return s.strip()
    for n in nodes:
        txt = node_text(n)
        if txt and (not parts or parts[-1] != txt):
            parts.append(txt)
    out = "\n\n".join(parts).strip()
    return out or None


def _extract_section_from_abstract(
    root: etree._Element,
    canonical: str,
    type_hints: tuple[str, ...] = (),
) -> Optional[str]:
    nodes: List[etree._Element] = []
    # Prefer explicit types if any (rare in abstracts)
    for t in type_hints:
        nodes.extend(root.findall(f".//tei:teiHeader//tei:abstract//tei:div[@type='{t}']", TEI_NS))
    # Otherwise pick by head mapping under abstract
    if not nodes:
        for div in root.findall(".//tei:teiHeader//tei:abstract//tei:div", TEI_NS):
            head = div.find("./tei:head", TEI_NS)
            head_txt = _norm_text("".join(head.itertext()) if head is not None else "")
            if is_heading_of(head_txt, canonical):
                nodes.append(div)
    if not nodes:
        return None
    parts: List[str] = []
    def node_text(n: etree._Element) -> str:
        cp = copy.deepcopy(n)
        for ref in cp.findall('.//tei:ref[@type="bibr"]', TEI_NS):
            par = ref.getparent()
            if par is not None:
                par.remove(ref)
        for h in cp.findall('.//tei:head', TEI_NS):
            par = h.getparent()
            if par is not None:
                par.remove(h)
        s = "\n\n".join(_norm_text(x) for x in ["".join(cp.itertext())])
        s = re.sub(r"\[(?:\s*\d+(?:\s*[-–]\s*\d+)?\s*(?:,\s*\d+(?:\s*[-–]\s*\d+)?)*)\]", "", s)
        s = re.sub(r"\n+\d+\n+", "\n\n", s)
        s = re.sub(r"(?m)^\|\s*", "", s)
        return s.strip()
    for n in nodes:
        txt = node_text(n)
        if txt and (not parts or parts[-1] != txt):
            parts.append(txt)
    out = "\n\n".join(parts).strip()
    return out or None


def _extract_labeled_from_text(block: str, start_labels: tuple[str, ...]) -> Optional[str]:
    """Extract text following a label like 'Results:' inside a paragraph.

    Finds the first occurrence of any start label (case-insensitive), then
    returns text up to the next known label or end of block.
    """
    if not (block or "").strip():
        return None
    text = _norm_text(block)
    low = text.lower()
    # Define candidate end-labels to stop at
    end_labels = (
        "introduction",
        "background",
        "materials and methods",
        "material and methods",
        "material and method",
        "methods",
        "results",
        "discussion",
        "conclusion",
        "conclusions",
        "clinical significance",
    )
    # Find start
    start_pos = -1
    for lab in start_labels:
        lab_low = lab.lower() + ":"
        pos = low.find(lab_low)
        if pos != -1 and (start_pos == -1 or pos < start_pos):
            start_pos = pos
            start_lab = lab_low
    if start_pos == -1:
        return None
    content_start = start_pos + len(start_lab)
    # Find nearest next label occurrence
    next_pos = -1
    for lab in end_labels:
        lab_low = lab + ":"
        p = low.find(lab_low, content_start)
        if p != -1 and (next_pos == -1 or p < next_pos):
            next_pos = p
    content = text[content_start: next_pos if next_pos != -1 else len(text)].strip()
    return content or None


def _extract_labeled_from_elements(elems: List[etree._Element], start_labels: tuple[str, ...]) -> Optional[str]:
    best: Optional[str] = None
    for el in elems:
        s = _norm_text("".join(el.itertext()))
        got = _extract_labeled_from_text(s, start_labels=start_labels)
        if got:
            if not best or len(got) > len(best):
                best = got
    return best


def _extract_labeled_from_abstract(root: etree._Element, start_labels: tuple[str, ...]) -> Optional[str]:
    elems = root.findall(".//tei:teiHeader//tei:abstract//tei:p", TEI_NS)
    return _extract_labeled_from_elements(elems, start_labels=start_labels)


def extract_methods(tei_path: str) -> Optional[str]:
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()
    return _extract_section_aggregate_from_root(root, canonical="materials_and_methods", type_hints=("methods", "materialsMethods"))


def extract_results(tei_path: str) -> Optional[str]:
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()
    body = _extract_section_aggregate_from_root(root, canonical="results", type_hints=("results",))
    if (body or "").strip():
        return body
    # Fallback A: labeled 'Results:' inline in body paragraphs
    body_ps = root.findall(".//tei:text//tei:div//tei:p", TEI_NS)
    inline_body = _extract_labeled_from_elements(body_ps, start_labels=("results",))
    if (inline_body or "").strip():
        return inline_body
    # Fallback B: labeled 'Results:' inside abstract
    inline_abs = _extract_labeled_from_abstract(root, start_labels=("results",))
    return inline_abs or None


def extract_discussion(tei_path: str) -> Optional[str]:
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()
    return _extract_section_aggregate_from_root(root, canonical="discussion", type_hints=("discussion",))


def extract_conclusions(tei_path: str) -> Optional[str]:
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()
    body = _extract_section_aggregate_from_root(root, canonical="conclusions", type_hints=("conclusion", "conclusions", "clinicalSignificance"))
    if (body or "").strip():
        return body
    # Fallback A: labeled 'Conclusion(s):' inline in body paragraphs
    body_ps = root.findall(".//tei:text//tei:div//tei:p", TEI_NS)
    inline_body = _extract_labeled_from_elements(body_ps, start_labels=("conclusions", "conclusion", "clinical significance"))
    if (inline_body or "").strip():
        return inline_body
    # Fallback B: labeled in abstract
    inline_abs = _extract_labeled_from_abstract(root, start_labels=("conclusions", "conclusion", "clinical significance"))
    return inline_abs or None


def extract_results_and_discussion(tei_path: str) -> Optional[str]:
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()
    # Some TEI may type combined sections with custom types; rely on heading mapping primarily
    return _extract_section_aggregate_from_root(
        root,
        canonical="results_and_discussion",
        type_hints=("resultsAndDiscussion", "resultsDiscussion"),
    )


def extract_references(tei_path: str) -> Optional[str]:
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()
    return _extract_section_from_root(root, canonical="references", type_hints=("references",))


def extract_unmapped_sections(tei_path: str) -> List[Dict[str, str]]:
    """Return a list of {'head': ..., 'text': ...} for sections with unmapped headings."""
    from paperslicer.utils.sections_mapping import canonicalize
    out: List[Dict[str, str]] = []
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()
    def _clean_body(el: etree._Element) -> str:
        cp = copy.deepcopy(el)
        for ref in cp.findall('.//tei:ref[@type="bibr"]', TEI_NS):
            par = ref.getparent()
            if par is not None:
                par.remove(ref)
        for h in cp.findall('.//tei:head', TEI_NS):
            par = h.getparent()
            if par is not None:
                par.remove(h)
        s = "\n\n".join(_norm_text(x) for x in ["".join(cp.itertext())])
        s = re.sub(r"\[(?:\s*\d+(?:\s*[-–]\s*\d+)?\s*(?:,\s*\d+(?:\s*[-–]\s*\d+)?)*)\]", "", s)
        s = re.sub(r"\n+\d+\n+", "\n\n", s)
        s = re.sub(r"(?m)^\|\s*", "", s)
        return s.strip()
    for div in root.findall(".//tei:text//tei:div", TEI_NS):
        head = div.find("./tei:head", TEI_NS)
        head_txt = _norm_text("".join(head.itertext()) if head is not None else "")
        if not head_txt:
            continue
        if canonicalize(head_txt) is not None:
            continue
        txt = _clean_body(div)
        if txt:
            out.append({"head": head_txt, "text": txt})
    return out
