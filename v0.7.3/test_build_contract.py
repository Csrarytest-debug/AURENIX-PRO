"""Checks GPU build/packaging contracts; not a Windows build or runtime test."""
from pathlib import Path
root = Path(__file__).resolve().parent
build = (root / 'BUILD_WINDOWS_GPU.bat').read_text()
ui = (root / 'aurenix_pro.py').read_text()
core = (root / 'background_remover_pro.py').read_text()
assert '".venv-gpu\\Scripts\\python.exe" -m PyInstaller' in build
assert 'PREPARE_MODEL.py' in build and '--add-data "models;models"' in build
assert 'if not defined MODEL_FOUND' in build
assert 'if errorlevel 1' in build
assert 'BUILD_WINDOWS_GPU.bat' in (root / 'BUILD_WINDOWS.bat').read_text()
assert 'BUILD_WINDOWS_GPU.bat' in (root / 'ONE_CLICK_WINDOWS_BUILD.bat').read_text()
assert "os.environ['U2NET_HOME']" in ui
assert 'getattr(sys, \'_MEIPASS\'' in core
assert 'canvas.alpha_composite(preview)' in ui
assert 'self.library.setCurrentRow(row)' in ui
assert 'QTimer.singleShot(0, self._refresh_completed_preview)' not in ui
assert 'onnxruntime-gpu==1.22.0' in (root / 'requirements-gpu.txt').read_text()
assert 'nvidia-cudnn-cu12' in (root / 'requirements-gpu.txt').read_text()
assert not any(line.strip().startswith('onnxruntime-gpu[') for line in (root / 'requirements-gpu.txt').read_text().splitlines())
print('PASS GPU-only build entry, model bundling, portable model path, reduced preview memory')
