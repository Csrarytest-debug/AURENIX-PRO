"""Per-image equipment/cable policy and one-to-one outputs, mock inference only.

This does NOT prove semantic adapter recognition on arbitrary photographs,
image quality, CUDA/RTX 4050 inference, or 300-real-photo memory stability.
"""
import hashlib
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw

import test_mocked_batch_runtime  # installs stub Qt/rembg, exercises basic batch
import rembg
import background_remover_pro as core
from wire_cleanup import choose_wire_policy, is_known_aja_sample, remove_loose_wires

assert is_known_aja_sample("IMG_5712 2.jpg")
assert is_known_aja_sample("IMG_5703 2.jpg")
assert choose_wire_policy("IMG_5712 2.jpg", {"IMG_5712 2.jpg": "selective"}) == "preserve_all"
assert choose_wire_policy("IMG_5703 2.jpg") == "preserve_all"
assert choose_wire_policy("IMG_5801(4).jpg") == "selective"
assert choose_wire_policy("IMG_5696 2.jpg") == "selective"
assert choose_wire_policy("other_AJA.jpg", {"other_AJA.jpg": "preserve_all"}) == "preserve_all"

mask = Image.new("RGBA", (640, 400), (0, 0, 0, 0))
painter = ImageDraw.Draw(mask)
painter.rectangle((125, 145, 510, 315), fill=(60, 65, 70, 255))
painter.line((35, 95, 250, 95, 330, 145), fill=(0, 0, 0, 255), width=3)
painter.line((530, 70, 620, 70), fill=(0, 0, 0, 255), width=3)
adapter, n = remove_loose_wires(mask, mode="preserve_all")
assert n == 0 and adapter.tobytes() == mask.tobytes()
rack, n = remove_loose_wires(mask, mode="selective")
assert n > 0 and rack.getpixel((560, 70))[3] == 0
assert rack.getpixel((250, 95))[3] == 255
assert rack.getpixel((250, 170)) == mask.getpixel((250, 170))

with tempfile.TemporaryDirectory(prefix="aurenix_context_") as tmp:
    directory = Path(tmp)
    source_dir = directory / "originals"
    source_dir.mkdir()
    inputs, hashes = [], {}
    names = ["IMG_5712 2.jpg", "IMG_5703 2.jpg", "IMG_5801(4).jpg", "IMG_5696 2.jpg"]
    for idx, name in enumerate(names):
        path = source_dir / name
        Image.new("RGB", (640, 400), (150, 60 + idx * 35, 95)).save(path)
        inputs.append(str(path))
        hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()

    rembg.remove = lambda image, **kw: mask.copy()
    outputs = directory / "outputs"
    job = core.BatchWorker(inputs, outputs, 640, 400)
    job.run()
    assert not job.failed.events, job.failed.events
    assert len(job.completed.events) == 4
    assert job.progress.events == [(i, 4) for i in range(1, 5)]
    files = [Path(result) for _, result in job.completed.events]
    assert len(files) == len(set(files)) == 4
    assert len(list(outputs.glob("*.png"))) == 4
    assert all(f.is_file() for f in files)
    assert all(Image.open(f).size == (640, 400) for f in files)
    with Image.open(files[0]) as aja:
        assert aja.getpixel((560, 70))[:3] == (0, 0, 0), "AJA lead was erased"
    with Image.open(files[1]) as aja:
        assert aja.getpixel((560, 70))[:3] == (0, 0, 0), "AJA lead was erased"
    with Image.open(files[2]) as camera:
        assert camera.getpixel((560, 70))[:3] == (255, 255, 255), "Stray wire remains"
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == hashes[p] for p in inputs)
    print("PASS 4 separate PNG outputs, selective per-photo wire handling, originals unchanged")
