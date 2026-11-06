"""GUI and image-output smoke checks. Does not replace real-world image QC."""
import io
import os
import sys
import tempfile
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image
from PySide6.QtWidgets import QApplication
import background_remover_pro as backend
from aurenix_pro import RoyalGoldApp


def test_gui():
    app = QApplication.instance() or QApplication([])
    window = RoyalGoldApp()
    assert "Dark Royal Gold" in window.windowTitle()
    assert window.processing_mode.count() == 2
    assert window.output_format.count() == 2
    assert window.output_format.currentText() == "PNG (Transparent)"
    assert window.quality == "High"
    assert window.library.count() == 0
    assert window.start_btn.text().endswith("Process Images")
    # Capture a CI-rendered UI reference, not a claim of clean-PC verification.
    preview = Path("build-preview")
    preview.mkdir(parents=True, exist_ok=True)
    window.show()
    app.processEvents()
    assert window.grab().save(str(preview / "aurenix-royal-gold-ui.png"))
    window.close()
    print("[PASS] Royal Gold Qt interface, controls and preview screenshot")
    return app


def test_export():
    # No internet or model needed: mock only segmentation to test
    # transparent/white PNG export and post-processing behavior.
    orig_session, orig_remove = backend.new_session, backend.remove
    backend.new_session = lambda name: object()
    def fake_remove(image_bytes, session=None):
        image = Image.new("RGBA", (32, 32), (180, 30, 60, 255))
        for x in range(12):
            for y in range(32):
                image.putpixel((x, y), (0, 0, 0, 0))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
    backend.remove = fake_remove
    try:
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            source = base / "sample.jpg"
            Image.new("RGB", (32, 32), "red").save(source)
            for transparent in (True, False):
                target = base / ("alpha" if transparent else "white")
                worker = backend.BatchWorker(
                    [str(source)], target, 1080, 810,
                    transparent=transparent, sharpness=True,
                    denoise=True, detail=True, quality="High"
                )
                worker.run()
                output = target / "sample.png"
                assert output.exists(), output
                with Image.open(output) as image:
                    assert image.size == (1080, 810)
                    assert abs(image.info["dpi"][0] - 400) < 1
                    if transparent:
                        assert image.mode == "RGBA"
                        assert image.getchannel("A").getextrema()[0] == 0
                    else:
                        assert image.convert("RGB").getpixel((0, 0)) == (255, 255, 255)
            print("[PASS] PNG alpha/white exports, dimensions and DPI")
    finally:
        backend.new_session, backend.remove = orig_session, orig_remove


if __name__ == "__main__":
    test_gui()
    test_export()
