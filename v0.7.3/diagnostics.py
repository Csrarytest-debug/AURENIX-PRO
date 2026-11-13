"""Local, privacy-conscious diagnostics for AURENIX PRO.

No telemetry is transmitted. Reports are written to the user's data directory.
"""
import logging
import os
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path


def log_directory():
    base = os.environ.get('LOCALAPPDATA') or os.environ.get('APPDATA')
    if base:
        folder = Path(base) / 'AURENIX-PRO' / 'Logs'
    else:
        folder = Path.home() / '.aurenix-pro' / 'logs'
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def configure_logging():
    folder = log_directory()
    target = folder / 'aurenix.log'
    logger = logging.getLogger('aurenix')
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        from logging.handlers import RotatingFileHandler
        handler = RotatingFileHandler(str(target), maxBytes=2_000_000, backupCount=4, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(handler)
    return logger


def record_error(scope, exception=None, *, details=None):
    logger = configure_logging()
    if exception is not None:
        logger.error('%s: %s', scope, exception,
                     exc_info=(type(exception), exception, exception.__traceback__))
    elif details is not None:
        logger.error('%s: %s', scope, details)
    else:
        logger.error('%s', scope)


def install_exception_hooks():
    original_sys_hook = sys.excepthook
    def handle(exc_type, exc_value, exc_traceback):
        record_error('Uncaught application exception', exc_value)
        original_sys_hook(exc_type, exc_value, exc_traceback)
    sys.excepthook = handle
    original_thread_hook = getattr(threading, 'excepthook', None)
    if original_thread_hook:
        def thread_hook(args):
            record_error('Uncaught worker thread exception', args.exc_value)
            original_thread_hook(args)
        threading.excepthook = thread_hook


def export_report(destination):
    """Export sanitized-in-transport? No: local log may include file paths; user chooses sharing."""
    from shutil import copyfile
    target = Path(destination)
    if not target.parent.exists():
        raise FileNotFoundError(str(target.parent))
    log = log_directory() / 'aurenix.log'
    if log.exists():
        copyfile(log, target)
    else:
        target.write_text('AURENIX PRO diagnostics\nNo errors have been recorded.\n', encoding='utf-8')
    return target
