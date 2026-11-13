"""Synthetic regression tests: real OpenCV alpha cleanup, no ONNX inference."""
from PIL import Image, ImageDraw
from wire_cleanup import remove_loose_wires

# Rack equipment, printed label and a cable extending from the top edge.
img = Image.new('RGBA', (640, 400), (255, 255, 255, 0))
d = ImageDraw.Draw(img)
d.rectangle((125, 145, 510, 315), fill=(75, 80, 85, 255))
d.rectangle((155, 165, 335, 190), fill=(210, 210, 210, 255))  # printed label
# Detached black wire and a cable that touches the product body.
d.line([(35, 95), (250, 95), (330, 145)], fill=(0, 0, 0, 255), width=3)
d.line([(520, 80), (600, 100)], fill=(0, 0, 0, 255), width=3)
clean, removed = remove_loose_wires(img)
assert removed > 200, removed
assert clean.getpixel((100, 95))[3] == 0, 'Detached wire was not removed'
assert clean.getpixel((550, 88))[3] == 0, 'Second cable was not removed'
assert clean.getpixel((280, 100))[3] == 0, 'Connected cable was not removed'
assert clean.getpixel((250, 170)) == img.getpixel((250, 170)), 'Product label was modified'
assert clean.getpixel((125, 225)) == img.getpixel((125, 225)), 'Rack edge was modified'
assert clean.getpixel((510, 315)) == img.getpixel((510, 315)), 'Product corner was modified'
# Preserve separate product units; do not keep only the largest connected object.
second = Image.new('RGBA', (640, 400), (0, 0, 0, 0))
d = ImageDraw.Draw(second)
d.rectangle((40, 80, 200, 220), fill=(200, 10, 10, 255))
d.rectangle((350, 120, 460, 280), fill=(10, 200, 10, 255))
d.line((15, 25, 610, 25), fill=(0, 0, 0, 255), width=3)
clean, removed = remove_loose_wires(second)
assert clean.getpixel((100, 120)) == second.getpixel((100, 120))
assert clean.getpixel((400, 170)) == second.getpixel((400, 170))
assert clean.getpixel((300, 25))[3] == 0
# Protect very thin objects: when no substantial object is detected, no trim.
only_wire = Image.new('RGBA', (640, 400), (0, 0, 0, 0))
ImageDraw.Draw(only_wire).line((20, 30, 600, 30), fill=(255, 0, 0, 255), width=2)
unchanged, count = remove_loose_wires(only_wire)
assert count == 0 and unchanged.tobytes() == only_wire.tobytes()
print('PASS conservative auto-wire alpha cleanup, product labels/edges, multiple objects, safe fallback')
