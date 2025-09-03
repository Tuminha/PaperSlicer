from __future__ import annotations
import os
import hashlib
from typing import List, Dict, Any, Optional


def _safe_stem(path: str) -> str:
    base = os.path.splitext(os.path.basename(path))[0]
    # include a short hash to avoid collisions
    h = hashlib.sha1(path.encode("utf-8")).hexdigest()[:8]
    return f"{base}_{h}"


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def export_embedded_images(pdf_path: str, media_root: Optional[str] = None, max_images: int = 50) -> List[Dict[str, Any]]:
    """
    Extract embedded images from a PDF using PyMuPDF (fitz) and save them as PNGs.
    Returns a list of figure-like dicts {label, caption, path, source}.

    If PyMuPDF is not available, returns an empty list.
    """
    try:
        import fitz  # type: ignore
    except Exception:
        return []

    media_root = media_root or os.path.join("media")
    stem = _safe_stem(pdf_path)
    out_dir = os.path.join(media_root, stem)
    _ensure_dir(out_dir)

    results: List[Dict[str, Any]] = []
    doc = fitz.open(pdf_path)
    count = 0
    for page_index in range(len(doc)):
        page = doc[page_index]
        images = page.get_images(full=True)
        for img_index, img in enumerate(images, start=1):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n > 4:  # CMYK or similar -> convert to RGB
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                out_name = f"page{page_index+1:03d}_img{img_index:02d}.png"
                out_path = os.path.join(out_dir, out_name)
                pix.save(out_path)
                out_abs = os.path.abspath(out_path)
            except Exception:
                continue
            results.append({
                "label": f"Page {page_index+1} Image {img_index}",
                "caption": None,
                "path": out_abs,
                "source": "embedded-image",
            })
            count += 1
            if count >= max_images:
                break
        if count >= max_images:
            break
    doc.close()
    return results


