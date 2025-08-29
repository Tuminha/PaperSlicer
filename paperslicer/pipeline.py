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
