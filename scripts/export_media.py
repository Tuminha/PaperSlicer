#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import List, Dict, Any, Iterable


def _iter_pdfs(root: str) -> List[str]:
    if os.path.isdir(root):
        acc: List[str] = []
        for dp, _, files in os.walk(root):
            for f in files:
                if f.lower().endswith(".pdf"):
                    acc.append(os.path.join(dp, f))
        return sorted(acc)
    return [root] if root.lower().endswith(".pdf") else []


def _write_csv(rows: Iterable[List[str]], out_path: str, header: List[str]) -> None:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if header:
            w.writerow(header)
        for r in rows:
            w.writerow(r)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract images and tables from PDFs into media/ using PaperSlicer pipeline"
    )
    parser.add_argument("path", help="PDF file or directory of PDFs")
    parser.add_argument("--images-mode", choices=["embedded", "pages", "auto"], default="auto",
                        help="Image export mode: embedded images, page renders, or auto")
    parser.add_argument("--tables", choices=["auto", "tei", "plumber", "detector", "docling", "none"], default="auto",
                        help="Table extraction strategy preference")
    parser.add_argument("--grobid", action="store_true", help="Use GROBID (if reachable) for TEI and coords cropping")
    parser.add_argument("--tei-dir", help="Directory to save TEI XML (used when --grobid)")
    parser.add_argument("--out-summary", help="Directory for CSV summaries", default=os.path.join("out", "tests"))
    parser.add_argument("--no-summaries", action="store_true", help="Do not write CSV summaries")
    args = parser.parse_args()

    # Configure environment toggles for strategies
    # Images
    os.environ["EXPORT_IMAGES"] = "1"
    os.environ["IMAGES_MODE"] = args.images_mode
    # Tables
    if args.tables == "tei":
        os.environ["PAPERSLICER_DISABLE_PLUMBER"] = "1"
        os.environ["PAPERSLICER_DISABLE_DETECTORS"] = "1"
        os.environ.pop("USE_DOCLING", None)
    elif args.tables == "plumber":
        os.environ["PAPERSLICER_DISABLE_DETECTORS"] = "1"
        os.environ.pop("USE_DOCLING", None)
        os.environ.pop("PAPERSLICER_DISABLE_PLUMBER", None)
    elif args.tables == "detector":
        os.environ["PAPERSLICER_DISABLE_PLUMBER"] = "1"
        os.environ.pop("USE_DOCLING", None)
        os.environ.pop("PAPERSLICER_DISABLE_DETECTORS", None)  # allow detectors
    elif args.tables == "docling":
        os.environ["USE_DOCLING"] = "1"
        os.environ.setdefault("PAPERSLICER_DISABLE_PLUMBER", "1")
        os.environ.setdefault("PAPERSLICER_DISABLE_DETECTORS", "1")
    elif args.tables == "none":
        os.environ["PAPERSLICER_DISABLE_PLUMBER"] = "1"
        os.environ["PAPERSLICER_DISABLE_DETECTORS"] = "1"
        os.environ.pop("USE_DOCLING", None)

    # TEI save dir when using GROBID
    if args.grobid and args.tei_dir:
        os.makedirs(args.tei_dir, exist_ok=True)
        os.environ["TEI_SAVE_DIR"] = args.tei_dir
        os.environ["PAPERSLICER_XML_DIR"] = args.tei_dir

    pdfs = _iter_pdfs(args.path)
    if not pdfs:
        print("No PDFs found.")
        return 1

    # Ensure we import from the PaperSlicer package here
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from paperslicer.pipeline import Pipeline
    pipe = Pipeline(try_start_grobid=args.grobid,
                    xml_save_dir=(args.tei_dir or os.getenv("TEI_SAVE_DIR")),
                    export_images=True,
                    images_mode=args.images_mode)

    images_rows: List[List[str]] = []
    tables_rows: List[List[str]] = []

    for p in pdfs:
        try:
            rec = pipe.process(p)
        except Exception as e:
            print(f"Error processing {p}: {e}")
            continue
        # Figures summary
        for f in (rec.figures or []):
            if not isinstance(f, dict):
                continue
            images_rows.append([
                p,
                f.get("label") or "",
                f.get("caption") or "",
                f.get("path") or "",
                f.get("source") or "",
            ])
        # Tables summary
        for t in (rec.tables or []):
            if not isinstance(t, dict):
                continue
            tables_rows.append([
                p,
                t.get("label") or "",
                t.get("caption") or "",
                t.get("path") or "",
                t.get("source") or "",
                t.get("csv_path") or "",
            ])

    if not args.no_summaries:
        out_dir = args.out_summary
        os.makedirs(out_dir, exist_ok=True)
        if images_rows:
            _write_csv(images_rows, os.path.join(out_dir, "images_summary.csv"),
                       ["pdf", "label", "caption", "path", "source"])
        if tables_rows:
            _write_csv(tables_rows, os.path.join(out_dir, "tables_summary.csv"),
                       ["pdf", "label", "caption", "path", "source", "csv_path"])
        print(f"Wrote summaries to {out_dir}")

    print(f"Done. Processed {len(pdfs)} PDF(s). Media saved under 'media/'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

