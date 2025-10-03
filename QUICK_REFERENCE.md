# PaperSlicer Validation Testing - Quick Reference Card

## 🚀 One-Command Testing

```bash
# Run validation tests (takes ~30 seconds)
./scripts/run_validation_tests.sh
```

---

## 📋 Common Commands

### Run Tests

```bash
# Fast tests (3 priority PDFs)
./scripts/run_validation_tests.sh

# All tests (38 PDFs) - takes 5-10 minutes
./scripts/run_validation_tests.sh --all

# Specific component
./scripts/run_validation_tests.sh --metadata
./scripts/run_validation_tests.sh --abstract
./scripts/run_validation_tests.sh --sections
./scripts/run_validation_tests.sh --figures
./scripts/run_validation_tests.sh --tables
```

### Generate Reports

```bash
# Quick report (priority PDFs)
./scripts/run_validation_tests.sh --report

# Full report (all 38 PDFs)
./scripts/run_validation_tests.sh --full-report
```

### Debug Single PDF

```bash
# Full comparison
python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf

# Focus on specific aspect
python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf --focus abstract
python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf --focus sections
```

---

## 📁 Important Locations

| What | Where |
|------|-------|
| Ground truth maps | `manus_work/file_extraction_in_json/` |
| Test file | `tests/test_extraction_validation.py` |
| Validation script | `scripts/validate_extractions.py` |
| Comparison tool | `scripts/compare_extraction.py` |
| Test runner | `scripts/run_validation_tests.sh` |
| Complete guide | `VALIDATION_GUIDE.md` |
| Reports output | `out/validation_report.json` |

---

## ✅ What's Being Validated

- ✅ **Metadata:** Title, DOI, journal, authors
- ✅ **Abstract:** Presence, content accuracy, word count
- ✅ **Sections:** Introduction, methods, results, discussion, conclusions
- ✅ **Figures:** Count, labels, captions
- ✅ **Tables:** Count, labels, captions
- ✅ **References:** Presence and count

---

## 📊 Ground Truth Stats

- **38 PDFs** with extraction maps
- **137 figures** catalogued
- **88 tables** catalogued
- **79 sections** with content
- **19 abstracts** fully mapped
- **1,135 references** counted

---

## 🎯 Success Criteria

| Component | Criteria |
|-----------|----------|
| **Metadata** | Title/DOI/journal must match closely |
| **Abstract** | First/last 50 chars ≥80% similar, word count ±10% |
| **Sections** | ≥50% of expected sections extracted |
| **Figures** | Count within ±2 or ±50% |
| **Tables** | Count within ±1 or ±50% |
| **Overall** | ≥70% success rate across all PDFs |

---

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Tests skipped | Check TEI XML files exist in `data/xml/` |
| Abstract tests fail | Verify GROBID processed PDF correctly |
| Section count low | Check section mapping in `sections_mapping.py` |
| Figure count off | Try `--export-images` and `--images-mode auto` |
| All tests fail | Ensure GROBID is running, TEI files exist |

**Generate TEI files:**
```bash
python project.py data/pdf --tei-only --tei-dir data/xml
```

---

## 📈 Interpreting Scores

| Score | Interpretation | Action |
|-------|----------------|--------|
| **90-100** | 🎉 Excellent | Production ready! |
| **80-89** | ✅ Very Good | Minor tweaks only |
| **70-79** | 👍 Good | Some improvements needed |
| **60-69** | ⚠️ Fair | Review common issues |
| **<60** | ❌ Poor | Investigate major problems |

---

## 🔧 Prerequisites Checklist

- [ ] Python 3.8+ installed
- [ ] `pip install -r requirements.txt` completed
- [ ] TEI XML files generated (optional but recommended)
- [ ] GROBID running (optional but recommended)

---

## 💡 Pro Tips

1. **Start Small:** Test priority files first
2. **Use Comparison Tool:** Debug issues quickly
3. **Generate Reports:** Track progress over time
4. **Check Ground Truth:** Verify extraction maps are accurate
5. **Run Before Commits:** Catch regressions early

---

## 🎓 Example Session

```bash
# 1. Quick validation
./scripts/run_validation_tests.sh
# ✅ 15 passed in 3.42s

# 2. One test failed - investigate
python scripts/compare_extraction.py bmc_oral_health_article2_bone_density_2025.pdf --focus abstract
# Shows: Abstract start doesn't match

# 3. Check TEI file
cat data/xml/bmc_oral_health_article2_bone_density_2025.tei.xml | grep -A 3 "<abstract"

# 4. Fix parser issue...

# 5. Retest
pytest tests/test_extraction_validation.py::TestAbstractExtraction -v
# ✅ All passed!

# 6. Full validation
./scripts/run_validation_tests.sh --all
# ✅ 95 passed in 8.23s

# 7. Generate report
python scripts/validate_extractions.py -v
# Overall Score: 87.5/100 ✅
```

---

## 📚 Documentation

- **VALIDATION_GUIDE.md** - Complete guide (detailed)
- **tests/README_VALIDATION_TESTS.md** - Test documentation
- **QUICK_REFERENCE.md** - This file (quick lookup)

---

**Last Updated:** October 2, 2025  
**Version:** 1.0

---

**Ready to test? Run:**
```bash
./scripts/run_validation_tests.sh
```

