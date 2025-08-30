import os
import json
import csv
import re
from datetime import datetime
from typing import Dict, List, Optional


def _ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def write_images_summary(meta_dir: str = "out/meta", out_dir: str = "out/tests") -> str:
    _ensure_dir(out_dir)
    csv_path = os.path.join(out_dir, f"images_summary_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")
    rows: List[Dict[str, object]] = []
    for name in sorted(os.listdir(meta_dir)):
        if not name.endswith('.json'):
            continue
        path = os.path.join(meta_dir, name)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                d = json.load(f)
        except Exception:
            continue
        figs = d.get('figures') or []
        tabs = d.get('tables') or []
        n_figs = len(figs)
        n_tabs = len(tabs)
        n_crop = sum(1 for x in figs if (x.get('source')=='grobid+crop')) + sum(1 for x in tabs if (x.get('source')=='grobid+crop'))
        n_page = sum(1 for x in figs if (x.get('source') in ('page-image','page-render')))
        rows.append({
            'json': name,
            'title': (d.get('title') or ''),
            'doi': d.get('doi') or '',
            'figures': n_figs,
            'tables': n_tabs,
            'cropped_from_coords': n_crop,
            'page_images_kept': n_page,
        })
    with open(csv_path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=['json','title','doi','figures','tables','cropped_from_coords','page_images_kept'])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return csv_path


def _chunks_by_chars(text: str, chunk_chars: int, overlap: int = 200) -> List[str]:
    text = text.strip()
    if not text:
        return []
    chunks: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        j = min(n, i + chunk_chars)
        chunk = text[i:j]
        chunks.append(chunk)
        if j >= n:
            break
        i = max(j - overlap, i + 1)
    return chunks


def export_rag_jsonl(meta_dir: str = "out/meta", out_path: Optional[str] = None, chunk_chars: int = 4800) -> str:
    rag_dir = os.path.join(os.path.dirname(meta_dir), 'rag') if os.path.dirname(meta_dir) else 'out/rag'
    _ensure_dir(rag_dir)
    out_path = out_path or os.path.join(rag_dir, f"corpus_{datetime.now().strftime('%Y%m%d_%H%M')}.jsonl")

    sec_keys = [
        'introduction',
        'materials_and_methods',
        'results',
        'discussion',
        'conclusions',
        'results_and_discussion',
    ]
    count = 0
    with open(out_path, 'w', encoding='utf-8') as out:
        for name in sorted(os.listdir(meta_dir)):
            if not name.endswith('.json'):
                continue
            path = os.path.join(meta_dir, name)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    d = json.load(f)
            except Exception:
                continue
            meta = {
                'title': d.get('title'),
                'doi': d.get('doi'),
                'journal': d.get('journal'),
                'date': d.get('date'),
            }
            # Canonical sections
            for sec in sec_keys:
                txt = d.get(sec)
                if isinstance(txt, str) and txt.strip():
                    chunks = _chunks_by_chars(txt, chunk_chars)
                    for idx, ch in enumerate(chunks, start=1):
                        rec = {
                            **meta,
                            'section': sec,
                            'original_heading': None,
                            'is_augmented': sec.startswith('results_and_discussion'),
                            'chunk_id': idx,
                            'tokens_estimate': int(len(ch) / 4),
                            'text': ch,
                        }
                        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        count += 1
            # Extra sections (unmapped topical heads)
            extras = d.get('sections_extra') or []
            for ex in extras:
                head = ex.get('head')
                txt = ex.get('text')
                if not isinstance(txt, str) or not txt.strip():
                    continue
                chunks = _chunks_by_chars(txt, chunk_chars)
                for idx, ch in enumerate(chunks, start=1):
                    rec = {
                        **meta,
                        'section': 'extra',
                        'original_heading': head,
                        'is_augmented': False,
                        'chunk_id': idx,
                        'tokens_estimate': int(len(ch) / 4),
                        'text': ch,
                    }
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    count += 1
    return out_path

