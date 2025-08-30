import os
import hashlib
from typing import List, Dict

import fitz  # PyMuPDF


def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]


def _ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


class ImageExporter:
    """Exports figure/table bitmaps using TEI coords if available; falls back to page images."""

    def __init__(self, media_root: str = "media") -> None:
        self.media_root = media_root
        _ensure_dir(media_root)

    def _bucket_dir(self, pdf_path: str) -> str:
        stem = os.path.splitext(os.path.basename(pdf_path))[0]
        bucket = f"{stem}_{_hash(pdf_path)}"
        outdir = os.path.join(self.media_root, bucket)
        _ensure_dir(outdir)
        return outdir

    def export_with_coords(self, pdf_path: str, items: List[Dict], outdir: str | None = None) -> List[Dict]:
        doc = fitz.open(pdf_path)
        outdir = outdir or self._bucket_dir(pdf_path)
        _ensure_dir(outdir)
        exported: List[Dict] = []
        fig_i = 0
        tab_i = 0
        for it in items:
            if not it.get("bbox"):
                continue
            page_no = int(it.get("page") or 1)
            bbox = it.get("bbox")
            page = doc[page_no - 1]
            rect = fitz.Rect(*bbox)
            pix = page.get_pixmap(clip=rect, dpi=300)
            if it.get("type") == "table":
                tab_i += 1
                img_name = f"table_{tab_i:02d}.png"
            else:
                fig_i += 1
                img_name = f"fig_{fig_i:02d}.png"
            img_path = os.path.join(outdir, img_name)
            pix.save(img_path)
            sha1 = hashlib.sha1(open(img_path, "rb").read()).hexdigest()[:8]
            exported.append({
                **it,
                "image_path": os.path.relpath(img_path),
                "sha1": sha1,
                "width_px": pix.width,
                "height_px": pix.height,
                "source": "grobid+crop",
            })
        doc.close()
        return exported

    def export_page_images(
        self,
        pdf_path: str,
        outdir: str | None = None,
        *,
        min_width_px: int | None = None,
        min_height_px: int | None = None,
        min_area_px: int | None = None,
        skip_full_page: bool = False,
    ) -> List[Dict]:
        doc = fitz.open(pdf_path)
        outdir = outdir or self._bucket_dir(pdf_path)
        _ensure_dir(outdir)
        out: List[Dict] = []
        for pno in range(len(doc)):
            page = doc[pno]
            imgs = page.get_images(full=True)
            if imgs:
                for j, info in enumerate(imgs, start=1):
                    xref = info[0]
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n > 4:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    w, h = pix.width, pix.height
                    area = w * h
                    if (
                        (min_width_px and w < min_width_px)
                        or (min_height_px and h < min_height_px)
                        or (min_area_px and area < min_area_px)
                    ):
                        continue
                    img_name = f"page{pno+1:03d}_img{j:02d}.png"
                    img_path = os.path.join(outdir, img_name)
                    pix.save(img_path)
                    sha1 = hashlib.sha1(open(img_path, "rb").read()).hexdigest()[:8]
                    out.append({
                        "type": "page-image",
                        "label": None,
                        "caption": None,
                        "page": pno + 1,
                        "bbox": None,
                        "image_path": os.path.relpath(img_path),
                        "sha1": sha1,
                        "width_px": w,
                        "height_px": h,
                        "source": "page-image",
                    })
                    pix = None
            else:
                # Fallback: render whole page if no embedded images found
                if skip_full_page:
                    continue
                pix = page.get_pixmap(dpi=200)
                img_name = f"page{pno+1:03d}_full.png"
                img_path = os.path.join(outdir, img_name)
                pix.save(img_path)
                sha1 = hashlib.sha1(open(img_path, "rb").read()).hexdigest()[:8]
                out.append({
                    "type": "page-image",
                    "label": None,
                    "caption": None,
                    "page": pno + 1,
                    "bbox": None,
                    "image_path": os.path.relpath(img_path),
                    "sha1": sha1,
                    "width_px": pix.width,
                    "height_px": pix.height,
                    "source": "page-render",
                })
        doc.close()
        return out
