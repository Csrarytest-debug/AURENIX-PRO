"""Native Windows packaged-EXE GPU smoke test (build gate, not a clean-PC test).

Runs a real AI inference in a child EXE, verifies CUDA provider, output image,
source preservation, and checks for unexpectedly high worker RAM.
"""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python VERIFY_WINDOWS_GPU.py dist\\AURENIX-PRO\\AURENIX-PRO.exe')
    executable = Path(sys.argv[1]).resolve()
    if not executable.is_file():
        raise SystemExit('EXE missing: ' + str(executable))
    with tempfile.TemporaryDirectory(prefix='aurenix_gpu_smoke_') as folder:
        root = Path(folder)
        src = root / 'synthetic_product.png'
        image = Image.new('RGB', (640, 480), '#ffffff')
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((130, 90, 510, 390), radius=20, fill='#13375b')
        draw.rectangle((180, 180, 460, 300), fill='#ffc42d')
        image.save(src)
        event_file = root / 'events.jsonl'
        command_file = root / 'commands.txt'
        event_file.touch()
        command_file.touch()
        cfg = root / 'job.json'
        cfg.write_text(json.dumps({
            'images': [str(src)], 'output_dir': str(root / 'output'),
            'width': 640, 'height': 480, 'model_name': 'u2net',
            'bg_mode': 'white', 'export_format': 'PNG',
            'event_file': str(event_file), 'command_file': str(command_file),
        }), encoding='utf-8')
        print('Launching packaged GPU smoke test:', executable, flush=True)
        proc = subprocess.Popen([str(executable), '--aurenix-worker', str(cfg)],
                                cwd=executable.parent, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        peak = 0
        try:
            import psutil
            process = psutil.Process(proc.pid)
            deadline = time.monotonic() + 240
            while proc.poll() is None:
                if time.monotonic() > deadline:
                    proc.kill()
                    raise RuntimeError('GPU inference timed out after 240 seconds')
                try:
                    peak = max(peak, process.memory_info().rss)
                    mem = psutil.virtual_memory()
                    if peak > min(6 * 1024**3, int(mem.total * .40)) or mem.available < 1024**3:
                        proc.kill()
                        raise MemoryError('GPU worker exceeded safe RAM limits during smoke test')
                except psutil.NoSuchProcess:
                    pass
                time.sleep(.2)
            code = proc.wait(timeout=10)
            events = [json.loads(line) for line in event_file.read_text(encoding='utf-8').splitlines()]
            status_text = '\n'.join(str(x['args'][0]) for x in events if x['event'] == 'status' and x['args'])
            completed = [x['args'] for x in events if x['event'] == 'completed']
            failed = [x['args'] for x in events if x['event'] == 'failed']
            if code != 0 or failed or len(completed) != 1 or 'CUDAExecutionProvider' not in status_text:
                raise RuntimeError(f'GPU smoke FAILED: code={code}; failed={failed}; status={status_text[-1200:]}')
            output = Path(completed[0][1])
            with Image.open(output) as result:
                result.verify()
            with Image.open(output) as result:
                if result.size != (640, 480):
                    raise RuntimeError('Wrong output dimensions')
            if not src.is_file():
                raise RuntimeError('Original source was modified/deleted')
            print(f'PASS real packaged CUDA inference; peak child RSS {peak / 1024**2:.0f} MiB')
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)


if __name__ == '__main__':
    main()
