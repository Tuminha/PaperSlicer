from typing import List, Dict, Optional, Tuple
from lxml import etree

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def _norm_text(node: Optional[etree._Element]) -> str:
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split()).strip()


def _build_zone_index(root: etree._Element) -> Dict[str, Tuple[int, List[float]]]:
    """Map zone xml:id -> (page, [x1,y1,x2,y2]) using facsimile/surface/zone ulx/uly/lrx/lry."""
    idx: Dict[str, Tuple[int, List[float]]] = {}
    for surf in root.findall(".//tei:facsimile/tei:surface", TEI_NS):
        page_num = surf.get("n")
        try:
            page = int(page_num) if page_num else None
        except Exception:
            page = None
        for z in surf.findall("./tei:zone", TEI_NS):
            zid = z.get("{http://www.w3.org/XML/1998/namespace}id") or z.get("xml:id") or z.get("id")
            try:
                ulx = float(z.get("ulx")) if z.get("ulx") else None
                uly = float(z.get("uly")) if z.get("uly") else None
                lrx = float(z.get("lrx")) if z.get("lrx") else None
                lry = float(z.get("lry")) if z.get("lry") else None
            except Exception:
                ulx = uly = lrx = lry = None
            if zid and None not in (ulx, uly, lrx, lry) and page:
                idx[f"#{zid}"] = (page, [ulx, uly, lrx, lry])
    return idx


def parse_figures_tables(tei_path: str) -> List[Dict]:
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser).getroot()
    return parse_figures_tables_from_root(root)


def parse_figures_tables_from_root(root: etree._Element) -> List[Dict]:
    items: List[Dict] = []
    zones = _build_zone_index(root)

    # Figures
    for fig in root.findall(".//tei:text//tei:figure", TEI_NS):
        label = fig.get("n") or _norm_text(fig.find("./tei:head", TEI_NS)) or ""
        caption = _norm_text(fig.find("./tei:figDesc", TEI_NS)) or _norm_text(fig.find("./tei:head", TEI_NS))
        facs = fig.get("facs")  # e.g., "#zone1" or "#z1 #z2"
        page = None
        bbox = None
        if facs:
            first = facs.split()[0]
            if first in zones:
                page, bbox = zones[first]
        # fallback: sometimes coords are inline attributes
        if bbox is None and fig.get("coords"):
            try:
                # try formats: "x1,y1,x2,y2" or similar
                parts = [float(x) for x in fig.get("coords").replace(",", " ").split()[:4]]
                if len(parts) == 4:
                    bbox = parts
            except Exception:
                bbox = None

        items.append({
            "type": "figure",
            "label": label or None,
            "caption": caption or None,
            "page": page or 1,
            "bbox": bbox,
        })

    # Tables (either <table> or figure type="table")
    for tab in root.findall(".//tei:text//tei:table", TEI_NS):
        head = _norm_text(tab.find("./tei:head", TEI_NS))
        caption = _norm_text(tab.find("./tei:figDesc", TEI_NS)) or head
        facs = tab.get("facs")
        page = None
        bbox = None
        if facs:
            first = facs.split()[0]
            if first in zones:
                page, bbox = zones[first]
        if bbox is None and tab.get("coords"):
            try:
                parts = [float(x) for x in tab.get("coords").replace(",", " ").split()[:4]]
                if len(parts) == 4:
                    bbox = parts
            except Exception:
                bbox = None
        items.append({
            "type": "table",
            "label": head or None,
            "caption": caption or None,
            "page": page or 1,
            "bbox": bbox,
        })

    # Figures that are actually tables
    for fig in root.findall(".//tei:text//tei:figure[@type='table']", TEI_NS):
        label = fig.get("n") or _norm_text(fig.find("./tei:head", TEI_NS)) or ""
        caption = _norm_text(fig.find("./tei:figDesc", TEI_NS)) or _norm_text(fig.find("./tei:head", TEI_NS))
        facs = fig.get("facs")
        page = None
        bbox = None
        if facs:
            first = facs.split()[0]
            if first in zones:
                page, bbox = zones[first]
        items.append({
            "type": "table",
            "label": label or None,
            "caption": caption or None,
            "page": page or 1,
            "bbox": bbox,
        })

    return items

