"""Static resource regression contracts; not Windows/GPU inference validation."""
from pathlib import Path
ui = Path(__file__).with_name('aurenix_pro.py').read_text()
core = Path(__file__).with_name('background_remover_pro.py').read_text()
assert 'from rembg import remove, new_session\n' in core
assert not any(x.startswith('from rembg import') for x in core.split('class BatchWorker')[0].splitlines())
assert 'class GpuMonitor(QThread)' in ui
assert 'QTimer.singleShot(2500, self.update_monitors)' in ui
assert 'import onnxruntime as ort' not in ui
assert 'self.model_name = os.environ.get("AURENIX_MODEL", "u2net")' in core
assert 'self.width * self.height > 16_000_000' in core
assert 'source_image.width * source_image.height > 8_000_000' in core
print('PASS lazy startup, background GPU monitor, safe default model, image memory guards')
