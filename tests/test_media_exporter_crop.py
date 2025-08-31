import sys
import types
from pathlib import Path

from paperslicer.media import exporter as exp


def make_fake_fitz(tmp_path: Path):
    mod = types.SimpleNamespace()

    class Pixmap:
        def __init__(self, *a, **k):
            pass

        def save(self, path):
            Path(path).write_bytes(b"PNG")

    class Page:
        def __init__(self, idx: int):
            self.idx = idx

        def get_pixmap(self, matrix=None, alpha=False, clip=None):
            return Pixmap()

        def get_images(self, full=True):
            return []

    class Doc:
        def __init__(self, path: str):
            self._pages = [Page(0), Page(1), Page(2)]

        def __len__(self):
            return len(self._pages)

        def __getitem__(self, i):
            return self._pages[i]

        def close(self):
            pass

    def open_func(path):
        return Doc(path)

    class Rect:
        def __init__(self, x0, y0, x1, y1):
            self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1

    class Matrix:
        def __init__(self, a, b):
            pass

    mod.Pixmap = Pixmap
    mod.Rect = Rect
    mod.Matrix = Matrix
    mod.open = open_func
    return mod


def test_export_from_tei_coords_crops_and_writes(tmp_path, monkeypatch):
    fake = make_fake_fitz(tmp_path)
    sys.modules['fitz'] = fake  # inject fake PyMuPDF

    pdf_path = str(tmp_path / "fake.pdf")
    # coords format: page,x,y,w,h (5 values). Ensure at least one chunk on page 1
    coords = "1,10,10,50,40"
    out = exp.export_from_tei_coords(pdf_path, coords, media_root=str(tmp_path / "media"))
    assert isinstance(out, list) and len(out) >= 1
    assert out[0]["source"] == "grobid+crop"
    p = out[0]["path"]
    assert p and Path(p).exists(), "Cropped image file should exist"


def test_export_page_previews_writes_pngs(tmp_path, monkeypatch):
    fake = make_fake_fitz(tmp_path)
    sys.modules['fitz'] = fake

    pdf_path = str(tmp_path / "fake.pdf")
    out = exp.export_page_previews(pdf_path, media_root=str(tmp_path / "media"), dpi=72, max_pages=2)
    assert len(out) == 2
    paths = [o["path"] for o in out]
    for p in paths:
        assert Path(p).exists(), f"Preview file missing: {p}"

