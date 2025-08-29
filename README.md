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
It is a command-line tool written in Python that extracts canonical sections from scientific research papers in PDF format.  

Scientific articles are typically structured with sections like *Abstract, Introduction, Materials and Methods, Results, Discussion, and References*. However, across journals these section titles vary:  
- "Patients and Methods" instead of "Materials and Methods"  
- "Clinical Significance" instead of "Conclusions"  
- "Results and Discussion" merged into one  

For a researcher, student, or developer working with large collections of papers, these inconsistencies make automated processing challenging. **PaperSlicer** addresses this by applying text normalization, regular expression matching, and heuristic rules to split articles into a standardized JSON format.

This project is also the foundation for a larger goal: building a structured corpus of dental research literature that could later be used for training large language models (LLMs) in dentistry.

---

## Requirements

- Python 3.8+
- PyMuPDF (for PDF text extraction)
- requests (for GROBID integration)
- lxml (for XML parsing)

---

## Features

- **PDF text extraction** using [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/)  
- **Normalization** of text (fix hyphenated words, remove page numbers/headers/footers)  
- **Robust section detection** via regex and heuristics (handles variants like "Patients and Methods", "Results and Discussion", etc.)  
- **Post-processing**: trims whitespace, removes empty or noise sections, and collapses multiple blank lines  
- **JSON/JSONL export** of each article, with consistent section labels  
- **Command-line interface**: process one PDF or an entire folder  

---

## GROBID Integration (Optional, Recommended)

PaperSlicer can use GROBID to convert PDFs into structured TEI XML, which greatly improves section, figure, table, and reference extraction compared to raw text heuristics.

**Run GROBID (choose one):**

• **Docker**
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

**Run the Grobid client test**
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

## Example Usage

```bash
# Single file → JSON
python project.py data/pdf/paper1.pdf --out out/paper1.json

# Folder of PDFs → JSONL (one record per line)
python project.py data/pdf --out out/papers.jsonl --jsonl

# Save TEI XML to a custom folder
python project.py data/pdf/paper1.pdf --tei-out data/xml
```

Directory layout:

- data/pdf: place your source PDF files here
- data/xml: TEI XML outputs from GROBID

TEI autosave:
- The pipeline automatically saves TEI XML to `data/xml` when Grobid is used.
- Override the save location with `TEI_SAVE_DIR` (preferred) or `PAPERSLICER_XML_DIR` (legacy).
- Or pass `--tei-out` on the CLI to set it per run.

Tip: when using the Grobid client directly, you can persist TEI alongside the bytes by passing a save directory:

```python
from paperslicer.grobid.client import GrobidClient
tei_bytes, tei_path = GrobidClient().process_fulltext("data/pdf/paper1.pdf", save_dir="data/xml")
print(tei_path)
```
