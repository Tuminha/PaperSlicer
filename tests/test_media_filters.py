import os
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from paperslicer.models import Meta, PaperRecord
from paperslicer.media import filters
from paperslicer.media.filters import filter_media_collections


def _make_record(figures=None, tables=None):
    return PaperRecord(
        meta=Meta(source_path="dummy.pdf"),
        sections={},
        other_sections={},
        figures=figures or [],
        tables=tables or [],
    )


def _create_img(path: Path, width=256, height=256, fill="white"):
    img = Image.new("RGB", (width, height), fill)
    img.save(path)
    return path


def test_filter_removes_blank_figure(tmp_path: Path):
    blank_path = _create_img(tmp_path / "blank.png")
    rec = _make_record(figures=[{"path": str(blank_path), "source": "embedded-image"}])
    filter_media_collections(rec, str(tmp_path / "missing.pdf"))
    assert rec.figures == []


def test_filter_keeps_informative_figure(tmp_path: Path):
    fig_path = tmp_path / "figure.png"
    img = Image.new("RGB", (256, 256), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((40, 40, 200, 200), fill="black")
    img.save(fig_path)
    rec = _make_record(figures=[{"path": str(fig_path), "source": "embedded-image"}])
    filter_media_collections(rec, str(tmp_path / "missing.pdf"))
    assert len(rec.figures) == 1


def test_filter_drops_invalid_detector_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    class DummyValidator:
        def __init__(self, *_):
            pass

        def is_valid(self, *_):
            return False

        def close(self):
            pass

    monkeypatch.setattr(filters, "TableRegionValidator", DummyValidator)
    tbl_path = _create_img(tmp_path / "table.png", 400, 300)
    rec = _make_record(
        tables=[
            {
                "path": str(tbl_path),
                "source": "detector-table",
                "pdf_bbox": {"page_index": 0, "bbox": [0.0, 0.0, 10.0, 10.0]},
            }
        ]
    )
    filter_media_collections(rec, str(tmp_path / "dummy.pdf"))
    assert rec.tables == []


def test_filter_keeps_valid_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    class DummyValidator:
        def __init__(self, *_):
            pass

        def is_valid(self, *_):
            return True

        def close(self):
            pass

    monkeypatch.setattr(filters, "TableRegionValidator", DummyValidator)
    tbl_path = tmp_path / "table_valid.png"
    img = Image.new("RGB", (400, 300), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((10, 10, 390, 290), outline="black", width=3)
    img.save(tbl_path)
    rec = _make_record(
        tables=[
            {
                "path": str(tbl_path),
                "source": "tei+tei-render",
                "pdf_bbox": {"page_index": 0, "bbox": [0.0, 0.0, 10.0, 10.0]},
            }
        ]
    )
    filter_media_collections(rec, str(tmp_path / "dummy.pdf"))
    assert len(rec.tables) == 1


def test_filters_prefer_crops_over_img(tmp_path: Path):
    crop_path = tmp_path / "page001_crop01.png"
    img_path = tmp_path / "page001_img01.png"
    for path in (crop_path, img_path):
        img = Image.new("RGB", (256, 256), "white")
        draw = ImageDraw.Draw(img)
        draw.rectangle((30, 30, 220, 180), fill="black")
        img.save(path)
    rec = _make_record(figures=[
        {"path": str(img_path), "source": "page-image"},
        {"path": str(crop_path), "source": "page-image"},
    ])
    filter_media_collections(rec, str(tmp_path / "missing.pdf"))
    assert len(rec.figures) == 1
    assert rec.figures[0]["path"].endswith("crop01.png")
