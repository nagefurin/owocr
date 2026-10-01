import sys
from types import ModuleType
from PIL import Image

from owocr.ocr import HayaiOCREngine


def make_fake_hayai(monkeypatch):
    fake = ModuleType('hayai_ocr')

    class FakeHayaiOcr:
        last_kwargs = None

        def __init__(self, **kwargs):
            FakeHayaiOcr.last_kwargs = kwargs
            self.kwargs = kwargs

        def __call__(self, image):
            return '上の行\\n\\n下の行'

    fake.HayaiOcr = FakeHayaiOcr
    monkeypatch.setitem(sys.modules, 'hayai_ocr', fake)
    return FakeHayaiOcr


def test_hayai_engine_multiline(monkeypatch):
    FakeHayaiOcr = make_fake_hayai(monkeypatch)

    engine = HayaiOCREngine(config={'backend': 'torch', 'compile': False, 'force_cpu': True})
    ok, result = engine(Image.new('RGB', (64, 64), 'white'))

    assert ok is True
    assert result == ['上の行', '\\n', '下の行']
    assert FakeHayaiOcr.last_kwargs['pretrained_model_name_or_path'] == 'JustANormalTinkerer/hayai-ocr-v2.5-nova'
    assert 'use_v2' not in FakeHayaiOcr.last_kwargs
    assert FakeHayaiOcr.last_kwargs['force_cpu'] is True


def test_hayai_engine_uses_v2_path(monkeypatch):
    FakeHayaiOcr = make_fake_hayai(monkeypatch)

    HayaiOCREngine(config={'use_v2': True, 'hayaiv2_path': 'local/v2', 'compile': False})

    assert FakeHayaiOcr.last_kwargs['pretrained_model_name_or_path'] == 'local/v2'
    assert FakeHayaiOcr.last_kwargs['use_v2'] is True


def test_hayai_engine_uses_v1_path(monkeypatch):
    FakeHayaiOcr = make_fake_hayai(monkeypatch)

    HayaiOCREngine(config={'use_v1': True, 'hayaiv1_path': 'local/v1', 'compile': False})

    assert FakeHayaiOcr.last_kwargs['pretrained_model_name_or_path'] == 'local/v1'
    assert FakeHayaiOcr.last_kwargs['use_v1'] is True


def test_hayai_engine_rejects_both_legacy_model_switches(monkeypatch):
    FakeHayaiOcr = make_fake_hayai(monkeypatch)

    engine = HayaiOCREngine(config={'use_v1': True, 'use_v2': True})
    assert engine.available is False
    assert FakeHayaiOcr.last_kwargs is None


def test_hayai_engine_rejects_unknown_backend(monkeypatch):
    FakeHayaiOcr = make_fake_hayai(monkeypatch)

    engine = HayaiOCREngine(config={'backend': 'unknown'})
    assert engine.available is False
    assert FakeHayaiOcr.last_kwargs is None
