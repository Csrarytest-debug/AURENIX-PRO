"""Verify model location is set before child dispatch, and missing weights fail fast."""
from pathlib import Path
root = Path(__file__).resolve().parent
ui = (root / 'aurenix_pro.py').read_text(encoding='utf-8')
child = (root / 'inference_worker.py').read_text(encoding='utf-8')
assert ui.index("os.environ['U2NET_HOME']") < ui.index("sys.argv[1] == '--aurenix-worker'")
assert "os.environ['U2NET_HOME'] = str(model_dir)" in child
assert "raise FileNotFoundError" in child
assert "if getattr(sys, 'frozen', False):" in child
print('PASS packaged model directory configured before isolated worker dispatch')
