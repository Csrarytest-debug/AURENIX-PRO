"""Actual OpenCV inpainting regression; no GUI, AI inference, or model involved."""
import ast
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw

# Execute the wire cleanup methods in a minimal fake class namespace; their
# source is extracted directly from the shipped core file to prevent drift.
tree = ast.parse(Path(__file__).with_name('background_remover_pro.py').read_text())
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'EditablePreview')
methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ('apply_wire_cleanup','undo_wire_cleanup')]
mock_cls = ast.ClassDef(name='WireHarness', bases=[], keywords=[], body=methods, decorator_list=[])
module = ast.fix_missing_locations(ast.Module(body=[mock_cls], type_ignores=[]))
namespace = {'Image':Image, 'np':np, 'cv2':cv2}
exec(compile(module, '<wire-harness>', 'exec'), namespace)
obj = namespace['WireHarness']()
obj.processed = Image.new('RGBA', (80,60), (255,255,255,255))
draw = ImageDraw.Draw(obj.processed)
draw.line((10,30,70,30), fill=(0,0,0,255), width=3)
obj.wire_mask = Image.new('L', (80,60), 0)
ImageDraw.Draw(obj.wire_mask).rectangle((9,27,71,33), fill=255)
obj.wire_undo = None
obj.refresh = lambda: None
obj.changed = type('Changed', (), {'emit':lambda self:None})()
obj.apply_wire_cleanup()
assert obj.processed.getpixel((40,30))[:3] == (255,255,255)
assert obj.wire_mask.getbbox() is None
obj.undo_wire_cleanup()
assert obj.processed.getpixel((40,30))[:3] == (0,0,0)
print('PASS actual OpenCV guided-wire inpainting and undo')
