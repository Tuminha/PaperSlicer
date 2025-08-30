# PaperSlicer: Scientific PDF Section Extractor

#### Video Demo: <URL HERE>  
#### Author: Francisco Teixeira Barbosa  
#### GitHub Username: Tuminha  
#### edX Username: Tuminha  
#### Location: Basel, Switzerland  
#### Date: <DATE YOU RECORD VIDEO>  

---

## Description

**PaperSlicer** is my final project for CS50's Introduction to Programming with Python.  
It is a comprehensive command-line tool written in Python that extracts canonical sections, metadata, and media from scientific research papers in PDF format using advanced NLP techniques.

Scientific articles are typically structured with sections like *Abstract, Introduction, Materials and Methods, Results, Discussion, and References*. However, across journals these section titles vary:  
- "Patients and Methods" instead of "Materials and Methods"  
- "Clinical Significance" instead of "Conclusions"  
- "Results and Discussion" merged into one  

For a researcher, student, or developer working with large collections of papers, these inconsistencies make automated processing challenging. **PaperSlicer** addresses this by applying GROBID-based TEI XML parsing, metadata enrichment from online sources, and intelligent section mapping to split articles into a standardized JSON format.

This project is also the foundation for a larger goal: building a structured corpus of dental research literature that could later be used for training large language models (LLMs) in dentistry.

---

## Requirements

- Python 3.8+
- PyMuPDF (for PDF text extraction and image cropping)
- requests (for GROBID integration and metadata APIs)
- lxml (for XML parsing)
- Docker (optional, for GROBID)

---

## Features

- **GROBID Integration**: High-fidelity PDF to TEI XML conversion
- **Metadata Enrichment**: Crossref and PubMed integration for DOI, abstracts, keywords
- **Intelligent Section Extraction**: Robust detection of Introduction, Methods, Results, Discussion, Conclusions
- **Media Processing**: Automatic extraction of figures and tables with coordinates
- **Canonical Mapping**: Normalizes section titles across different journal formats
- **Progress Tracking**: Real-time processing status with detailed reporting
- **Batch Processing**: End-to-end pipeline for large document collections
- **Flexible Output**: JSON metadata, section content, and media files
- **Journal-Specific Handlers**: Tailored processing for specific journals (e.g., Periodontology 2000)
- **Review Mode**: Special handling for review/consensus papers with section augmentation
- **Advanced Image Processing**: Multiple modes for figure/table extraction
- **RAG Export**: Generate chunked JSONL files ready for retrieval-augmented generation
- **Reference Parsing**: Extract and format bibliographic references

---

## Directory Structure

```
PaperSlicer/
├── data/
│   ├── pdf/          # Source PDF files
│   └── xml/          # TEI XML outputs from GROBID
├── media/            # Extracted images and tables
│   └── <year>/<journal>/<AUTHOR>_<year>_<title>_<hash>/
├── out/
│   ├── meta/         # Enriched JSON metadata
│   ├── rag/          # RAG-ready chunked JSONL files
│   └── tests/        # Processing reports and summaries
└── paperslicer/      # Core package
    ├── journals/     # Journal-specific handlers
    └── utils/        # Utilities including exports
```

---

## GROBID Integration (Optional, Recommended)

PaperSlicer uses GROBID to convert PDFs into structured TEI XML, which greatly improves section, figure, table, and reference extraction compared to raw text heuristics.

**Run GROBID (choose one):**

• **Docker (Recommended)**
```bash
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.1
```

• **Native (Java 17)**
```bash
# ensure Java 17
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
export PATH="$JAVA_HOME/bin:$PATH"
java -version
# build & run
git clone https://github.com/ourresearch/grobid.git
cd grobid
./gradlew clean install
cd grobid-service
../gradlew run  # serves at http://localhost:8070
```

**Environment variable**
```bash
export GROBID_URL=http://localhost:8070
```

**Test GROBID integration**
```bash
pytest -k grobid_client -vv
```

If GROBID_URL is not set or the service isn't reachable, the test is skipped.

**Troubleshooting**
• Build error "Unsupported class file major version 67": switch to Java 17 (Temurin) and retry:
```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
export PATH="$JAVA_HOME/bin:$PATH"
java -version
```

---

## Installation & Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment (optional)
cp .env.example .env
# Edit .env with your email for Crossref API
```

---

## Usage Examples

### Basic Operations

**TEI Generation (PDF → TEI XML)**
```bash
# Generate TEI for all PDFs in data/pdf
python project.py data/pdf --tei-only --tei-dir data/xml

# Regenerate TEI even if existing files present
python project.py data/pdf --tei-only --tei-dir data/xml --tei-refresh
```

**Metadata Extraction**
```bash
# Extract metadata from a TEI file
python project.py "data/xml/paper.tei.xml" --meta

# Enrich metadata with online sources
python project.py "data/xml/paper.tei.xml" --resolve-meta --mailto "you@example.com"
```

**End-to-End Processing**
```bash
# Full pipeline: PDF → TEI → metadata → sections → media → JSON
python project.py data/pdf --e2e --tei-dir data/xml --export-images --progress --mailto "you@example.com"

# Review mode for consensus/review papers
python project.py data/pdf --e2e --tei-dir data/xml --review-mode --mailto "you@example.com"
```

**Advanced Image Processing**
```bash
# Auto mode: coordinates then fallback to page images
python project.py data/pdf --e2e --export-images --images-mode auto

# Coordinates only (no fallback)
python project.py data/pdf --e2e --export-images --images-mode coords-only

