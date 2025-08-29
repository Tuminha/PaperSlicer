# project.py
import argparse
import json
import os
from typing import Dict, List

# ---- CS50 top-level functions (wrappers) ----

def get_pdf_text(path: str) -> str:
    """Step 4: PDF -> text (will use PyMuPDF)."""
    raise NotImplementedError("Implement in Step 4")

def normalize_text(text: str) -> str:
    """Step 1: call the normalizer class (you'll implement it)."""
    from paperslicer.extractors.normalizer import TextNormalizer
    return TextNormalizer().normalize(text)

def extract_sections_from_text(text: str) -> Dict[str, str]:
    """Step 2-3: regex/heuristics for section headers."""
    raise NotImplementedError("Implement in Step 2-3")

def process_pdf_to_record(path: str) -> Dict[str, object]:
    """Step 5+: full pipeline PDF->JSON dict (no dataclasses required for CS50)."""
    raise NotImplementedError("Implement in Step 5")

# ---- CLI (will become useful by Step 5) ----

def _iter_pdfs(root: str) -> List[str]:
    if os.path.isdir(root):
        acc = []
        for dp, _, files in os.walk(root):
            for f in files:
                if f.lower().endswith(".pdf"):
                    acc.append(os.path.join(dp, f))
        return sorted(acc)
    return [root] if root.lower().endswith(".pdf") else []

def main():
    parser = argparse.ArgumentParser(description="PaperSlicer (WIP)")
    parser.add_argument("path", nargs="?", help="PDF file or folder")
    parser.add_argument("--out", help="Output .json or .jsonl")
    parser.add_argument("--jsonl", action="store_true", help="Write JSON Lines format")
    parser.add_argument(
        "--tei-out",
        dest="tei_out",
        help="Directory to save TEI XML from Grobid (overrides PAPERSLICER_XML_DIR)",
    )
    args = parser.parse_args()

    # Allow setting TEI output dir even while CLI is WIP
    if args.tei_out:
        os.makedirs(args.tei_out, exist_ok=True)
        # Prefer TEI_SAVE_DIR; also set legacy env for compatibility
        os.environ["TEI_SAVE_DIR"] = args.tei_out
        os.environ["PAPERSLICER_XML_DIR"] = args.tei_out

    # For now, keep CLI inert so you can focus on tests-driven coding
    print("PaperSlicer CLI is WIP. Implement steps in order and run pytest first.")

if __name__ == "__main__":
    main()
