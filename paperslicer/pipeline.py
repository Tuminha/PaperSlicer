import os
import sys
from paperslicer.models import PaperRecord, Meta
from paperslicer.extractors.text_extractor import PDFTextExtractor
from paperslicer.extractors.normalizer import TextNormalizer
from paperslicer.extractors.sections_regex import SectionExtractor
from paperslicer.extractors.captions import CaptionExtractor

# NEW
from paperslicer.grobid.client import GrobidClient
from paperslicer.grobid.manager import GrobidManager
from lxml import etree  # for checking parseability of TEI
from datetime import datetime

from paperslicer.grobid.ingest import GrobidIngestor
from paperslicer.metadata.resolver import MetadataResolver
from paperslicer.utils.debug import save_metadata_json
from paperslicer.grobid.sections import (
    extract_introduction,
    extract_methods,
    extract_results,
    extract_discussion,
    extract_conclusions,
    extract_results_and_discussion,
    extract_unmapped_sections,
)
from paperslicer.grobid.sections import TEI_NS
from paperslicer.utils.harvest_sections import harvest_heads
from paperslicer.utils.sections_mapping import canonicalize
from paperslicer.utils.media_path import build_media_outdir
from paperslicer.grobid.sections import extract_references
from paperslicer.grobid.refs import parse_references, format_references_list
from paperslicer.journals.periodontology2000 import Periodontology2000Handler

class Pipeline:
    def __init__(self, try_start_grobid: bool = True, xml_save_dir: str | None = None):
        self.try_start_grobid = try_start_grobid
        self.xml_save_dir = xml_save_dir
        self.pdf = PDFTextExtractor()
        self.norm = TextNormalizer()
        self.sections = SectionExtractor()
        self.captions = CaptionExtractor()

    def _try_grobid(self, pdf_path: str) -> PaperRecord | None:
        mgr = GrobidManager()
        if not mgr.is_available() and self.try_start_grobid:
            mgr.start()  # best-effort; ignore result here
        
        if not mgr.is_available():
            return None

        # If available, process and map TEI to our schema
        cli = GrobidClient()
        # Auto-save TEI into data/xml by default. Allow env overrides.
        save_dir = (
            self.xml_save_dir
            or os.getenv("TEI_SAVE_DIR")
            or os.getenv("PAPERSLICER_XML_DIR")  # backward-compat
            or os.path.join("data", "xml")
        )
        tei_bytes, tei_path = cli.process_fulltext(pdf_path, save_dir=save_dir)
        # minimal TEI sanity check
        etree.fromstring(tei_bytes)

        # Very light TEI mapping for now (you’ll expand later)
        from paperslicer.grobid.parser import tei_to_record  # add this file when ready
        return tei_to_record(tei_bytes, pdf_path)

    def process(self, pdf_path: str) -> PaperRecord:
        # Prefer GROBID if reachable (or can be auto-started)
        try:
            rec = self._try_grobid(pdf_path)
            if rec is not None:
                return rec
        except Exception:
            # If GROBID fails mid-flight, fall back gracefully
            pass

        # Fallback: regex/PyMuPDF pipeline
        raw = self.pdf.extract(pdf_path)
        normalized = self.norm.normalize(raw)
        sec = self.sections.extract(normalized)
        figs = self.captions.extract_figures(normalized)
        tabs = self.captions.extract_tables(normalized)
        meta = Meta(source_path=pdf_path, title=sec.get("title"))
        return PaperRecord(meta=meta, sections=sec, figures=figs, tables=tabs)


