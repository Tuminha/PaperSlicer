# Enhanced PDF Extraction Mappings

**Generated:** October 2, 2025
**Total PDFs:** 38
**Extraction Quality:** Enhanced - Detailed manual-level extraction

---

## Overview

This directory contains **enhanced detailed extraction mappings** for all 38 academic dental research papers. Each mapping has been processed with the same level of detail as the original BMC Oral Health article 1 example.

### Key Features

- ✅ **Complete metadata** - Full titles, author lists, DOIs, journals, years
- ✅ **Detailed abstracts** - Complete text with accurate word/character counts
- ✅ **Section content** - Exact first/last sentences for each section
- ✅ **Subsections** - Identified and listed where present
- ✅ **Figures** - Complete captions, types, and page references
- ✅ **Tables** - Detailed structure information and captions
- ✅ **Other sections** - Funding, acknowledgements, declarations
- ✅ **Quality indicators** - Readability assessment and special notes

### Statistics

- **Total Figures Identified:** 137
- **Total Tables Identified:** 88
- **Total References:** 1135
- **Total Sections:** 79
- **PDFs with Abstracts:** 19/38
- **PDFs with Authors:** 17/38
- **PDFs with Subsections:** 21/38
- **Average Abstract Length:** 507 words
- **Average Sections per PDF:** 2.1

### Journal Distribution

| Journal | Count |
|---------|-------|
| Dentistry Journal (MDPI) | 7 |
| Clinical Oral Implants Research | 3 |
| BMC Oral Health | 3 |
| Dental Materials Journal | 3 |
| International Journal of Dental Materials | 3 |
| International Journal of Oral Science | 3 |
| International Journal of Implant Dentistry | 3 |
| Journal of Oral and Maxillofacial Research | 3 |
| The Open Dentistry Journal | 3 |
| Consensus Report | 3 |
| Periodontology 2000 | 2 |
| Oral (MDPI) | 2 |

### Usage

Each `*_extraction_map.json` file contains comprehensive structural information suitable for:

- Unit test development and validation
- PDF extraction algorithm testing
- Document structure analysis
- Content verification and quality assurance

### File Format

All files follow a consistent JSON schema with:

```json
{
  "file_name": "...",
  "metadata": { ... },
  "abstract": { ... },
  "sections": { ... },
  "figures": [ ... ],
  "tables": [ ... ],
  "other_sections": { ... },
  "structural_info": { ... },
  "quality_indicators": { ... }
}
```

---

**Ready for PaperSlicer unit test development!**
