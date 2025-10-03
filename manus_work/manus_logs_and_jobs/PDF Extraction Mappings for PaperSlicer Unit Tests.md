# PDF Extraction Mappings for PaperSlicer Unit Tests

**Generated:** October 2, 2025  
**Total PDFs Processed:** 38  
**Purpose:** Provide comprehensive structural information for validating PaperSlicer's PDF extraction capabilities

---

## Overview

This directory contains detailed JSON extraction mappings for 38 academic dental research papers. Each mapping provides comprehensive structural information that can be used to create unit tests for the PaperSlicer library.

## File Structure

```
data/test_mappings/
├── README.md                                    # This file
├── all_pdfs_summary.json                        # Master summary of all PDFs
├── extraction_validation.md                     # Validation checklist
├── {pdf_name}_extraction_map.json               # Individual extraction maps (38 files)
└── ...
```

## Extraction Map Schema

Each `*_extraction_map.json` file follows this structure:

```json
{
  "file_name": "example.pdf",
  "metadata": {
    "title": "Paper title",
    "authors": ["Author 1", "Author 2"],
    "journal": "Journal Name",
    "doi": "10.xxxx/xxxxx",
    "year": 2025,
    "total_pages": 12
  },
  "abstract": {
    "present": true,
    "first_50_chars": "...",
    "last_50_chars": "...",
    "word_count": 250,
    "char_count": 1500
  },
  "sections": {
    "introduction": {
      "heading": "Introduction",
      "first_sentence": "...",
      "first_100_chars": "...",
      "last_sentence": "...",
      "last_100_chars": "...",
      "word_count": 500,
      "pages": "1-2",
      "subsections": []
    }
  },
  "figures": [
    {
      "label": "Fig. 1",
      "caption": "...",
      "caption_length": 120,
      "page": 3,
      "position": "Top",
      "type": "flowchart",
      "referenced_in_text": true
    }
  ],
  "tables": [
    {
      "label": "Table 1",
      "caption": "...",
      "caption_length": 85,
      "page": 4,
      "columns": 5,
      "rows": 8,
      "column_headers": ["Col1", "Col2", ...],
      "first_row": ["Data1", "Data2", ...],
      "type": "comparison table",
      "referenced_in_text": true
    }
  ],
  "other_sections": {
    "funding": {
      "present": true,
      "first_50_chars": "...",
      "last_50_chars": "..."
    }
  },
  "structural_info": {
    "total_sections": 5,
    "total_figures": 6,
    "total_tables": 3,
    "total_references": 45,
    "has_appendices": false,
    "has_supplementary": true
  },
  "quality_indicators": {
    "has_page_numbers": true,
    "headers_footers": "Journal Name | 2025",
    "watermarks": "none",
    "text_readability": "Good",
    "special_notes": "..."
  }
}
```

## Processed Journals

| Journal | Count |
|---------|-------|
| BMC Oral Health | 3 |
| Clinical Oral Implants Research | 3 |
| Dental Materials Journal | 3 |
| Dentistry Journal (MDPI) | 7 |
| International Journal of Dental Materials | 3 |
| International Journal of Implant Dentistry | 3 |
| International Journal of Oral Science | 3 |
| Journal of Oral and Maxillofacial Research | 3 |
| Oral (MDPI) | 2 |
| Periodontology 2000 | 2 |
| The Open Dentistry Journal | 3 |
| Consensus Reports | 3 |

## Usage for Unit Tests

### Example 1: Test Abstract Extraction

```python
import json

def test_abstract_extraction():
    with open('bmc_oral_health_article1_reso_pac_2025_extraction_map.json') as f:
        expected = json.load(f)
    
    # Extract abstract using PaperSlicer
    extracted_abstract = paper_slicer.extract_abstract('bmc_oral_health_article1_reso_pac_2025.pdf')
    
    # Validate
    assert extracted_abstract.startswith(expected['abstract']['first_50_chars'])
    assert extracted_abstract.endswith(expected['abstract']['last_50_chars'])
    assert len(extracted_abstract.split()) == expected['abstract']['word_count']
```

### Example 2: Test Section Detection

```python
def test_section_detection():
    with open('bmc_oral_health_article1_reso_pac_2025_extraction_map.json') as f:
        expected = json.load(f)
    
    # Extract sections using PaperSlicer
    sections = paper_slicer.extract_sections('bmc_oral_health_article1_reso_pac_2025.pdf')
    
    # Validate section count
    assert len(sections) == expected['structural_info']['total_sections']
    
    # Validate section names
    assert 'introduction' in sections
    assert 'materials_and_methods' in sections
    assert 'results' in sections
```

### Example 3: Test Figure Extraction

