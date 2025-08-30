from __future__ import annotations
import re
from typing import Dict, List, Optional
from lxml import etree

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def _text(node: Optional[etree._Element]) -> str:
    return "" if node is None else " ".join(" ".join(node.itertext()).split()).strip()


def _norm_doi(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    x = s.strip()
    x = re.sub(r"^(doi:|https?://(dx\.)?doi\.org/)", "", x, flags=re.IGNORECASE)
    x = x.lstrip("/")
    return x or None


def _parse_biblstruct(b: etree._Element) -> Dict:
    """Parse a TEI biblStruct into a normalized dict."""
    out: Dict = {}
    # Title preference: analytic/title (article) then monogr/title (journal/book)
    t_analytic = b.find(".//tei:analytic/tei:title", TEI_NS)
    t_monogr = b.find(".//tei:monogr/tei:title", TEI_NS)
    title_node = t_analytic if t_analytic is not None else t_monogr
    out["title"] = _text(title_node)

    # Journal/Container
    journal = b.find(".//tei:monogr/tei:title", TEI_NS)
    out["journal"] = _text(journal)

    # Date (year or full)
    date = b.find(".//tei:imprint/tei:date", TEI_NS)
    out["date"] = (date.get("when") if date is not None and date.get("when") else _text(date))

    # DOI
    doi = b.find(".//tei:idno[@type='DOI']", TEI_NS)
    out["doi"] = _norm_doi(_text(doi))

    # Volume/Issue/Pages
    vol = b.find(".//tei:imprint/tei:biblScope[@unit='volume']", TEI_NS)
    iss = b.find(".//tei:imprint/tei:biblScope[@unit='issue']", TEI_NS)
    pp = b.find(".//tei:imprint/tei:biblScope[@unit='pp']", TEI_NS) or b.find(
        ".//tei:imprint/tei:biblScope[@unit='page']", TEI_NS
    )
    out["volume"] = vol.get("n") if vol is not None and vol.get("n") else _text(vol)
    out["issue"] = iss.get("n") if iss is not None and iss.get("n") else _text(iss)
    out["pages"] = _text(pp)

    # Authors (prefer analytic authors; fallback monogr authors)
    authors: List[Dict] = []
    for pers in b.findall(".//tei:analytic//tei:author/tei:persName", TEI_NS) or b.findall(
        ".//tei:monogr//tei:author/tei:persName", TEI_NS
    ):
        given = _text(pers.find("./tei:forename", TEI_NS))
        family = _text(pers.find("./tei:surname", TEI_NS))
        full = _text(pers)
        authors.append({"given": given, "family": family, "full": full})
    out["authors"] = authors

    # Publisher (if present)
    pub = b.find(".//tei:imprint/tei:publisher", TEI_NS)
    out["publisher"] = _text(pub)

    # Normalize empties
    for k, v in list(out.items()):
        if v in ("", None):
            out[k] = None
    if out.get("authors") is None:
        out["authors"] = []
    return out


def parse_references_from_root(root: etree._Element) -> List[Dict]:
    """Return structured references list from TEI root if possible, else []."""
    items: List[Dict] = []
    # Prefer listBibl/biblStruct if present
    seen: set[tuple] = set()
    for b in root.findall(".//tei:listBibl/tei:biblStruct", TEI_NS):
        rec = _parse_biblstruct(b)
        key = (
            (rec.get("doi") or "").lower(),
            (rec.get("title") or "").lower(),
            (rec.get("journal") or "").lower(),
            (rec.get("date") or "").lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        items.append(rec)
    return items


def parse_references(tei_path: str) -> List[Dict]:
    """
    Parse references from TEI into a list of dicts.
    Strategy:
      1) Use listBibl/biblStruct if present.
      2) Fallback: split the raw references section text into entries, extracting DOI and year heuristically.
    """
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()
    items = parse_references_from_root(root)
    if items:
        return items

    # Fallback to heuristics from the raw references section
    from paperslicer.grobid.sections import extract_references

    raw = extract_references(tei_path) or ""
    if not raw.strip():
        return []
    # Normalize whitespace
    txt = " ".join(raw.split())

    # Split on DOI boundaries to isolate references when possible
    # Keep the DOI with the chunk using a regex split that captures the separator
    doi_regex = re.compile(r"(10\.[0-9]{4,9}/\S+)")
    parts: List[str] = []
    last = 0
    for m in doi_regex.finditer(txt):
        start = m.start()
        if start > last:
            parts.append(txt[last:start].strip())
        parts.append(m.group(1))
        last = m.end()
    if last < len(txt):
        parts.append(txt[last:].strip())

    # Recombine into entries: assume pattern [pre, doi, post] repeating
    entries: List[str] = []
    i = 0
    while i < len(parts):
        if parts[i].startswith("10."):
            # missing leading context; merge with previous if exists
            if entries:
                entries[-1] = (entries[-1] + " " + parts[i]).strip()
            else:
                entries.append(parts[i])
            i += 1
            continue
        seg = parts[i]
        doi = parts[i + 1] if i + 1 < len(parts) and parts[i + 1].startswith("10.") else None
        tail = parts[i + 2] if doi and i + 2 < len(parts) else None
        if doi:
            entries.append(" ".join(x for x in [seg, doi, tail] if x))
            i += 3 if tail is not None else 2
        else:
            # no DOI nearby; split further by year markers to avoid giant blocks
            chunks = re.split(r"\b(19|20)\d{2}\b", seg)
            if len(chunks) > 1:
                # reattach the year token to each preceding chunk
                acc = []
                for j in range(0, len(chunks) - 1, 2):
                    acc.append((chunks[j] + " " + chunks[j + 1]).strip())
                entries.extend([c for c in acc if c])
            else:
                entries.append(seg)
            i += 1

    # Clean and dedupe consecutive duplicates
    cleaned: List[str] = []
    for e in entries:
        e = " ".join(e.split())
        if not e:
            continue
        if not cleaned or cleaned[-1] != e:
            cleaned.append(e)

    out: List[Dict] = []
    for e in cleaned:
        doi_m = doi_regex.search(e)
        year_m = re.search(r"\b(19|20)\d{2}\b", e)
        out.append({
            "raw": e,
            "doi": doi_m.group(1) if doi_m else None,
            "year": year_m.group(0) if year_m else None,
        })
    return out


# -------------------- Formatting helpers --------------------

def _initials(given: Optional[str]) -> str:
    if not given:
        return ""
    parts = re.split(r"[\s\-]+", given.strip())
    inits = "".join(p[0].upper() for p in parts if p)
    return inits


def _year_from_date(date: Optional[str]) -> Optional[str]:
    if not date:
        return None
    m = re.search(r"(19|20)\d{2}", date)
    return m.group(0) if m else None


def format_reference(rec: Dict) -> str:
    """Format one reference into a compact human-readable string (Vancouver-like)."""
    # Authors: Family Initials
    authors = rec.get("authors") or []
    auth_strs: List[str] = []
    for a in authors:
        fam = (a.get("family") or a.get("full") or "").strip()
        giv = a.get("given") or ""
        name = (fam + (" " + _initials(giv) if _initials(giv) else "")).strip()
        if name:
            auth_strs.append(name)
    authors_txt = ", ".join(auth_strs)

    title = rec.get("title") or ""
    journal = rec.get("journal") or ""
    year = _year_from_date(rec.get("date")) or ""
    vol = rec.get("volume") or ""
    iss = rec.get("issue") or ""
    pages = rec.get("pages") or ""
    doi = rec.get("doi") or ""

    parts: List[str] = []
    if authors_txt:
        parts.append(authors_txt)
    if title:
        parts.append(f"{title}.")
    tail: List[str] = []
    if journal:
        tail.append(journal)
    if year:
        tail.append(year)
    vi = ""
    if vol:
        vi = vol
        if iss:
            vi += f"({iss})"
    elif iss:
        vi = f"({iss})"
    if vi:
        tail.append(vi)
    if pages:
        tail.append(pages)
    if tail:
        parts.append(" ".join(tail))
    if doi:
        parts.append(f"doi:{doi}")
    return " ".join(p for p in parts if p).strip()


def format_references_list(items: List[Dict]) -> List[str]:
    return [format_reference(it) for it in items]
