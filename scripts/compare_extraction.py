#!/usr/bin/env python3
"""
Quick comparison tool for PaperSlicer extraction vs ground truth.

This script shows a side-by-side comparison of what PaperSlicer extracts
versus what's in the Manus AI ground truth mapping for a specific PDF.

Usage:
    python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf
    python scripts/compare_extraction.py bmc_oral_health_article1_reso_pac_2025.pdf --section introduction
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

from paperslicer.pipeline import Pipeline


# Directory paths
PROJECT_ROOT = Path(__file__).parent.parent
EXTRACTION_MAPS_DIR = PROJECT_ROOT / "manus_work" / "file_extraction_in_json"
PDF_DIR = PROJECT_ROOT / "data" / "pdf"
XML_DIR = PROJECT_ROOT / "data" / "xml"


def load_extraction_map(pdf_filename: str) -> Dict[str, Any]:
    """Load the ground truth extraction map for a given PDF."""
    map_filename = pdf_filename.replace('.pdf', '_extraction_map.json')
    map_path = EXTRACTION_MAPS_DIR / map_filename
    
    if not map_path.exists():
        print(f"❌ Extraction map not found: {map_filename}")
        return None
    
    with open(map_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def print_section_divider(title: str):
    """Print a section divider."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_comparison(label: str, expected: Any, actual: Any):
    """Print a comparison between expected and actual values."""
    match_symbol = "✅" if expected == actual else "❌"
    print(f"{match_symbol} {label}:")
    print(f"   Expected: {expected}")
    print(f"   Actual:   {actual}")
    print()


def print_text_comparison(label: str, expected: str, actual: str, max_len: int = 100):
    """Print text comparison with truncation."""
    exp_truncated = expected[:max_len] + "..." if len(expected) > max_len else expected
    act_truncated = actual[:max_len] + "..." if len(actual) > max_len else actual
    
    # Simple similarity check
    similarity = "✅" if expected.lower() in actual.lower() or actual.lower() in expected.lower() else "❌"
    
    print(f"{similarity} {label}:")
    print(f"   Expected: {exp_truncated}")
    print(f"   Actual:   {act_truncated}")
    print()


def compare_metadata(expected: Dict, actual: Any):
    """Compare metadata extraction."""
    print_section_divider("METADATA COMPARISON")
    
    exp_meta = expected.get('metadata', {})
    
    print_text_comparison("Title", exp_meta.get('title', ''), actual.meta.title or '')
    print_comparison("DOI", exp_meta.get('doi', ''), actual.meta.doi or '')
    print_text_comparison("Journal", exp_meta.get('journal', ''), actual.meta.journal or '')
    print_comparison("Year", exp_meta.get('year', ''), actual.meta.year or '')
    print_comparison("Authors Count", len(exp_meta.get('authors', [])), len(actual.meta.authors or []))


def compare_abstract(expected: Dict, actual: Any):
    """Compare abstract extraction."""
    print_section_divider("ABSTRACT COMPARISON")
    
    exp_abstract = expected.get('abstract', {})
    act_abstract = actual.sections.get('abstract', '')
    
    print_comparison("Abstract Present", exp_abstract.get('present', False), bool(act_abstract))
    
    if exp_abstract.get('present') and act_abstract:
        print_text_comparison("First 50 chars", exp_abstract.get('first_50_chars', ''), act_abstract[:50])
        print_text_comparison("Last 50 chars", exp_abstract.get('last_50_chars', ''), act_abstract[-50:])
        
        exp_wc = exp_abstract.get('word_count', 0)
        act_wc = len(act_abstract.split())
        wc_diff = abs(exp_wc - act_wc)
        wc_symbol = "✅" if wc_diff <= exp_wc * 0.1 else "❌"
        
        print(f"{wc_symbol} Word Count:")
        print(f"   Expected: {exp_wc}")
        print(f"   Actual:   {act_wc} (diff: {wc_diff})")
        print()


