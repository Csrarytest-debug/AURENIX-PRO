"""Strict per-image wiring policy and 1 source -> 1 output regression.

This test exercises real PNG I/O, mask cleanup and source hashes, with MOCK
segmentation. It does NOT verify semantic AI cable detection, product fidelity,
contact shadows, ONNX CUDA, RTX 4050, or long-batch memory stability.
"""
import hashlib
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw

import test_mocked_batch_runtime  # Qt and rembg stubs, existing batch tests
import background_remover_pro as core
import rembg
from wire_cleanup import (
    POLICIES, get_requested_policy, choose_wire_policy,
    is_known_aja_sample, remove_loose_wires,
)

assert POLICIES == (
    "auto_context", "remove_stray", "keep_attached", "keep_all"
)
assert is_known_aja_sample("IMG_5712 2.jpg")
assert is_known_aja_sample("IMG_5703 2.jpg")
assert not is_known_aja_sample("IMG_57122.jpg")
assert choose_wire_policy("IMG_5712 2.jpg") == "keep_attached"
assert choose_wire_policy("IMG_5703 2.jpg") == "keep_attached"
assert choose_wire_policy("IMG_5801(4).jpg") == "remove_stray"
assert choose_wire_policy("IMG_5696 2.jpg") == "remove_stray"
assert choose_wire_policy("unknown-product.jpg") == "keep_attached"
assert get_requested_policy("IMG_5712 2.jpg") == "auto_context"
assert choose_wire_policy(
    "IMG_5712 2.jpg", {"IMG_5712 2.jpg": "remove_stray"}
) == "remove_stray", "AJA default must NOT prevent an explicit manual choice"
assert choose_wire_policy(
    "IMG_5801(4).jpg", {"IMG_5801(4).jpg": "keep_all"}
) == "keep_all"
for policy in POLICIES:
    assert get_requested_policy("x.jpg", {"x.jpg": policy}) == policy

# Synthetic device, connected lead and separate cable near product top edge.
mask = Image.new("RGBA", (640, 400), (0, 0, 0, 0))
d = ImageDraw.Draw(mask)
d.rectangle((125, 145, 510, 315), fill=(60, 65, 70, 255))
d.rectangle((180, 170, 280, 190), fill=(210, 210, 210, 255))
d.line([(35, 95), (250, 95), (330, 145)], fill=(0, 0, 0, 255), width=3)
d.line((530, 70, 620, 70), fill=(0, 0, 0, 255), width=3)

result_stray, removed = remove_loose_wires(mask, mode="remove_stray")
assert removed > 0 and result_stray.getpixel((560, 70))[3] == 0
assert result_stray.getpixel((250, 95))[3] == 255
assert result_stray.getpixel((200, 180)) == mask.getpixel((200, 180))
result_attached, count = remove_loose_wires(mask, mode="keep_attached")
assert count == 0 and result_attached.getpixel((560, 70))[3] == 255
result_all, count = remove_loose_wires(mask, mode="keep_all")
assert count == 0 and result_all.tobytes() == mask.tobytes()

with tempfile.TemporaryDirectory(prefix="aurenix_per_item_") as tmp:
    base = Path(tmp)
    original_dir = base / "originals"
    alt_dir = base / "alternate"
    original_dir.mkdir()
    alt_dir.mkdir()
    names = [
        "IMG_5712 2.jpg", "IMG_5703 2.jpg",
        "IMG_5801(4).jpg", "IMG_5696 2.jpg",
        "IMG_5727 2.jpg", "IMG_5782(1).jpg",
    ]
    paths = []
    hashes = {}
    for idx, name in enumerate(names):
        src = original_dir / name
        Image.new("RGB", (640, 400), (145, 40 + idx * 26, 70)).save(src)
        paths.append(str(src))
        hashes[str(src)] = hashlib.sha256(src.read_bytes()).hexdigest()
    # Identical filename from ANOTHER input folder: keep_all override must
    # apply to that exact input only, not the original IMG_5801.
    duplicate_path = alt_dir / "IMG_5801(4).jpg"
    Image.new("RGB", (640, 400), (20, 80, 130)).save(duplicate_path)
    paths.append(str(duplicate_path))
    hashes[str(duplicate_path)] = hashlib.sha256(duplicate_path.read_bytes()).hexdigest()

    overrides = {
        paths[1]: "keep_all",      # known AJA, explicit override
        paths[3]: "keep_attached", # rack gear, override retains near cables
        paths[4]: "remove_stray",  # individual circuit board example
        paths[5]: "keep_all",      # Behringer, explicit keep-all
        paths[6]: "keep_all",      # duplicate filename, different full path
    }
    assert choose_wire_policy(paths[2], overrides) == "remove_stray"
    assert choose_wire_policy(paths[6], overrides) == "keep_all"

    rembg.remove = lambda image, **kwargs: mask.copy()
    folder = base / "outputs"
    worker = core.BatchWorker(paths, folder, 640, 400)
    worker.wire_policy_overrides = overrides.copy()
    worker.run()
    assert not worker.failed.events, worker.failed.events
    assert len(worker.completed.events) == len(paths) == 7
    assert worker.progress.events == [(i, 7) for i in range(1, 8)]
    mapping = dict(worker.completed.events)
    assert set(mapping) == set(paths)
    assert len(set(mapping.values())) == 7
    assert len(list(folder.glob("*.png"))) == 7
    assert all(Path(out).is_file() for out in mapping.values())
    for source_path, output_path in mapping.items():
        with Image.open(output_path) as img:
            assert img.format == "PNG" and img.size == (640, 400)
            is_near_wire_kept = choose_wire_policy(
                source_path, overrides
            ) in ("keep_attached", "keep_all")
            assert (img.getpixel((560, 70))[0] == 0) == is_near_wire_kept, source_path
            assert img.getpixel((200, 180))[:3] == (210, 210, 210)
    assert Path(mapping[paths[2]]).name != Path(mapping[paths[6]]).name
    assert all(
        hashlib.sha256(Path(path).read_bytes()).hexdigest() == hashes[path]
        for path in paths
    ), "Original source was overwritten"

    # Simulate Retry Failed with the exact original input policy: it remains
    # unchanged, generates its own output, and touches no other input file.
    retry = core.BatchWorker([paths[6]], folder, 640, 400)
    retry.wire_policy_overrides = overrides.copy()
    retry.pause()
    retry.resume()
    retry.run()
    assert len(retry.completed.events) == 1 and not retry.failed.events
    assert len(list(folder.glob("*.png"))) == 8
    with Image.open(retry.completed.events[0][1]) as image:
        assert image.getpixel((560, 70))[:3] == (0, 0, 0)
    assert all(
        hashlib.sha256(Path(path).read_bytes()).hexdigest() == hashes[path]
        for path in paths
    )
    print("PASS four modes, mixed 7-input/7-output batch, same-name "
          "different-path isolation, UI-ready retry state, source fidelity")
