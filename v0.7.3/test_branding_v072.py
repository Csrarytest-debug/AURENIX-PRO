from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent
s=(root/"aurenix_pro.py").read_text(encoding="utf-8")
assert "V0.7.3" in s
assert "bs_broadcast_glow.png" in s
assert "Output Destination:" in s
with Image.open(root/"assets"/"bs_broadcast_glow.png") as im:
    assert im.width>=800 and im.height>=500
print("PASS: V0.7.3 source-branding checks")