def run_corpus_e2e(
    input_path: str,
    tei_dir: str | None = None,
    debug_out_dir: str | None = None,
    mailto: str | None = None,
    export_images: bool = False,
    images_mode: str = "auto",
    progress: bool = False,
    review_mode: bool = False,
    tei_refresh: bool = False,
) -> str:
    """
    End-to-end: PDFs -> TEI (GROBID) -> metadata (+enrichment) -> debug JSONs.
    Writes a plain-text report under out/tests/test_HHMM_YYYY-MM-DD.txt and returns its path.
    """
    tei_dir = tei_dir or os.getenv("TEI_SAVE_DIR") or os.path.join("data", "xml")
    reports_dir = os.path.join("out", "tests")
    os.makedirs(reports_dir, exist_ok=True)
    now = datetime.now()
    report_name = f"test_{now.strftime('%H%M')}_{now.strftime('%Y-%m-%d')}.txt"
    report_path = os.path.join(reports_dir, report_name)

    # Prepare ingestor and resolver
    ing = GrobidIngestor(tei_dir=tei_dir, skip_existing=not tei_refresh)
    resolver = MetadataResolver(mailto=mailto or os.getenv("CROSSREF_MAILTO") or "you@example.com")

    lines: list[str] = []
    lines.append(f"E2E run at {now.isoformat(timespec='seconds')}")
    lines.append(f"Input: {input_path}")
    lines.append(f"TEI dir: {tei_dir}")
    lines.append("")

    try:
        tei_paths = ing.ingest_path(input_path)
    except Exception as e:
        lines.append(f"ERROR: Ingestion failed: {e}")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        return report_path

    ok = 0
    fail = 0
    sec_keys = [
        "introduction",
        "materials_and_methods",
        "results",
        "discussion",
        "conclusions",
    ]
    section_counts: dict[str, int] = {k: 0 for k in sec_keys}
    missing_by_article: list[tuple[str, list[str]]] = []
    combined_present = 0
    # Media aggregation counters
    total_figs = 0
    total_tabs = 0
    total_items_with_coords = 0
    total = len(tei_paths)
    # auto-enable progress if running in a TTY and not explicitly disabled
    if not progress and sys.stdout and hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
        progress = True
    if progress:
        print(f"Discovered {total} TEI file(s) to process from '{input_path}'.", flush=True)
    # --- helper: review-aware augmentation ---
    def _augment_sections_if_needed(md_plus: dict, tei_path: str) -> list[str]:
        augmented: list[str] = []
        # compute coverage on canonical set
        sec_keys_local = [
            "introduction",
            "materials_and_methods",
            "results",
            "discussion",
            "conclusions",
        ]
        cov = sum(1 for k in sec_keys_local if (md_plus.get(k) or "").strip())
        if not review_mode or cov >= 3:
            return augmented
        try:
            extras = md_plus.get("sections_extra")
            if extras is None:
                from paperslicer.grobid.sections import extract_unmapped_sections
                extras = extract_unmapped_sections(tei_path)
        except Exception:
            extras = []
        if not extras or len(extras) < 5:
            return augmented

        def pick(extras_list: list[dict], keywords: list[str]) -> str:
            out_chunks: list[str] = []
            for ex in extras_list:
                head = (ex.get("head") or "").lower()
                if any(kw in head for kw in keywords):
                    txt = (ex.get("text") or "").strip()
                    if txt:
                        out_chunks.append(txt)
            return "\n\n".join(out_chunks).strip()

        # conservative keyword sets
        intro_kw = ["overview", "scope", "background", "aim", "purpose"]
        meth_kw = [
            "study selection",
            "eligibility",
            "information sources",
            "search strategy",
            "data extraction",
            "risk of bias",
            "data synthesis",
            "methodology",
            "sample size",
        ]
        res_kw = [
            "included studies",
            "findings",
            "outcomes",
            "meta-analysis",
            "meta analysis",
            "evidence",
        ]
        disc_kw = [
            "limitations",
            "challenges",
            "perspectives",
            "practice points",
            "implications",
            "recommendations",
        ]
        concl_kw = [
            "summary",
            "decision-making",
            "decision making",
            "concluding remarks",
            "conclusion",
            "clinical significance",
            "implications",
        ]

        if not (md_plus.get("introduction") or "").strip():
            agg = pick(extras, intro_kw)
            if agg:
                md_plus["augmented_introduction"] = agg
                augmented.append("introduction")
        if not (md_plus.get("materials_and_methods") or "").strip():
            agg = pick(extras, meth_kw)
            if agg:
                md_plus["augmented_materials_and_methods"] = agg
                augmented.append("materials_and_methods")
        if not (md_plus.get("results") or "").strip():
            agg = pick(extras, res_kw)
            if agg:
                md_plus["augmented_results"] = agg
                augmented.append("results")
        if not (md_plus.get("discussion") or "").strip():
            agg = pick(extras, disc_kw)
            if agg:
                md_plus["augmented_discussion"] = agg
                augmented.append("discussion")
        if not (md_plus.get("conclusions") or "").strip():
            agg = pick(extras, concl_kw)
            if agg:
                md_plus["augmented_conclusions"] = agg
                augmented.append("conclusions")
        # Generic, domain-agnostic fallback: if results/discussion still empty,
        # aggregate unmapped body sections between Introduction and Conclusions/References.
        try:
            need_results = not (md_plus.get("results") or "").strip()
            need_discussion = not (md_plus.get("discussion") or "").strip()
            if (need_results or need_discussion):
                parser = etree.XMLParser(recover=True)
                root = etree.parse(tei_path, parser).getroot()
                divs = root.findall(".//tei:text//tei:div", TEI_NS)
                def head_of(d):
                    h = d.find("./tei:head", TEI_NS)
                    return "".join(h.itertext()) if h is not None else ""
                intro_idx = None
                end_idx = None
                for i, dv in enumerate(divs):
                    canon = canonicalize(head_of(dv))
                    if intro_idx is None and canon == "introduction":
                        intro_idx = i
                    if canon in ("conclusions", "references") and end_idx is None:
                        end_idx = i
                start = (intro_idx + 1) if intro_idx is not None else 0
                stop = end_idx if end_idx is not None else len(divs)
                parts: list[str] = []
                import copy, re
                for i in range(max(0, start), max(start, min(stop, len(divs)))):
                    dv = divs[i]
                    canon = canonicalize(head_of(dv))
                    if canon is None:
                        cp = copy.deepcopy(dv)
                        for ref in cp.findall('.//tei:ref[@type="bibr"]', TEI_NS):
                            par = ref.getparent()
                            if par is not None:
                                par.remove(ref)
                        for h in cp.findall('.//tei:head', TEI_NS):
                            par = h.getparent()
                            if par is not None:
                                par.remove(h)
                        s = "\n\n".join(" ".join(x.split()) for x in ["".join(cp.itertext())])
                        s = re.sub(r"\[(?:\s*\d+(?:\s*[-–]\s*\d+)?\s*(?:,\s*\d+(?:\s*[-–]\s*\d+)?)*)\]", "", s)
                        s = re.sub(r"\n+\d+\n+", "\n\n", s)
                        s = re.sub(r"(?m)^\|\s*", "", s)
                        s = s.strip()
                        if s:
                            parts.append(s)
                agg_body = "\n\n".join(parts).strip()
                if agg_body:
                    md_plus["augmented_results_and_discussion"] = agg_body
                    if need_results and not (md_plus.get("results") or "").strip():
                        md_plus["results"] = agg_body
                        augmented.append("results")
                    if need_discussion and not (md_plus.get("discussion") or "").strip():
                        md_plus["discussion"] = agg_body
                        augmented.append("discussion")
        except Exception:
            pass
        return augmented

    for idx, tei in enumerate(tei_paths, 1):
        if progress:
            print(f"[{idx}/{total}] Processing {os.path.basename(tei)} ...", flush=True)
        try:
            md = resolver.resolve_from_tei(tei)
            # Extract introduction (full), add into saved JSON
            intro = extract_introduction(tei) or ""
            methods = extract_methods(tei) or ""
            results = extract_results(tei) or ""
            discussion = extract_discussion(tei) or ""
            conclusions = extract_conclusions(tei) or ""
            rd_combined = extract_results_and_discussion(tei) or ""
            md_plus = dict(md)
            md_plus["introduction"] = intro
            md_plus["materials_and_methods"] = methods
            md_plus["results"] = results
            md_plus["discussion"] = discussion
            md_plus["conclusions"] = conclusions
            if rd_combined:
                md_plus["results_and_discussion"] = rd_combined
                # If separate ones are empty, populate them with the combined text as a fallback
                if not results:
                    md_plus["results"] = rd_combined
                if not discussion:
                    md_plus["discussion"] = rd_combined
                combined_present += 1

            # Always include figure/table metadata from TEI
            figures_meta = []
            tables_meta = []
            try:
                from paperslicer.grobid.figures import parse_figures_tables, parse_table_data
                items = parse_figures_tables(tei)
                if items:
                    md_plus["figures_list"] = [it for it in items if it.get("type") == "figure"]
                    md_plus["tables_list"] = [it for it in items if it.get("type") == "table"]
                # Optional: structured table rows
                table_rows = parse_table_data(tei)
                if table_rows:
                    md_plus["tables_data"] = table_rows
            except Exception:
                pass

            # Export images optionally
            if export_images:
                try:
                    from paperslicer.grobid.figures import parse_figures_tables
                    from paperslicer.media.extractor import ImageExporter
                    # Find the matching PDF path by stem
                    name = os.path.basename(tei)
                    stem = name[:-8] if name.lower().endswith('.tei.xml') else os.path.splitext(name)[0]
                    pdf_root = os.path.join("data", "pdf")
                    pdf_path = None
                    for dp, _, files in os.walk(pdf_root):
                        for f in files:
                            if f.lower().endswith(".pdf") and os.path.splitext(f)[0] == stem:
                                pdf_path = os.path.join(dp, f)
                                break
                        if pdf_path:
                            break
                    if pdf_path:
                        items = parse_figures_tables(tei)
                        total_items_with_coords += sum(1 for it in items if it.get("bbox"))
                        media_root = os.getenv("MEDIA_DIR", "media")
                        outdir = build_media_outdir(media_root, md_plus, pdf_path)
                        exp = ImageExporter(media_root=media_root)
                        with_coords = [it for it in items if it.get("bbox")]
                        exported = exp.export_with_coords(pdf_path, with_coords, outdir=outdir) if with_coords else []
                        # Fallback to page images only if allowed by mode
                        if not exported and images_mode != "coords-only":
                            if images_mode == "pages-large":
                                exported = exp.export_page_images(
                                    pdf_path,
                                    outdir=outdir,
                                    min_width_px=300,
                                    min_height_px=300,
                                    min_area_px=80000,
                                    skip_full_page=True,
                                )
                            else:
                                exported = exp.export_page_images(pdf_path, outdir=outdir)
                        for e in exported:
                            if e.get("type") == "table":
                                tables_meta.append(e)
                            else:
                                figures_meta.append(e)
                except Exception:
                    pass
            if figures_meta:
                md_plus["figures"] = figures_meta
            if tables_meta:
                md_plus["tables"] = tables_meta
            total_figs += len(figures_meta)
            total_tabs += len(tables_meta)

            # References section (raw text)
            refs_text = extract_references(tei) or ""
            if refs_text:
                md_plus["references"] = refs_text
            # Structured references list (best-effort)
            try:
                refs_struct = parse_references(tei)
                if refs_struct:
                    md_plus["references_list"] = refs_struct
                    # Human-readable formatted citations
                    md_plus["references_citations"] = format_references_list(refs_struct)
                    md_plus["references_text"] = "\n".join(md_plus["references_citations"])[:50000]
                    # Prefer readable references_text over raw references
                    md_plus["references"] = md_plus.get("references_text") or md_plus.get("references")
            except Exception:
                pass

            # Include extra sections (unmapped) for review-style articles
            try:
                extras = extract_unmapped_sections(tei)
                if extras:
                    md_plus["sections_extra"] = extras
            except Exception:
                pass

            # Optional review-aware augmentation (does not overwrite canonical)
            augmented = _augment_sections_if_needed(md_plus, tei)
            # Journal-specific adjustments (safe, conservative)
            try:
                changed = Periodontology2000Handler().apply(md_plus, tei)
                if changed:
                    augmented.extend([f"p2000:{c}" for c in changed])
            except Exception:
                pass

            saved_json = save_metadata_json(
                md_plus,
                out_dir=debug_out_dir or os.getenv("DEBUG_OUT_DIR", "out/meta"),
            )

            title = (md.get("title") or "").strip()
            doi = md.get("doi") or ""
            intro_snippet = " ".join((md_plus.get("introduction") or "").split())[:240]
            # section accounting
            missing: list[str] = []
            for k in sec_keys:
                val = (md_plus.get(k) or "").strip()
                if val:
                    section_counts[k] += 1
                else:
                    missing.append(k)
            art_id = title or tei
            if missing:
                missing_by_article.append((art_id, missing))
            lines.append(f"OK: {tei}")
            lines.append(f"    title: {title}")
            lines.append(f"    doi: {doi}")
            lines.append(f"    intro: {intro_snippet}")
            if missing:
                lines.append(f"    missing_sections: {', '.join(missing)}")
            if augmented:
                lines.append(f"    augmented_sections: {', '.join(augmented)}")
            if figures_meta or tables_meta:
                lines.append(f"    media: figures={len(figures_meta)} tables={len(tables_meta)}")
            lines.append(f"    saved: {saved_json}")
            ok += 1
            if progress:
                have = sum(1 for k in sec_keys if (md_plus.get(k) or "").strip())
                media_msg = f", media f{len(figures_meta)} t{len(tables_meta)}" if (figures_meta or tables_meta) else ""
                print(f" -> OK '{title[:80]}' | sections {have}/{len(sec_keys)}{media_msg}", flush=True)
        except Exception as e:
            lines.append(f"FAIL: {tei} :: {e}")
            fail += 1
            if progress:
                print(f" -> FAIL: {e}", flush=True)

        # Append unmapped headings to suggestions file
        try:
            heads = harvest_heads(tei)
            unmapped = [h for h in heads if canonicalize(h) is None]
            if unmapped:
                suggestions_dir = os.path.join("out", "sections")
                os.makedirs(suggestions_dir, exist_ok=True)
                suggestions_path = os.path.join(suggestions_dir, "suggestions.txt")
                existing = set()
                if os.path.isfile(suggestions_path):
                    with open(suggestions_path, "r", encoding="utf-8") as sf:
                        existing = {line.strip() for line in sf if line.strip()}
                new_items = [u for u in unmapped if u not in existing]
                if new_items:
                    with open(suggestions_path, "a", encoding="utf-8") as sf:
                        for u in sorted(set(new_items)):
                            sf.write(u + "\n")
        except Exception:
            # best-effort; ignore
            pass

    lines.append("")
    lines.append(f"Summary: files_parsed={len(tei_paths)} ok={ok} fail={fail}")
    lines.append("Section extraction summary (non-empty):")
    for k in sec_keys:
        lines.append(f"  - {k}: {section_counts[k]}/{ok}")
    lines.append(f"  - results_and_discussion (present): {combined_present}/{ok}")
    if missing_by_article:
        lines.append("")
        lines.append("Missing sections by article:")
        for art_id, miss in missing_by_article:
            lines.append(f"  * {art_id}: {', '.join(miss)}")

    # Media export summary (only if images were requested)
    if export_images:
        lines.append("")
        lines.append("Media export summary:")
        lines.append(f"  - figures exported: {total_figs}")
        lines.append(f"  - tables exported: {total_tabs}")
        lines.append(f"  - items with coords (figures/tables): {total_items_with_coords}")

    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    if progress:
        print(f"Completed. Report: {report_path}", flush=True)
    return report_path
