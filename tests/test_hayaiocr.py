import sys
from types import ModuleType
from PIL import Image

from owocr.ocr import HayaiOCREngine

def test_hayai_engine_multiline(monkeypatch):
    fake = ModuleType('hayai_ocr')

    class FakeHayaiOcr:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __call__(self, image):
            return '上の行\n\n下の行'

    fake.HayaiOcr = FakeHayaiOcr
    monkeypatch.setitem(sys.modules, 'hayai_ocr', fake)

    engine = HayaiOCREngine(config={'backend': 'torch', 'compile': False, 'force_cpu': True})
    ok, result = engine(Image.new('RGB', (64, 64), 'white'))
    assert ok is True
    assert result == ['上の行', '\n', '下の行']

def test_hayai_engine_rejects_unknown_backend(monkeypatch):
    fake = ModuleType('hayai_ocr')

    class FakeHayaiOcr:
        def __init__(self, **kwargs):
            raise AssertionError('model should not initialize')

    fake.HayaiOcr = FakeHayaiOcr
    monkeypatch.setitem(sys.modules, 'hayai_ocr', fake)

    engine = HayaiOCREngine(config={'backend': 'unknown'})
    assert engine.available is False
