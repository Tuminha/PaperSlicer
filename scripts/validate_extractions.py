#!/usr/bin/env python3
"""
Validation report generator for PaperSlicer extraction quality.

This script compares PaperSlicer's output against the ground truth 
extraction maps created by Manus AI and generates a detailed report.

Usage:
    python scripts/validate_extractions.py
    python scripts/validate_extractions.py --pdf bmc_oral_health_article1_reso_pac_2025.pdf
    python scripts/validate_extractions.py --report-path out/validation_report.json
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from paperslicer.pipeline import Pipeline


# Directory paths
PROJECT_ROOT = Path(__file__).parent.parent
EXTRACTION_MAPS_DIR = PROJECT_ROOT / "manus_work" / "file_extraction_in_json"
PDF_DIR = PROJECT_ROOT / "data" / "pdf"
XML_DIR = PROJECT_ROOT / "data" / "xml"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "out" / "validation_report.json"


def load_extraction_map(pdf_filename: str) -> Dict[str, Any]:
    """Load the ground truth extraction map for a given PDF."""
    map_filename = pdf_filename.replace('.pdf', '_extraction_map.json')
    map_path = EXTRACTION_MAPS_DIR / map_filename
    
    if not map_path.exists():
        return None
    
    with open(map_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def fuzzy_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two strings."""
    if not text1 or not text2:
        return 1.0 if text1 == text2 else 0.0
    
    # Normalize whitespace
    t1 = ' '.join(text1.split())
    t2 = ' '.join(text2.split())
    
    # Simple character-level similarity
    longer_len = max(len(t1), len(t2))
    if longer_len == 0:
        return 1.0
    
    matches = sum(1 for a, b in zip(t1, t2) if a == b)
    return matches / longer_len


