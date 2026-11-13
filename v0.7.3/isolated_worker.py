"""Qt adapter that runs AI in a disposable OS process instead of a GUI thread."""
import json
import os
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QTimer, Signal
from diagnostics import record_error


class IsolatedBatchWorker(QObject):
    progress = Signal(int, int)
    completed = Signal(str, str)
    failed = Signal(str, str)
    status = Signal(str)
    finished = Signal()

    def __init__(self, images, output_dir, width, height, parent=None):
        super().__init__(parent)
        self.images = list(images)
        self.output_dir = Path(output_dir)
        self.width, self.height = width, height
        self.bg_mode = 'white'
        self.bg_color = '#ffffff'
        self.export_format = 'PNG'
        self.export_quality = 95
        self.export_dpi = 400
        self.model_name = os.environ.get('AURENIX_MODEL', 'u2net').strip().lower()
        self.auto_wire_cleanup = True
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self._process.readyReadStandardOutput.connect(self._discard_stdout)
        self._process.readyReadStandardError.connect(self._read_stderr)
        self._process.finished.connect(self._process_finished)
        self._process.errorOccurred.connect(self._process_error)
        self._buffer = bytearray()
        self._stderr_tail = bytearray()
        self._config_path = None
        self._event_path = None
        self._command_path = None
        self._event_offset = 0
        self._event_remainder = b''
        self._done = False
        self._reported_failure = False
        self._finished = False
        self._stopping = False
        self._events_timer = QTimer(self)
        self._events_timer.setInterval(150)
        self._events_timer.timeout.connect(self._read_events)
        self._watchdog = QTimer(self)
        self._watchdog.setInterval(1500)
        self._watchdog.timeout.connect(self._check_memory)
        self._stop_timer = QTimer(self)
        self._stop_timer.setSingleShot(True)
        self._stop_timer.timeout.connect(self._force_stop)

    def isRunning(self):
        return self._process.state() != QProcess.ProcessState.NotRunning

    def start(self):
        if self.isRunning() or self._finished:
            return
        fd, path = tempfile.mkstemp(prefix='aurenix_job_', suffix='.json')
        self._config_path = path
        self._event_path = path + '.events'
        self._command_path = path + '.commands'
        try:
            Path(self._event_path).touch()
            Path(self._command_path).touch()
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump({
                    'event_file': self._event_path,
                    'command_file': self._command_path,
                    'images': self.images, 'output_dir': str(self.output_dir),
                    'width': self.width, 'height': self.height,
                    'bg_mode': self.bg_mode, 'bg_color': self.bg_color,
                    'export_format': self.export_format, 'export_quality': self.export_quality,
                    'export_dpi': self.export_dpi, 'model_name': self.model_name,
                    'auto_wire_cleanup': self.auto_wire_cleanup,
                }, f)
            # The packaged EXE dispatches --aurenix-worker before importing Qt.
            if getattr(sys, 'frozen', False):
                args = ['--aurenix-worker', path]
            else:
                args = [str(Path(__file__).with_name('aurenix_pro.py')),
                        '--aurenix-worker', path]
            self._process.start(sys.executable, args)
            self._events_timer.start()
            self._watchdog.start()
        except Exception as exc:
            record_error('Starting isolated AI engine', exc)
            self.failed.emit('AI initialization', str(exc))
            self._complete()

    def _read_events(self):
        if not self._event_path:
            return
        try:
            with open(self._event_path, 'rb') as stream:
                stream.seek(self._event_offset)
                chunk = stream.read(1_000_000)
                self._event_offset = stream.tell()
        except OSError:
            return
        data = self._event_remainder + chunk
        if len(data) > 1_000_000:
            self._event_remainder = b''
            record_error('AI event IPC exceeded safety limit')
            return
        lines = data.split(b'\n')
        self._event_remainder = lines.pop()
        for raw in lines:
            try:
                payload = json.loads(raw.decode('utf-8'))
                event, args = payload['event'], payload.get('args', [])
                if event == 'completed' and len(args) == 2:
                    self.completed.emit(str(args[0]), str(args[1]))
                elif event == 'progress' and len(args) == 2:
                    self.progress.emit(int(args[0]), int(args[1]))
                elif event == 'failed' and len(args) == 2:
                    if str(args[0]) == 'AI initialization':
                        self._reported_failure = True
                    self.failed.emit(str(args[0]), str(args[1]))
                elif event == 'status' and args:
                    self.status.emit(str(args[0]))
                elif event == 'done':
                    self._done = True
            except (ValueError, KeyError, TypeError, UnicodeError):
                continue

    def _discard_stdout(self):
        # Third-party native libraries may write to stdout; drain the pipe so
        # Qt cannot accumulate unbounded buffered output in the GUI process.
        self._process.readAllStandardOutput()

    def _read_stderr(self):
        self._stderr_tail.extend(bytes(self._process.readAllStandardError()))
        if len(self._stderr_tail) > 8192:
            del self._stderr_tail[:-8192]

    def _process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.failed.emit('AI initialization', 'AI subprocess failed to start')
            self._complete()

    def _process_finished(self, code, status):
        self._read_events()
        self._read_stderr()
        if not self._done and not self._stopping and not self._reported_failure:
            detail = self._stderr_tail.decode('utf-8', errors='replace')[-900:]
            reason = (f'AI engine exited unexpectedly (exit {code}, {status}). '
                      'The main application remains open. ' + detail)
            record_error('Isolated AI process failure', details=reason)
            self.failed.emit('AI initialization', reason)
        elif self._stopping:
            self.status.emit('AI processing stopped; main application remains open')
        self._complete()

    def _complete(self):
        if self._finished:
            return
        self._finished = True
        self._watchdog.stop()
        self._events_timer.stop()
        self._stop_timer.stop()
        for path in (self._config_path, self._event_path, self._command_path):
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass
        self._config_path = self._event_path = self._command_path = None
        self.finished.emit()

    def _send(self, command):
        if self.isRunning() and self._command_path:
            try:
                with open(self._command_path, 'a', encoding='ascii') as stream:
                    stream.write(command + '\n')
            except OSError as exc:
                record_error('Sending AI worker command', exc)

    def pause(self):
        self._send('pause')
        self.status.emit('Pause requested')

    def resume(self):
        self._send('resume')
        self.status.emit('Resume requested')

    def stop(self):
        if self.isRunning():
            self._stopping = True
            self._send('stop')
            self._stop_timer.start(8000)
            self.status.emit('Stopping isolated AI engine safely...')

    def _force_stop(self):
        if self.isRunning():
            self.status.emit('AI engine did not stop in time; terminating child process')
            self._process.kill()

    def _check_memory(self):
        if not self.isRunning():
            return
        try:
            import psutil
            pid = int(self._process.processId())
            if pid <= 0:
                return
            process = psutil.Process(pid)
            memory = psutil.virtual_memory()
            rss = process.memory_info().rss
            # The cap is deliberately per-child, not system-wide. On 16 GB
            # machines this is 6 GB; on 8 GB machines approximately 3.2 GB.
            cap = min(6 * 1024**3, int(memory.total * 0.40))
            if rss > cap or memory.available < 1024**3:
                reason = (f'AI worker exceeded safe memory limits: '
                          f'{rss / 1024**3:.1f} GB worker RAM, '
                          f'{memory.available / 1024**3:.1f} GB free system RAM. '
                          'The worker was stopped to protect Windows.')
                record_error('AI memory watchdog', details=reason)
                self._stopping = True
                # Kill BEFORE showing a modal error dialog. Otherwise the dialog
                # could block the GUI while the child keeps allocating memory.
                self._process.kill()
                self.failed.emit('AI initialization', reason)
        except (ImportError, OSError, ValueError):
            pass
        except Exception as exc:
            record_error('AI watchdog warning', exc)
