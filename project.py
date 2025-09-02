# project.py
import argparse
import json
import os
from typing import Dict, List, Iterable, Optional

# ---- CS50 top-level functions (wrappers) ----

def get_pdf_text(path: str) -> str:
    """Step 4: PDF -> text (placeholder uses PDFTextExtractor)."""
    from paperslicer.extractors.text_extractor import PDFTextExtractor
    return PDFTextExtractor().extract(path)

def normalize_text(text: str) -> str:
    """Step 1: call the normalizer class (you'll implement it)."""
    from paperslicer.extractors.normalizer import TextNormalizer
    return TextNormalizer().normalize(text)

def extract_sections_from_text(text: str) -> Dict[str, str]:
    """Step 2-3: regex/heuristics for section headers (placeholder)."""
    from paperslicer.extractors.sections_regex import SectionExtractor
    return SectionExtractor().extract(text)

def process_pdf_to_record(path: str) -> Dict[str, object]:
    """Step 5+: full pipeline PDF->JSON dict (via Pipeline)."""
    from paperslicer.pipeline import Pipeline
    xml_dir: Optional[str] = (
        os.getenv("TEI_SAVE_DIR")
        or os.getenv("PAPERSLICER_XML_DIR")
        or os.path.join("data", "xml")
    )
    export_images_env = (os.getenv("EXPORT_IMAGES") or "0").lower() in {"1", "true", "yes"}
    images_mode_env = os.getenv("IMAGES_MODE") or "embedded"
    pipe = Pipeline(try_start_grobid=True, xml_save_dir=xml_dir,
                    export_images=export_images_env, images_mode=images_mode_env)
    rec = pipe.process(path)
    return rec.to_dict()

# ---- CLI (will become useful by Step 5) ----

def _iter_pdfs(root: str) -> List[str]:
    if os.path.isdir(root):
        acc = []
        for dp, _, files in os.walk(root):
            for f in files:
                if f.lower().endswith(".pdf"):
                    acc.append(os.path.join(dp, f))
        return sorted(acc)
    return [root] if root.lower().endswith(".pdf") else []

