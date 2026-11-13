"""Real subprocess IPC tests with a fake AI engine; no CUDA/Qt dependency.

Checks Windows-windowed-safe file IPC, completion, cancellation, and native
child-process death without killing the parent test process.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FAKE_ENGINE = '''
import os
import time
class Signal:
    def __init__(self): self.callbacks = []
    def connect(self, callback): self.callbacks.append(callback)
    def emit(self, *args):
        for callback in self.callbacks: callback(*args)
class BatchWorker:
    def __init__(self, images, output_dir, width, height):
        self.images = images
        self.output_dir = output_dir
        self.progress = Signal()
        self.completed = Signal()
        self.failed = Signal()
        self.status = Signal()
        self.stopped = False
        self.paused = False
    def pause(self): self.paused = True
    def resume(self): self.paused = False
    def stop(self): self.stopped = True
    def run(self):
        if os.environ.get('SIMULATE_NATIVE_CRASH'):
            os._exit(137)
        for i, image in enumerate(self.images):
            for _ in range(30):
                if self.stopped: return
                while self.paused and not self.stopped: time.sleep(.01)
                time.sleep(.01)
            if self.stopped: return
            self.completed.emit(image, self.output_dir + '/result_' + str(i) + '.png')
            self.progress.emit(i+1, len(self.images))
'''

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    shutil.copyfile(ROOT / 'inference_worker.py', root / 'inference_worker.py')
    (root / 'background_remover_pro.py').write_text(FAKE_ENGINE)
    for mode in ('complete', 'stop', 'crash'):
        config = root / (mode + '.json')
        events = root / (mode + '.events')
        commands = root / (mode + '.commands')
        events.touch()
        commands.touch()
        config.write_text(json.dumps({
            'images': ['image1.png', 'image2.png', 'image3.png'],
            'output_dir': str(root), 'width': 128, 'height': 96,
            'event_file': str(events), 'command_file': str(commands),
        }))
        env = os.environ.copy()
        if mode == 'crash': env['SIMULATE_NATIVE_CRASH'] = '1'
        proc = subprocess.Popen([sys.executable, str(root / 'inference_worker.py'), str(config)],
                                cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if mode == 'stop':
            time.sleep(.15)
            with commands.open('a') as f: f.write('stop\n')
        out, err = proc.communicate(timeout=8)
        messages = [json.loads(line) for line in events.read_text().splitlines()]
        kinds = [m['event'] for m in messages]
        if mode == 'complete':
            assert proc.returncode == 0, (proc.returncode, err)
            assert kinds.count('completed') == 3, kinds
            assert 'done' in kinds
        elif mode == 'stop':
            assert proc.returncode == 0, (proc.returncode, err)
            assert kinds.count('completed') < 3, kinds
            assert 'done' in kinds
        else:
            assert proc.returncode == 137, (proc.returncode, err)
            assert 'done' not in kinds
        print('PASS subprocess ' + mode + ' / file IPC')
