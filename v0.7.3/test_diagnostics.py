"""Regression checks for local error logging; no Qt or AI dependency required."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from diagnostics import configure_logging, record_error, export_report, log_directory, install_exception_hooks

with tempfile.TemporaryDirectory() as home:
    os.environ['LOCALAPPDATA'] = home
    folder = log_directory()
    assert folder == Path(home) / 'AURENIX-PRO' / 'Logs'
    configure_logging()
    try:
        raise RuntimeError('test failure for reporting')
    except RuntimeError as err:
        record_error('Test processing', err)
    log_path = folder / 'aurenix.log'
    assert log_path.exists()
    contents = log_path.read_text(encoding='utf-8')
    assert 'test failure for reporting' in contents
    assert 'Traceback' in contents
    output = Path(home) / 'report.log'
    export_report(output)
    assert output.read_text(encoding='utf-8') == contents
    install_exception_hooks()
    assert callable(sys.excepthook)
print('PASS: local error logging, traceback, report export and exception hook checks')
