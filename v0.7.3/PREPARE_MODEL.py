"""Fetch and validate the BiRefNet model in the release's local models directory.

Only run at BUILD time, not when the installed application starts. If the
model cannot be fetched, the build fails rather than shipping a broken EXE.
"""
import gc
import os
from pathlib import Path

root = Path(__file__).resolve().parent
model_dir = root / 'models'
model_dir.mkdir(exist_ok=True)
os.environ['U2NET_HOME'] = str(model_dir)

print('Preparing safe U2Net + optional BiRefNet weights in:', model_dir, flush=True)
from rembg import new_session

for model in ('u2net', 'birefnet-general'):
    session = new_session(model, providers=['CPUExecutionProvider'])
    if 'CPUExecutionProvider' not in session.inner_session.get_providers():
        raise SystemExit(f'Model validation failed: {model}')
    del session
    gc.collect()
weights = [p for p in model_dir.rglob('*.onnx')]
if not any('u2net' in p.name.lower() for p in weights) or not any('birefnet' in p.name.lower() for p in weights):
    raise SystemExit('Missing U2Net or BiRefNet weights in models/')
if not all(p.stat().st_size > 100000 for p in weights):
    raise SystemExit('Invalid model weights in models/')
print('Model files validated:', ', '.join(p.name for p in weights))
