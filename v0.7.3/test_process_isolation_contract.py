"""Static integration checks for packaged subprocess isolation."""
from pathlib import Path
root = Path(__file__).resolve().parent
ui = (root / 'aurenix_pro.py').read_text()
core = (root / 'background_remover_pro.py').read_text()
adapter = (root / 'isolated_worker.py').read_text()
child = (root / 'inference_worker.py').read_text()
assert ui.index("sys.argv[1] == '--aurenix-worker'") < ui.index('from PIL import Image')
assert 'self.worker = IsolatedBatchWorker(' in core
assert 'QProcess(self)' in adapter
assert 'self._process.start(sys.executable, args)' in adapter
assert 'self._process.kill()' in adapter
assert "'event_file': self._event_path" in adapter
assert "'command_file': self._command_path" in adapter
assert 'memory.available < 1024**3' in adapter
assert 'worker.run()' in child
assert 'print(payload, flush=True)' in child  # only in non-windowed fallback
print('PASS process-isolated AI, watchdog, file IPC and frozen-entry dispatch')
