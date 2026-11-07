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
    assert window.windowTitle() == "AURENIX PRO — AI Background Remover"
    assert window.resource_label is not None
    assert "Dark Royal Gold Edition" not in window.windowTitle()
    assert window.output_format.currentIndex() == 0
    assert window.processing_mode.count() == 2
    assert window.output_format.count() == 3
    assert window.output_format.currentIndex() == 0  # White is default.
    assert window.background_color_hex == "#FFFFFF"
    assert not window.custom_color_button.isVisible()
    window.output_format.setCurrentIndex(1)
    assert not window.custom_color_button.isHidden()
    window.output_format.setCurrentIndex(2)
    assert window.custom_color_button.isHidden()
    window.output_format.setCurrentIndex(0)
    assert window.resolution_preset.count() == 5
    assert (window.width_input.value(), window.height_input.value()) == (1080, 810)
    assert not window.width_input.isEnabled()
    for index, expected in (
        (1, (1280, 720)), (2, (1920, 1080)), (3, (3840, 2160))
    ):
        window.resolution_preset.setCurrentIndex(index)
        assert (window.width_input.value(), window.height_input.value()) == expected
    window.resolution_preset.setCurrentIndex(4)
    assert window.width_input.isEnabled() and window.height_input.isEnabled()
    window.width_input.setValue(1234)
    window.height_input.setValue(987)
    assert (window.width_input.value(), window.height_input.value()) == (1234, 987)
    window.resolution_preset.setCurrentIndex(0)
    assert (window.width_input.value(), window.height_input.value()) == (1080, 810)
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
    # Test transparent, default white, and custom-color PNG exports.
    # Segmentation is mocked; this does not test model quality.
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
            for label, transparent, background_color in (
                ("white", False, "#FFFFFF"),
                ("custom", False, "#2277CC"),
                ("alpha", True, "#FFFFFF"),
            ):
                target = base / label
                worker = backend.BatchWorker(
                    [str(source)], target, 1080, 810,
                    transparent=transparent, background_color=background_color,
                    sharpness=True, denoise=True, detail=True, quality="High"
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
                        from PIL import ImageColor
                        assert image.mode == "RGB"
                        assert image.getpixel((0, 0)) == ImageColor.getrgb(background_color)
            print("[PASS] PNG white/custom/alpha exports, dimensions and DPI")
    finally:
        backend.new_session, backend.remove = orig_session, orig_remove


if __name__ == "__main__":
    test_gui()
    test_export()