# Page images for large items only
python project.py data/pdf --e2e --export-images --images-mode pages-large
```

**Section Harvesting**
```bash
# Analyze section headings across TEI files
python project.py data/xml --harvest-sections
```

### Advanced Features

**RAG Export**
```bash
# Generate chunked JSONL for retrieval-augmented generation
python project.py --rag-jsonl out/rag/corpus.jsonl

# Custom chunk size (default: 4800 characters)
python project.py --rag-jsonl out/rag/corpus.jsonl --chunk-chars 6000
```

**Image Summary**
```bash
# Generate CSV summary of image exports
python project.py --images-summary
```

**Custom TEI Output Directory**
```bash
python project.py data/pdf --tei-only --tei-out custom/xml/dir
```

**Progress Tracking**
```bash
# Force progress output (auto-enabled in TTY)
python project.py data/pdf --e2e --progress
```

### Programmatic Usage

**TEI Generation**
```python
from project import grobid_generate_tei
saved_paths = grobid_generate_tei("data/pdf", tei_dir="data/xml")
print(saved_paths)
```

**Metadata Extraction**
```python
from project import extract_metadata_from_tei
md = extract_metadata_from_tei("data/xml/paper.tei.xml")
print(md["title"], md["doi"])
```

**Metadata Enrichment**
```python
from project import resolve_metadata
md = resolve_metadata("data/xml/paper.tei.xml", mailto="you@example.com")
print(md.get("title"), md.get("doi"), md.get("abstract"))
```

**RAG Export**
```python
from paperslicer.utils.exports import export_rag_jsonl
export_rag_jsonl(meta_dir="out/meta", out_path="out/rag/corpus.jsonl")
```

---

## Journal-Specific Processing

PaperSlicer includes specialized handlers for specific journals to improve section extraction accuracy.

### Periodontology 2000 Handler

Automatically detects and applies special processing for Periodontology 2000 review articles:

- **Review-aware section augmentation**: When canonical sections are missing, aggregates body content into discussion
- **Content filtering**: Excludes disclaimers, ORCID info, data availability statements
- **Reference cleanup**: Removes citation markers from aggregated text
- **Conservative approach**: Domain-agnostic heuristics for reliable processing

The handler is automatically applied when `--review-mode` is enabled or when Periodontology 2000 articles are detected.

---

## Output Files

### Metadata JSON (`out/meta/`)
```json
{
  "title": "Paper Title",
  "authors": [{"name": "Author Name", "affiliation": "Institution"}],
  "journal": "Journal Name",
  "doi": "10.1000/xyz123",
  "abstract": "Abstract text...",
  "keywords": ["keyword1", "keyword2"],
  "sections": {
    "introduction": "Introduction text...",
    "materials_and_methods": "Methods text...",
    "results": "Results text...",
    "discussion": "Discussion text...",
    "conclusions": "Conclusions text...",
    "results_and_discussion": "Combined section text..."
  },
  "figures": [{"label": "Fig 1", "caption": "Caption text", "path": "media/...", "source": "grobid+crop"}],
  "tables": [{"label": "Table 1", "caption": "Caption text", "path": "media/...", "source": "page-image"}],
  "references": [{"text": "Author et al. (2023)", "type": "bibr"}]
}
```

### RAG JSONL (`out/rag/`)
```jsonl
{"title": "Paper Title", "doi": "10.1000/xyz123", "section": "introduction", "chunk": "Introduction text chunk...", "chunk_id": 0}
{"title": "Paper Title", "doi": "10.1000/xyz123", "section": "introduction", "chunk": "Next chunk with overlap...", "chunk_id": 1}
```

### Processing Report (`out/tests/`)
- Files processed, successful, failed
- Section coverage statistics
- Media extraction summary
- Missing sections by article
- Image summary CSV with extraction statistics

### Media Files (`media/`)
- Organized by year/journal/author
- Figures and tables with coordinates
- Fallback to page images when coordinates unavailable
- Source tracking (grobid+crop, page-image, page-render)

---

## Environment Variables

- `GROBID_URL`: GROBID service URL (default: http://localhost:8070)
- `TEI_SAVE_DIR`: Directory for TEI XML files (preferred)
- `PAPERSLICER_XML_DIR`: Legacy TEI directory variable
- `CROSSREF_MAILTO`: Email for Crossref User-Agent header
- `PUBMED_API_KEY`: NCBI E-utilities API key for higher limits
- `ALLOW_NET`: Enable network-dependent tests
- `IMAGES_MODE`: Image export mode (auto, coords-only, pages-large)
- `REPORTS_DIR`: Directory for processing reports

---

## Testing

```bash
# Unit tests (no network required)
pytest -k "not grobid_client and not resolver" -vv

# GROBID integration tests
pytest -k grobid_client -vv

# Network-dependent tests
export ALLOW_NET=1
pytest -k resolver -vv

# Save directory tests
pytest -k saves_xml -vv

# Journal handler tests
pytest -k periodontology -vv
```

---

## Troubleshooting

**GROBID Connection Issues**
- Ensure GROBID is running on port 8070
- Check `GROBID_URL` environment variable
- Verify Java 17 is installed (for native setup)

**Metadata Enrichment Fails**
- Set `CROSSREF_MAILTO` for Crossref API access
- Check internet connection
- Verify TEI file contains sufficient metadata

**Media Extraction Issues**
- Ensure PyMuPDF is properly installed
- Check PDF file integrity
- Verify TEI contains figure/table coordinates
- Try different `--images-mode` settings

**Section Mapping**
- Check `out/sections/suggestions.txt` for unmapped headings
- Review `paperslicer/utils/sections_mapping.py` for custom mappings
- Enable `--review-mode` for review/consensus papers

**RAG Export Issues**
- Ensure `out/meta` contains processed JSON files
- Check chunk size settings for your use case
- Verify output directory permissions
