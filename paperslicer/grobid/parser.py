from __future__ import annotations
from typing import Dict, Any, List, Optional
from lxml import etree

from paperslicer.models import PaperRecord, Meta
from paperslicer.utils.sections_mapping import canonical_section_name, NON_CONTENT_KEYS

NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def _txt(el: Optional[etree._Element]) -> str:
    if el is None:
        return ""
    return " ".join(" ".join(el.itertext()).split())


def _first(root: etree._Element, xpath: str) -> Optional[etree._Element]:
    res = root.xpath(xpath, namespaces=NS)
    return res[0] if res else None


def _all(root: etree._Element, xpath: str) -> List[etree._Element]:
    return list(root.xpath(xpath, namespaces=NS))


NON_CONTENT_KEYS = NON_CONTENT_KEYS


def _canonical_section_name(name: str) -> str:
    return canonical_section_name(name)


def tei_to_record(tei_bytes: bytes, pdf_path: str) -> PaperRecord:
    """Map a subset of GROBID TEI to our PaperRecord.

    Conservative and simple: extract meta, a few canonical sections, and basic figure/table captions.
    """
    root = etree.fromstring(tei_bytes)

    # ---- Meta
    title_el = _first(root, "//tei:teiHeader//tei:titleStmt/tei:title")
    title = _txt(title_el)

    doi_el = _first(root, "//tei:teiHeader//tei:sourceDesc//tei:biblStruct//tei:idno[@type='DOI']")
    doi = _txt(doi_el)

    journal_el = _first(root, "//tei:teiHeader//tei:sourceDesc//tei:biblStruct/tei:monogr/tei:title")
    journal = _txt(journal_el)

    authors: List[Dict[str, Optional[str]]] = []
    for a in _all(root, "//tei:teiHeader//tei:sourceDesc//tei:biblStruct/tei:analytic/tei:author"):
        name = _txt(_first(a, "./tei:persName")) or (
            _txt(_first(a, "./tei:persName/tei:surname"))
            + ", "
            + _txt(_first(a, "./tei:persName/tei:forename"))
            if _first(a, "./tei:persName/tei:surname") is not None
            else ""
        )
        aff = _txt(_first(a, "./tei:affiliation"))
        authors.append({"name": name or None, "affiliation": aff or None})

    meta = Meta(source_path=pdf_path, title=title or None, journal=journal or None, doi=doi or None, authors=authors)

    # ---- Sections (by body div/head)
    sections: Dict[str, str] = {}
    other_sections: Dict[str, str] = {}
    for div in _all(root, "//tei:text/tei:body//tei:div"):
        head = _txt(_first(div, "./tei:head"))
        if not head:
            continue
        key = _canonical_section_name(head)
        # Exclude references and known non-content heads from body sections
        if key in {"references", "bibliography"} or key in NON_CONTENT_KEYS:
            continue
        # Skip figure/table heads that sometimes appear as body sections
        if key.startswith("fig.") or key.startswith("table"):
            continue

        content_texts: List[str] = []
        # Prefer paragraph-like nodes to avoid pulling in nested heads/captions
        for node in div.xpath(".//tei:p|.//tei:ab", namespaces=NS):
            t = _txt(node)
            if t:
                content_texts.append(t)
        body_text = "\n\n".join(content_texts)
        body_text = " ".join(body_text.split())
        if body_text:
            # Append if key repeats
            canonical_keys = {"abstract", "introduction", "materials_and_methods", "results", "discussion", "conclusions", "results_and_discussion"}
            if key in canonical_keys:
                if key in sections:
                    sections[key] += "\n\n" + body_text
                else:
                    sections[key] = body_text
            else:
                # Unmapped but potentially relevant heading: keep under other_sections using original head text
                if head in other_sections:
                    other_sections[head] += "\n\n" + body_text
                else:
                    other_sections[head] = body_text

    # ---- Abstract (often under teiHeader/profileDesc/abstract)
    abs_el = _first(root, "//tei:teiHeader//tei:profileDesc/tei:abstract")
    if abs_el is not None:
        abs_txt = _txt(abs_el)
        if abs_txt:
            sections.setdefault("abstract", abs_txt)

    # ---- Figures and Tables (basic caption harvest)
    figures: List[Dict[str, Any]] = []
    for fig in _all(root, "//tei:text//tei:figure"):
        label = _txt(_first(fig, "./tei:label"))
        caption = _txt(_first(fig, "./tei:figDesc")) or _txt(_first(fig, "./tei:head"))
        coords = None
        g = _first(fig, ".//tei:graphic")
        if g is not None:
            coords = g.get("coords")
        if caption or label:
            figures.append({
                "label": label or None,
                "caption": caption or None,
                "path": None,
                "source": "tei",
                "coords": coords,
            })

    tables: List[Dict[str, Any]] = []
    for tab in _all(root, "//tei:text//tei:table"):
        # GROBID table may have head/caption as preceding sibling div, but we try head inside table
        label = _txt(_first(tab, "./tei:head/tei:label")) or None
        caption = _txt(_first(tab, "./tei:head"))
        coords = None
        g = _first(tab, ".//tei:graphic")
        if g is not None:
            coords = g.get("coords")
        if caption or label:
            tables.append({
                "label": label or None,
                "caption": caption or None,
                "path": None,
                "source": "tei",
                "coords": coords,
            })

    # Fallback: Some journals don't emit <table>; use textual cues and <ref type="table">
    try:
        import re
        existing_labels = {t.get("label") for t in tables if t.get("label")}
        # A) refs like: Table <ref type="table">1</ref>
        for ref in _all(root, "//tei:text//tei:ref[@type='table']"):
            num = _txt(ref)
            if not num:
                continue
            label = f"Table {num}"
            if label in existing_labels:
                continue
            # find ancestor paragraph
            par = ref.getparent()
            while par is not None and par.tag != "{http://www.tei-c.org/ns/1.0}p":
                par = par.getparent()
            caption = None
            if par is not None:
                ptxt = _txt(par)
                # strip the label text if present at start
                m = re.search(r"(?i)\btable\s*" + re.escape(num) + r"\s*[:\.\-]\s*(.+)", ptxt)
                if m:
                    caption = m.group(1).strip()
                else:
                    # otherwise, use paragraph text without the-word 'Table <num>'
                    caption = re.sub(r"(?i)\btable\s*" + re.escape(num) + r"\b", "", ptxt).strip()
            tables.append({
                "label": label,
                "caption": caption or None,
                "path": None,
                "source": "tei-ref",
            })
            existing_labels.add(label)

        # B) paragraphs starting with "Table 2. ..."
        for p in _all(root, "//tei:text//tei:p"):
            t = _txt(p)
            if not t:
                continue
            m = re.match(r"(?is)^table\s+([A-Za-z0-9IVXLC]+)\s*[:\.\-]\s*(.+)", t.strip())
            if not m:
                continue
            num = m.group(1)
            label = f"Table {num}"
            if label in existing_labels:
                continue
            caption = m.group(2).strip()
            tables.append({
                "label": label,
                "caption": caption or None,
                "path": None,
                "source": "tei-text",
            })
            existing_labels.add(label)
    except Exception:
        pass

    return PaperRecord(meta=meta, sections=sections, other_sections=other_sections, figures=figures, tables=tables)
