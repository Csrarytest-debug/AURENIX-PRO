"""Pure-Python static regressions; run without a GUI, models or Windows."""
import ast
from pathlib import Path

root = Path(__file__).parent
sources = {name: (root / name).read_text(encoding='utf-8') for name in ('aurenix_pro.py', 'background_remover_pro.py')}
trees = {name: ast.parse(data) for name, data in sources.items()}
classes = {}
for tree in trees.values():
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes[node.name] = {n.name for n in node.body if isinstance(n, (ast.FunctionDef,ast.AsyncFunctionDef))}

# Find self.foo references in UI and ensure they are provided by the subclass or its recovered base.
base = classes['BackgroundRemoverPro'] | classes['AurenixPro'] | classes['QMainWindow'] if 'QMainWindow' in classes else classes['BackgroundRemoverPro'] | classes['AurenixPro']
required_callbacks = (
    'remove_selected_image','clear_image_library','import_images','import_folder',
    'start_processing','pause_processing','resume_processing','stop_processing',
    'retry_failed','save_edited','choose_output','open_output','change_tool',
    'change_brush','change_zoom','select_image','update_controls',
)
for callback in required_callbacks:
    assert callback in base, f'Missing UI callback: {callback}'
assert 'new_session(model, providers=requested)' in sources['background_remover_pro.py']
assert '"birefnet-general"' in sources['background_remover_pro.py']
assert 'self.editor=FitEditor()' in sources['aurenix_pro.py']
assert 'self.transparent_bg' in sources['aurenix_pro.py']
assert 'self.worker is not None' in sources['aurenix_pro.py']
print(f'PASS: syntax checks and {len(required_callbacks)} UI callbacks resolved; BiRefNet mode and previews present')
for callback in ('save_error_report', 'open_error_logs', 'image_failed'):
    assert callback in classes['AurenixPro'], f'Missing diagnostics callback: {callback}'
print('PASS: diagnostic UI callbacks resolved')
