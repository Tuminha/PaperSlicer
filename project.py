# project.py
import argparse
import json
import os


def _load_dotenv_if_present():
    """Minimal .env loader to set env vars before parsing CLI flags."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    # also try project root (one level up)
    root_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    for p in (env_path, root_env):
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k and (k not in os.environ):
                                os.environ[k] = v
            except Exception:
                pass
from typing import Dict, List

# ---- CS50 top-level functions (wrappers) ----

def get_pdf_text(path: str) -> str:
    """Step 4: PDF -> text (will use PyMuPDF)."""
    raise NotImplementedError("Implement in Step 4")

def normalize_text(text: str) -> str:
    """Step 1: call the normalizer class (you'll implement it)."""
    from paperslicer.extractors.normalizer import TextNormalizer
    return TextNormalizer().normalize(text)

def extract_sections_from_text(text: str) -> Dict[str, str]:
    """Step 2-3: regex/heuristics for section headers."""
    raise NotImplementedError("Implement in Step 2-3")

def process_pdf_to_record(path: str) -> Dict[str, object]:
    """Step 5+: full pipeline PDF->JSON dict (no dataclasses required for CS50)."""
    raise NotImplementedError("Implement in Step 5")

# ---- CS50 helper: TEI generation via GROBID ----

def grobid_generate_tei(path: str, tei_dir: str = "data/xml") -> List[str]:
    """
    Generate TEI XML files for a single PDF or a directory of PDFs.
    Returns list of saved TEI file paths.
    """
    from paperslicer.grobid.ingest import GrobidIngestor

    ing = GrobidIngestor(tei_dir=tei_dir)
    if not ing.client.is_available():
        raise SystemExit(
            "GROBID not available. Start it and set GROBID_URL, or use Docker."
        )
    return ing.ingest_path(path)

def extract_metadata_from_tei(tei_path: str) -> Dict:
    """Parse a TEI XML and return metadata dict."""
    from paperslicer.extractors.metadata import TEIMetadataExtractor

    return TEIMetadataExtractor().from_file(tei_path)

def resolve_metadata(tei_path: str, mailto: str = "you@example.com") -> Dict:
    """Enrich metadata from TEI using Crossref/PubMed fallbacks."""
    from paperslicer.metadata.resolver import MetadataResolver
    return MetadataResolver(mailto=mailto).resolve_from_tei(tei_path)

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

def main():
    # best-effort: load .env if present so env vars (mailto, keys) are available
    _load_dotenv_if_present()
    parser = argparse.ArgumentParser(description="PaperSlicer (WIP)")
    parser.add_argument("path", nargs="?", help="PDF file or folder")
    parser.add_argument("--out", help="Output .json or .jsonl")
    parser.add_argument("--jsonl", action="store_true", help="Write JSON Lines format")
    parser.add_argument(
        "--tei-out",
        dest="tei_out",
        help="Directory to save TEI XML from Grobid (overrides PAPERSLICER_XML_DIR)",
    )
    parser.add_argument(
        "--tei-only",
        action="store_true",
        help="Only generate TEI XML using GROBID (no further processing)",
    )
    parser.add_argument(
        "--tei-dir",
        default=os.getenv("TEI_SAVE_DIR", "data/xml"),
        help="Directory to save TEI XML (default: data/xml)",
    )
    parser.add_argument(
        "--meta",
        action="store_true",
        help="Treat PATH as a TEI file and print extracted metadata JSON",
    )
    parser.add_argument(
        "--resolve-meta",
        action="store_true",
        help="Enrich TEI metadata using online sources (Crossref / PubMed)",
    )
    parser.add_argument(
        "--mailto",
        default=os.getenv("CROSSREF_MAILTO", "you@example.com"),
        help="Contact email for Crossref User-Agent header",
    )
    parser.add_argument(
        "--e2e",
        action="store_true",
        help="End-to-end: PDFs → TEI → metadata → debug JSON + report",
    )
    parser.add_argument(
        "--reports-dir",
        default=os.getenv("REPORTS_DIR", "out/tests"),
        help="Directory to write test reports (txt)",
    )
    parser.add_argument(
        "--export-images",
        action="store_true",
        help="When used with --e2e, export images from PDFs and add figure/table metadata",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Show real-time progress for --e2e runs",
    )
    parser.add_argument(
        "--harvest-sections",
        action="store_true",
        help="Scan TEI files under PATH and report discovered section headings",
    )
    args = parser.parse_args()

    # Normalize TEI dir flags: --tei-out (legacy) overrides --tei-dir if provided
    if args.tei_out:
        args.tei_dir = args.tei_out
    if args.tei_dir:
        os.makedirs(args.tei_dir, exist_ok=True)
        # Prefer TEI_SAVE_DIR; also set legacy env for compatibility
        os.environ["TEI_SAVE_DIR"] = args.tei_dir
        os.environ["PAPERSLICER_XML_DIR"] = args.tei_dir
    
    # Metadata-only mode: parse a TEI and print metadata JSON
    if args.meta:
        if not args.path:
            print("Please provide a TEI file path.")
            return
        if not os.path.isfile(args.path):
            print(f"File not found: {args.path}")
            return
        from paperslicer.extractors.metadata import TEIMetadataExtractor
        from paperslicer.grobid.sections import (
            extract_introduction,
            extract_methods,
            extract_results,
            extract_discussion,
            extract_conclusions,
            extract_results_and_discussion,
            extract_references,
        )
        md = TEIMetadataExtractor().from_file(args.path)
        # include major sections in output and saved JSON
        md["introduction"] = extract_introduction(args.path) or ""
        md["materials_and_methods"] = extract_methods(args.path) or ""
        md["results"] = extract_results(args.path) or ""
        md["discussion"] = extract_discussion(args.path) or ""
        md["conclusions"] = extract_conclusions(args.path) or ""
        rd_combined = extract_results_and_discussion(args.path) or ""
        if rd_combined:
            md["results_and_discussion"] = rd_combined
            if not md["results"]:
                md["results"] = rd_combined
            if not md["discussion"]:
                md["discussion"] = rd_combined
        refs_text = extract_references(args.path) or ""
        if refs_text:
            md["references"] = refs_text
        print(json.dumps(md, ensure_ascii=False, indent=2))
        # Save a debug JSON under out/meta
        try:
            from paperslicer.utils.debug import save_metadata_json
            saved_path = save_metadata_json(md)
            print(f"Saved debug JSON to: {saved_path}")
        except Exception:
            pass
        return

    # Resolve/enrich metadata via Crossref/PubMed
    if args.resolve_meta:
        if not args.path:
            print("Please provide a TEI file path.")
            return
        if not os.path.isfile(args.path):
            print(f"File not found: {args.path}")
            return
        from paperslicer.grobid.sections import (
            extract_introduction,
            extract_methods,
            extract_results,
            extract_discussion,
            extract_conclusions,
            extract_results_and_discussion,
            extract_references,
        )
        md = resolve_metadata(args.path, mailto=args.mailto)
        # include major sections in output and saved JSON
        md["introduction"] = extract_introduction(args.path) or ""
        md["materials_and_methods"] = extract_methods(args.path) or ""
        md["results"] = extract_results(args.path) or ""
        md["discussion"] = extract_discussion(args.path) or ""
        md["conclusions"] = extract_conclusions(args.path) or ""
        rd_combined = extract_results_and_discussion(args.path) or ""
        if rd_combined:
            md["results_and_discussion"] = rd_combined
            if not md["results"]:
                md["results"] = rd_combined
            if not md["discussion"]:
                md["discussion"] = rd_combined
        refs_text = extract_references(args.path) or ""
        if refs_text:
            md["references"] = refs_text
        print(json.dumps(md, ensure_ascii=False, indent=2))
        # Save a debug JSON under out/meta
        try:
            from paperslicer.utils.debug import save_metadata_json
            saved_path = save_metadata_json(md)
            print(f"Saved debug JSON to: {saved_path}")
        except Exception:
            pass
        return

    # End-to-end batch: PDFs -> TEI -> metadata -> debug JSON + report
    if args.e2e:
        if not args.path:
            print("Please provide a PDF file or folder.")
            return
        from paperslicer.pipeline import run_corpus_e2e
        report = run_corpus_e2e(
            input_path=args.path,
            tei_dir=args.tei_dir,
            debug_out_dir=os.getenv("DEBUG_OUT_DIR", "out/meta"),
            mailto=args.mailto,
            export_images=args.export_images,
            progress=args.progress,
        )
        print(f"E2E report written to: {report}")
        return

    # Harvest section headings from TEI files
    if args.harvest_sections:
        if not args.path:
            print("Please provide a TEI file or folder.")
            return
        from paperslicer.utils.harvest_sections import write_reports
        reports = write_reports(args.path)
        print(f"Harvest reports written to: {reports['txt']} and {reports['json']}")
        return

    # TEI-only mode: just generate TEI XML under the chosen directory
    if args.tei_only:
        if not args.path:
            print("Please provide a PDF file or folder path.")
            return
        saved = grobid_generate_tei(args.path, tei_dir=args.tei_dir)
        print(f"Saved {len(saved)} TEI file(s):")
        for p in saved:
            print("  ", p)
        return

    # For now, keep CLI inert so you can focus on tests-driven coding
    print("PaperSlicer CLI is WIP. Implement steps in order and run pytest first.")

if __name__ == "__main__":
    main()
