"""AURENIX isolated inference process (stdio JSON event protocol).

No GUI is instantiated in this process. A native ONNX/CUDA crash affects this
child, not the parent GUI. This module is only imported for --aurenix-worker.
"""
import json
import os
import sys
import threading
import traceback
import time
from pathlib import Path


_EVENT_FILE = None


def emit(kind, *args):
    """File IPC works with PyInstaller --windowed (sys.stdout can be None)."""
    payload = json.dumps({'event': kind, 'args': list(args)}, ensure_ascii=True)
    if _EVENT_FILE:
        with open(_EVENT_FILE, 'a', encoding='utf-8') as stream:
            stream.write(payload + '\n')
            stream.flush()
    elif sys.stdout is not None:
        print(payload, flush=True)


def main(config_path):
    global _EVENT_FILE
    try:
        config = json.loads(Path(config_path).read_text(encoding='utf-8'))
        _EVENT_FILE = config.get('event_file')
        if not isinstance(config.get('images'), list) or not config['images']:
            raise ValueError('No input images were provided')
        # In a frozen release, model weights must be present locally. Never
        # attempt a surprise download while processing a customer's images.
        if getattr(sys, 'frozen', False):
            bundle = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
            model_dir = bundle / 'models'
            os.environ['U2NET_HOME'] = str(model_dir)
            model = config.get('model_name', 'u2net')
            prefix = 'u2net' if model == 'u2net' else 'birefnet'
            if not any(p.is_file() and p.name.lower().startswith(prefix)
                       for p in model_dir.glob('*.onnx')):
                raise FileNotFoundError(f'Bundled AI model missing: {model} in {model_dir}')
        # Qt is imported only into the child; no QApplication is created.
        from background_remover_pro import BatchWorker
        worker = BatchWorker(config['images'], config['output_dir'],
                             int(config['width']), int(config['height']))
        for name in ('bg_mode', 'bg_color', 'export_format', 'export_quality',
                     'export_dpi', 'model_name', 'auto_wire_cleanup'):
            if name in config:
                setattr(worker, name, config[name])
        worker.progress.connect(lambda *a: emit('progress', *a))
        worker.completed.connect(lambda *a: emit('completed', *a))
        worker.failed.connect(lambda *a: emit('failed', *a))
        worker.status.connect(lambda *a: emit('status', *a))

        def read_commands():
            # File-based commands avoid stdin, which may be None in a windowed EXE.
            command_file = Path(config['command_file'])
            offset = 0
            while True:
                try:
                    with command_file.open('r', encoding='ascii') as stream:
                        stream.seek(offset)
                        commands = stream.readlines()
                        offset = stream.tell()
                    for command in commands:
                        command = command.strip().lower()
                        if command == 'pause':
                            worker.pause()
                        elif command == 'resume':
                            worker.resume()
                        elif command == 'stop':
                            worker.stop()
                except (OSError, ValueError):
                    pass
                time.sleep(0.2)

        threading.Thread(target=read_commands, daemon=True).start()
        emit('status', 'Isolated AI engine started')
        worker.run()  # Synchronous in the child process; GUI is in another process.
        emit('done')
        return 0
    except BaseException as exc:
        emit('failed', 'AI initialization', f'{type(exc).__name__}: {exc}')
        if sys.stderr is not None:
            traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
