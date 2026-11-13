"""Real PIL image I/O, mock AI and Qt to exercise batch orchestration offline.

Does NOT verify actual rembg inference, Qt GUI, CUDA, or Windows packaging.
"""
import importlib
import sys
import tempfile
import types
from pathlib import Path
from PIL import Image

class Signal:
    def __init__(self, *_): self.name = None
    def __set_name__(self, owner, name): self.name = name
    def __get__(self, instance, owner):
        if instance is None: return self
        key = '_signal_' + self.name
        if key not in instance.__dict__:
            instance.__dict__[key] = EmittedSignal()
        return instance.__dict__[key]
class EmittedSignal:
    def __init__(self): self.events = []
    def emit(self, *args): self.events.append(args)
class QThread:
    def __init__(self, *_): pass
class Dummy:
    def __init__(self, *_): pass

qt = types.ModuleType('PySide6')
qtcore = types.ModuleType('PySide6.QtCore')
qtcore.Qt, qtcore.QThread, qtcore.Signal = Dummy, QThread, Signal
qtgui = types.ModuleType('PySide6.QtGui')
qtgui.QImage = qtgui.QPixmap = Dummy
qtwidgets = types.ModuleType('PySide6.QtWidgets')
for name in ('QApplication','QMainWindow','QWidget','QLabel','QPushButton',
             'QListWidget','QFileDialog','QVBoxLayout','QHBoxLayout','QSplitter',
             'QProgressBar','QComboBox','QSpinBox','QMessageBox','QScrollArea',
             'QGroupBox','QColorDialog','QCheckBox'):
    setattr(qtwidgets, name, type(name, (Dummy,), {}))
rembg = types.ModuleType('rembg')
class FakeSession:
    inner_session = None
    def __init__(self): self.inner_session = self
    def get_providers(self): return ['CPUExecutionProvider']
rembg.new_session = lambda *a, **kw: FakeSession()
rembg.remove = lambda image, **kw: image.convert('RGBA')
ort = types.ModuleType('onnxruntime')
ort.get_available_providers = lambda: ['CPUExecutionProvider']
for name, module in [('PySide6', qt), ('PySide6.QtCore', qtcore),
                     ('PySide6.QtGui', qtgui), ('PySide6.QtWidgets', qtwidgets),
                     ('rembg', rembg), ('onnxruntime', ort)]:
    sys.modules[name] = module

core = importlib.import_module('background_remover_pro')
with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    inputs = root / 'inputs'; outputs = root / 'outputs'
    inputs.mkdir()
    files = []
    for i in range(3):
        src = inputs / f'product_{i}.png'
        Image.new('RGB', (50 + i, 30 + i), (200, 80, i)).save(src)
        files.append(str(src))
    worker = core.BatchWorker(files, outputs, 128, 96)
    worker.run()
    assert len(worker.completed.events) == 3, worker.failed.events
    assert not worker.failed.events
    assert worker.progress.events[-1] == (3, 3)
    assert all(Path(x[1]).is_file() for x in worker.completed.events)
    assert all(Image.open(x[1]).size == (128, 96) for x in worker.completed.events)
    assert all(Path(src).is_file() for src in files)
    # A second run must not overwrite the first batch's outputs.
    again = core.BatchWorker(files, outputs, 128, 96)
    again.run()
    assert len(again.completed.events) == 3, again.failed.events
    assert len(list(outputs.glob('*.png'))) == 6
    assert len({x[1] for x in worker.completed.events + again.completed.events}) == 6
    # Stop before processing must leave all source files intact.
    stopped = core.BatchWorker(files, outputs, 128, 96)
    stopped.stop()
    stopped.run()
    assert not stopped.completed.events
    assert len(list(outputs.glob('*.png'))) == 6
    print('PASS mocked 3-image batch, 3-image repeat, unique outputs, stop, source preservation')
