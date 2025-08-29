import os
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, Iterable, List, Tuple

from lxml import etree

from paperslicer.utils.sections_mapping import canonicalize

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def iter_tei_files(path: str) -> Iterable[str]:
    if os.path.isfile(path) and path.lower().endswith(".xml"):
        yield path
        return
    for dp, _, files in os.walk(path):
        for f in files:
            if f.lower().endswith(".xml"):
                yield os.path.join(dp, f)


def harvest_heads(tei_path: str) -> List[str]:
    parser = etree.XMLParser(recover=True)
    root = etree.parse(tei_path, parser)
    heads = []
    for h in root.findall(".//tei:text//tei:div/tei:head", TEI_NS):
        txt = "".join(h.itertext()).strip()
        if txt:
            heads.append(txt)
    return heads


def harvest_sections(path: str) -> Tuple[Counter, Dict[str, List[str]]]:
    counts: Counter = Counter()
    unmapped: Dict[str, List[str]] = defaultdict(list)
    for tei in iter_tei_files(path):
        for head in harvest_heads(tei):
            counts[head] += 1
            can = canonicalize(head)
            if can is None:
                unmapped[tei].append(head)
    return counts, unmapped


def write_reports(path: str, out_dir: str = "out/sections") -> Dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    now = datetime.now()
    stamp = f"{now.strftime('%H%M')}_{now.strftime('%Y-%m-%d')}"
    txt_path = os.path.join(out_dir, f"harvest_{stamp}.txt")
    json_path = os.path.join(out_dir, f"harvest_{stamp}.json")

    import json

    counts, unmapped = harvest_sections(path)
    # Top headings sorted by frequency
    top = counts.most_common()

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"Harvest run at {now.isoformat(timespec='seconds')}\n")
        f.write(f"Source: {path}\n\n")
        f.write("Top headings (count, heading):\n")
        for h, c in top:
            f.write(f"{c:5d}  {h}\n")
        f.write("\nUnmapped by file:\n")
        for tei, heads in unmapped.items():
            f.write(f"- {tei}:\n")
            for h in heads:
                f.write(f"    * {h}\n")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"top": top, "unmapped": unmapped}, f, ensure_ascii=False, indent=2)

    return {"txt": txt_path, "json": json_path}

