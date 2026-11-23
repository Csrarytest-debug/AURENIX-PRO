"""Static resource regression contracts; not Windows/GPU inference validation."""
from pathlib import Path
ui = Path(__file__).with_name('aurenix_pro.py').read_text(encoding='utf-8')
core = Path(__file__).with_name('background_remover_pro.py').read_text()
assert 'from rembg import remove, new_session\n' in core
assert not any(x.startswith('from rembg import') for x in core.split('class BatchWorker')[0].splitlines())
assert 'class GpuMonitor(QThread)' in ui
# Regression: GPU/nvidia-smi monitoring must never start during GUI initialization.
assert 'QTimer.singleShot(2500, self.update_monitors)' not in ui
assert 'QTimer.singleShot(4000, self.update_ram_monitor)' in ui
assert "GPU idle" in ui and "monitoring starts with processing" in ui
initialization = ui.split('    def _gpu_metrics_ready(self, message, percent):', 1)[0]
assert 'self.monitor_timer.start(15000)' not in initialization, 'GPU monitoring starts during GUI setup'
assert 'self._gpu_monitor.start()' not in initialization, 'NVIDIA probe starts during GUI setup'
job_start = ui.split('    def start_worker(self,files):', 1)[1].split('    def export_selection_changed', 1)[0]
assert 'self.monitor_timer.start(15000)' in job_start, 'GPU monitoring should activate for a real job'
assert 'import onnxruntime as ort' not in ui
assert 'self.model_name = os.environ.get("AURENIX_MODEL", "u2net")' in core
assert 'self.width * self.height > 16_000_000' in core
assert 'source_image.width * source_image.height > 8_000_000' in core
print('PASS lazy startup, GPU monitoring deferred to job, safe default model, image memory guards')
