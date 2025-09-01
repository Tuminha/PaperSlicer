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


def export_from_tei_coords(pdf_path: str, coords_str: str, media_root: Optional[str] = None) -> List[Dict[str, Any]]:
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
        # Split by semicolon or whitespace groups
        parts = [p.strip() for p in re.split(r"[;\s]+", s) if p.strip()]
        # Recombine into groups of 5 numbers
        nums: List[float] = []
        for p in parts:
            try:
                nums.append(float(p))
            except ValueError:
                # handle comma-separated as one token
                for q in p.split(','):
                    q = q.strip()
                    if not q:
                        continue
                    try:
                        nums.append(float(q))
                    except ValueError:
                        pass
        # Group into quintuples
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
        rect = fitz.Rect(x, y, x + max(0, w), y + max(0, h))
        try:
            pix = page.get_pixmap(clip=rect, alpha=False)
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