def validate_single_pdf(pdf_filename: str, verbose: bool = False) -> Dict[str, Any]:
    """Validate extraction for a single PDF."""
    pdf_path = PDF_DIR / pdf_filename
    
    if not pdf_path.exists():
        return {
            'status': 'error',
            'error': f'PDF not found: {pdf_filename}'
        }
    
    # Load ground truth
    expected = load_extraction_map(pdf_filename)
    if not expected:
        return {
            'status': 'error',
            'error': f'Extraction map not found for {pdf_filename}'
        }
    
    # Run PaperSlicer
    try:
        pipeline = Pipeline(try_start_grobid=False, xml_save_dir=str(XML_DIR), export_images=False)
        record = pipeline.process(str(pdf_path))
    except Exception as e:
        return {
            'status': 'error',
            'error': f'PaperSlicer failed: {str(e)}'
        }
    
    # Compare results
    results = {
        'status': 'success',
        'pdf_filename': pdf_filename,
        'metadata': {},
        'abstract': {},
        'sections': {},
        'figures': {},
        'tables': {},
        'overall_score': 0.0
    }
    
    # Validate metadata
    metadata_checks = {
        'title_present': bool(record.meta.title),
        'title_matches': False,
        'doi_present': bool(record.meta.doi),
        'doi_matches': False,
        'journal_present': bool(record.meta.journal),
        'journal_matches': False,
        'authors_present': bool(record.meta.authors),
    }
    
    if record.meta.title and expected['metadata'].get('title'):
        exp_title = expected['metadata']['title'].lower()
        act_title = record.meta.title.lower()
        metadata_checks['title_matches'] = exp_title in act_title or act_title in exp_title
    
    if record.meta.doi and expected['metadata'].get('doi'):
        metadata_checks['doi_matches'] = record.meta.doi == expected['metadata']['doi']
    
    if record.meta.journal and expected['metadata'].get('journal'):
        exp_journal = expected['metadata']['journal'].lower()
        act_journal = record.meta.journal.lower()
        metadata_checks['journal_matches'] = exp_journal in act_journal or act_journal in exp_journal
    
    results['metadata'] = metadata_checks
    
    # Validate abstract
    if expected['abstract'].get('present'):
        abstract_text = record.sections.get('abstract', '')
        abstract_checks = {
            'extracted': bool(abstract_text),
            'first_50_similarity': 0.0,
            'last_50_similarity': 0.0,
            'word_count_diff': 0
        }
        
        if abstract_text:
            if expected['abstract'].get('first_50_chars'):
                abstract_checks['first_50_similarity'] = fuzzy_similarity(
                    expected['abstract']['first_50_chars'],
                    abstract_text[:50]
                )
            
            if expected['abstract'].get('last_50_chars'):
                abstract_checks['last_50_similarity'] = fuzzy_similarity(
                    expected['abstract']['last_50_chars'],
                    abstract_text[-50:]
                )
            
            expected_wc = expected['abstract'].get('word_count', 0)
            actual_wc = len(abstract_text.split())
            if expected_wc > 0:
                abstract_checks['word_count_diff'] = abs(actual_wc - expected_wc) / expected_wc
        
        results['abstract'] = abstract_checks
    
    # Validate sections
    expected_sections = expected.get('sections', {})
    section_checks = {
        'expected_count': len(expected_sections),
        'extracted_count': 0,
        'matching_sections': []
    }
    
    canonical_keys = {'introduction', 'materials_and_methods', 'results', 'discussion', 'conclusions'}
    section_checks['extracted_count'] = sum(1 for k in record.sections.keys() 
                                            if k in canonical_keys and record.sections[k])
    
    for section_name in expected_sections.keys():
        if section_name in record.sections and record.sections[section_name]:
            section_checks['matching_sections'].append(section_name)
    
    results['sections'] = section_checks
    
    # Validate figures
    expected_fig_count = expected['structural_info'].get('total_figures', 0)
    actual_fig_count = len(record.figures)
    
    results['figures'] = {
        'expected_count': expected_fig_count,
        'extracted_count': actual_fig_count,
        'count_diff': abs(actual_fig_count - expected_fig_count),
        'figures_with_captions': sum(1 for f in record.figures if f.get('caption'))
    }
    
    # Validate tables
    expected_tbl_count = expected['structural_info'].get('total_tables', 0)
    actual_tbl_count = len(record.tables)
    
    results['tables'] = {
        'expected_count': expected_tbl_count,
        'extracted_count': actual_tbl_count,
        'count_diff': abs(actual_tbl_count - expected_tbl_count),
        'tables_with_captions': sum(1 for t in record.tables if t.get('caption'))
    }
    
    # Calculate overall score (0-100)
    score_components = []
    
    # Metadata score (30%)
    metadata_score = sum([
        1 if metadata_checks['title_present'] else 0,
        1 if metadata_checks['title_matches'] else 0,
        1 if metadata_checks['doi_present'] else 0,
        1 if metadata_checks['doi_matches'] else 0,
        1 if metadata_checks['journal_present'] else 0,
        1 if metadata_checks['journal_matches'] else 0,
    ]) / 6.0
    score_components.append(metadata_score * 30)
    
    # Abstract score (20%)
    if expected['abstract'].get('present'):
        abs_checks = results['abstract']
        abstract_score = sum([
            1 if abs_checks.get('extracted') else 0,
            abs_checks.get('first_50_similarity', 0),
            abs_checks.get('last_50_similarity', 0),
            1 - min(abs_checks.get('word_count_diff', 1), 1)
        ]) / 4.0
        score_components.append(abstract_score * 20)
    else:
        score_components.append(20)  # Full points if no abstract expected
    
    # Sections score (30%)
    if section_checks['expected_count'] > 0:
        section_score = min(section_checks['extracted_count'] / section_checks['expected_count'], 1.0)
        score_components.append(section_score * 30)
    else:
        score_components.append(15)  # Partial points if unclear
    
    # Figures score (10%)
    if expected_fig_count > 0:
        fig_score = max(0, 1 - (results['figures']['count_diff'] / expected_fig_count))
        score_components.append(fig_score * 10)
    else:
        score_components.append(10)
    
    # Tables score (10%)
    if expected_tbl_count > 0:
        tbl_score = max(0, 1 - (results['tables']['count_diff'] / expected_tbl_count))
        score_components.append(tbl_score * 10)
    else:
        score_components.append(10)
    
    results['overall_score'] = sum(score_components)
    
    if verbose:
        print(f"\n{pdf_filename}:")
        print(f"  Overall Score: {results['overall_score']:.1f}/100")
        print(f"  Metadata: {metadata_score*100:.1f}%")
        print(f"  Sections: {section_checks['extracted_count']}/{section_checks['expected_count']}")
        print(f"  Figures: {actual_fig_count}/{expected_fig_count}")
        print(f"  Tables: {actual_tbl_count}/{expected_tbl_count}")
    
    return results


