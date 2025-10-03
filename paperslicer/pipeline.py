import os
from paperslicer.models import PaperRecord, Meta
from paperslicer.extractors.text_extractor import PDFTextExtractor
from paperslicer.extractors.normalizer import TextNormalizer
from paperslicer.extractors.sections_regex import SectionExtractor
from paperslicer.extractors.captions import CaptionExtractor
from paperslicer.media.filters import filter_media_collections

# NEW
from paperslicer.grobid.client import GrobidClient
from paperslicer.grobid.manager import GrobidManager
from lxml import etree  # for checking parseability of TEI
from paperslicer.metadata.resolver import ensure_abstract
from paperslicer.journals import review as review_profile

from typing import Optional, Dict, Any, Tuple, List


def _merge_table_entries(rec: PaperRecord) -> None:
    """Merge duplicate table entries and attach media paths to structured rows."""
    if not rec.tables:
        return

    merged: Dict[Tuple[str, str], Dict[str, Any]] = {}
    ordered: List[Dict[str, Any]] = []

    for tbl in rec.tables:
        if not isinstance(tbl, dict):
            continue
        label = (tbl.get("label") or "").strip()
        caption = (tbl.get("caption") or "").strip()
        if caption:
            key = ("caption", caption.lower())
        elif label:
            key = ("label", label.lower())
        elif tbl.get("path"):
            key = ("path", str(tbl.get("path")))
        else:
            key = ("index", str(len(ordered)))
        existing = merged.get(key)
        if existing is None:
            data = dict(tbl)
            src = data.get("source")
            data_sources = []
            if src:
                data_sources.append(src)
            data["source"] = "+".join(sorted(set(data_sources))) if data_sources else data.get("source")
            data["_sources"] = set(data_sources)
            ordered.append(data)
            merged[key] = data
            existing = data
        else:
            src = tbl.get("source")
            if src:
                existing["_sources"].add(src)
        for field in ("label", "caption", "coords", "pdf_bbox"):
            if not existing.get(field) and tbl.get(field):
                existing[field] = tbl[field]
        if not existing.get("path") and tbl.get("path"):
            existing["path"] = tbl["path"]

    for data in ordered:
        if isinstance(data, dict) and "_sources" in data:
            sources = sorted(s for s in data["_sources"] if s)
            if sources:
                data["source"] = "+".join(sources)
            elif "source" in data and not data["source"]:
                data.pop("source")
            data.pop("_sources", None)

    rec.tables = ordered


