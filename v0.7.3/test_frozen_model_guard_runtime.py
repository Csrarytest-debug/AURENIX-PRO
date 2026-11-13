"""Exercise missing bundled-model guard without Qt, rembg or CUDA."""
import json
import sys
import tempfile
from pathlib import Path
import inference_worker

with tempfile.TemporaryDirectory(prefix='aurenix_missing_model_') as temp:
    root = Path(temp)
    cfg = root / 'job.json'
    events = root / 'events.jsonl'
    cfg.write_text(json.dumps({
        'images': ['test.png'], 'output_dir': str(root), 'width': 640, 'height': 480,
        'model_name': 'u2net', 'event_file': str(events),
    }), encoding='utf-8')
    had_frozen = hasattr(sys, 'frozen')
    old_frozen = getattr(sys, 'frozen', None)
    had_bundle = hasattr(sys, '_MEIPASS')
    old_bundle = getattr(sys, '_MEIPASS', None)
    try:
        sys.frozen = True
        sys._MEIPASS = str(root)
        result = inference_worker.main(str(cfg))
        assert result == 1
        messages = [json.loads(line) for line in events.read_text().splitlines()]
        assert messages[0]['event'] == 'failed'
        assert 'Bundled AI model missing' in messages[0]['args'][1]
        assert not (root / 'models').exists(), 'Guard should not download models'
    finally:
        if had_frozen: sys.frozen = old_frozen
        else: del sys.frozen
        if had_bundle: sys._MEIPASS = old_bundle
        else: del sys._MEIPASS
print('PASS missing bundled model fails safely without loading AI')
