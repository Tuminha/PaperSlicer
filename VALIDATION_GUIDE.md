# PaperSlicer Validation Testing Guide

## 🎯 Overview

This guide explains how to use the comprehensive validation testing system for PaperSlicer. The system uses **38 ground truth extraction mappings** created by Manus AI to validate PaperSlicer's PDF extraction accuracy.

## 📊 Ground Truth Data

**Location:** `manus_work/file_extraction_in_json/`

**Statistics:**
- ✅ **38 PDFs** with detailed extraction maps
- ✅ **137 figures** identified and catalogued
- ✅ **88 tables** identified and catalogued  
- ✅ **79 sections** with complete content analysis
- ✅ **19 abstracts** with first/last characters and word counts
- ✅ **1,135 references** counted across all papers

**Journals Covered:**
- BMC Oral Health (3)
- Clinical Oral Implants Research (3)
- Dental Materials Journal (3)
- International Journal of Dental Materials (3)
- International Journal of Implant Dentistry (3)
- International Journal of Oral Science (3)
- Journal of Oral and Maxillofacial Research (3)
- Dentistry Journal - MDPI (7)
- Oral - MDPI (2)
- The Open Dentistry Journal (3)
- Periodontology 2000 (2)
- Consensus Reports (3)

---

## 🧪 Running Validation Tests

### Quick Start (Fast Tests Only)

Run validation on the 3 priority BMC Oral Health articles:

```bash
# Using pytest directly
pytest tests/test_extraction_validation.py -v -m "not slow"

# Or using the convenience script
./scripts/run_validation_tests.sh
```

### Full Validation (All 38 PDFs)

```bash
# Using pytest
pytest tests/test_extraction_validation.py -v

# Or using the convenience script
./scripts/run_validation_tests.sh --all
```

### Test Specific Components

```bash
# Test only metadata extraction
./scripts/run_validation_tests.sh --metadata

# Test only abstract extraction
./scripts/run_validation_tests.sh --abstract

# Test only section extraction
./scripts/run_validation_tests.sh --sections

# Test only figure extraction
./scripts/run_validation_tests.sh --figures

# Test only table extraction
./scripts/run_validation_tests.sh --tables
```

---

## 📈 Generate Validation Reports

### Quick Report (Priority Files)

```bash
./scripts/run_validation_tests.sh --report
```

This generates a detailed JSON report with:
- Overall score for each PDF (0-100)
- Breakdown by component (metadata, abstract, sections, figures, tables)
- Common issues identified
- Success/failure statistics

### Full Report (All 38 PDFs)

```bash
./scripts/run_validation_tests.sh --full-report
```

Or directly:

```bash
python scripts/validate_extractions.py -v
```

### Custom Report Location

```bash
python scripts/validate_extractions.py --report-path custom/path/report.json
```

---

## 🔍 Quick Comparison Tool

For debugging a specific PDF, use the comparison script:

```bash
# Compare all aspects
python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf

# Focus on specific component
python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf --focus metadata
python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf --focus abstract
python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf --focus sections
python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf --focus figures
python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf --focus tables

# Compare specific section in detail
python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf --section introduction
python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf --section results
```

**Output Example:**
```
================================================================================
  METADATA COMPARISON
================================================================================

✅ Title:
   Expected: Effectiveness of Reso-Pac in enhancing wound healing...
   Actual:   Effectiveness of Reso-Pac in enhancing wound healing...

✅ DOI:
   Expected: 10.1186/s12903-025-06459-4
   Actual:   10.1186/s12903-025-06459-4

✅ Journal:
   Expected: BMC Oral Health
   Actual:   BMC Oral Health

================================================================================
  SUMMARY
================================================================================

Overall Quality Score: 92.3/100
✅ Excellent extraction quality!
```

---

## 📋 Test Categories

### 1. Metadata Tests
- **test_title_extraction**: Validates title is extracted and matches
- **test_doi_extraction**: Validates DOI matches exactly
- **test_journal_extraction**: Validates journal name matches
- **test_author_extraction**: Validates authors are extracted

### 2. Abstract Tests
- **test_abstract_presence**: Validates abstract is detected
- **test_abstract_content_start**: Validates first 50 chars match (≥80% similarity)
- **test_abstract_content_end**: Validates last 50 chars match (≥80% similarity)
- **test_abstract_word_count**: Validates word count is within ±10%

