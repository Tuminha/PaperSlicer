from typing import Dict, List, Optional
from lxml import etree

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


class TEIMetadataExtractor:
    """
    Extracts high-level metadata from a TEI XML produced by GROBID.
    Returns a dict like:
    {
      "title": "...",
      "journal": "...",
      "publisher": "...",
      "date": "YYYY-MM-DD" (when available),
      "doi": "...",
      "authors": [{"given": "...", "family": "...", "full": "...", "affiliations": ["..."]}],
      "keywords": ["..."],
      "abstract": "..."
    }
    """

    def from_file(self, tei_path: str) -> Dict:
        tree = etree.parse(tei_path)
        return self._extract(tree.getroot())

    def from_bytes(self, tei_bytes: bytes) -> Dict:
        root = etree.fromstring(tei_bytes)
        return self._extract(root)

    # ---------- internals ----------

    def _text(self, node) -> str:
        return "" if node is None else "".join(node.itertext()).strip()

    # ---- affiliation cleaning helpers ----
    def _clean_spaces(self, s: str) -> str:
        import re
        s = s.replace("\n", " ")
        s = re.sub(r"\s+", " ", s)
        s = re.sub(r"\s+,", ",", s)
        s = re.sub(r"\s+;", ";", s)
        s = re.sub(r",(\S)", r", \1", s)
        s = re.sub(r";(\S)", r"; \1", s)
        return s.strip()

    def _clean_affiliation_text(self, s: str) -> str:
        import re
        s = self._clean_spaces(s)
        s = re.sub(r"^\d+\s+", "", s)  # drop leading numeric labels
        s = s.rstrip(";,")
        parts = [p.strip() for p in s.split(",")]
        seen = set()
        dedup = []
        for p in parts:
            if not p:
                continue
            k = p.lower()
            if k not in seen:
                seen.add(k)
                dedup.append(p)
        return ", ".join(dedup)

    def _affiliation_string(self, aff_node) -> str:
        note = aff_node.find("./tei:note[@type='raw_affiliation']", TEI_NS)
        raw = self._text(note) if note is not None else ""
        if raw:
            return self._clean_affiliation_text(raw)
        # Build from structured fields
        parts: List[str] = []
        for tag in ("orgName", "address", "settlement", "region", "country"):
            for sub in aff_node.findall(f".//tei:{tag}", TEI_NS):
                t = self._text(sub)
                if t:
                    parts.append(t)
        if not parts:
            parts = [self._text(aff_node)]
        return self._clean_affiliation_text(", ".join(parts))

    def _extract(self, root) -> Dict:
        md: Dict = {}

        # Title
        title = root.find(".//tei:teiHeader//tei:titleStmt/tei:title", TEI_NS)
        md["title"] = self._text(title)

        # Journal (monogr title in sourceDesc/biblStruct)
        jtitle = root.find(".//tei:teiHeader//tei:sourceDesc//tei:monogr/tei:title", TEI_NS)
        md["journal"] = self._text(jtitle)

        # Publisher
        publisher = root.find(".//tei:teiHeader//tei:publicationStmt/tei:publisher", TEI_NS)
        md["publisher"] = self._text(publisher)

        # Date (published) — avoid boolean evaluation of Elements; check non-None explicitly
        date = root.find(
            ".//tei:teiHeader//tei:publicationStmt//tei:date[@type='published']",
            TEI_NS,
        )
        if date is None:
            date = root.find(
                ".//tei:teiHeader//tei:sourceDesc//tei:monogr//tei:imprint/tei:date",
                TEI_NS,
            )
        md["date"] = self._text(date)

        # DOI (idno type='DOI' in idno or monogr/idno)
        doi = root.find(
            ".//tei:teiHeader//tei:idno[@type='DOI']",
            TEI_NS,
        )
        if doi is None:
            doi = root.find(
                ".//tei:teiHeader//tei:sourceDesc//tei:monogr/tei:idno[@type='DOI']",
                TEI_NS,
            )
        md["doi"] = self._text(doi)

        # Keywords (when present)
        keywords: List[str] = []
        for term in root.findall(
            ".//tei:teiHeader//tei:profileDesc//tei:textClass//tei:keywords//tei:term",
            TEI_NS,
        ):
            t = self._text(term)
            if t:
                keywords.append(t)
        md["keywords"] = keywords

        # Abstract (header-first, else any abstract in text)
        abstract = root.find(".//tei:teiHeader//tei:abstract", TEI_NS)
        if abstract is None:
            abstract = root.find(".//tei:text//tei:div[@type='abstract']", TEI_NS)
        md["abstract"] = self._text(abstract)

        # Authors + affiliations (prefer analytic/authors if present; fallback to monogr)
        authors: List[Dict] = []
        seen_keys: set[str] = set()
        paths = [
            ".//tei:teiHeader//tei:sourceDesc//tei:biblStruct//tei:analytic//tei:author/tei:persName",
            ".//tei:teiHeader//tei:sourceDesc//tei:biblStruct//tei:monogr//tei:author/tei:persName",
        ]
        for path in paths:
            for pers in root.findall(path, TEI_NS):
                given = self._text(pers.find("./tei:forename", TEI_NS))
                family = self._text(pers.find("./tei:surname", TEI_NS))
                full = self._text(pers)
                key = "|".join([given, family, full])
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                affs: List[str] = []
                seen_aff: set[str] = set()
                for aff in pers.findall("../tei:affiliation", TEI_NS):
                    txt = self._affiliation_string(aff)
                    if txt and txt not in seen_aff:
                        seen_aff.add(txt)
                        affs.append(txt)
                authors.append({
                    "given": given,
                    "family": family,
                    "full": full,
                    "affiliations": affs,
                })
        md["authors"] = authors

        return md
