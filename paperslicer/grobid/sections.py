from typing import Optional
from lxml import etree

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}

from paperslicer.utils.sections_mapping import is_heading_of


def _norm_text(s: str) -> str:
    return " ".join((s or "").split()).strip()


def _is_intro_head(head_text: Optional[str]) -> bool:
    return bool(head_text) and is_heading_of(head_text or "", "introduction")


def extract_introduction_from_root(root: etree._Element) -> Optional[str]:
    return _extract_section_from_root(root, canonical="introduction", type_hints=("introduction", "background"))


def extract_introduction(tei_path: str) -> Optional[str]:
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()
    return extract_introduction_from_root(root)


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
    # Gather text recursively from descendants, excluding <head>
    parts: list[str] = []
    for el in node.iter():
        if el.tag.endswith('}head'):
            continue
        txt = _norm_text("".join(el.itertext()))
        if txt:
            parts.append(txt)
    # De-duplicate consecutive identical chunks
    collapsed: list[str] = []
    for p in parts:
        if not collapsed or collapsed[-1] != p:
            collapsed.append(p)
    text = "\n\n".join(collapsed)
    return text or None


def extract_methods(tei_path: str) -> Optional[str]:
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()
    return _extract_section_from_root(root, canonical="materials_and_methods", type_hints=("methods", "materialsMethods"))


def extract_results(tei_path: str) -> Optional[str]:
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()
    return _extract_section_from_root(root, canonical="results", type_hints=("results",))


def extract_discussion(tei_path: str) -> Optional[str]:
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()
    return _extract_section_from_root(root, canonical="discussion", type_hints=("discussion",))


def extract_conclusions(tei_path: str) -> Optional[str]:
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()
    return _extract_section_from_root(root, canonical="conclusions", type_hints=("conclusion", "conclusions", "clinicalSignificance"))


def extract_results_and_discussion(tei_path: str) -> Optional[str]:
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()
    # Some TEI may type combined sections with custom types; rely on heading mapping primarily
    return _extract_section_from_root(
        root,
        canonical="results_and_discussion",
        type_hints=("resultsAndDiscussion", "resultsDiscussion"),
    )


def extract_references(tei_path: str) -> Optional[str]:
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()
    return _extract_section_from_root(root, canonical="references", type_hints=("references",))
