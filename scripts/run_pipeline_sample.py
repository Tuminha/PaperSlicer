#!/usr/bin/env python3
"""
Run the Pipeline on three example PDFs and write JSON outputs + a summary.
"""
import os
import json
from pathlib import Path

from paperslicer.pipeline import Pipeline


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    pdf_dir = root / "data" / "pdf"
    xml_dir = root / "data" / "xml"
    xml_dir.mkdir(parents=True, exist_ok=True)
    out_dir = root / "out" / "meta"
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = root / "out" / "tests"
    reports_dir.mkdir(parents=True, exist_ok=True)

    pdfs = [
        pdf_dir / "open_dentistry_journal_article1_consort_orthodontics_2024.pdf",
        pdf_dir / "open_dentistry_journal_article2_hypericum_nanoemulsion_2024.pdf",
        pdf_dir / "open_dentistry_journal_article3_root_canal_prevalence_2024.pdf",
    ]

    pipe = Pipeline(try_start_grobid=False, xml_save_dir=str(xml_dir), export_images=True, images_mode="auto")

    results = {}
    for p in pdfs:
        rec = pipe.process(str(p))
        d = rec.to_dict()
        out_path = out_dir / (p.stem + ".json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        results[str(p)] = {
            "title": d["meta"].get("title"),
            "doi": d["meta"].get("doi"),
            "journal": d["meta"].get("journal"),
            "sections": list(d["sections"].keys())[:12],
            "figures_count": len(d["figures"]),
            "tables_count": len(d["tables"]),
            "json_saved": str(out_path),
        }

    summary_path = reports_dir / "sample_run_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