def export_page_previews(pdf_path: str, media_root: Optional[str] = None, dpi: int = 144, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Render page preview PNGs for the first N pages (or all if None).
    Returns a list of figure-like dicts {label, caption, path, source}.
    """
    try:
        import fitz  # type: ignore
    except Exception:
        return []

    media_root = media_root or os.path.join("media")
    stem = _safe_stem(pdf_path)
    out_dir = os.path.join(media_root, stem)
    _ensure_dir(out_dir)

    results: List[Dict[str, Any]] = []
    doc = fitz.open(pdf_path)
    max_p = max_pages or len(doc)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    for page_index in range(min(len(doc), max_p)):
        page = doc[page_index]
        pix = page.get_pixmap(matrix=mat, alpha=False)
        out_name = f"page{page_index+1:03d}.png"
        out_path = os.path.join(out_dir, out_name)
        pix.save(out_path)
        out_path = os.path.abspath(out_path)
        results.append({
            "label": f"Page {page_index+1}",
            "caption": None,
            "path": out_path,
            "source": "page-image",
        })
    doc.close()
    return results


def export_pages_with_keywords(
    pdf_path: str,
    keywords: List[str],
    media_root: Optional[str] = None,
    dpi: int = 144,
    max_pages: int = 6,
) -> List[Dict[str, Any]]:
    """
    Render page previews for pages whose text contains any of the given keywords
    (case-insensitive). Useful as a heuristic fallback to target pages with
    figures/tables when TEI coordinates are unavailable.
    """
    try:
        import fitz  # type: ignore
    except Exception:
        return []

    media_root = media_root or os.path.join("media")
    stem = _safe_stem(pdf_path)
    out_dir = os.path.join(media_root, stem)
    _ensure_dir(out_dir)

    kws = [k.lower() for k in (keywords or [])]
    if not kws:
        return []

    results: List[Dict[str, Any]] = []
    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    for page_index in range(len(doc)):
        try:
            text = doc[page_index].get_text("text") or ""
        except Exception:
            text = ""
        s = text.lower()
        if any(k in s for k in kws):
            page = doc[page_index]
            pix = page.get_pixmap(matrix=mat, alpha=False)
            out_name = f"page{page_index+1:03d}_kw.png"
            out_path = os.path.join(out_dir, out_name)
            try:
                pix.save(out_path)
            except Exception:
                continue
            results.append({
                "label": f"Page {page_index+1}",
                "caption": None,
                "path": os.path.abspath(out_path),
                "source": "page-image",
            })
            if len(results) >= max_pages:
                break
    doc.close()
    return results


def export_crops_by_labels(
    pdf_path: str,
    labels: List[str],
    media_root: Optional[str] = None,
    x_margin: Optional[float] = None,
    y_above: Optional[float] = None,
    y_below: Optional[float] = None,
    max_crops: int = 12,
) -> List[Dict[str, Any]]:
    """
    Heuristic crops around label text like "Figure 1" or "Table 2".
    - Searches page text for each label, crops a rectangle spanning from slightly
      above the match downwards to capture the likely figure/table region.
    - Returns figure-like dicts with saved paths.
    """
    try:
        import fitz  # type: ignore
    except Exception:
        return []

    labels = [l for l in (labels or []) if l]
    if not labels:
        return []

    media_root = media_root or os.path.join("media")
    stem = _safe_stem(pdf_path)
    out_dir = os.path.join(media_root, stem)
    _ensure_dir(out_dir)

    # Build normalized label numbers for matching (e.g., "1", "2")
    label_nums = set()
    for s in labels:
        s0 = (s or "").strip().lower()
        # pull a trailing/leading number token if present
        import re as _re
        m = _re.search(r"\b(\d{1,3})\b", s0)
        if m:
            label_nums.add(m.group(1))

    results: List[Dict[str, Any]] = []
    doc = fitz.open(pdf_path)
    crops = 0
    for page_index in range(len(doc)):
        page = doc[page_index]
        page_rect = page.rect
        # Word-level matching for headers like "Table 1" / "Figure 2"
        try:
            words = page.get_text("words")  # list of (x0,y0,x1,y1,word,block,line,wordno)
        except Exception:
            words = []
        anchors: List[fitz.Rect] = []
        lwr = [(w[0], w[1], w[2], w[3], (w[4] or "").strip().lower()) for w in words]
        n = len(lwr)
        for i in range(n):
            x0, y0, x1, y1, w0 = lwr[i]
            if w0 not in {"table", "figure", "tab.", "fig.", "tab", "fig"}:
                continue
            # look ahead a few tokens for a number that matches any label
            for j in range(i + 1, min(i + 4, n)):
                x0b, y0b, x1b, y1b, w1 = lwr[j]
                if w1.isdigit() and (not label_nums or w1 in label_nums):
                    anchors.append(fitz.Rect(x0, y0, x1b, max(y1, y1b)))
                    break
        # Sort anchors by vertical position
        anchors.sort(key=lambda r: (r.y0, r.x0))
        # Dynamic margins
        xa = x_margin if x_margin is not None else float(os.getenv("PAPERSLICER_LABEL_X_MARGIN", "24"))
        ya = y_above if y_above is not None else float(os.getenv("PAPERSLICER_LABEL_Y_ABOVE", "24"))
        # set below bound up to next anchor to avoid overrun; default span 60% page height
        default_span = 0.6 * page_rect.height
        try:
            yb_fixed = y_below if y_below is not None else float(os.getenv("PAPERSLICER_LABEL_Y_BELOW", "0"))
        except Exception:
            yb_fixed = 0.0
        for idx, a in enumerate(anchors, start=1):
            y0 = max(page_rect.y0, a.y0 - ya)
            # determine y1: next anchor start minus small gap, else default span or page bottom
            if idx < len(anchors):
                y1 = min(page_rect.y1, anchors[idx].y0 - 12)
            else:
                y1 = min(page_rect.y1, y0 + (yb_fixed if yb_fixed > 0 else default_span))
            crop_rect = fitz.Rect(page_rect.x0 + xa, y0, page_rect.x1 - xa, y1)
            if crop_rect.height <= 5 or crop_rect.width <= 5:
                continue
            try:
                pix = page.get_pixmap(clip=crop_rect, alpha=False)
            except Exception:
                continue
            out_name = f"page{page_index+1:03d}_lbl{idx:02d}.png"
            out_path = os.path.join(out_dir, out_name)
            try:
                pix.save(out_path)
            except Exception:
                continue
            results.append({
                "label": None,
                "caption": None,
                "path": os.path.abspath(out_path),
                "source": "grobid+crop",
            })
            crops += 1
            if crops >= max_crops:
                break
        if crops >= max_crops:
            break
    doc.close()
    return results

def export_from_tei_coords(
    pdf_path: str,
    coords_str: str,
    media_root: Optional[str] = None,
    pad_pct: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Crop images from PDF using GROBID TEI coordinates.

    coords_str format observed: "page,x,y,width,height" (points), possibly multiple entries separated by spaces or semicolons.
    Returns a list of figure-like dicts with saved paths.
    """
    try:
        import fitz  # type: ignore
    except Exception:
        return []

    media_root = media_root or os.path.join("media")
    stem = _safe_stem(pdf_path)
    out_dir = os.path.join(media_root, stem)
    _ensure_dir(out_dir)

    def _parse_chunks(s: str) -> List[tuple]:
        chunks: List[tuple] = []
        if not s:
            return chunks
        parts = [p.strip() for p in re.split(r"[;\s]+", s) if p.strip()]
        nums: List[float] = []
        for p in parts:
            try:
                nums.append(float(p))
            except ValueError:
                for q in p.split(','):
                    q = q.strip()
                    if not q:
                        continue
                    try:
                        nums.append(float(q))
                    except ValueError:
                        pass
        for i in range(0, len(nums), 5):
            if i + 4 < len(nums):
                page, x, y, w, h = nums[i:i+5]
                chunks.append((int(page), x, y, w, h))
        return chunks

    import re
    coords = _parse_chunks(coords_str)
    if not coords:
        return []

    doc = fitz.open(pdf_path)
    out: List[Dict[str, Any]] = []
    for idx, (page_no, x, y, w, h) in enumerate(coords, start=1):
        if page_no <= 0 or page_no > len(doc):
            continue
        page = doc[page_no - 1]
        # Accept both xywh (w,h are sizes) and xyxy (w,h are bottom-right coords)
        # Heuristic: prefer xywh if it fits within page bounds; otherwise fall back to xyxy.
        page_rect = page.rect
        rx1, ry1, rx2, ry2 = x, y, x + max(0, w), y + max(0, h)
        rect_wh = fitz.Rect(rx1, ry1, rx2, ry2) & page_rect
        rect_xyxy = fitz.Rect(x, y, w, h) & page_rect
        use_xyxy = False
        if (w > page_rect.width) or (h > page_rect.height):
            use_xyxy = True
        elif (x + w > page_rect.x1 + 1) or (y + h > page_rect.y1 + 1):
            use_xyxy = True
        elif rect_wh.width <= 1 or rect_wh.height <= 1:
            use_xyxy = True
        rect = rect_xyxy if use_xyxy else rect_wh
        # Apply optional padding to include margins around crops
        try:
            pad = pad_pct if pad_pct is not None else float(os.getenv("PAPERSLICER_CROP_PAD_PCT", "0.06"))
        except Exception:
            pad = 0.06
        if pad and rect.width > 1 and rect.height > 1:
            dx = rect.width * pad
            dy = rect.height * pad
            rect = fitz.Rect(rect.x0 - dx, rect.y0 - dy, rect.x1 + dx, rect.y1 + dy) & page.rect
        # DPI control
        try:
            dpi = int(os.getenv("PAPERSLICER_CROP_DPI", "220"))
        except Exception:
            dpi = 220
        zoom = max(1.0, dpi / 72.0)
        mat = fitz.Matrix(zoom, zoom)
        try:
            pix = page.get_pixmap(matrix=mat, clip=rect, alpha=False)
        except Exception:
            continue
        out_name = f"page{page_no:03d}_crop{idx:02d}.png"
        out_path = os.path.join(out_dir, out_name)
        try:
            pix.save(out_path)
        except Exception:
            continue
        out_path = os.path.abspath(out_path)
        out.append({
            "label": None,
            "caption": None,
            "path": out_path,
            "source": "grobid+crop",
        })
    doc.close()
    return out
