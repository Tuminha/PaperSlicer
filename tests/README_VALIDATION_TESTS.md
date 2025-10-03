# PaperSlicer Validation Tests

## Overview

The `test_extraction_validation.py` file contains comprehensive validation tests that compare PaperSlicer's extraction output against ground truth mappings created by Manus AI for 38 dental research papers.

## Test Structure

### 1. **TestMetadataExtraction**
Validates metadata extraction accuracy:
- ✅ Title extraction
- ✅ DOI extraction  
- ✅ Journal name extraction
- ✅ Author extraction

### 2. **TestAbstractExtraction**
Validates abstract extraction:
- ✅ Abstract presence detection
- ✅ Abstract content start (first 50 characters)
- ✅ Abstract content end (last 50 characters)
- ✅ Word count accuracy (±10% tolerance)

### 3. **TestSectionExtraction**
Validates section extraction:
- ✅ Section count accuracy
- ✅ Introduction section presence
- ✅ Materials and Methods section presence
- ✅ Results section presence
- ✅ Section content starts correctly

### 4. **TestFigureExtraction**
Validates figure extraction:
- ✅ Figure count accuracy (±2 or 50% tolerance)
- ✅ Figure labels extraction
- ✅ Figure captions extraction

### 5. **TestTableExtraction**
Validates table extraction:
- ✅ Table count accuracy (±1 or 50% tolerance)
- ✅ Table labels extraction
- ✅ Table captions extraction

### 6. **TestStructuralInfo**
Validates overall structural information:
- ✅ Reference count validation

### 7. **TestComprehensiveExtraction**
Integration test that runs on all 38 PDFs (marked as slow):
- ✅ Smoke test to ensure PaperSlicer doesn't crash
- ✅ Success rate calculation (expected ≥70%)
- ✅ Summary report generation

## Running the Tests

### Run All Validation Tests
```bash
pytest tests/test_extraction_validation.py -v
```

### Run Only Fast Tests (Priority Files)
```bash
pytest tests/test_extraction_validation.py -v -m "not slow"
```

### Run Only Slow/Integration Tests (All 38 PDFs)
```bash
pytest tests/test_extraction_validation.py -v -m slow
```

### Run Specific Test Class
```bash
# Test only metadata extraction
pytest tests/test_extraction_validation.py::TestMetadataExtraction -v

# Test only abstract extraction
pytest tests/test_extraction_validation.py::TestAbstractExtraction -v

# Test only figures
pytest tests/test_extraction_validation.py::TestFigureExtraction -v
```

### Run Single Test
```bash
pytest tests/test_extraction_validation.py::TestMetadataExtraction::test_title_extraction -v
```

### Run with Detailed Output
```bash
pytest tests/test_extraction_validation.py -v -s
```

## Ground Truth Data

The ground truth extraction mappings are located in:
```
manus_work/file_extraction_in_json/
```

Each PDF has a corresponding `*_extraction_map.json` file containing:
- Complete metadata (title, authors, DOI, journal, year)
- Abstract with first/last 50 characters
- Sections with first/last sentences and word counts
- Figures with labels, captions, and types
- Tables with labels, captions, and structure
- Structural information (totals)
- Quality indicators

## Priority Test Files

The tests use these BMC Oral Health articles as priority files (most complete ground truth):
1. `bmc_oral_health_article1_reso_pac_2025.pdf`
2. `bmc_oral_health_article2_bone_density_2025.pdf`
3. `bmc_oral_health_article3_cytokine_orthodontics_2025.pdf`

## Validation Script

For detailed validation reports, use the validation script:

```bash
# Validate all PDFs and generate report
python scripts/validate_extractions.py

# Validate specific PDF
python scripts/validate_extractions.py --pdf bmc_oral_health_article1_reso_pac_2025.pdf

# Validate only priority files
python scripts/validate_extractions.py --priority-only -v

# Custom report location
python scripts/validate_extractions.py --report-path custom/path/report.json
```

The validation script generates a JSON report with:
- Overall score (0-100) for each PDF
- Detailed metrics for metadata, abstract, sections, figures, tables
- Summary statistics and common issues
- Success/failure counts

## Understanding Test Results

### Success Criteria

**Metadata Tests:**
- Title should match or contain expected title
- DOI should match exactly
- Journal name should match closely

**Abstract Tests:**
- First 50 characters: ≥80% similarity
- Last 50 characters: ≥80% similarity
- Word count: ±10% tolerance

**Section Tests:**
- Section count: ≥50% of expected
- Section content: First 100 chars should be ≥70% similar

**Figure/Table Tests:**
- Count difference: ±2 figures or ±50% (whichever is larger)
- Count difference: ±1 table or ±50% (whichever is larger)

### Common Failure Reasons

1. **GROBID not running**: Tests require TEI XML files
2. **Missing TEI files**: Run `python project.py data/pdf --tei-only --tei-dir data/xml` first
3. **Abstract variations**: Some journals use non-standard formats
4. **Section naming**: Variations in section headers
5. **Figure/table detection**: PDFs with complex layouts

## Prerequisites

Before running validation tests:

1. **Ensure GROBID is running** (optional but recommended):
   ```bash
   docker run -d --rm -p 8070:8070 lfoppiano/grobid:0.8.1
   ```

2. **Generate TEI files** (if not already present):
   ```bash
   python project.py data/pdf --tei-only --tei-dir data/xml
   ```

3. **Install test dependencies**:
   ```bash
   pip install pytest
   ```

## Interpreting Results

### High Scores (≥80/100)
PaperSlicer is extracting content accurately and completely.

### Medium Scores (50-79/100)
PaperSlicer is working but may have issues with:
- Section detection or mapping
- Figure/table count accuracy
- Abstract extraction

### Low Scores (<50/100)
Significant extraction issues. Check:
- TEI XML file quality
- PDF structure complexity
- Section mapping rules

## Continuous Integration

Add to CI pipeline:
```yaml
# .github/workflows/test.yml
- name: Run validation tests
  run: |
    pytest tests/test_extraction_validation.py -v -m "not slow"
```

## Contributing

When adding new PDFs to test:
1. Get Manus AI to create extraction map
2. Place in `manus_work/file_extraction_in_json/`
3. Add PDF filename to test parameters if needed
4. Run validation to ensure quality

## Troubleshooting

### Tests Skipped
- **Cause**: Extraction map or PDF file not found
- **Solution**: Check file paths and naming

### Tests Fail on Metadata
- **Cause**: TEI parsing issues or missing data
- **Solution**: Verify TEI XML file exists and is valid

### Tests Fail on Sections
- **Cause**: Section mapping issues
- **Solution**: Check `paperslicer/utils/sections_mapping.py` for mapping rules

### Tests Fail on Figures/Tables
- **Cause**: Complex PDF layouts or missing coordinates
- **Solution**: Try different extraction modes (`--images-mode`, `--tables`)

## Statistics

Based on Manus AI extraction mappings:
- **38 PDFs** with ground truth data
- **137 figures** to validate
- **88 tables** to validate
- **79 sections** with content
- **19 abstracts** with full text
- **1,135 references** total

## Future Enhancements

Planned improvements to validation tests:
1. ✨ Validate subsection detection
2. ✨ Test section content completeness
3. ✨ Verify figure/table page numbers
4. ✨ Check reference parsing accuracy
5. ✨ Test special section handling (funding, acknowledgements)

---

**Last Updated:** October 2, 2025