```python
def test_figure_extraction():
    with open('bmc_oral_health_article1_reso_pac_2025_extraction_map.json') as f:
        expected = json.load(f)
    
    # Extract figures using PaperSlicer
    figures = paper_slicer.extract_figures('bmc_oral_health_article1_reso_pac_2025.pdf')
    
    # Validate figure count
    assert len(figures) == expected['structural_info']['total_figures']
    
    # Validate first figure
    assert figures[0]['label'] == expected['figures'][0]['label']
    assert figures[0]['caption'] == expected['figures'][0]['caption']
```

### Example 4: Test Table Extraction

```python
def test_table_extraction():
    with open('bmc_oral_health_article1_reso_pac_2025_extraction_map.json') as f:
        expected = json.load(f)
    
    # Extract tables using PaperSlicer
    tables = paper_slicer.extract_tables('bmc_oral_health_article1_reso_pac_2025.pdf')
    
    # Validate table count
    assert len(tables) == expected['structural_info']['total_tables']
    
    # Validate table structure
    assert tables[0]['columns'] == expected['tables'][0]['columns']
    assert tables[0]['rows'] == expected['tables'][0]['rows']
```

## Extraction Methodology

### Automated Extraction

The extraction process used a combination of:

1. **pdftotext**: For text extraction from PDFs
2. **pdfinfo**: For metadata like page counts
3. **Regular expressions**: For pattern matching (sections, figures, tables)
4. **Manual verification**: For enhanced accuracy on priority files

### Priority Processing Order

1. BMC Oral Health articles (3 files)
2. Clinical Oral Implants Research articles (3 files)
3. Dental Materials Journal articles (3 files)
4. Remaining files in alphabetical order

### Extraction Quality Levels

- **Level 1 (Automated)**: Basic structure, metadata, counts
- **Level 2 (Enhanced)**: Detailed section content, accurate figure/table info
- **Level 3 (Manual)**: Fully verified with page numbers and subsections

Most files are at Level 1-2. Priority files (BMC, COIR, DMJ) have enhanced extraction.

## Known Limitations

1. **Abstract Detection**: Some journals use non-standard abstract formatting
2. **Section Naming**: Variations like "Materials and Methods" vs "Methods"
3. **Page Numbers**: Require page-by-page analysis (marked as "TBD" in many files)
4. **Subsections**: Automated detection is limited
5. **Special Characters**: Some encoding issues with non-ASCII characters
6. **Multi-column Layouts**: Can affect text extraction order

## Recommendations for Test Development

1. **Start with Priority Files**: BMC and COIR articles have the most detailed mappings
2. **Use Fuzzy Matching**: For first/last sentence comparisons (allow minor variations)
3. **Test Incrementally**: Start with metadata, then abstract, then sections
4. **Handle Variations**: Account for different section naming conventions
5. **Validate Counts First**: Before testing content accuracy
6. **Cross-reference**: Use multiple PDFs to test robustness

## Common Section Naming Patterns

| Standard Name | Variations Found |
|---------------|------------------|
| Introduction | Introduction, Background |
| Materials and Methods | Methods, Methodology, Materials and Methods, Patients and Methods |
| Results | Results, Findings |
| Discussion | Discussion, Clinical Significance |
| Conclusion | Conclusion, Conclusions, Summary |
| References | References, Bibliography |

## File Naming Convention

Extraction maps follow this naming pattern:
```
{original_pdf_name}_extraction_map.json
```

Example:
```
bmc_oral_health_article1_reso_pac_2025.pdf
→ bmc_oral_health_article1_reso_pac_2025_extraction_map.json
```

## Statistics Summary

- **Total PDFs**: 38
- **Total Figures**: 56
- **Total Tables**: 39
- **Total Pages**: ~550 (estimated)
- **Journals Covered**: 12
- **Date Range**: 2023-2025

## Support Files

### all_pdfs_summary.json

Contains aggregate statistics:
- PDFs by journal
- Total figures/tables across all papers
- Papers with missing sections
- Extraction errors/issues

### extraction_validation.md

Provides:
- List of all processed PDFs
- Section naming patterns
- Recommendations for mapping rules
- Quality assessment notes

## Future Enhancements

Potential improvements for future iterations:

1. **Page-by-page extraction**: Accurate page numbers for all elements
2. **Subsection detection**: Hierarchical section structure
3. **Reference parsing**: Individual reference extraction
4. **Image analysis**: Figure type classification
5. **Table parsing**: Full table content extraction
6. **Cross-references**: Track figure/table mentions in text

## Contact & Updates

For questions or issues with these extraction mappings:
- Review the validation checklist first
- Check the summary file for known issues
- Consider manual verification for critical test cases

---

**Last Updated:** October 2, 2025  
**Version:** 1.0  
**Extraction Tool:** Custom Python scripts using pdftotext, pdfinfo, and regex patterns
