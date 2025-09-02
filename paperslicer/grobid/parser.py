from __future__ import annotations
from typing import Dict, Any, List, Optional
from lxml import etree
import re

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


def _normalize_label(kind: str, raw_label: Optional[str], head_text: str, caption_text: str) -> Optional[str]:
    """
    Normalize figure/table labels to a consistent form like "Figure 1" or "Table 2".
    Some TEI exports (certain journals) produce concatenated digits like "51" for
    "Figure 1" due to running headers. Prefer extracting from head/caption.
    """
    kind_lc = (kind or "").strip().lower()
    # 1) Try to parse from head_text (e.g., "Figure 1 .", "Table 3.")
    head = (head_text or "").strip()
    cap = (caption_text or "").strip()
    patterns = []
    if kind_lc == "figure":
        patterns = [r"(?i)\bfig(?:ure)?\s*([A-Za-z0-9IVXLC]+)"]
    elif kind_lc == "table":
        patterns = [r"(?i)\btab(?:le)?\s*([A-Za-z0-9IVXLC]+)"]
    for s in (head, cap):
        for pat in patterns:
            m = re.search(pat, s)
            if m:
                num = m.group(1).strip().rstrip(".:)")
                return f"{kind_lc.capitalize()} {num}"
    # 2) Fall back to raw_label numeric token if it looks sane
    rl = (raw_label or "").strip()
    # If TEI label is something like "51" but head/caption contained a match above, we'd have returned already.
    # Accept a simple integer token
    m2 = re.fullmatch(r"\d{1,3}", rl)
    if m2:
        return f"{kind_lc.capitalize()} {rl}"
    # 3) Last resort: use head/caption without number
    if kind_lc == "figure" and head:
        return "Figure"
    if kind_lc == "table" and head:
        return "Table"
    return None


def _nearest_page_number(el: etree._Element) -> Optional[int]:
    """Best-effort page number for an element using nearest preceding tei:pb/@n.
    Falls back to None if not found or unparsable.
    """
    try:
        pb = el.xpath("preceding::tei:pb[1]", namespaces=NS)
        if pb:
            n = pb[0].get("n")
            if n and str(n).strip().isdigit():
                return int(str(n).strip())
    except Exception:
        pass
    return None


def _coords_with_page(el: etree._Element, coords: Optional[str]) -> Optional[str]:
    """Normalize coords to "page,x,y,w,h" if possible.
    If coords already contains 5 numbers, return as-is. If 4 numbers, prefix the
    nearest page number if available.
    """
    if not coords:
        return None
    # extract numbers from coords (space/comma/semicolon separated)
    parts = re.split(r"[;,\s]+", coords.strip())
    nums: List[float] = []
    for p in parts:
        if not p:
            continue
        try:
            nums.append(float(p))
        except Exception:
            pass
    if len(nums) >= 5:
        # assume already includes page
        return ",".join(str(int(nums[0] if i == 0 else nums[i])) if i == 0 else (str(nums[i])) for i in range(5))
    if len(nums) >= 4:
        page = _nearest_page_number(el)
        if page is not None:
            x, y, w, h = nums[:4]
            return f"{page},{x},{y},{w},{h}"
    return None


def _coords_from_facs(root: etree._Element, el: etree._Element) -> Optional[str]:
    """
    Resolve coordinates via facsimile/zone when element carries @facs="#zoneId".
    Returns "page,x,y,w,h" string when resolvable.
    """
    try:
        facs = el.get("facs")
        if not facs and el.attrib:
            # try namespaced attribute if any (some TEI exports)
            facs = el.attrib.get("{http://www.w3.org/2000/xmlns/}facs")
        if not facs or not facs.startswith("#"):
            return None
        zone_id = facs[1:]
        z = root.xpath(f"//tei:zone[@xml:id='{zone_id}']", namespaces=NS)
        if not z:
            return None
        zone = z[0]
        surface = zone.getparent()
        if surface is None or not surface.tag.endswith("surface"):
            return None
        page_n = surface.get("n")
        try:
            page = int(str(page_n)) if page_n and str(page_n).strip().isdigit() else None
        except Exception:
            page = None
        ulx = float(zone.get("ulx"))
        uly = float(zone.get("uly"))
        lrx = float(zone.get("lrx"))
        lry = float(zone.get("lry"))
        w = max(0.0, lrx - ulx)
        h = max(0.0, lry - uly)
        if page is not None:
            return f"{page},{ulx},{uly},{w},{h}"
        # if page unknown, leave None; exporter requires page
        return None
    except Exception:
        return None


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
    tables: List[Dict[str, Any]] = []
    fig_labels_seen = set()
    tab_labels_seen = set()

    for fig in _all(root, "//tei:text//tei:figure"):
        ftype = (fig.get("type") or "").strip().lower()
        label_raw = _txt(_first(fig, "./tei:label"))
        head_text = _txt(_first(fig, "./tei:head"))
        caption_text = _txt(_first(fig, "./tei:figDesc")) or head_text
        coords = None
        g = _first(fig, ".//tei:graphic")
        if g is not None:
            coords = _coords_with_page(fig, g.get("coords"))
        if not coords:
            coords = _coords_from_facs(root, fig)

        if ftype == "table":
            label = _normalize_label("table", label_raw, head_text, caption_text)
            if (caption_text or label):
                key = label or caption_text or ""
                if key not in tab_labels_seen:
                    tables.append({
                        "label": label or None,
                        "caption": caption_text or None,
                        "path": None,
                        "source": "tei",
                        "coords": coords,
                    })
                    tab_labels_seen.add(key)
            continue

        # default: treat as figure
        label = _normalize_label("figure", label_raw, head_text, caption_text)
        if (caption_text or label):
            key = label or caption_text or ""
            if key not in fig_labels_seen:
                figures.append({
                    "label": label or None,
                    "caption": caption_text or None,
                    "path": None,
                    "source": "tei",
                    "coords": coords,
                })
                fig_labels_seen.add(key)
    for tab in _all(root, "//tei:text//tei:table"):
        # GROBID table may have head/caption as preceding sibling div, but we try head inside table
        label_raw = _txt(_first(tab, "./tei:head/tei:label")) or None
        head_text = _txt(_first(tab, "./tei:head"))
        caption = head_text
        label = _normalize_label("table", label_raw, head_text, caption)
        coords = None
        g = _first(tab, ".//tei:graphic")
        if g is not None:
            coords = _coords_with_page(tab, g.get("coords"))
        if not coords:
            coords = _coords_from_facs(root, tab)
        if caption or label:
            key = label or caption or ""
            if key not in tab_labels_seen:
                tables.append({
                    "label": label or None,
                    "caption": caption or None,
                    "path": None,
                    "source": "tei",
                    "coords": coords,
                })
                tab_labels_seen.add(key)

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
