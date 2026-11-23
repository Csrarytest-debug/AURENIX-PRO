"""10 -> 300 image batch regression with real PNG I/O and mock inference.

Checks item counts, progress, failed-image continuation, stop and preservation.
Not evidence of RTX 4050 CUDA, ONNX memory, product quality or 300-image
real-hardware throughput. Run each staged production gate independently.
"""
import hashlib
import tempfile
from pathlib import Path
from PIL import Image

import test_mocked_batch_runtime  # installs independent Qt/ONNX stubs
import background_remover_pro as core
import rembg


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


with tempfile.TemporaryDirectory(prefix="aurenix_scale_") as temp:
    root = Path(temp)
    source_dir = root / "source"
    source_dir.mkdir()
    paths = []
    for i in range(300):
        src = source_dir / f"sample_{i:03d}.png"
        Image.new("RGB", (48, 32), (i % 251, (i * 7) % 251, 95)).save(src)
        paths.append(str(src))
    fingerprints = {p: digest(p) for p in paths}

    def run_batch(inputs, folder):
        worker = core.BatchWorker(inputs, root / folder, 96, 64)
        # Assess bulk orchestration separately from segmentation/wire quality.
        worker.auto_wire_cleanup = False
        worker.run()
        return worker

    rembg.remove = lambda image, **kwargs: image.convert("RGBA")
    first = run_batch(paths[:10], "stage_10")
    assert not first.failed.events, first.failed.events
    assert len(first.completed.events) == 10
    assert first.progress.events == [(i, 10) for i in range(1, 11)]
    assert any("Batch completed" in e[0] for e in first.status.events)

    full = run_batch(paths, "stage_300")
    assert not full.failed.events, full.failed.events
    assert len(full.completed.events) == 300
    assert full.progress.events == [(i, 300) for i in range(1, 301)]
    assert len({output for _, output in full.completed.events}) == 300
    assert all(Path(output).is_file() for _, output in full.completed.events)
    assert any("Saved 300/300" in e[0] for e in full.status.events)
    assert any("Batch completed" in e[0] for e in full.status.events)

    bad = source_dir / "invalid.png"
    bad.write_bytes(b"not an image")
    recovery = run_batch(paths[:5] + [str(bad)] + paths[5:10], "stage_recovery")
    assert len(recovery.completed.events) == 10
    assert len(recovery.failed.events) == 1, recovery.failed.events
    assert recovery.failed.events[0][0] == str(bad)
    assert recovery.progress.events[-1] == (11, 11)
    assert not recovery.stop_event.is_set(), "Ordinary corrupt files must not stop batch"

    calls = []
    stopping = core.BatchWorker(paths, root / "stage_stop", 96, 64)
    stopping.auto_wire_cleanup = False

    def stop_after_seven(image, **kwargs):
        calls.append(1)
        if len(calls) == 7:
            stopping.stop()
        return image.convert("RGBA")

    rembg.remove = stop_after_seven
    stopping.run()
    assert len(stopping.completed.events) == 7
    assert stopping.progress.events[-1] == (7, 300)
    assert any("Batch stopped" in e[0] for e in stopping.status.events)

    assert all(digest(path) == fingerprints[path] for path in paths)
    print("PASS mocked live batches 10/10 and 300/300, progress,"
          " corrupt input recovery, stop-after-current, original preservation")
