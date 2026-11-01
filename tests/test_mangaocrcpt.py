import sys
from types import ModuleType

from PIL import Image

from owocr.ocr import MangaOcrCPTEngine


def install_fake_cpt(monkeypatch):
    module = ModuleType("manga_ocr_cpt")
    captured = {}

    class FakeMangaOcrCPT:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs
            captured["initialized"] = True

        def __call__(self, image):
            captured["image"] = image
            return "テストの文章"

    module.MangaOcrCPT = FakeMangaOcrCPT
    monkeypatch.setitem(sys.modules, "manga_ocr_cpt", module)
    return captured


def test_manga_ocr_cpt_engine_loads_configured_local_model_lazily(monkeypatch, tmp_path):
    captured = install_fake_cpt(monkeypatch)
    model_dir = tmp_path / "mangaocrcpt"
    model_dir.mkdir()

    engine = MangaOcrCPTEngine(config={
        "pretrained_model_name_or_path": str(model_dir),
        "backend": "plain",
        "decoder": "fp16",
        "force_cpu": True,
    })

    assert engine.available is True
    assert "initialized" not in captured

    ok, result = engine(Image.new("RGB", (80, 120), "white"))

    assert ok is True
    assert result == ["テストの文章"]
    assert captured["kwargs"]["model"] == str(model_dir)
    assert captured["kwargs"]["device"] == "cpu"
    assert captured["kwargs"]["backend"] == "plain"
    assert captured["kwargs"]["decoder"] == "fp16"


def test_manga_ocr_cpt_engine_defaults_to_hugging_face_model(monkeypatch):
    captured = install_fake_cpt(monkeypatch)
    engine = MangaOcrCPTEngine()

    assert engine.available is True
    assert engine.model_path == "muscgab/manga-ocr-base-CPT-flex"
    assert "initialized" not in captured


def test_manga_ocr_cpt_engine_rejects_invalid_backend(monkeypatch):
    install_fake_cpt(monkeypatch)
    engine = MangaOcrCPTEngine(config={"backend": "unknown"})

    assert engine.available is False


def test_manga_ocr_cpt_engine_rejects_invalid_decoder(monkeypatch):
    install_fake_cpt(monkeypatch)
    engine = MangaOcrCPTEngine(config={"decoder": "unknown"})

    assert engine.available is False