### 3. Section Tests
- **test_section_count**: Validates section count (≥50% of expected)
- **test_introduction_present**: Validates introduction exists
- **test_methods_present**: Validates methods section exists
- **test_results_present**: Validates results section exists
- **test_section_first_sentence**: Validates content starts correctly (≥70% similarity)

### 4. Figure Tests
- **test_figure_count**: Validates figure count (±2 or ±50% tolerance)
- **test_figure_labels**: Validates figure labels extracted
- **test_figure_captions**: Validates figure captions extracted

### 5. Table Tests
- **test_table_count**: Validates table count (±1 or ±50% tolerance)
- **test_table_labels**: Validates table labels extracted
- **test_table_captions**: Validates table captions extracted

### 6. Reference Tests
- **test_total_references**: Validates references extracted

### 7. Integration Tests
- **test_all_pdfs_basic_extraction**: Smoke test on all 38 PDFs (≥70% success rate)

---

## 🎯 Success Criteria

### Metadata
- ✅ Title: Must be present and match closely
- ✅ DOI: Must match exactly if present in ground truth
- ✅ Journal: Must match closely

### Abstract
- ✅ First 50 chars: ≥80% similarity
- ✅ Last 50 chars: ≥80% similarity
- ✅ Word count: ±10% tolerance

### Sections
- ✅ Section count: ≥50% of expected sections extracted
- ✅ Content: First 100 chars ≥70% similarity

### Figures
- ✅ Count difference: ≤2 figures or ≤50% (whichever is greater)
- ✅ At least some captions extracted

### Tables
- ✅ Count difference: ≤1 table or ≤50% (whichever is greater)
- ✅ At least some captions extracted

---

## 📖 Example Workflows

### Workflow 1: Quick Validation Check

```bash
# 1. Run fast tests to check core functionality
./scripts/run_validation_tests.sh

# 2. If issues found, debug specific PDF
python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf

# 3. Run full validation
./scripts/run_validation_tests.sh --all
```

### Workflow 2: Detailed Analysis

```bash
# 1. Generate full validation report
python scripts/validate_extractions.py -v

# 2. Review report
cat out/validation_report.json | jq .summary

# 3. Debug problematic PDFs
python scripts/compare_extraction.py [problematic_pdf.pdf]
```

### Workflow 3: Component-Specific Testing

```bash
# Test only abstract extraction across all priority files
./scripts/run_validation_tests.sh --abstract

# If failures, compare specific file
python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf --focus abstract
```

---

## 🔧 Prerequisites

### 1. TEI XML Files (Recommended)

For best results, generate TEI XML files first:

```bash
# Start GROBID
docker run -d --rm -p 8070:8070 lfoppiano/grobid:0.8.1

# Generate TEI files
python project.py data/pdf --tei-only --tei-dir data/xml
```

### 2. Python Dependencies

```bash
pip install pytest
```

---

## 📊 Understanding Test Output

### Successful Test Run

```
tests/test_extraction_validation.py::TestMetadataExtraction::test_title_extraction[bmc_oral_health_article1_reso_pac_2025.pdf] PASSED
tests/test_extraction_validation.py::TestMetadataExtraction::test_doi_extraction[bmc_oral_health_article1_reso_pac_2025.pdf] PASSED
tests/test_extraction_validation.py::TestAbstractExtraction::test_abstract_presence[bmc_oral_health_article1_reso_pac_2025.pdf] PASSED

======================== 15 passed in 3.42s ========================
```

### Test Failures

```
FAILED tests/test_extraction_validation.py::TestAbstractExtraction::test_abstract_content_start
AssertionError: Abstract start mismatch for bmc_oral_health_article1_reso_pac_2025.pdf:
  Expected: Background Surgical site infections (SSIs) and pos
  Got: Surgical site infections are a major concern in oral
```

This indicates PaperSlicer's abstract doesn't start exactly as expected.

---

## 🐛 Debugging Failed Tests

### Step 1: Identify the Issue

```bash
# Run the specific failing test with verbose output
pytest tests/test_extraction_validation.py::TestAbstractExtraction::test_abstract_content_start -v -s
```

### Step 2: Compare Expected vs Actual

```bash
# Use comparison tool
python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf --focus abstract
```

### Step 3: Investigate Root Cause