class Pipeline:
    def __init__(self, try_start_grobid: bool = True, xml_save_dir: Optional[str] = None,
                 export_images: bool = False, images_mode: str = "embedded",
                 review_mode: Optional[bool] = None):
        self.try_start_grobid = try_start_grobid
        self.xml_save_dir = xml_save_dir
        self.export_images = export_images
        self.images_mode = images_mode
        self.review_mode = review_mode
        self.pdf = PDFTextExtractor()
        self.norm = TextNormalizer()
        self.sections = SectionExtractor()
        self.captions = CaptionExtractor()

    def _try_grobid(self, pdf_path: str) -> Optional[PaperRecord]:
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
        rec = tei_to_record(tei_bytes, pdf_path)
        _merge_table_entries(rec)
        filter_media_collections(rec, pdf_path)
        # Journal/profile augmentation for reviews
        try:
            force_review = self.review_mode if self.review_mode is not None else (os.getenv("REVIEW_MODE") in {"1", "true", "yes", "on"})
            if force_review or review_profile.should_apply(rec):
                rec = review_profile.apply(rec)
        except Exception:
            pass
        # Ensure abstract exists via Crossref/PubMed if TEI lacks it
        mailto = os.getenv("CROSSREF_MAILTO")
        try:
            ensure_abstract(rec, mailto=mailto)
        except Exception:
            pass
        # Basic image export if requested
        if self.export_images:
            try:
                from paperslicer.media.exporter import (
                    export_embedded_images,
                    export_page_previews,
                    export_from_tei_coords,
                    export_pages_with_keywords,
                    export_crops_by_labels,
                )
                # YOLO PubLayNet detector (optional dependency)
                try:
                    from paperslicer.media.detector_hf import detect_publaynet_crops
                except Exception:
                    detect_publaynet_crops = None  # type: ignore
                # Table Transformer detector (optional dependency)
                try:
                    from paperslicer.media.detector_tables import detect_table_crops
                except Exception:
                    detect_table_crops = None  # type: ignore
                # pdfplumber tables (deterministic bboxes)
                try:
                    from paperslicer.media.tables_pdfplumber import extract_tables_pdfplumber
                except Exception:
                    extract_tables_pdfplumber = None  # type: ignore
                # Docling adapter (optional)
                try:
                    from paperslicer.media.docling_adapter import extract_tables_docling
                except Exception:
                    extract_tables_docling = None  # type: ignore
                # TEI -> table renderer (matplotlib) as last resort for tables
                try:
                    from paperslicer.media.tei_table_render import render_tei_tables_to_images
                except Exception:
                    render_tei_tables_to_images = None  # type: ignore
                # 1) Try TEI coords-based crops for figures/tables that have coords
                any_coords = False
                for coll in (rec.figures, rec.tables):
                    for item in coll:
                        coords = item.get("coords") if isinstance(item, dict) else None
                        if coords:
                            crops = export_from_tei_coords(pdf_path, coords)
                            if crops:
                                # attach first crop to this item; add extras as separate figures
                                item["path"] = crops[0].get("path")
                                item["source"] = "grobid+crop"
                                for extra in crops[1:]:
                                    rec.figures.append(extra)
                                any_coords = True
                # Prefer TEI-rendered tables before other strategies
                tables_have_paths = any((isinstance(t, dict) and t.get("path")) for t in rec.tables)
                if not tables_have_paths and render_tei_tables_to_images is not None and tei_path:
                    try:
                        tei_renders = render_tei_tables_to_images(pdf_path, tei_path)
                        if tei_renders:
                            rec.tables.extend(tei_renders)
                            tables_have_paths = True
                    except Exception:
                        pass
                # 2) If no coords-derived media found and mode is embedded/auto, export embedded images
                if self.images_mode in ("embedded", "auto"):
                    emb = export_embedded_images(pdf_path)
                    if emb:
                        rec.figures.extend(emb)
                # 2.5) Docling tables (optional; content-based) if requested and still no tables
                use_docling = (os.getenv("USE_DOCLING") in {"1","true","yes","on"})
                tables_have_paths = any((isinstance(t, dict) and t.get("path")) for t in rec.tables)
                if use_docling and extract_tables_docling is not None and not tables_have_paths:
                    try:
                        dlt = extract_tables_docling(pdf_path)
                        if dlt:
                            rec.tables.extend(dlt)
                            tables_have_paths = True
                    except Exception:
                        pass
                # 2.55) pdfalto illustration crops (optional) if still no media paths
                has_paths = any((isinstance(i, dict) and i.get("path")) for i in (rec.figures + rec.tables))
                use_pdfalto = (os.getenv("PAPERSLICER_USE_PDFALTO", "1").lower() in {"1","true","yes","on"})
                if not has_paths and use_pdfalto:
                    try:
                        from paperslicer.media.pdfalto_adapter import extract_illustrations_pdfalto
                        palto = extract_illustrations_pdfalto(pdf_path)
                        if palto:
                            rec.figures.extend(palto)
                            has_paths = True
                    except Exception:
                        pass
                # 2.6) pdfplumber table crops (preferred deterministic) if still no table paths
                tables_have_paths = any((isinstance(t, dict) and t.get("path")) for t in rec.tables)
                disable_plumber = (os.getenv("PAPERSLICER_DISABLE_PLUMBER") in {"1","true","yes","on"})
                if not tables_have_paths and extract_tables_pdfplumber is not None and not disable_plumber:
                    try:
                        pdet = extract_tables_pdfplumber(pdf_path)
                        if pdet:
                            rec.tables.extend(pdet)
                    except Exception:
                        pass
                # 2.7) Detector-based crops (figures/tables) if still no paths
                has_paths = any((isinstance(i, dict) and i.get("path")) for i in (rec.figures + rec.tables))
                disable_detectors = (os.getenv("PAPERSLICER_DISABLE_DETECTORS") in {"1","true","yes","on"})
                if not has_paths and detect_publaynet_crops is not None and not disable_detectors:
                    try:
                        det_figs, det_tabs = detect_publaynet_crops(pdf_path, conf=None)
                        if det_figs:
                            rec.figures.extend(det_figs)
                        if det_tabs:
                            rec.tables.extend(det_tabs)
                    except Exception:
                        pass
                # 2.8) (moved) Table Transformer crops: run regardless of figure media presence
                if detect_table_crops is not None and not disable_detectors:
                    try:
                        tdet = detect_table_crops(pdf_path, dpi=None, conf=None, tiles=None)
                        if tdet:
                            rec.tables.extend(tdet)
                    except Exception:
                        pass
                # 2.9) TEI-render moved earlier; keep here as safety no-op if nothing added
                tables_have_paths = any((isinstance(t, dict) and t.get("path")) for t in rec.tables)
                # 3) If still no saved media paths, try label-based crops using detected labels
                has_paths = any((isinstance(i, dict) and i.get("path")) for i in (rec.figures + rec.tables))
                if not has_paths:
                    labels = []
                    for coll in (rec.figures, rec.tables):
                        for it in coll:
                            lbl = it.get("label") if isinstance(it, dict) else None
                            if not lbl:
                                continue
                            s = str(lbl).strip()
                            if not s:
                                continue
                            if not s.lower().startswith(("figure", "fig", "table", "tab")):
                                # Prefix based on source hint
                                if it.get("source") == "tei" and it in rec.tables:
                                    s = f"Table {s}"
                                elif it.get("source") == "tei" and it in rec.figures:
                                    s = f"Figure {s}"
                            labels.append(s)
                    if labels:
                        crops = export_crops_by_labels(pdf_path, labels, max_crops=8)
                        if crops:
                            rec.figures.extend(crops)
                # 4) If still no saved media paths, try keyword-targeted page previews (Figure/Table)
                has_paths = any((isinstance(i, dict) and i.get("path")) for i in (rec.figures + rec.tables))
                if not has_paths:
                    kw_pages = export_pages_with_keywords(pdf_path, ["figure", "table"], max_pages=6)
                    if kw_pages:
                        rec.figures.extend(kw_pages)
                # 5) If still no saved media paths for this doc and mode allows, export a few page previews
                has_paths = any((isinstance(i, dict) and i.get("path")) for i in (rec.figures + rec.tables))
                if self.images_mode in ("pages", "auto") and not has_paths:
                    pages = export_page_previews(pdf_path, max_pages=2)
                    if pages:
                        rec.figures.extend(pages)
                # 6) Last-resort safety: if still no saved paths, force minimal page previews
                has_paths = any((isinstance(i, dict) and i.get("path")) for i in (rec.figures + rec.tables))
                if not has_paths:
                    pages = export_page_previews(pdf_path, max_pages=2)
                    if pages:
                        rec.figures.extend(pages)
            except Exception:
                pass
        _merge_table_entries(rec)
        filter_media_collections(rec, pdf_path)
        return rec

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
        rec = PaperRecord(meta=meta, sections=sec, figures=figs, tables=tabs)
        if self.export_images:
            try:
                from paperslicer.media.exporter import (
                    export_embedded_images,
                    export_page_previews,
                    export_pages_with_keywords,
                    export_crops_by_labels,
                )
                # YOLO PubLayNet detector (optional dependency)
                try:
                    from paperslicer.media.detector_hf import detect_publaynet_crops
                except Exception:
                    detect_publaynet_crops = None  # type: ignore
                # Table Transformer detector (optional dependency)
                try:
                    from paperslicer.media.detector_tables import detect_table_crops
                except Exception:
                    detect_table_crops = None  # type: ignore
                # pdfplumber tables (deterministic bboxes)
                try:
                    from paperslicer.media.tables_pdfplumber import extract_tables_pdfplumber
                except Exception:
                    extract_tables_pdfplumber = None  # type: ignore
                # Docling adapter (optional)
                try:
                    from paperslicer.media.docling_adapter import extract_tables_docling
                except Exception:
                    extract_tables_docling = None  # type: ignore
                media = []
                if self.images_mode in ("embedded", "auto"):
                    media = export_embedded_images(pdf_path)
                # If none found, try detector crops first
                disable_detectors = (os.getenv("PAPERSLICER_DISABLE_DETECTORS") in {"1","true","yes","on"})
                if not media and detect_publaynet_crops is not None and not disable_detectors:
                    try:
                        det_figs, det_tabs = detect_publaynet_crops(pdf_path, conf=None)
                        # Keep figures and tables separated in the fallback path
                        if det_figs:
                            media = det_figs
                        if det_tabs:
                            rec.tables.extend(det_tabs)
                    except Exception:
                        pass
                # Also try Table Transformer to add table crops regardless of image media presence
                if detect_table_crops is not None and not disable_detectors:
                    try:
                        tdet = detect_table_crops(pdf_path, dpi=None, conf=None, tiles=None)
                        if tdet:
                            rec.tables.extend(tdet)
                    except Exception:
                        pass
                # Deterministic tables via pdfplumber
                disable_plumber = (os.getenv("PAPERSLICER_DISABLE_PLUMBER") in {"1","true","yes","on"})
                if extract_tables_pdfplumber is not None and not disable_plumber:
                    try:
                        pdet = extract_tables_pdfplumber(pdf_path)
                        if pdet:
                            rec.tables.extend(pdet)
                    except Exception:
                        pass
                # Docling structured tables if requested
                use_docling = (os.getenv("USE_DOCLING") in {"1","true","yes","on"})
                if use_docling and extract_tables_docling is not None:
                    try:
                        dlt = extract_tables_docling(pdf_path)
                        if dlt:
                            rec.tables.extend(dlt)
                    except Exception:
                        pass
                # (pdfalto integration removed)
                # If none found, try keyword-targeted previews first for relevance
                if not media:
                    # Try crops by labels harvested from regex sections (if any)
                    labels = []
                    # no structured rec.tables here; rely on captions extractor if present
                    # fall back to generic keywords next
                    if labels:
                        media = export_crops_by_labels(pdf_path, labels, max_crops=6)
                if not media:
                    media = export_pages_with_keywords(pdf_path, ["figure", "table"], max_pages=6)
                if (self.images_mode in ("pages", "auto") and not media):
                    media = export_page_previews(pdf_path, max_pages=5)
                # Safety fallback: if still empty, force minimal previews
                if not media:
                    media = export_page_previews(pdf_path, max_pages=2)
                rec.figures.extend(media)
            except Exception:
                pass
        _merge_table_entries(rec)
        return rec
