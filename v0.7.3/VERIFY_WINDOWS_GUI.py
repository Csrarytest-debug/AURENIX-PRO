"""Packaged Windows GUI startup smoke test (not a clean-PC UI certification).

Start the built EXE using Qt offscreen platform. Observe idle GUI memory
for 45 seconds and reject early exit, runaway RAM, or unexpected children.
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
            import psutil
            handle = psutil.Process(proc.pid)
            peak_rss = 0
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                code = proc.poll()
                if code is not None:
                    break
                try:
                    peak_rss = max(peak_rss, handle.memory_info().rss)
                    # No AI is processing yet. GUI should not consume >1.5 GiB
                    # or spawn an AI child solely by opening the app.
                    if peak_rss > 1536 * 1024**2:
                        raise MemoryError(
                            f'Idle GUI RAM exceeded 1.5 GiB: {peak_rss / 1024**2:.0f} MiB'
                        )
                    children = handle.children(recursive=True)
                    if any('aurenix-pro.exe' in p.name().lower() for p in children):
                        raise RuntimeError('AI worker unexpectedly started during idle GUI startup')
                except psutil.NoSuchProcess:
                    break
                time.sleep(1)
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
            print(f'PASS packaged GUI stable 45s while idle; peak RSS '
                  f'{peak_rss / 1024**2:.0f} MiB (limit 1536 MiB). '
                  'Functional GUI and clean-PC tests still required', flush=True)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=15)


if __name__ == '__main__':
    main()
