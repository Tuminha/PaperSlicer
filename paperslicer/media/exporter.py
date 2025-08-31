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
            except Exception:
                continue
            results.append({
                "label": f"Page {page_index+1} Image {img_index}",
                "caption": None,
                "path": out_path,
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
        results.append({
            "label": f"Page {page_index+1}",
            "caption": None,
            "path": out_path,
            "source": "page-image",
        })
    doc.close()
    return results

