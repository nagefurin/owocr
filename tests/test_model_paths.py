import sys
from types import SimpleNamespace, ModuleType

from owocr import ocr


def test_manga_segmented_uses_configured_comic_text_detector_path(monkeypatch, tmp_path):
    model_file = tmp_path / "comictextdetector.pt"
    model_file.write_bytes(b"model")

    fake_torch = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: False),
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: False)),
    )
    captured = {}

    class FakeTextDetector:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(ocr.MangaOcrSegmented, "_import_dependencies", lambda self: True)
    monkeypatch.setattr(ocr, "torch", fake_torch, raising=False)
    monkeypatch.setattr(ocr, "TextDetector", FakeTextDetector, raising=False)
    monkeypatch.setattr(ocr, "initialize_manga_ocr", lambda *args: None)

    engine = ocr.MangaOcrSegmented(config={"comictextdetector_path": str(model_file)})
    assert engine.available is True
    assert captured["model_path"] == model_file


def test_screenai_uses_configured_resource_path(monkeypatch, tmp_path):
    monkeypatch.setattr(ocr.ChromeScreenAI, "_import_dependencies", lambda self: True)
    monkeypatch.setattr(ocr.ChromeScreenAI, "_download_files_if_needed", lambda self: False)

    engine = ocr.ChromeScreenAI(config={"screenai_path": str(tmp_path / "screen_ai" / "resources")})
    assert engine.model_dir == tmp_path / "screen_ai" / "resources"


def test_oneocr_uses_configured_model_path(monkeypatch, tmp_path):
    target = tmp_path / "oneocr"
    target.mkdir()
    for name in ("oneocr.dll", "oneocr.onemodel", "onnxruntime.dll"):
        (target / name).write_bytes(b"model")

    fake = ModuleType("oneocr")
    captured = {}

    class FakeOcrEngine:
        def __init__(self):
            captured["config_dir"] = fake.CONFIG_DIR

    fake.OcrEngine = FakeOcrEngine
    fake.CONFIG_DIR = "unused"
    monkeypatch.setitem(sys.modules, "oneocr", fake)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ocr.platform, "release", lambda: "11")

    engine = ocr.OneOCR(config={"oneocr_path": str(target)})
    assert engine.available is True
    assert captured["config_dir"] == str(target)


def test_meikiocr_uses_configured_huggingface_cache(monkeypatch, tmp_path):
    captured = {}

    def fake_import(self, model_path=None):
        captured["model_path"] = model_path
        return False

    monkeypatch.setattr(ocr.MeikiOCR, "_import_dependencies", fake_import)

    engine = ocr.MeikiOCR(config={"meikiocr_path": str(tmp_path / "hf-cache")})
    assert engine.available is False
    assert captured["model_path"] == str(tmp_path / "hf-cache")