def compare_sections(expected: Dict, actual: Any, section_name: str = None):
    """Compare section extraction."""
    if section_name:
        print_section_divider(f"SECTION COMPARISON: {section_name.upper()}")
        
        exp_sections = expected.get('sections', {})
        if section_name not in exp_sections:
            print(f"Section '{section_name}' not found in ground truth.")
            return
        
        exp_section = exp_sections[section_name]
        act_section = actual.sections.get(section_name, '')
        
        print_comparison("Section Present", bool(exp_section), bool(act_section))
        
        if exp_section and act_section:
            print_text_comparison(
                "First 100 chars",
                exp_section.get('first_100_chars', ''),
                act_section[:100],
                max_len=100
            )
            print_text_comparison(
                "Last 100 chars",
                exp_section.get('last_100_chars', ''),
                act_section[-100:],
                max_len=100
            )
            
            exp_wc = exp_section.get('word_count', 0)
            act_wc = len(act_section.split())
            wc_diff = abs(exp_wc - act_wc)
            wc_symbol = "✅" if exp_wc == 0 or wc_diff <= exp_wc * 0.15 else "❌"
            
            print(f"{wc_symbol} Word Count:")
            print(f"   Expected: {exp_wc}")
            print(f"   Actual:   {act_wc} (diff: {wc_diff})")
            print()
    else:
        print_section_divider("SECTIONS OVERVIEW")
        
        exp_sections = expected.get('sections', {})
        canonical_sections = {
            'introduction', 'materials_and_methods', 'results', 
            'discussion', 'conclusions', 'results_and_discussion'
        }
        
        print("Expected Sections:")
        for sec in exp_sections.keys():
            print(f"  - {sec}")
        
        print("\nExtracted Sections:")
        for sec in actual.sections.keys():
            if sec in canonical_sections and actual.sections[sec]:
                word_count = len(actual.sections[sec].split())
                print(f"  - {sec} ({word_count} words)")
        
        print()


def compare_figures(expected: Dict, actual: Any):
    """Compare figure extraction."""
    print_section_divider("FIGURES COMPARISON")
    
    exp_count = expected['structural_info'].get('total_figures', 0)
    act_count = len(actual.figures)
    
    count_symbol = "✅" if abs(exp_count - act_count) <= 2 else "❌"
    print(f"{count_symbol} Figure Count:")
    print(f"   Expected: {exp_count}")
    print(f"   Actual:   {act_count}")
    print()
    
    exp_figures = expected.get('figures', [])
    
    print(f"Expected Figures:")
    for i, fig in enumerate(exp_figures[:5], 1):  # Show first 5
        label = fig.get('label', 'N/A')
        caption = fig.get('caption', '')[:60] + "..." if len(fig.get('caption', '')) > 60 else fig.get('caption', '')
        print(f"  {i}. {label}: {caption}")
    
    if len(exp_figures) > 5:
        print(f"  ... and {len(exp_figures) - 5} more")
    
    print(f"\nExtracted Figures:")
    for i, fig in enumerate(actual.figures[:5], 1):  # Show first 5
        label = fig.get('label', 'N/A')
        caption = fig.get('caption', '')[:60] + "..." if len(fig.get('caption', '')) > 60 else fig.get('caption', '')
        source = fig.get('source', 'unknown')
        print(f"  {i}. {label}: {caption} [source: {source}]")
    
    if len(actual.figures) > 5:
        print(f"  ... and {len(actual.figures) - 5} more")
    
    print()