Possible causes:
1. **TEI XML missing or incomplete** → Regenerate TEI files
2. **Section mapping issue** → Check `paperslicer/utils/sections_mapping.py`
3. **Parser bug** → Check `paperslicer/grobid/parser.py`
4. **Ground truth issue** → Verify extraction map is correct

### Step 4: Fix and Retest

```bash
# After fixes, rerun the specific test
pytest tests/test_extraction_validation.py::TestAbstractExtraction -v
```

---

## 📈 Validation Report Structure

The validation report (`out/validation_report.json`) contains:

```json
{
  "generated_at": "2025-10-02T...",
  "summary": {
    "total_pdfs": 38,
    "successful": 35,
    "failed": 3,
    "avg_score": 78.5,
    "common_issues": [
      {"issue": "missing_sections", "count": 12},
      {"issue": "figure_count_diff", "count": 8}
    ]
  },
  "detailed_results": [
    {
      "status": "success",
      "pdf_filename": "bmc_oral_health_article1_reso_pac_2025.pdf",
      "overall_score": 92.3,
      "metadata": {
        "title_present": true,
        "title_matches": true,
        "doi_matches": true
      },
      "abstract": {
        "extracted": true,
        "first_50_similarity": 0.95,
        "last_50_similarity": 0.92,
        "word_count_diff": 0.05
      },
      "sections": {
        "expected_count": 5,
        "extracted_count": 5,
        "matching_sections": ["introduction", "materials_and_methods", "results", "discussion", "conclusions"]
      },
      "figures": {
        "expected_count": 5,
        "extracted_count": 6,
        "count_diff": 1
      },
      "tables": {
        "expected_count": 4,
        "extracted_count": 4,
        "count_diff": 0
      }
    }
  ]
}
```

---

## 🎓 Best Practices

### 1. Run Tests Before Code Changes
```bash
# Establish baseline
./scripts/run_validation_tests.sh
```

### 2. Run Tests After Code Changes
```bash
# Verify improvements or catch regressions
./scripts/run_validation_tests.sh
```

### 3. Use Priority Files for Quick Feedback
```bash
# Fast iteration during development
pytest tests/test_extraction_validation.py -k "bmc_oral_health_article1" -v
```

### 4. Generate Reports Regularly
```bash
# Track progress over time
python scripts/validate_extractions.py --report-path out/validation_$(date +%Y%m%d).json
```

### 5. Compare Before/After
```bash
# Before changes
python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf > before.txt

# Make changes...

# After changes
python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf > after.txt

# Compare
diff before.txt after.txt
```

---

## 🚀 Integration with CI/CD

### GitHub Actions Example

```yaml
name: Validation Tests

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: pip install -r requirements.txt
    
    - name: Run validation tests
      run: pytest tests/test_extraction_validation.py -v -m "not slow"
    
    - name: Generate validation report
      run: python scripts/validate_extractions.py --priority-only
      
    - name: Upload report
      uses: actions/upload-artifact@v2
      with:
        name: validation-report
        path: out/validation_report.json
```

---

## 📝 Adding New PDFs to Validation

### Step 1: Get Ground Truth from Manus AI

Ask Manus AI to extract the PDF following the template in `file_extraction_in_json/`.

### Step 2: Save Extraction Map

Save the JSON file as:
```
manus_work/file_extraction_in_json/{pdf_name}_extraction_map.json
```

### Step 3: Add PDF to Test Parameters (Optional)

If you want priority testing, add to `PRIORITY_FILES` in `test_extraction_validation.py`:

```python
PRIORITY_FILES = [
    "bmc_oral_health_article1_reso_pac_2025.pdf",
    "bmc_oral_health_article2_bone_density_2025.pdf",
    "bmc_oral_health_article3_cytokine_orthodontics_2025.pdf",
    "your_new_pdf.pdf",  # Add here
]
```

### Step 4: Run Validation

```bash
python scripts/compare_extraction.py your_new_pdf.pdf
```

---

## 🎯 Quality Scoring

The validation system assigns a quality score (0-100) based on:

- **Metadata (30%)**: Title, DOI, journal matching
- **Abstract (20%)**: Presence, content similarity, word count
- **Sections (30%)**: Section count and content accuracy
- **Figures (10%)**: Figure count accuracy
- **Tables (10%)**: Table count accuracy

