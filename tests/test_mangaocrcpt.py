import sys
from types import ModuleType

from PIL import Image

from owocr.ocr import MangaOcrCPTEngine


REQUIRED_MODEL_FILES = ("model.safetensors", "config.json", "nar_vocabulary_6817.json")


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


def install_fake_hub(monkeypatch):
    fake = ModuleType("huggingface_hub")
    captured = {}

    def snapshot_download(**kwargs):
        captured.update(kwargs)
        target = __import__("pathlib").Path(kwargs["local_dir"])
        target.mkdir(parents=True, exist_ok=True)
        for filename in REQUIRED_MODEL_FILES:
            (target / filename).write_bytes(b"test")
        return str(target)

    fake.snapshot_download = snapshot_download
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake)
    return captured


def test_manga_ocr_cpt_engine_defaults_to_portable_model_folder(monkeypatch, tmp_path):
    captured = make_fake_cpt(monkeypatch)
    hub = install_fake_hub(monkeypatch)
    monkeypatch.setattr(MangaOcrCPTEngine, "_portable_root", lambda self: tmp_path)

    engine = MangaOcrCPTEngine()
    assert engine.available is True
    assert engine.portable_model is True

    ok, result = engine(Image.new("RGB", (80, 120), "white"))

    expected_dir = tmp_path / "models" / "manga-ocr-base-CPT-flex"
    assert ok is True
    assert result == ["テストの文章"]
    assert hub["repo_id"] == "muscgab/manga-ocr-base-CPT-flex"
    assert hub["local_dir"] == str(expected_dir.resolve())
    assert set(hub["allow_patterns"]) == set(REQUIRED_MODEL_FILES)
    assert captured["kwargs"]["model"] == str(expected_dir.resolve())
    assert (expected_dir / ".owocr-model-id").read_text(encoding="utf-8") == "muscgab/manga-ocr-base-CPT-flex"


def test_manga_ocr_cpt_engine_uses_existing_local_model(monkeypatch, tmp_path):
    captured = make_fake_cpt(monkeypatch)
    local_model = tmp_path / "local-cpt-model"
    local_model.mkdir()
    for filename in REQUIRED_MODEL_FILES:
        (local_model / filename).write_bytes(b"test")

    engine = MangaOcrCPTEngine(config={
        "pretrained_model_name_or_path": str(local_model),
        "backend": "plain", "decoder": "fp16", "force_cpu": True,
    })
    ok, result = engine(Image.new("RGB", (80, 120), "white"))

    assert engine.available is True
    assert ok is True
    assert captured["kwargs"]["model"] == str(local_model.resolve())
    assert captured["kwargs"]["device"] == "cpu"
    assert captured["kwargs"]["backend"] == "plain"
    assert captured["kwargs"]["decoder"] == "fp16"


def test_manga_ocr_cpt_engine_can_use_standard_huggingface_cache(monkeypatch):
    captured = make_fake_cpt(monkeypatch)
    engine = MangaOcrCPTEngine(config={"portable_model": False})

    assert engine._resolve_model_path() == "muscgab/manga-ocr-base-CPT-flex"
    assert engine.portable_model is False


def test_manga_ocr_cpt_engine_rejects_invalid_backend(monkeypatch):
    make_fake_cpt(monkeypatch)
    engine = MangaOcrCPTEngine(config={"backend": "unknown"})
    assert engine.available is False