def compare_tables(expected: Dict, actual: Any):
    """Compare table extraction."""
    print_section_divider("TABLES COMPARISON")
    
    exp_count = expected['structural_info'].get('total_tables', 0)
    act_count = len(actual.tables)
    
    count_symbol = "✅" if abs(exp_count - act_count) <= 1 else "❌"
    print(f"{count_symbol} Table Count:")
    print(f"   Expected: {exp_count}")
    print(f"   Actual:   {act_count}")
    print()
    
    exp_tables = expected.get('tables', [])
    
    print(f"Expected Tables:")
    for i, tbl in enumerate(exp_tables[:5], 1):  # Show first 5
        label = tbl.get('label', 'N/A')
        caption = tbl.get('caption', '')[:60] + "..." if len(tbl.get('caption', '')) > 60 else tbl.get('caption', '')
        print(f"  {i}. {label}: {caption}")
    
    if len(exp_tables) > 5:
        print(f"  ... and {len(exp_tables) - 5} more")
    
    print(f"\nExtracted Tables:")
    for i, tbl in enumerate(actual.tables[:5], 1):  # Show first 5
        label = tbl.get('label', 'N/A')
        caption = tbl.get('caption', '')[:60] + "..." if len(tbl.get('caption', '')) > 60 else tbl.get('caption', '')
        source = tbl.get('source', 'unknown')
        print(f"  {i}. {label}: {caption} [source: {source}]")
    
    if len(actual.tables) > 5:
        print(f"  ... and {len(actual.tables) - 5} more")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Compare PaperSlicer extraction with ground truth for a specific PDF"
    )
    parser.add_argument(
        'pdf_filename',
        help='PDF filename to compare (e.g., bmc_oral_health_article1_reso_pac_2025.pdf)'
    )
    parser.add_argument(
        '--section',
        choices=['introduction', 'materials_and_methods', 'results', 'discussion', 'conclusions'],
        help='Compare specific section in detail'
    )
    parser.add_argument(
        '--focus',
        choices=['metadata', 'abstract', 'sections', 'figures', 'tables', 'all'],
        default='all',
        help='Focus comparison on specific area'
    )
    
    args = parser.parse_args()
    
    # Ensure .pdf extension
    pdf_filename = args.pdf_filename
    if not pdf_filename.endswith('.pdf'):
        pdf_filename += '.pdf'
    
    # Load ground truth
    print(f"\n📄 Loading ground truth for: {pdf_filename}")
    expected = load_extraction_map(pdf_filename)
    
    if not expected:
        print(f"❌ No ground truth found. Ensure extraction map exists in:")
        print(f"   {EXTRACTION_MAPS_DIR}")
        sys.exit(1)
    
    # Check PDF exists
    pdf_path = PDF_DIR / pdf_filename
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)
    
    # Run PaperSlicer
    print(f"🔄 Running PaperSlicer extraction...")
    try:
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(str(pdf_path))
        print(f"✅ Extraction completed successfully!\n")
    except Exception as e:
        print(f"❌ PaperSlicer failed: {str(e)}")
        sys.exit(1)
    
    # Perform comparisons based on focus
    if args.focus in ['metadata', 'all']:
        compare_metadata(expected, record)
    
    if args.focus in ['abstract', 'all']:
        compare_abstract(expected, record)
    
    if args.focus in ['sections', 'all']:
        compare_sections(expected, record, section_name=args.section)
    
    if args.focus in ['figures', 'all']:
        compare_figures(expected, record)
    
    if args.focus in ['tables', 'all']:
        compare_tables(expected, record)
    
    print_section_divider("SUMMARY")
    
    # Calculate quick score
    scores = []
    
    # Metadata score
    if expected.get('metadata', {}).get('doi'):
        scores.append(1 if record.meta.doi == expected['metadata']['doi'] else 0)
    
    # Abstract score
    if expected.get('abstract', {}).get('present'):
        scores.append(1 if 'abstract' in record.sections else 0)
    
    # Sections score
    exp_sections = len(expected.get('sections', {}))
    act_sections = sum(1 for k in record.sections.keys() 
                      if k in {'introduction', 'materials_and_methods', 'results', 'discussion', 'conclusions'}
                      and record.sections[k])
    if exp_sections > 0:
        scores.append(min(act_sections / exp_sections, 1.0))
    
    # Figures score
    exp_figs = expected['structural_info'].get('total_figures', 0)
    act_figs = len(record.figures)
    if exp_figs > 0:
        scores.append(max(0, 1 - abs(exp_figs - act_figs) / exp_figs))
    
    # Tables score
    exp_tbls = expected['structural_info'].get('total_tables', 0)
    act_tbls = len(record.tables)
    if exp_tbls > 0:
        scores.append(max(0, 1 - abs(exp_tbls - act_tbls) / exp_tbls))
    
    avg_score = (sum(scores) / len(scores) * 100) if scores else 0
    
    print(f"Overall Quality Score: {avg_score:.1f}/100")
    
    if avg_score >= 80:
        print("✅ Excellent extraction quality!")
    elif avg_score >= 60:
        print("⚠️  Good extraction, but some issues present")
    else:
        print("❌ Significant extraction issues detected")
    
    print()


if __name__ == "__main__":
    main()

