"""AURENIX PRO headless GUI startup and image-library smoke tests."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import unittest
from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import QApplication

from aurenix_pro import AurenixPro


class TestAurenixGui(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = AurenixPro()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.window.close)

    def test_initializes_all_callbacks(self):
        self.assertEqual(self.window.windowTitle(), "AURENIX PRO")
        self.assertTrue(callable(self.window.remove_selected_image))
        self.assertTrue(callable(self.window.clear_image_library))
        self.assertFalse(self.window.start_btn.isEnabled())

    def test_remove_and_clear_preserve_source_files(self):
        folder = Path(self.temp.name)
        paths = [folder / "sample1.png", folder / "sample2.png"]
        for path in paths:
            Image.new("RGB", (80, 60), "white").save(path)

        self.window.add_images([str(p) for p in paths])
        self.assertEqual(len(self.window.images), 2)
        self.window.library.setCurrentRow(0)
        self.window.remove_selected_image()
        self.assertEqual(len(self.window.images), 1)
        self.assertTrue(all(p.is_file() for p in paths))
        self.window.clear_image_library()
        self.assertEqual(self.window.images, [])
        self.assertEqual(self.window.library.count(), 0)
        self.assertFalse(self.window.start_btn.isEnabled())
        self.assertTrue(all(p.is_file() for p in paths))

    def test_cannot_change_library_while_worker_active(self):
        self.window.worker = object()
        self.window.remove_selected_image()
        self.window.clear_image_library()
        self.assertEqual(self.window.images, [])
        self.window.worker = None


if __name__ == "__main__":
    unittest.main()
