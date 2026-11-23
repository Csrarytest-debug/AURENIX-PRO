"""Fine-edge mode regression: opt-in wire-safe configuration and bounded RAM.

Uses real PIL image I/O and fake inference; it does not prove alpha-matting
fidelity on real photos, CUDA inference or bounded VRAM on a target RTX 4050.
"""
import tempfile
from pathlib import Path
from types import SimpleNamespace
from PIL import Image

import test_mocked_batch_runtime  # stubs Qt and rembg; verifies standard batch
import background_remover_pro as core
import rembg
import psutil

root = Path(__file__).parent
ui = (root / "aurenix_pro.py").read_text(encoding="utf-8")
adapter = (root / "isolated_worker.py").read_text(encoding="utf-8")
child = (root / "inference_worker.py").read_text(encoding="utf-8")
assert "self.fine_edge_checkbox.setChecked(False)" in ui
assert "self.current_fine_edge_matting = self.fine_edge_checkbox.isChecked()" in ui
assert "self.worker.fine_edge_matting" in (root / "background_remover_pro.py").read_text(encoding="utf-8")
assert "'fine_edge_matting': self.fine_edge_matting" in adapter
assert "'fine_edge_matting', 'wire_policy_overrides')" in child

original_memory = psutil.virtual_memory
psutil.virtual_memory = lambda: SimpleNamespace(
    percent=12.0, available=10 * 1024**3, total=16 * 1024**3
)
calls = []
def fake_remove(image, **kwargs):
    calls.append(kwargs.copy())
    return image.convert("RGBA")
rembg.remove = fake_remove
try:
    with tempfile.TemporaryDirectory(prefix="aurenix_edge_") as temp:
        folder = Path(temp)
        source = folder / "source.png"
        Image.new("RGB", (48, 32), (150, 30, 40)).save(source)
        before = source.read_bytes()
        normal = core.BatchWorker([str(source)], folder / "crisp", 80, 60)
        normal.auto_wire_cleanup = False
        normal.run()
        assert len(normal.completed.events) == 1, normal.failed.events
        assert calls[-1].get("alpha_matting") is None, "Default should remain crisp"
        fine = core.BatchWorker([str(source)], folder / "fine", 80, 60)
        fine.auto_wire_cleanup = False
        fine.fine_edge_matting = True
        fine.run()
        assert len(fine.completed.events) == 1, fine.failed.events
        assert calls[-1]["alpha_matting"] is True
        assert calls[-1]["alpha_matting_foreground_threshold"] == 240
        assert calls[-1]["alpha_matting_background_threshold"] == 10
        assert calls[-1]["alpha_matting_erode_size"] == 5
        with Image.open(fine.completed.events[0][1]) as out:
            assert out.format == "PNG" and out.size == (80, 60)
        assert source.read_bytes() == before

        # Size guard: don't begin alpha-matting large source frames.
        large = folder / "large.png"
        Image.new("RGB", (1500, 1500), (70, 60, 50)).save(large)
        unsafe = core.BatchWorker([str(large)], folder / "guard", 80, 60)
        unsafe.fine_edge_matting = True
        unsafe.auto_wire_cleanup = False
        unsafe.run()
        assert len(unsafe.completed.events) == 0
        assert len(unsafe.failed.events) == 1
        assert "2 megapixels" in unsafe.failed.events[0][1]
        assert large.is_file()
        print("PASS opt-in alpha-matting config, crisp default, PNG and "
              "original preservation, 2MP safety guard")
finally:
    psutil.virtual_memory = original_memory
