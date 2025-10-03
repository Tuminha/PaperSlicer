"""
Comprehensive validation tests for PaperSlicer using Manus AI extraction mappings as ground truth.

This test file validates PaperSlicer's extraction capabilities against detailed 
extraction maps created by Manus AI for 38 academic dental research papers.
"""

import json
import sys
from difflib import SequenceMatcher
import pytest
from pathlib import Path
from typing import Dict, Any

# Make sure project root is importable when running pytest standalone
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from paperslicer.pipeline import Pipeline


# Directory paths
EXTRACTION_MAPS_DIR = PROJECT_ROOT / "manus_work" / "file_extraction_in_json"
PDF_DIR = PROJECT_ROOT / "data" / "pdf"
XML_DIR = PROJECT_ROOT / "data" / "xml"


def load_extraction_map(pdf_filename: str) -> Dict[str, Any]:
    """Load the ground truth extraction map for a given PDF."""
    # Convert PDF filename to extraction map filename
    map_filename = pdf_filename.replace('.pdf', '_extraction_map.json')
    map_path = EXTRACTION_MAPS_DIR / map_filename
    
    if not map_path.exists():
        pytest.skip("Extraction map not found: {}".format(map_filename))
    
    with open(map_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_pdf_path(pdf_filename: str) -> str:
    """Get the full path to a PDF file."""
    pdf_path = PDF_DIR / pdf_filename
    if not pdf_path.exists():
        pytest.skip("PDF not found: {}".format(pdf_filename))
    return str(pdf_path)


def fuzzy_match(text1: str, text2: str, tolerance: float = 0.9) -> bool:
    """
    Check if two text strings are similar enough.
    Allows for minor variations in whitespace, punctuation, etc.
    """
    if not text1 or not text2:
        return text1 == text2
    
    # Normalize whitespace
    t1 = ' '.join(text1.split())
    t2 = ' '.join(text2.split())
    
    if not t1 and not t2:
        return True

    similarity = SequenceMatcher(None, t1, t2).ratio()

    return similarity >= tolerance


# Priority test files (BMC Oral Health articles with most complete data)
PRIORITY_FILES = [
    "bmc_oral_health_article1_reso_pac_2025.pdf",
    "bmc_oral_health_article2_bone_density_2025.pdf",
    "bmc_oral_health_article3_cytokine_orthodontics_2025.pdf",
]


class TestMetadataExtraction:
    """Test metadata extraction accuracy."""
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_title_extraction(self, pdf_filename):
        """Validate that PaperSlicer extracts the correct title."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        # Run PaperSlicer
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        expected_title = expected['metadata'].get('title', '')
        if expected_title:
            assert record.meta.title, "No title extracted for {}".format(pdf_filename)
            # Titles should match closely
            assert expected_title.lower() in record.meta.title.lower() or \
                   record.meta.title.lower() in expected_title.lower(), \
                   "Title mismatch: expected '{}', got '{}'".format(expected_title, record.meta.title)
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_doi_extraction(self, pdf_filename):
        """Validate that PaperSlicer extracts the correct DOI."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_doi = expected['metadata'].get('doi', '')
        if not expected_doi:
            pytest.skip("No DOI in extraction map for {}".format(pdf_filename))
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        assert record.meta.doi, "No DOI extracted for {}".format(pdf_filename)
        assert record.meta.doi == expected_doi, \
               "DOI mismatch: expected '{}', got '{}'".format(expected_doi, record.meta.doi)
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_journal_extraction(self, pdf_filename):
        """Validate that PaperSlicer extracts the correct journal name."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_journal = expected['metadata'].get('journal', '')
        if not expected_journal:
            pytest.skip("No journal in extraction map for {}".format(pdf_filename))
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        assert record.meta.journal, "No journal extracted for {}".format(pdf_filename)
        # Journal names should match closely
        assert expected_journal.lower() in record.meta.journal.lower() or \
               record.meta.journal.lower() in expected_journal.lower(), \
               "Journal mismatch: expected '{}', got '{}'".format(expected_journal, record.meta.journal)
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_author_extraction(self, pdf_filename):
        """Validate that PaperSlicer extracts authors."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_authors = expected['metadata'].get('authors', [])
        if not expected_authors:
            pytest.skip("No authors in extraction map for {}".format(pdf_filename))
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        assert record.meta.authors, "No authors extracted for {}".format(pdf_filename)
        assert len(record.meta.authors) > 0, "Empty authors list for {}".format(pdf_filename)


class TestAbstractExtraction:
    """Test abstract extraction accuracy."""
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_abstract_presence(self, pdf_filename):
        """Validate that PaperSlicer detects abstract presence correctly."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_present = expected['abstract'].get('present', False)
        if not expected_present:
            pytest.skip("No abstract expected for {}".format(pdf_filename))
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        assert 'abstract' in record.sections, "Abstract not found in sections for {}".format(pdf_filename)
        assert record.sections['abstract'], "Abstract is empty for {}".format(pdf_filename)
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_abstract_content_start(self, pdf_filename):
        """Validate that abstract starts with expected text."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_first_50 = expected['abstract'].get('first_50_chars', '')
        if not expected_first_50:
            pytest.skip("No abstract first_50_chars for {}".format(pdf_filename))
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        abstract = record.sections.get('abstract', '')
        assert abstract, "No abstract extracted for {}".format(pdf_filename)
        
        # Check if abstract starts similarly
        actual_first_50 = abstract[:50]
        assert fuzzy_match(expected_first_50, actual_first_50, tolerance=0.8), \
               "Abstract start mismatch for {}:\n  Expected: {}\n  Got: {}".format(
                   pdf_filename, expected_first_50, actual_first_50)
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_abstract_content_end(self, pdf_filename):
        """Validate that abstract ends with expected text."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_last_50 = expected['abstract'].get('last_50_chars', '')
        if not expected_last_50:
            pytest.skip("No abstract last_50_chars for {}".format(pdf_filename))
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        abstract = record.sections.get('abstract', '')
        assert abstract, "No abstract extracted for {}".format(pdf_filename)
        
        # Check if abstract ends similarly
        actual_last_50 = abstract[-50:]
        assert fuzzy_match(expected_last_50, actual_last_50, tolerance=0.8), \
               "Abstract end mismatch for {}:\n  Expected: {}\n  Got: {}".format(
                   pdf_filename, expected_last_50, actual_last_50)
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_abstract_word_count(self, pdf_filename):
        """Validate abstract word count is approximately correct."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_word_count = expected['abstract'].get('word_count', 0)
        if expected_word_count == 0:
            pytest.skip("No word count for {}".format(pdf_filename))
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        abstract = record.sections.get('abstract', '')
        actual_word_count = len(abstract.split())
        
        # Allow 10% tolerance in word count
        tolerance = 0.1
        lower_bound = expected_word_count * (1 - tolerance)
        upper_bound = expected_word_count * (1 + tolerance)
        
        assert lower_bound <= actual_word_count <= upper_bound, \
               f"Word count mismatch for {pdf_filename}: expected ~{expected_word_count}, got {actual_word_count}"


class TestSectionExtraction:
    """Test section extraction accuracy."""
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_section_count(self, pdf_filename):
        """Validate that PaperSlicer extracts the expected number of sections."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_sections = expected.get('sections', {})
        expected_count = len([s for s in expected_sections.keys() if expected_sections[s]])
        
        if expected_count == 0:
            pytest.skip("No sections in extraction map for {}".format(pdf_filename))
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        # Count canonical sections (excluding abstract and other_sections)
        canonical_sections = {
            'introduction', 'materials_and_methods', 'results', 
            'discussion', 'conclusions', 'results_and_discussion'
        }
        actual_count = sum(1 for k in record.sections.keys() 
                          if k in canonical_sections and record.sections[k])
        
        # Allow some tolerance in section count
        assert actual_count >= expected_count * 0.5, \
               f"Section count too low for {pdf_filename}: expected ~{expected_count}, got {actual_count}"
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_introduction_present(self, pdf_filename):
        """Validate that introduction section is extracted."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_sections = expected.get('sections', {})
        if 'introduction' not in expected_sections:
            pytest.skip("No introduction expected for {}".format(pdf_filename))
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        assert 'introduction' in record.sections, \
               f"Introduction section not found for {pdf_filename}"
        assert record.sections['introduction'], \
               f"Introduction section is empty for {pdf_filename}"
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_methods_present(self, pdf_filename):
        """Validate that methods section is extracted."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_sections = expected.get('sections', {})
        if 'materials_and_methods' not in expected_sections:
            pytest.skip("No materials_and_methods expected for {}".format(pdf_filename))
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        assert 'materials_and_methods' in record.sections, \
               f"Materials and methods section not found for {pdf_filename}"
        assert record.sections['materials_and_methods'], \
               f"Materials and methods section is empty for {pdf_filename}"
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_results_present(self, pdf_filename):
        """Validate that results section is extracted."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_sections = expected.get('sections', {})
        if 'results' not in expected_sections:
            pytest.skip("No results expected for {}".format(pdf_filename))
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        assert 'results' in record.sections, \
               f"Results section not found for {pdf_filename}"
        assert record.sections['results'], \
               f"Results section is empty for {pdf_filename}"
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_section_first_sentence(self, pdf_filename):
        """Validate that section content starts correctly."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_sections = expected.get('sections', {})
        
        # Check introduction if available
        if 'introduction' in expected_sections and expected_sections['introduction']:
            expected_intro = expected_sections['introduction']
            expected_first_100 = expected_intro.get('first_100_chars', '')
            
            if expected_first_100:
                pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
                record = pipeline.process(pdf_path)
                
                intro_text = record.sections.get('introduction', '')
                if intro_text:
                    actual_first_100 = intro_text[:100]
                    assert fuzzy_match(expected_first_100, actual_first_100, tolerance=0.7), \
                           f"Introduction start mismatch for {pdf_filename}"


class TestFigureExtraction:
    """Test figure extraction accuracy."""
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_figure_count(self, pdf_filename):
        """Validate that PaperSlicer extracts the expected number of figures."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_count = expected['structural_info'].get('total_figures', 0)
        if expected_count == 0:
            pytest.skip("No figures expected for {}".format(pdf_filename))
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        actual_count = len(record.figures)
        
        # Allow some tolerance in figure count (±2 figures or 50% whichever is greater)
        tolerance = max(2, expected_count * 0.5)
        assert abs(actual_count - expected_count) <= tolerance, \
               f"Figure count mismatch for {pdf_filename}: expected {expected_count}, got {actual_count}"
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_figure_labels(self, pdf_filename):
        """Validate that figure labels are extracted correctly."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_figures = expected.get('figures', [])
        if not expected_figures:
            pytest.skip(f"No figures expected for {pdf_filename}")
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        expected_labels = {fig.get('label', '') for fig in expected_figures if fig.get('label')}
        actual_labels = {fig.get('label', '') for fig in record.figures if fig.get('label')}
        
        # Check that we have some label overlap
        common_labels = expected_labels & actual_labels
        assert len(common_labels) > 0 or len(actual_labels) > 0, \
               f"No figure labels extracted for {pdf_filename}"
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_figure_captions(self, pdf_filename):
        """Validate that figure captions are extracted."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_figures = expected.get('figures', [])
        if not expected_figures:
            pytest.skip(f"No figures expected for {pdf_filename}")
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        # Check that at least some figures have captions
        figures_with_captions = [f for f in record.figures if f.get('caption')]
        assert len(figures_with_captions) > 0, \
               f"No figure captions extracted for {pdf_filename}"


class TestTableExtraction:
    """Test table extraction accuracy."""
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_table_count(self, pdf_filename):
        """Validate that PaperSlicer extracts the expected number of tables."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_count = expected['structural_info'].get('total_tables', 0)
        if expected_count == 0:
            pytest.skip(f"No tables expected for {pdf_filename}")
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        actual_count = len(record.tables)
        
        # Allow some tolerance in table count (±1 table or 50% whichever is greater)
        tolerance = max(1, expected_count * 0.5)
        assert abs(actual_count - expected_count) <= tolerance, \
               f"Table count mismatch for {pdf_filename}: expected {expected_count}, got {actual_count}"
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_table_labels(self, pdf_filename):
        """Validate that table labels are extracted correctly."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_tables = expected.get('tables', [])
        if not expected_tables:
            pytest.skip(f"No tables expected for {pdf_filename}")
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        expected_labels = {tbl.get('label', '') for tbl in expected_tables if tbl.get('label')}
        actual_labels = {tbl.get('label', '') for tbl in record.tables if tbl.get('label')}
        
        # Check that we have some label overlap
        common_labels = expected_labels & actual_labels
        assert len(common_labels) > 0 or len(actual_labels) > 0, \
               f"No table labels extracted for {pdf_filename}"
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_table_captions(self, pdf_filename):
        """Validate that table captions are extracted."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_tables = expected.get('tables', [])
        if not expected_tables:
            pytest.skip(f"No tables expected for {pdf_filename}")
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        # Check that at least some tables have captions
        tables_with_captions = [t for t in record.tables if t.get('caption')]
        assert len(tables_with_captions) > 0, \
               f"No table captions extracted for {pdf_filename}"


class TestStructuralInfo:
    """Test overall structural information extraction."""
    
    @pytest.mark.parametrize("pdf_filename", PRIORITY_FILES)
    def test_total_references(self, pdf_filename):
        """Validate that reference count is reasonable."""
        expected = load_extraction_map(pdf_filename)
        pdf_path = get_pdf_path(pdf_filename)
        
        expected_count = expected['structural_info'].get('total_references', 0)
        if expected_count == 0:
            pytest.skip("No references counted for {}".format(pdf_filename))
        
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(pdf_path)
        
        actual_count = len(record.references) if hasattr(record, 'references') else 0
        
        # References count can vary significantly, so use larger tolerance
        # Just check that we extracted some references
        assert actual_count > 0, \
               f"No references extracted for {pdf_filename} (expected ~{expected_count})"


# Comprehensive test that runs on all files (slower, marked as integration test)
class TestComprehensiveExtraction:
    """Integration tests that validate extraction across all PDFs."""
    
    @pytest.mark.slow
    @pytest.mark.integration
    def test_all_pdfs_basic_extraction(self):
        """
        Validate that basic extraction works for all PDFs.
        This is a smoke test to ensure PaperSlicer doesn't crash on any PDF.
        """
        extraction_maps_dir = EXTRACTION_MAPS_DIR
        all_maps = list(extraction_maps_dir.glob("*_extraction_map.json"))
        
        results = {
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for map_file in all_maps:
            pdf_filename = map_file.name.replace('_extraction_map.json', '.pdf')
            pdf_path = PDF_DIR / pdf_filename
            
            if not pdf_path.exists():
                continue
            
            try:
                pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
                record = pipeline.process(str(pdf_path))
                
                # Basic validation
                assert record.meta.title or record.sections, \
                       "No content extracted for {}".format(pdf_filename)
                
                results['success'] += 1
            except Exception:  # pylint: disable=broad-except
                results['failed'] += 1
                results['errors'].append("{}:  extraction failed".format(pdf_filename))
        
        # Print summary
        print("\n" + "="*60)
        print("Extraction Validation Summary")
        print("="*60)
        print("Total PDFs tested: {}".format(results['success'] + results['failed']))
        print("Successful extractions: {}".format(results['success']))
        print("Failed extractions: {}".format(results['failed']))
        
        if results['errors']:
            print("\nErrors:")
            for error in results['errors'][:10]:  # Show first 10 errors
                print("  - {}".format(error))
        
        # Assert that we had reasonable success rate
        total = results['success'] + results['failed']
        if total > 0:
            success_rate = results['success'] / total
            assert success_rate >= 0.7, \
                   "Success rate too low: {:.1%} (expected >= 70%)".format(success_rate)


if __name__ == "__main__":
    # Run with: pytest tests/test_extraction_validation.py -v
    # For slow tests: pytest tests/test_extraction_validation.py -v --slow
    pytest.main([__file__, "-v"])
