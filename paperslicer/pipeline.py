import os
from paperslicer.models import PaperRecord, Meta
from paperslicer.extractors.text_extractor import PDFTextExtractor
from paperslicer.extractors.normalizer import TextNormalizer
from paperslicer.extractors.sections_regex import SectionExtractor
from paperslicer.extractors.captions import CaptionExtractor

# NEW
from paperslicer.grobid.client import GrobidClient
from paperslicer.grobid.manager import GrobidManager
from lxml import etree  # for checking parseability of TEI
from paperslicer.metadata.resolver import ensure_abstract
from paperslicer.journals import review as review_profile

from typing import Optional


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
                from paperslicer.media.exporter import export_embedded_images, export_page_previews, export_from_tei_coords
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
                # 2) If no coords-derived media found and mode is embedded/auto, export embedded images
                if self.images_mode in ("embedded", "auto"):
                    emb = export_embedded_images(pdf_path)
                    if emb:
                        rec.figures.extend(emb)
                # 3) If still no saved media paths for this doc and mode allows, export a few page previews
                has_paths = any((isinstance(i, dict) and i.get("path")) for i in (rec.figures + rec.tables))
                if self.images_mode in ("pages", "auto") and not has_paths:
                    pages = export_page_previews(pdf_path, max_pages=2)
                    if pages:
                        rec.figures.extend(pages)
            except Exception:
                pass
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
                from paperslicer.media.exporter import export_embedded_images, export_page_previews
                media = []
                if self.images_mode in ("embedded", "auto"):
                    media = export_embedded_images(pdf_path)
                if (self.images_mode in ("pages", "auto") and not media):
                    media = export_page_previews(pdf_path, max_pages=5)
                rec.figures.extend(media)
            except Exception:
                pass
        return rec
