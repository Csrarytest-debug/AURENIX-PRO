"""Monitoring source contract. GPU provider is reported by worker, not imported at startup."""
from pathlib import Path
s=(Path(__file__).parent/'aurenix_pro.py').read_text(encoding='utf8')
core=(Path(__file__).parent/'background_remover_pro.py').read_text(encoding='utf8')
for token in ['gpu_bar', 'ram_bar', 'memory.used,memory.total', 'GpuMonitor(QThread)', 'V0.7.3', 'right_wing.setFixedWidth(430)', 'left_wing.setFixedWidth(430)']:
    assert token in s, token
assert 'onnxruntime as ort' not in s, 'Heavy inference library must not load in GUI telemetry'
assert 'CUDAExecutionProvider' in core, 'Provider check belongs in the processing worker'
print('PASS non-blocking telemetry, GPU provider deferred until processing, UI layout')
