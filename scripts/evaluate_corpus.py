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

import sys
# Ensure repository root is on sys.path regardless of CWD
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lxml import etree
from paperslicer.utils.sections_mapping import canonical_section_name as canon_name, NON_CONTENT_KEYS


TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def _txt(el: Optional[etree._Element]) -> str:
    if el is None:
        return ""
    return " ".join(" ".join(el.itertext()).split())




def canonical_section_name(name: str) -> str:  # keep exported name for this script
    return canon_name(name)


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
    images_details: List[Dict[str, Any]]
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
    images_details: List[Dict[str, Any]] = []
    for kind, items in (("figure", figures), ("table", tables)):
        for item in items:
            src = item.get("source") or "unknown"
            p = item.get("path")
            exists = bool(p and os.path.exists(p))
            size = os.path.getsize(p) if exists else 0
            images_sources[src] += 1
            if p:
                images_with_paths += 1
                if exists:
                    images_existing += 1
            images_details.append({
                "type": kind,
                "label": item.get("label"),
                "source": src,
                "path": p,
                "exists": exists,
                "size_bytes": size,
            })

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
        images_details=images_details,
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

    # Unmapped head frequency (samples only; conservative proxy)
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

    # Build per-document payload with media details
    documents: Dict[str, Any] = {}
    for r in results:
        documents[r.json_path] = {
            "file": r.file,
            "title": r.title,
            "doi": r.doi,
            "journal": r.journal,
            "abstract_len": r.abstract_len,
            "abstract_present": r.abstract_present,
            "sections_count": r.sections_count,
            "canonical_present": r.canonical_present,
            "figures_count": r.figures_count,
            "tables_count": r.tables_count,
            "images_with_paths": r.images_with_paths,
            "images_existing": r.images_existing,
            "images_sources": r.images_sources,
            "tei_heads_total": r.tei_heads_total,
            "tei_mapped": r.tei_mapped,
            "tei_unmapped": r.tei_unmapped,
            "tei_noncontent": r.tei_noncontent,
            "noise_ratio": r.noise_ratio,
            "images": r.images_details,
        }

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
        "unmapped_head_frequencies": dict(um_counter.most_common()),
        "documents": documents,
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


def _sanitize_head_for_suggestion(h: str) -> str:
    s = (h or "").strip().lower()
    s = re.sub(r"^[|>•\-\u2013\u2014\s]+", "", s)
    s = re.sub(r"^(?:[ivxlcdm]+\.|\d+(?:\.\d+)*\.?)[\s\-:]*", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s)
    return s


def suggest_mappings(unmapped_counter: Counter[str], min_count: int = 1) -> Dict[str, str]:
    suggestions: Dict[str, str] = {}
    method_kw = (
        "analysis", "analyses", "examination", "examinations", "assessment",
        "selection", "extraction", "imaging", "radiographic", "protocol",
    )
    intro_kw = ("objective", "objectives", "aim", "purpose", "background")
    disc_kw = ("limitation", "strength")
    concl_kw = ("conclusion", "clinical significance")
    for raw, cnt in unmapped_counter.most_common():
        if cnt < min_count:
            continue
        h = _sanitize_head_for_suggestion(raw)
        if not h:
            continue
        if any(k in h for k in method_kw):
            suggestions[raw] = "materials_and_methods"
        elif any(k in h for k in intro_kw):
            suggestions[raw] = "introduction"
        elif any(k in h for k in disc_kw):
            suggestions[raw] = "discussion"
        elif any(k in h for k in concl_kw):
            suggestions[raw] = "conclusions"
    return suggestions


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
            "other_sections_count",
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
                # compute from JSON file quickly (other_sections length)
                len((json.loads(Path(r.json_path).read_text(encoding='utf-8')).get('other_sections') or {})) if Path(r.json_path).exists() else 0,
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

    # No separate images CSV; media info is embedded in JSON summary under "documents[].images"
    # Suggested mappings based on unmapped heads (heuristic)
    sugg = suggest_mappings(unmapped_counter)
    (out_dir / "mapping_suggestions.json").write_text(json.dumps(sugg, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "mapping_suggestions.txt").write_text("\n".join(f"{k} -> {v}" for k, v in sugg.items()), encoding="utf-8")


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
