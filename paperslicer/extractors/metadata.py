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

        # Date (published)
        date = root.find(
            ".//tei:teiHeader//tei:publicationStmt//tei:date[@type='published']",
            TEI_NS,
        ) or root.find(
            ".//tei:teiHeader//tei:sourceDesc//tei:monogr//tei:imprint/tei:date",
            TEI_NS,
        )
        md["date"] = self._text(date)

        # DOI (idno type='DOI' in idno or monogr/idno)
        doi = root.find(
            ".//tei:teiHeader//tei:idno[@type='DOI']",
            TEI_NS,
        ) or root.find(
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

        # Authors + affiliations
        authors: List[Dict] = []
        for pers in root.findall(
            ".//tei:teiHeader//tei:sourceDesc//tei:monogr//tei:author/tei:persName",
            TEI_NS,
        ):
            given = self._text(pers.find("./tei:forename", TEI_NS))
            family = self._text(pers.find("./tei:surname", TEI_NS))
            full = self._text(pers)
            affs: List[str] = []
            for aff in pers.findall("../tei:affiliation", TEI_NS):
                txt = self._text(aff)
                if txt:
                    affs.append(txt)
            authors.append({
                "given": given,
                "family": family,
                "full": full,
                "affiliations": affs,
            })
        md["authors"] = authors

        return md

