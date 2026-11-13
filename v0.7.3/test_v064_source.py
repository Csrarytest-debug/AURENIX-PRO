"""No-Qt source contract tests for V0.6.4 integration."""
from pathlib import Path
import ast
import re
base=Path(__file__).parent
ui=(base/'aurenix_pro.py').read_text()
core=(base/'background_remover_pro.py').read_text()
assert 'QSplashScreen(splash_image)' in ui
assert "'bs_broadcast_glow.png'" in ui
assert "'Output Destination:'" in ui
assert "['PNG', 'JPEG', 'WebP', 'TIFF', 'BMP']" in ui
assert 'self.worker.export_format = getattr(self, "current_export_format", "PNG")' in core
assert re.search(r'save_image_atomic\s*\(\s*result\s*,\s*output\s*,\s*self\.export_format', core)
assert 'save_image_atomic(self.editor.processed' in core
assert '_SESSION_CACHE.get(model)' in core
assert 'get_providers()' in core
ast.parse(ui);ast.parse(core)
print('PASS V0.6.4 splash, real-export wiring, session reuse, provider telemetry and syntax')