def _write_json(obj: Dict[str, object], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _iter_json_dicts(paths: Iterable[str]) -> Iterable[Dict[str, object]]:
    for p in paths:
        try:
            yield process_pdf_to_record(p)
        except Exception as e:
            yield {"error": str(e), "meta": {"source_path": p}}


def main():
    parser = argparse.ArgumentParser(description="PaperSlicer CLI")
    parser.add_argument("path", nargs="?", help="PDF file or folder to process")
    parser.add_argument("--out", help="Output path: directory, .json, or .jsonl")
    parser.add_argument("--jsonl", action="store_true", help="Write JSON Lines format to --out")
    parser.add_argument(
        "--tei-out",
        dest="tei_out",
        help="Directory to save TEI XML from Grobid (overrides PAPERSLICER_XML_DIR)",
    )
    parser.add_argument("--mailto", help="Email for Crossref User-Agent header (metadata lookup)")
    parser.add_argument("--export-images", action="store_true", help="Export images (embedded or page previews)")
    parser.add_argument("--images-mode", choices=["embedded", "pages", "auto"], default="embedded",
                        help="Image export mode")
    parser.add_argument("--e2e", action="store_true",
                        help="Enable TEI + metadata resolution + image export (auto); defaults TEI dir to data/xml")
    parser.add_argument("--dedup", action="store_true", help="Skip duplicates by DOI or normalized title")
    parser.add_argument("--review-mode", action="store_true", help="Force review-profile augmentation")
    parser.add_argument("--tables", choices=["auto", "tei", "plumber", "detector", "docling"], default="auto",
                        help="Table extraction strategy preference")
    args = parser.parse_args()

    # Allow setting TEI output dir
    if args.tei_out:
        os.makedirs(args.tei_out, exist_ok=True)
        os.environ["TEI_SAVE_DIR"] = args.tei_out
        os.environ["PAPERSLICER_XML_DIR"] = args.tei_out
    if args.mailto:
        os.environ["CROSSREF_MAILTO"] = args.mailto
    if args.review_mode:
        os.environ["REVIEW_MODE"] = "1"
    # Table strategy toggles
    if args.tables == "tei":
        os.environ["PAPERSLICER_DISABLE_PLUMBER"] = "1"
        os.environ["PAPERSLICER_DISABLE_DETECTORS"] = "1"
    elif args.tables == "plumber":
        os.environ["PAPERSLICER_DISABLE_DETECTORS"] = "1"
    elif args.tables == "detector":
        os.environ["PAPERSLICER_DISABLE_PLUMBER"] = "1"
    elif args.tables == "docling":
        os.environ["USE_DOCLING"] = "1"
        # default: isolate docling results unless user opts in for others
        os.environ["PAPERSLICER_DISABLE_PLUMBER"] = os.environ.get("PAPERSLICER_DISABLE_PLUMBER", "1")
        os.environ["PAPERSLICER_DISABLE_DETECTORS"] = os.environ.get("PAPERSLICER_DISABLE_DETECTORS", "1")

    if not args.path:
        parser.print_help()
        return

    pdfs = _iter_pdfs(args.path)
    if not pdfs:
        print("No PDFs found.")
        return

    out = args.out
    # Default output directory if not provided
    if not out:
        out = os.path.join("out", "meta")

    # E2E convenience setup
    if args.e2e:
        # Default TEI save dir if not provided and not set
        if not args.tei_out and not os.getenv("TEI_SAVE_DIR") and not os.getenv("PAPERSLICER_XML_DIR"):
            default_xml = os.path.join("data", "xml")
            os.makedirs(default_xml, exist_ok=True)
            os.environ["TEI_SAVE_DIR"] = default_xml
            os.environ["PAPERSLICER_XML_DIR"] = default_xml
        # Force image export auto mode
        os.environ["EXPORT_IMAGES"] = "1"
        os.environ["IMAGES_MODE"] = "auto"

    # Propagate image export flags via env for process_pdf_to_record
    if args.export_images:
        os.environ["EXPORT_IMAGES"] = "1"
    if args.images_mode:
        os.environ["IMAGES_MODE"] = args.images_mode

    # JSONL mode
    if args.jsonl or (out.lower().endswith(".jsonl")):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        count = 0
        seen_doi = set()
        seen_title = set()
        with open(out, "w", encoding="utf-8") as fh:
            for d in _iter_json_dicts(pdfs):
                if args.dedup and isinstance(d, dict):
                    doi = ((d.get("meta") or {}).get("doi") or "").strip().lower()
                    title = ((d.get("meta") or {}).get("title") or "").strip().lower()
                    key = doi or title
                    if key:
                        if doi and doi in seen_doi:
                            continue
                        if (not doi) and title and title in seen_title:
                            continue
                        if doi:
                            seen_doi.add(doi)
                        elif title:
                            seen_title.add(title)
                fh.write(json.dumps(d, ensure_ascii=False) + "\n")
                count += 1
        print(f"Wrote {count} records to {out}")
        return

    # If output is a directory, write one JSON per PDF
    if os.path.isdir(out) or not out.lower().endswith(".json"):
        os.makedirs(out, exist_ok=True)
        seen_doi = set()
        seen_title = set()
        written = 0
        for p in pdfs:
            d = process_pdf_to_record(p)
            if args.dedup and isinstance(d, dict):
                doi = ((d.get("meta") or {}).get("doi") or "").strip().lower()
                title = ((d.get("meta") or {}).get("title") or "").strip().lower()
                key = doi or title
                if key:
                    if doi and doi in seen_doi:
                        continue
                    if (not doi) and title and title in seen_title:
                        continue
                    if doi:
                        seen_doi.add(doi)
                    elif title:
                        seen_title.add(title)
            stem = os.path.splitext(os.path.basename(p))[0]
            _write_json(d, os.path.join(out, f"{stem}.json"))
            written += 1
        print(f"Wrote {written} JSON files to {out}")
        return

    # If a single .json path provided
    if len(pdfs) == 1:
        _write_json(process_pdf_to_record(pdfs[0]), out)
        print(f"Wrote JSON to {out}")
    else:
        # Multiple PDFs -> write a list into the single JSON file
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        payload = list(_iter_json_dicts(pdfs))
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(payload)} records to {out}")

if __name__ == "__main__":
    main()