def generate_validation_report(pdf_files: List[str], output_path: str, verbose: bool = False):
    """Generate comprehensive validation report."""
    print(f"Validating PaperSlicer extraction against ground truth mappings...")
    print(f"Processing {len(pdf_files)} PDFs...\n")
    
    all_results = []
    summary_stats = {
        'total_pdfs': 0,
        'successful': 0,
        'failed': 0,
        'avg_score': 0.0,
        'scores_by_journal': {},
        'common_issues': []
    }
    
    for pdf_file in pdf_files:
        result = validate_single_pdf(pdf_file, verbose=verbose)
        all_results.append(result)
        
        summary_stats['total_pdfs'] += 1
        if result['status'] == 'success':
            summary_stats['successful'] += 1
        else:
            summary_stats['failed'] += 1
    
    # Calculate average score
    successful_results = [r for r in all_results if r['status'] == 'success']
    if successful_results:
        summary_stats['avg_score'] = sum(r['overall_score'] for r in successful_results) / len(successful_results)
    
    # Identify common issues
    issues = []
    for result in successful_results:
        if result['metadata'].get('title_present') and not result['metadata'].get('title_matches'):
            issues.append('title_mismatch')
        if result['sections'].get('expected_count', 0) > result['sections'].get('extracted_count', 0):
            issues.append('missing_sections')
        if result['figures'].get('count_diff', 0) > 2:
            issues.append('figure_count_diff')
        if result['tables'].get('count_diff', 0) > 1:
            issues.append('table_count_diff')
    
    # Count issue frequency
    from collections import Counter
    issue_counts = Counter(issues)
    summary_stats['common_issues'] = [
        {'issue': issue, 'count': count} 
        for issue, count in issue_counts.most_common(5)
    ]
    
    # Create final report
    report = {
        'generated_at': datetime.now().isoformat(),
        'summary': summary_stats,
        'detailed_results': all_results
    }
    
    # Save report
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"PaperSlicer Extraction Validation Report")
    print(f"{'='*70}")
    print(f"Total PDFs tested: {summary_stats['total_pdfs']}")
    print(f"Successful: {summary_stats['successful']}")
    print(f"Failed: {summary_stats['failed']}")
    print(f"Average Score: {summary_stats['avg_score']:.1f}/100")
    
    if summary_stats['common_issues']:
        print(f"\nMost Common Issues:")
        for issue in summary_stats['common_issues']:
            print(f"  - {issue['issue']}: {issue['count']} occurrences")
    
    print(f"\nDetailed report saved to: {output_path}")
    print(f"{'='*70}\n")
    
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Validate PaperSlicer extraction against ground truth mappings"
    )
    parser.add_argument(
        '--pdf',
        help='Specific PDF to validate (or validate all if not specified)'
    )
    parser.add_argument(
        '--report-path',
        default=str(DEFAULT_REPORT_PATH),
        help='Path to save validation report JSON'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Print verbose output for each PDF'
    )
    parser.add_argument(
        '--priority-only',
        action='store_true',
        help='Only validate priority files (BMC Oral Health articles)'
    )
    
    args = parser.parse_args()
    
    # Determine which PDFs to process
    if args.pdf:
        pdf_files = [args.pdf]
    elif args.priority_only:
        pdf_files = [
            "bmc_oral_health_article1_reso_pac_2025.pdf",
            "bmc_oral_health_article2_bone_density_2025.pdf",
            "bmc_oral_health_article3_cytokine_orthodontics_2025.pdf",
        ]
    else:
        # Get all PDFs that have extraction maps
        extraction_maps = list(EXTRACTION_MAPS_DIR.glob("*_extraction_map.json"))
        pdf_files = [m.name.replace('_extraction_map.json', '.pdf') for m in extraction_maps]
    
    # Generate report
    generate_validation_report(pdf_files, args.report_path, verbose=args.verbose)


if __name__ == "__main__":
    main()