**Score Interpretation:**
- **90-100**: Excellent - Production ready
- **80-89**: Very Good - Minor issues
- **70-79**: Good - Some improvements needed
- **60-69**: Fair - Notable issues present
- **Below 60**: Poor - Significant extraction problems

---

## 🔍 Common Issues and Solutions

### Issue: Abstract Not Found

**Symptoms:**
```
FAILED test_abstract_presence - AssertionError: Abstract not found
```

**Solutions:**
1. Check if TEI XML file exists in `data/xml/`
2. Verify GROBID processed the PDF correctly
3. Check if journal uses non-standard abstract format
4. Review ground truth - some PDFs genuinely lack abstracts

### Issue: Section Count Low

**Symptoms:**
```
AssertionError: Section count too low: expected ~5, got 2
```

**Solutions:**
1. Check section mapping rules in `paperslicer/utils/sections_mapping.py`
2. Review TEI XML for unmapped section headings
3. Check `out/sections/unmapped_heads.csv` for missing mappings
4. Add new mappings if needed

### Issue: Figure/Table Count Mismatch

**Symptoms:**
```
AssertionError: Figure count mismatch: expected 6, got 3
```

**Solutions:**
1. Try different extraction strategies (`--tables auto`, `--images-mode auto`)
2. Check if figures have coordinates in TEI XML
3. Enable image export: `--export-images`
4. Review ground truth - Manus may have counted non-extractable figures

### Issue: Title/DOI Mismatch

**Symptoms:**
```
AssertionError: DOI mismatch: expected '10.1186/...', got ''
```

**Solutions:**
1. Verify TEI XML contains DOI
2. Check PDF metadata
3. Try metadata enrichment: `--mailto your@email.com`
4. Update ground truth if incorrect

---

## 📚 Additional Resources

### Test Files
- `tests/test_extraction_validation.py` - Main validation test suite
- `tests/README_VALIDATION_TESTS.md` - Detailed test documentation

### Scripts
- `scripts/validate_extractions.py` - Report generator
- `scripts/compare_extraction.py` - Quick comparison tool
- `scripts/run_validation_tests.sh` - Convenience test runner

### Ground Truth Data
- `manus_work/file_extraction_in_json/` - Extraction maps (38 files)
- `manus_work/file_extraction_in_json/ENHANCED_SUMMARY.json` - Statistics
- `manus_work/file_extraction_in_json/README.md` - Ground truth documentation

### Configuration
- `pytest.ini` - Pytest configuration with custom markers

---

## 💡 Tips and Tricks

### Tip 1: Use Markers for Selective Testing

```bash
# Run only fast tests
pytest -v -m "not slow"

# Run only slow tests
pytest -v -m slow

# Run only integration tests
pytest -v -m integration
```

### Tip 2: Focus on One PDF During Development

```bash
# Test specific PDF
pytest tests/test_extraction_validation.py -k "bmc_oral_health_article1" -v
```

### Tip 3: Generate Reports Regularly

Track improvement over time:
```bash
# Weekly validation
python scripts/validate_extractions.py --report-path out/validation_week_$(date +%U).json
```

### Tip 4: Use Comparison Tool for Quick Checks

```bash
# Quick sanity check
python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf | grep "Overall"
```

### Tip 5: Combine with Other Tests

```bash
# Run all tests including validation
pytest -v
```

---

## 🎉 Success Metrics

Based on initial validation runs, PaperSlicer should achieve:

- ✅ **≥90% metadata accuracy** (title, DOI, journal)
- ✅ **≥85% abstract extraction** for papers with abstracts
- ✅ **≥75% section detection** for standard research articles
- ✅ **≥80% figure detection** accuracy
- ✅ **≥85% table detection** accuracy
- ✅ **≥70% overall success rate** across all 38 PDFs

---

## 🔮 Future Enhancements

Planned improvements to validation system:
1. ✨ Validate subsection detection accuracy
2. ✨ Test section content completeness (not just first/last sentences)
3. ✨ Verify figure/table page numbers
4. ✨ Validate reference parsing accuracy
5. ✨ Test special sections (funding, acknowledgements)
6. ✨ Cross-reference validation (figures mentioned in text)
7. ✨ Image quality validation (file size, dimensions)
8. ✨ Table structure validation (rows, columns, headers)

---

**Last Updated:** October 2, 2025  
**Version:** 1.0  
**Ground Truth Source:** Manus AI Enhanced Extraction

