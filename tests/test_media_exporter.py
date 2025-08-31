import builtins
import types
from paperslicer.media import exporter as exp


def test_exporters_return_empty_when_pymupdf_missing(monkeypatch, tmp_path):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "fitz":
            raise ImportError("No module named 'fitz'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert exp.export_embedded_images(str(tmp_path / "x.pdf")) == []
    assert exp.export_page_previews(str(tmp_path / "x.pdf")) == []

