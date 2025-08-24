# PaperSlicer: Scientific PDF Section Extractor

#### Video Demo: <URL HERE>  
#### Author: Francisco Teixeira Barbosa  
#### GitHub Username: Tuminha  
#### edX Username: <YOUR EDX USERNAME>  
#### Location: Basel, Switzerland  
#### Date: <DATE YOU RECORD VIDEO>  

---

## Description

**PaperSlicer** is my final project for CS50’s Introduction to Programming with Python.  
It is a command-line tool written in Python that extracts canonical sections from scientific research papers in PDF format.  

Scientific articles are typically structured with sections like *Abstract, Introduction, Materials and Methods, Results, Discussion, and References*. However, across journals these section titles vary:  
- “Patients and Methods” instead of “Materials and Methods”  
- “Clinical Significance” instead of “Conclusions”  
- “Results and Discussion” merged into one  

For a researcher, student, or developer working with large collections of papers, these inconsistencies make automated processing challenging. **PaperSlicer** addresses this by applying text normalization, regular expression matching, and heuristic rules to split articles into a standardized JSON format.

This project is also the foundation for a larger goal: building a structured corpus of dental research literature that could later be used for training large language models (LLMs) in dentistry.

---

## Features

- **PDF text extraction** using [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/)  
- **Normalization** of text (fix hyphenated words, remove page numbers/headers/footers)  
- **Robust section detection** via regex and heuristics (handles variants like “Patients and Methods”, “Results and Discussion”, etc.)  
- **Post-processing**: trims whitespace, removes empty or noise sections, and collapses multiple blank lines  
- **JSON/JSONL export** of each article, with consistent section labels  
- **Command-line interface**: process one PDF or an entire folder  

---

## Example Usage

```bash
# Single file → JSON
python project.py data/paper1.pdf --out out/paper1.json

# Folder of PDFs → JSONL (one record per line)
python project.py data/ --out out/papers.jsonl --jsonl