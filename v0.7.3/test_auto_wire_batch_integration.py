"""Batch integration: fake AI segmentation, real automatic cleanup and real PNG save.

Does not run ONNX, CUDA, Windows EXE or real product photographs.
"""
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw
import test_mocked_batch_runtime  # installs stub Qt and ONNX, exercises existing batch
import background_remover_pro as core
import rembg

segmented = Image.new('RGBA', (640, 400), (0, 0, 0, 0))
d = ImageDraw.Draw(segmented)
d.rectangle((125, 145, 510, 315), fill=(75, 80, 85, 255))
d.rectangle((155, 165, 335, 190), fill=(210, 210, 210, 255))
d.line((35, 95, 250, 95, 330, 145), fill=(0, 0, 0, 255), width=3)
rembg.remove = lambda image, **kw: segmented.copy()

with tempfile.TemporaryDirectory() as temp:
    base = Path(temp)
    original = base / 'original.png'
    Image.new('RGB', (640, 400), (200, 200, 200)).save(original)
    worker = core.BatchWorker([str(original)], base / 'auto', 640, 400)
    worker.auto_wire_cleanup = True
    worker.run()
    assert len(worker.completed.events) == 1, worker.failed.events
    with Image.open(worker.completed.events[0][1]) as result:
        assert result.getpixel((100, 95))[:3] == (255, 255, 255), 'Wire remains in output'
        assert result.getpixel((250, 170))[:3] == (210, 210, 210), 'Product label changed'
    assert any('Loose-wire cleanup:' in event[0] for event in worker.status.events)

    worker_off = core.BatchWorker([str(original)], base / 'manual', 640, 400)
    worker_off.auto_wire_cleanup = False
    worker_off.run()
    assert len(worker_off.completed.events) == 1, worker_off.failed.events
    with Image.open(worker_off.completed.events[0][1]) as result:
        assert result.getpixel((100, 95))[:3] == (0, 0, 0), 'Disabling cleanup did not work'
    assert original.exists(), 'Source file was modified'
print('PASS fake AI -> auto wire cleanup -> PNG export, disabled mode, original preservation')
