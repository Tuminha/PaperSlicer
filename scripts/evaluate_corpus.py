#!/usr/bin/env python3
"""
Evaluate the processed corpus in out/meta and report quality metrics.

Outputs in out/tests by default:
 - corpus_quality.json: aggregate metrics
 - corpus_quality.csv: per-document summary
 - unmapped_heads.txt: TEI heads not mapped to canonical keys
 - images_summary.csv: per-image (figures+tables) existence/sizes summary

Usage:
  python3 scripts/evaluate_corpus.py \
      --meta-dir out/meta \
      --tei-dir data/xml \
      --media-root media \
      --out-dir out/tests
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from lxml import etree


TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def _txt(el: Optional[etree._Element]) -> str:
    if el is None:
        return ""
    return " ".join(" ".join(el.itertext()).split())


NON_CONTENT_KEYS = {
    "acknowledgements",
    "acknowledgments",
    "funding",
    "conflict_of_interest",
    "conflicts_of_interest",
    "competing_interests",
    "author_contributions",
    "authors_contributions",
    "contributorship",
    "availability_of_data_and_materials",
    "data_availability",
    "ethical_statement",
    "ethics_statement",
    "human_and_animal_rights",
    "patient_consent",
    "consent_for_publication",
    "list_of_abbreviations",
    "abbreviations",
    "orcid",
}


def canonical_section_name(name: str) -> str:
    n = (name or "").strip().lower()
    mapping = {
        "abstract": "abstract",
        "introduction": "introduction",
        "background": "introduction",
        "materials and methods": "materials_and_methods",
        "materials & methods": "materials_and_methods",
        "methods and materials": "materials_and_methods",
        "patients and methods": "materials_and_methods",
        "subjects and methods": "materials_and_methods",
        "methodology": "materials_and_methods",
        "experimental procedures": "materials_and_methods",
        "study design": "materials_and_methods",
        "methods": "materials_and_methods",
        "results": "results",
        "discussion": "discussion",
        "conclusion": "conclusions",
        "conclusions": "conclusions",
        "clinical significance": "conclusions",
        "results and discussion": "results_and_discussion",
        "results & discussion": "results_and_discussion",
        # boilerplate
        "acknowledgements": "acknowledgements",
        "acknowledgments": "acknowledgments",
        "funding": "funding",
        "conflict of interest": "conflict_of_interest",
        "conflicts of interest": "conflicts_of_interest",
        "competing interests": "competing_interests",
        "authors' contributions": "author_contributions",
        "author contributions": "author_contributions",
        "availability of data and materials": "availability_of_data_and_materials",
        "data availability": "data_availability",
        "ethical statement": "ethical_statement",
        "ethics statement": "ethics_statement",
        "human and animal rights": "human_and_animal_rights",
        "consent for publication": "consent_for_publication",
        "list of abbreviations": "list_of_abbreviations",
        "abbreviations": "abbreviations",
    }
    if n in mapping:
        return mapping[n]
    if "results and discussion" in n or "results & discussion" in n:
        return "results_and_discussion"
    if "method" in n or "methodology" in n:
        return "materials_and_methods"
    if "introduc" in n:
        return "introduction"
    if "conclusion" in n or "clinical significance" in n:
        return "conclusions"
    if "result" in n:
        return "results"
    if "discussion" in n:
        return "discussion"
    return n.replace(" ", "_")


def _safe_read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _collect_heads(tei_path: Path) -> List[str]:
    try:
        root = etree.parse(str(tei_path)).getroot()
        heads = [
            _txt(el) for el in root.xpath("//tei:text/tei:body//tei:div/tei:head", namespaces=TEI_NS)
        ]
        return [h for h in heads if h]
    except Exception:
        return []


def _noise_ratio(text: str) -> float:
    if not text:
        return 0.0
    total = len(text)
    # Allowed: ASCII alnum, whitespace, basic punctuation
    ok = 0
    allowed = set(" .,;:'\"!?()[]{}-_/\\\n\r\t%+*=<>")
    for ch in text:
        if ch.isascii() and (ch.isalnum() or ch in allowed or ch.isspace()):
            ok += 1
    bad = max(0, total - ok)
    return bad / total if total else 0.0


@dataclass
class DocMetrics:
    file: str
    json_path: str
    title: Optional[str]
    doi: Optional[str]
    journal: Optional[str]
    abstract_len: int
    abstract_present: bool
    sections_count: int
    canonical_present: Dict[str, bool]
    figures_count: int
    tables_count: int
    images_with_paths: int
    images_existing: int
    images_sources: Dict[str, int]
    tei_heads_total: int
    tei_mapped: int
    tei_unmapped: int
    tei_noncontent: int
    unmapped_samples: List[str]
    noise_ratio: float

def evaluate_one(doc: Dict[str, Any], tei_dir: Path, media_root: Path, json_path: Path) -> DocMetrics:
    meta = doc.get("meta") or {}
    sections = doc.get("sections") or {}
    figures = doc.get("figures") or []
    tables = doc.get("tables") or []

    title = meta.get("title")
    doi = meta.get("doi")
    journal = meta.get("journal")
    abstract = sections.get("abstract") or ""
    canonical = {
        "introduction": bool(sections.get("introduction")),
        "materials_and_methods": bool(sections.get("materials_and_methods")),
        "results": bool(sections.get("results")),
        "discussion": bool(sections.get("discussion")),
        "conclusions": bool(sections.get("conclusions")),
    }
    # Media
    images_with_paths = 0
    images_existing = 0
    images_sources: Dict[str, int] = defaultdict(int)
    for item in list(figures) + list(tables):
        src = item.get("source") or "unknown"
        images_sources[src] += 1
        p = item.get("path")
        if p:
            images_with_paths += 1
            if os.path.exists(p):
                images_existing += 1

    # TEI heads mapping
    source_path = meta.get("source_path") or ""
    stem = Path(source_path).stem if source_path else None
    tei_path = tei_dir / f"{stem}.tei.xml" if stem else None
    heads = _collect_heads(tei_path) if (tei_path and tei_path.exists()) else []
    mapped = 0
    noncontent = 0
    unmapped: List[str] = []
    for h in heads:
        key = canonical_section_name(h)
        if key in NON_CONTENT_KEYS or key in {"references", "bibliography"}:
            noncontent += 1
        elif key in {"introduction", "materials_and_methods", "results", "discussion", "conclusions", "results_and_discussion"}:
            mapped += 1
        else:
            unmapped.append(h)

    # Noise ratio from all text sections
    text_concat = "\n\n".join(v for k, v in sections.items() if v)
    nr = _noise_ratio(text_concat)

    return DocMetrics(
        file=meta.get("source_path") or "",
        json_path=str(json_path),
        title=title,
        doi=doi,
        journal=journal,
        abstract_len=len(abstract),
        abstract_present=bool(abstract and len(abstract) >= 30),
        sections_count=len(sections),
        canonical_present=canonical,
        figures_count=len(figures),
        tables_count=len(tables),
        images_with_paths=images_with_paths,
        images_existing=images_existing,
        images_sources=dict(images_sources),
        tei_heads_total=len(heads),
        tei_mapped=mapped,
        tei_unmapped=len(unmapped),
        tei_noncontent=noncontent,
        unmapped_samples=unmapped[:8],
        noise_ratio=nr,
    )


def evaluate_corpus(meta_dir: Path, tei_dir: Path, media_root: Path) -> Tuple[Dict[str, Any], List[DocMetrics]]:
    meta_dir.mkdir(parents=True, exist_ok=True)
    docs: List[Path] = sorted(p for p in meta_dir.glob("*.json"))
    results: List[DocMetrics] = []
    for jpath in docs:
        d = _safe_read_json(jpath)
        if not d:
            continue
        try:
            m = evaluate_one(d, tei_dir=tei_dir, media_root=media_root, json_path=jpath)
            results.append(m)
        except Exception:
            continue

    # Aggregate
    total = len(results)
    with_title = sum(1 for r in results if r.title)
    with_doi_or_journal = sum(1 for r in results if r.doi or r.journal)
    with_abstract = sum(1 for r in results if r.abstract_present)
    sec_ge3 = sum(1 for r in results if sum(r.canonical_present.values()) >= 3)
    sec_ge4 = sum(1 for r in results if sum(r.canonical_present.values()) >= 4)
    sec_ge5 = sum(1 for r in results if sum(r.canonical_present.values()) >= 5)
    docs_with_images = sum(1 for r in results if (r.figures_count + r.tables_count) > 0)
    docs_with_existing_images = sum(1 for r in results if r.images_existing > 0)
    tei_heads_total = sum(r.tei_heads_total for r in results)
    tei_mapped = sum(r.tei_mapped for r in results)
    tei_unmapped = sum(r.tei_unmapped for r in results)
    tei_noncontent = sum(r.tei_noncontent for r in results)
    noise_avg = sum(r.noise_ratio for r in results) / total if total else 0.0

    # Unmapped head frequency
    um_counter: Counter[str] = Counter()
    for r in results:
        um_counter.update(r.unmapped_samples)

    # Duplicates by DOI and title
    doi_counter: Counter[str] = Counter([r.doi for r in results if r.doi])
    title_counter: Counter[str] = Counter([(r.title or "").strip().lower() for r in results if r.title])
    duplicate_dois = [k for k, v in doi_counter.items() if v > 1]
    duplicate_titles = [k for k, v in title_counter.items() if v > 1]

    images_sources_totals: Counter[str] = Counter()
    for r in results:
        images_sources_totals.update(r.images_sources)

    summary: Dict[str, Any] = {
        "total_docs": total,
        "with_title": with_title,
        "with_doi_or_journal": with_doi_or_journal,
        "with_abstract_len_ge_30": with_abstract,
        "sections_ge3": sec_ge3,
        "sections_ge4": sec_ge4,
        "sections_ge5": sec_ge5,
        "docs_with_any_media": docs_with_images,
        "docs_with_existing_media_files": docs_with_existing_images,
        "tei_heads_total": tei_heads_total,
        "tei_mapped": tei_mapped,
        "tei_unmapped": tei_unmapped,
        "tei_noncontent": tei_noncontent,
        "noise_ratio_avg": noise_avg,
        "duplicate_dois": duplicate_dois,
        "duplicate_titles": duplicate_titles,
        "images_sources_totals": dict(images_sources_totals),
    }

    # Simple PASS/FAIL gates (editable thresholds)
    gates = {
        "title_rate_ge_0.99": (with_title / total >= 0.99) if total else True,
        "doi_or_journal_rate_ge_0.95": (with_doi_or_journal / total >= 0.95) if total else True,
        "abstract_rate_ge_1.0": (with_abstract / total >= 1.0) if total else True,
        "sections_ge3_rate_ge_0.85": (sec_ge3 / total >= 0.85) if total else True,
        "tei_mapping_rate_ge_0.8": ((tei_mapped / tei_heads_total) >= 0.8) if tei_heads_total else True,
        "noise_avg_le_0.02": (noise_avg <= 0.02),
        "duplicates_doi_le_1pct": (len(duplicate_dois) / total <= 0.01) if total else True,
    }
    summary["gates"] = gates
    summary["gates_pass"] = all(gates.values())

    return summary, results


def write_outputs(out_dir: Path, summary: Dict[str, Any], results: List[DocMetrics]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    # JSON summary
    (out_dir / "corpus_quality.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    # CSV per-doc
    csv_path = out_dir / "corpus_quality.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "file",
            "title",
            "doi",
            "journal",
            "abstract_len",
            "abstract_present",
            "sections_count",
            "intro",
            "methods",
            "results",
            "discussion",
            "conclusions",
            "figures_count",
            "tables_count",
            "images_with_paths",
            "images_existing",
            "tei_heads_total",
            "tei_mapped",
            "tei_unmapped",
            "tei_noncontent",
            "noise_ratio",
        ])
        for r in results:
            w.writerow([
                r.file,
                (r.title or ""),
                (r.doi or ""),
                (r.journal or ""),
                r.abstract_len,
                r.abstract_present,
                r.sections_count,
                int(r.canonical_present.get("introduction", False)),
                int(r.canonical_present.get("materials_and_methods", False)),
                int(r.canonical_present.get("results", False)),
                int(r.canonical_present.get("discussion", False)),
                int(r.canonical_present.get("conclusions", False)),
                r.figures_count,
                r.tables_count,
                r.images_with_paths,
                r.images_existing,
                r.tei_heads_total,
                r.tei_mapped,
                r.tei_unmapped,
                r.tei_noncontent,
                f"{r.noise_ratio:.4f}",
            ])

    # Unmapped heads list from aggregate counts
    unmapped_counter: Counter[str] = Counter()
    for r in results:
        for h in r.unmapped_samples:
            unmapped_counter[h] += 1
    with (out_dir / "unmapped_heads.txt").open("w", encoding="utf-8") as f:
        for head, cnt in unmapped_counter.most_common():
            f.write(f"{cnt}\t{head}\n")

    # Images summary (scan JSONs for figure/table paths and stats)
    img_csv = out_dir / "images_summary.csv"
    with img_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["doc_json", "type", "label", "source", "path", "exists", "size_bytes"])
        for r in results:
            try:
                dj = json.loads(Path(r.json_path).read_text(encoding="utf-8"))
            except Exception:
                dj = None
            if not isinstance(dj, dict):
                continue
            for kind in ("figures", "tables"):
                items = dj.get(kind) or []
                for it in items:
                    path = it.get("path")
                    exists = bool(path and os.path.exists(path))
                    size = (os.path.getsize(path) if exists else 0)
                    w.writerow([
                        r.json_path,
                        kind[:-1],
                        (it.get("label") or ""),
                        (it.get("source") or ""),
                        (path or ""),
                        int(exists),
                        size,
                    ])


def main() -> None:
    p = argparse.ArgumentParser(description="Evaluate processed corpus quality")
    p.add_argument("--meta-dir", default="out/meta", help="Directory with JSON metadata files")
    p.add_argument("--tei-dir", default="data/xml", help="Directory with TEI XML files")
    p.add_argument("--media-root", default="media", help="Root of media exports")
    p.add_argument("--out-dir", default="out/tests", help="Directory for reports")
    args = p.parse_args()

    meta_dir = Path(args.meta_dir)
    tei_dir = Path(args.tei_dir)
    media_root = Path(args.media_root)
    out_dir = Path(args.out_dir)

    summary, results = evaluate_corpus(meta_dir=meta_dir, tei_dir=tei_dir, media_root=media_root)
    write_outputs(out_dir=out_dir, summary=summary, results=results)
    print(f"Wrote summary to {out_dir}/corpus_quality.json and CSV to {out_dir}/corpus_quality.csv")


if __name__ == "__main__":
    main()
