#!/usr/bin/env bash
set -euo pipefail

# End-to-end runner for three sample PDFs using the PaperSlicer CLI.
# - Uses --e2e (TEI + abstract resolution + image export)
# - Saves JSONs in out/meta and a compact summary in out/tests
#
# Usage:
#   scripts/e2e_three.sh [--mailto you@example.com]

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
PY=python3

MAILTO_ARG=()
if [[ "${1:-}" == "--mailto" && -n "${2:-}" ]]; then
  MAILTO_ARG=(--mailto "$2"); shift 2
elif [[ "${1:-}" == *"@"* ]]; then
  MAILTO_ARG=(--mailto "$1"); shift 1
fi

PDF1="$ROOT/data/pdf/open_dentistry_journal_article1_consort_orthodontics_2024.pdf"
PDF2="$ROOT/data/pdf/open_dentistry_journal_article2_hypericum_nanoemulsion_2024.pdf"
PDF3="$ROOT/data/pdf/open_dentistry_journal_article3_root_canal_prevalence_2024.pdf"

OUT_DIR="$ROOT/out/meta"
XML_DIR="$ROOT/data/xml"
REPORTS_DIR="$ROOT/out/tests"
mkdir -p "$OUT_DIR" "$XML_DIR" "$REPORTS_DIR"

# Try to ensure GROBID is up (best-effort)
GURL="${GROBID_URL:-http://localhost:8070}"
if ! curl -sfS "$GURL/api/isalive" >/dev/null 2>&1; then
  if [[ -x "$ROOT/scripts/start_grobid.sh" && -n "${GROBID_HOME:-}" ]]; then
    echo "[e2e] GROBID not responding; trying start_grobid.sh with GROBID_HOME=$GROBID_HOME" >&2
    "$ROOT/scripts/start_grobid.sh" "$GROBID_HOME" || true
    sleep 2
  else
    echo "[e2e] GROBID not responding at $GURL; continuing anyway (pipeline may attempt fallback/auto-start)." >&2
  fi
fi

echo "[e2e] Processing three PDFs with --e2e..."
"$PY" "$ROOT/project.py" "$PDF1" --e2e --tei-out "$XML_DIR" --out "$OUT_DIR" "${MAILTO_ARG[@]}"
"$PY" "$ROOT/project.py" "$PDF2" --e2e --tei-out "$XML_DIR" --out "$OUT_DIR" "${MAILTO_ARG[@]}"
"$PY" "$ROOT/project.py" "$PDF3" --e2e --tei-out "$XML_DIR" --out "$OUT_DIR" "${MAILTO_ARG[@]}"

JSON1="$OUT_DIR/$(basename "${PDF1%.pdf}").json"
JSON2="$OUT_DIR/$(basename "${PDF2%.pdf}").json"
JSON3="$OUT_DIR/$(basename "${PDF3%.pdf}").json"

SUMMARY_TXT="$REPORTS_DIR/e2e_three_summary.txt"
SUMMARY_JSON="$REPORTS_DIR/e2e_three_summary.json"

echo "[e2e] Building summary: $SUMMARY_TXT"
SUMMARY_JSON="$SUMMARY_JSON" "$PY" - "$JSON1" "$JSON2" "$JSON3" >"$SUMMARY_TXT" << 'PY'
import json, sys, os
out = {}
for p in sys.argv[1:]:
    if not os.path.exists(p):
        print(p)
        print("  ERROR: file not found")
        continue
    d = json.load(open(p, 'r', encoding='utf-8'))
    meta = d.get('meta') or {}
    secs = d.get('sections') or {}
    figs = d.get('figures') or []
    tabs = d.get('tables') or []
    abs_text = (secs.get('abstract') or '')
    row = {
        'title': meta.get('title'),
        'doi': meta.get('doi'),
        'journal': meta.get('journal'),
        'abstract_len': len(abs_text),
        'abstract_present': bool(abs_text),
        'sections_count': len(secs),
        'section_keys_sample': list(secs.keys())[:8],
        'figures_count': len(figs),
        'tables_count': len(tabs),
    }
    out[p] = row
    print(p)
    for k in ['title','doi','journal','abstract_len','abstract_present','sections_count','figures_count','tables_count']:
        print(f"  {k}: {row.get(k)}")
open(os.environ.get('SUMMARY_JSON','/dev/null'), 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=2))
PY
echo "[e2e] Done. Inspect $SUMMARY_TXT and JSONs under $OUT_DIR"
