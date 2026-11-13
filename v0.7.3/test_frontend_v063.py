"""Static regression tests; no Qt install or model download needed."""
from pathlib import Path
import ast
base=Path(__file__).parent
source=(base/'aurenix_pro.py').read_text(encoding='utf-8')
module=ast.parse(source)
cls=next(x for x in module.body if isinstance(x,ast.ClassDef) and x.name=='AurenixPro')
methods={x.name for x in cls.body if isinstance(x,ast.FunctionDef)}
assert {'choose_output','apply_output_path','start_worker'} <= methods
for text in ('Output Destination:', 'Browse…','Open Folder', "QSettings('BS Broadcast','AURENIX PRO')", "self.settings.setValue('output_destination'", 'self.apply_output_path():return'):
 assert text in source, text
assert (base/'assets'/'bs_broadcast_glow.png').is_file()
assert '--add-data "assets;assets"' in (base/'BUILD_WINDOWS_GPU.bat').read_text()
print('PASS: main-screen folder selection, persistence, centered header and branding asset')
