"""Packaged Windows GUI startup smoke test (not a clean-PC UI certification).

Start the built EXE using Qt offscreen platform, verify it does not exit
immediately, and terminate it after the startup observation period.
Does not test manual UI workflows, image quality, or GPU inference.
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python VERIFY_WINDOWS_GUI.py PATH_TO_PACKAGED_EXE')
    exe = Path(sys.argv[1]).resolve()
    if not exe.is_file():
        raise FileNotFoundError(f'Packaged GUI EXE missing: {exe}')
    with tempfile.TemporaryDirectory(prefix='aurenix_gui_smoke_') as tmp:
        env = os.environ.copy()
        env['QT_QPA_PLATFORM'] = 'offscreen'
        env['LOCALAPPDATA'] = str(Path(tmp) / 'AppData')
        Path(env['LOCALAPPDATA']).mkdir(parents=True, exist_ok=True)
        print('Starting packaged Windows GUI offscreen:', exe, flush=True)
        proc = subprocess.Popen(
            [str(exe)], cwd=exe.parent, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            time.sleep(10)
            code = proc.poll()
            if code is not None:
                logs = list(Path(env['LOCALAPPDATA']).rglob('aurenix*.log'))
                details = []
                for log in sorted(logs, key=lambda p: p.stat().st_mtime)[-2:]:
                    details.append(log.read_text(encoding='utf-8', errors='replace')[-1600:])
                raise RuntimeError(
                    f'Packaged GUI closed during startup (exit={code}). '
                    f'Last logs: {" | ".join(details) if details else "none"}'
                )
            print('PASS packaged GUI remains running after 10-second startup observation; '
                  'functional GUI and clean-PC testing still required', flush=True)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=15)


if __name__ == '__main__':
    main()
