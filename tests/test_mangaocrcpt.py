import sys
from types import ModuleType

from PIL import Image

from owocr.ocr import MangaOcrCPTEngine


def make_fake_cpt(monkeypatch):
    fake = ModuleType("manga_ocr_cpt")
    captured = {}

    class FakeMangaOcrCPT:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs

        def __call__(self, image):
            captured["image"] = image
            return "テストの文章"

    fake.MangaOcrCPT = FakeMangaOcrCPT
    monkeypatch.setitem(sys.modules, "manga_ocr_cpt", fake)
    return captured


def test_manga_ocr_cpt_engine_defaults_and_output(monkeypatch):
    captured = make_fake_cpt(monkeypatch)
    engine = MangaOcrCPTEngine()
    assert engine.available is True
    assert "kwargs" not in captured  # model loading is lazy

    ok, result = engine(Image.new("RGB", (80, 120), "white"))
    assert ok is True
    assert result == ["テストの文章"]
    assert captured["kwargs"]["model"] == "muscgab/manga-ocr-base-CPT-flex"
    assert captured["kwargs"]["device"] is None
    assert captured["kwargs"]["backend"] == "auto"
    assert captured["kwargs"]["decoder"] == "fp32"


def test_manga_ocr_cpt_engine_respects_local_model_and_cpu(monkeypatch, tmp_path):
    captured = make_fake_cpt(monkeypatch)
    local_model = tmp_path / "manga-ocr-base-CPT-flex"
    engine = MangaOcrCPTEngine(config={
        "pretrained_model_name_or_path": str(local_model),
        "backend": "plain", "decoder": "fp16", "force_cpu": True,
    })
    ok, result = engine(Image.new("RGB", (80, 120), "white"))
    assert engine.available is True
    assert ok is True
    assert captured["kwargs"]["model"] == str(local_model)
    assert captured["kwargs"]["device"] == "cpu"
    assert captured["kwargs"]["backend"] == "plain"
    assert captured["kwargs"]["decoder"] == "fp16"


def test_manga_ocr_cpt_engine_rejects_invalid_backend(monkeypatch):
    captured = make_fake_cpt(monkeypatch)
    engine = MangaOcrCPTEngine(config={"backend": "unknown"})
    assert engine.available is False
    assert "kwargs" not in captured
