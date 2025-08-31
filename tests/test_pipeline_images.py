import sys
import types
from pathlib import Path

from paperslicer.pipeline import Pipeline


def make_fake_fitz(tmp_path: Path):
    mod = types.SimpleNamespace()

    class Pixmap:
        def __init__(self, *a, **k):
            pass

        def save(self, path):
            Path(path).write_bytes(b"PNG")

    class Page:
        def get_pixmap(self, matrix=None, alpha=False, clip=None):
            return Pixmap()

        def get_images(self, full=True):
            return []

    class Doc:
        def __init__(self, path: str):
            self._pages = [Page()]

        def __len__(self):
            return 1

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


def _tei_with_coords() -> bytes:
    return ("""
    <TEI xmlns=\"http://www.tei-c.org/ns/1.0\">
      <teiHeader>
        <fileDesc><titleStmt><title>ImgTitle</title></titleStmt>
          <sourceDesc><biblStruct><monogr><title>J</title></monogr><idno type=\"DOI\">10.10/img</idno></biblStruct></sourceDesc>
        </fileDesc>
        <profileDesc><abstract>A.</abstract></profileDesc>
      </teiHeader>
      <text><body>
        <div><head>Introduction</head><p>x</p></div>
        <figure xml:id=\"f1\"><head>Figure 1.</head><label>1</label><figDesc>desc</figDesc><graphic coords=\"1,10,10,50,40\" type=\"bitmap\" /></figure>
      </body></text>
    </TEI>
    """).encode("utf-8")


def test_pipeline_attaches_cropped_paths_from_coords(tmp_path, monkeypatch):
    # Fake GROBID availability and response
    from paperslicer import grobid as gmod

    class DummyMgr:
        def is_available(self, timeout_s: float = 1.0) -> bool:
            return True

    class DummyCli:
        def process_fulltext(self, pdf_path: str, save_dir=None, **kwargs):
            tei = _tei_with_coords()
            out = Path(save_dir or tmp_path) / "x.tei.xml"
            out.write_bytes(tei)
            return tei, str(out)

    monkeypatch.setattr(gmod.manager, "GrobidManager", lambda *a, **k: DummyMgr())
    monkeypatch.setattr(gmod.client, "GrobidClient", lambda *a, **k: DummyCli())

    # Fake fitz to avoid real dependency
    sys.modules['fitz'] = make_fake_fitz(tmp_path)

    pipe = Pipeline(try_start_grobid=False, xml_save_dir=str(tmp_path), export_images=True, images_mode="auto")
    rec = pipe.process(str(tmp_path / "dummy.pdf"))
    # Expect at least one figure with source 'grobid+crop' and a valid path
    crops = [f for f in rec.figures if f.get("source") == "grobid+crop" and f.get("path")]
    assert crops, "No cropped images attached to figures"
    for c in crops:
        assert Path(c["path"]).exists(), f"Missing crop path: {c['path']}"

