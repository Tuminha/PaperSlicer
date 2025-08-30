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
        "--review-mode",
        action="store_true",
        help="Enable review-aware fallback to augment sections for review/consensus papers",
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
        "--images-mode",
        choices=["auto", "coords-only", "pages-large"],
        default=os.getenv("IMAGES_MODE", "auto"),
        help="Image export mode: 'auto' (coords then fallback), 'coords-only' (no fallback), 'pages-large' (fallback but filter small/page renders)",
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
    parser.add_argument(
        "--tei-refresh",
        action="store_true",
        help="Regenerate TEI via GROBID even if an existing TEI file is present",
    )
    parser.add_argument(
        "--images-summary",
        action="store_true",
        help="Write a CSV summary of image exports for all JSONs in out/meta",
    )
    parser.add_argument(
        "--rag-jsonl",
        help="Export a RAG-ready JSONL from out/meta with chunked sections (provide output path)",
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
        from paperslicer.grobid.sections import extract_unmapped_sections
        from paperslicer.grobid.figures import parse_figures_tables, parse_table_data
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
        # figures/tables metadata and rows
        try:
            items = parse_figures_tables(args.path)
            if items:
                md["figures_list"] = [it for it in items if it.get("type") == "figure"]
                md["tables_list"] = [it for it in items if it.get("type") == "table"]
            trows = parse_table_data(args.path)
            if trows:
                md["tables_data"] = trows
        except Exception:
            pass
        # extras (thematic unmapped sections)
        try:
            extras = extract_unmapped_sections(args.path)
            if extras:
                md["sections_extra"] = extras
        except Exception:
            pass
        # Optional review-aware augmentation
        try:
            if args.review_mode:
                sec_keys_local = [
                    "introduction",
                    "materials_and_methods",
                    "results",
                    "discussion",
                    "conclusions",
                ]
                cov = sum(1 for k in sec_keys_local if (md.get(k) or "").strip())
                extras = md.get("sections_extra") or []
                if cov < 3 and len(extras) >= 5:
                    def pick(extras_list, keywords):
                        out_chunks = []
                        for ex in extras_list:
                            head = (ex.get("head") or "").lower()
                            if any(kw in head for kw in keywords):
                                txt = (ex.get("text") or "").strip()
                                if txt:
                                    out_chunks.append(txt)
                        return "\n\n".join(out_chunks).strip()
                    intro_kw = ["overview", "scope", "background", "aim", "purpose"]
                    meth_kw = ["study selection","eligibility","information sources","search strategy","data extraction","risk of bias","data synthesis","methodology","sample size"]
                    res_kw = ["included studies","findings","outcomes","meta-analysis","meta analysis","evidence"]
                    disc_kw = ["limitations","challenges","perspectives","practice points","implications","recommendations"]
                    concl_kw = ["summary","decision-making","decision making","concluding remarks","conclusion","clinical significance","implications"]
                    if not (md.get("introduction") or "").strip():
                        agg = pick(extras, intro_kw)
                        if agg:
                            md["augmented_introduction"] = agg
                    if not (md.get("materials_and_methods") or "").strip():
                        agg = pick(extras, meth_kw)
                        if agg:
                            md["augmented_materials_and_methods"] = agg
                    if not (md.get("results") or "").strip():
                        agg = pick(extras, res_kw)
                        if agg:
                            md["augmented_results"] = agg
                    if not (md.get("discussion") or "").strip():
                        agg = pick(extras, disc_kw)
                        if agg:
                            md["augmented_discussion"] = agg
                    if not (md.get("conclusions") or "").strip():
                        agg = pick(extras, concl_kw)
                        if agg:
                            md["augmented_conclusions"] = agg
        except Exception:
            pass
        refs_text = extract_references(args.path) or ""
        if refs_text:
            md["references"] = refs_text
        # Add structured references too
        try:
            from paperslicer.grobid.refs import parse_references, format_references_list
            refs_list = parse_references(args.path)
            if refs_list:
                md["references_list"] = refs_list
                md["references_citations"] = format_references_list(refs_list)
                md["references_text"] = "\n".join(md["references_citations"])[:50000]
                md["references"] = md.get("references_text") or md.get("references")
        except Exception:
            pass
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
        from paperslicer.grobid.sections import extract_unmapped_sections
        from paperslicer.grobid.figures import parse_figures_tables, parse_table_data
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
        # figures/tables metadata and rows
        try:
            items = parse_figures_tables(args.path)
            if items:
                md["figures_list"] = [it for it in items if it.get("type") == "figure"]
                md["tables_list"] = [it for it in items if it.get("type") == "table"]
            trows = parse_table_data(args.path)
            if trows:
                md["tables_data"] = trows
        except Exception:
            pass
        # extras (thematic unmapped sections)
        try:
            extras = extract_unmapped_sections(args.path)
            if extras:
                md["sections_extra"] = extras
        except Exception:
            pass
        # Optional review-aware augmentation
        try:
            if args.review_mode:
                sec_keys_local = [
                    "introduction",
                    "materials_and_methods",
                    "results",
                    "discussion",
                    "conclusions",
                ]
                cov = sum(1 for k in sec_keys_local if (md.get(k) or "").strip())
                extras = md.get("sections_extra") or []
                if cov < 3 and len(extras) >= 5:
                    def pick(extras_list, keywords):
                        out_chunks = []
                        for ex in extras_list:
                            head = (ex.get("head") or "").lower()
                            if any(kw in head for kw in keywords):
                                txt = (ex.get("text") or "").strip()
                                if txt:
                                    out_chunks.append(txt)
                        return "\n\n".join(out_chunks).strip()
                    intro_kw = ["overview", "scope", "background", "aim", "purpose"]
                    meth_kw = ["study selection","eligibility","information sources","search strategy","data extraction","risk of bias","data synthesis","methodology","sample size"]
                    res_kw = ["included studies","findings","outcomes","meta-analysis","meta analysis","evidence"]
                    disc_kw = ["limitations","challenges","perspectives","practice points","implications","recommendations"]
                    concl_kw = ["summary","decision-making","decision making","concluding remarks","conclusion","clinical significance","implications"]
                    if not (md.get("introduction") or "").strip():
                        agg = pick(extras, intro_kw)
                        if agg:
                            md["augmented_introduction"] = agg
                    if not (md.get("materials_and_methods") or "").strip():
                        agg = pick(extras, meth_kw)
                        if agg:
                            md["augmented_materials_and_methods"] = agg
                    if not (md.get("results") or "").strip():
                        agg = pick(extras, res_kw)
                        if agg:
                            md["augmented_results"] = agg
                    if not (md.get("discussion") or "").strip():
                        agg = pick(extras, disc_kw)
                        if agg:
                            md["augmented_discussion"] = agg
                    if not (md.get("conclusions") or "").strip():
                        agg = pick(extras, concl_kw)
                        if agg:
                            md["augmented_conclusions"] = agg
        except Exception:
            pass
        refs_text = extract_references(args.path) or ""
        if refs_text:
            md["references"] = refs_text
        try:
            from paperslicer.grobid.refs import parse_references, format_references_list
            refs_list = parse_references(args.path)
            if refs_list:
                md["references_list"] = refs_list
                md["references_citations"] = format_references_list(refs_list)
                md["references_text"] = "\n".join(md["references_citations"])[:50000]
                md["references"] = md.get("references_text") or md.get("references")
        except Exception:
            pass
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
            images_mode=args.images_mode,
            progress=args.progress,
            review_mode=args.review_mode,
            tei_refresh=args.tei_refresh,
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

    # Utilities: images summary and RAG export
    if args.images_summary:
        try:
            from paperslicer.utils.exports import write_images_summary
            csv_path = write_images_summary(meta_dir=os.getenv("DEBUG_OUT_DIR", "out/meta"))
            print(f"Wrote image summary CSV to: {csv_path}")
        except Exception as e:
            print(f"Failed to write images summary: {e}")
        return
    if args.rag_jsonl:
        try:
            from paperslicer.utils.exports import export_rag_jsonl
            outp = export_rag_jsonl(meta_dir=os.getenv("DEBUG_OUT_DIR", "out/meta"), out_path=args.rag_jsonl)
            print(f"Wrote RAG JSONL to: {outp}")
        except Exception as e:
            print(f"Failed to export RAG JSONL: {e}")
        return

    # For now, keep CLI inert so you can focus on tests-driven coding
    print("PaperSlicer CLI is WIP. Implement steps in order and run pytest first.")

if __name__ == "__main__":
    main()
