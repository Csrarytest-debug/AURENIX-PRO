
import io
import sys
import threading
from pathlib import Path

from PIL import Image, ImageOps, ImageDraw, ImageEnhance, ImageFilter
from rembg import remove, new_session

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel,
    QPushButton, QListWidget, QFileDialog,
    QVBoxLayout, QHBoxLayout, QSplitter,
    QProgressBar, QComboBox, QSpinBox,
    QMessageBox, QScrollArea, QGroupBox,
    QColorDialog, QCheckBox
)

APP_NAME = "AURENIX PRO"
WIDTH = 1080
HEIGHT = 810
DPI = 400

SUPPORTED = {
    ".jpg", ".jpeg", ".png", ".webp",
    ".bmp", ".tif", ".tiff"
}


def valid_image(path):
    p = Path(path)
    return (
        p.suffix.lower() in SUPPORTED
        and "__MACOSX" not in p.parts
        and not p.name.startswith("._")
        and p.is_file()
    )


def output_filename(folder, name):
    folder = Path(folder)
    candidate = folder / (name + ".png")
    counter = 2

    while candidate.exists():
        candidate = folder / (
            f"{name}_{counter}.png"
        )
        counter += 1

    return candidate


def resize_image(image, width, height):
    image = image.convert("RGBA")

    fitted = ImageOps.contain(
        image,
        (width, height),
        Image.Resampling.LANCZOS
    )

    result = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0)
    )

    x = (width - fitted.width) // 2
    y = (height - fitted.height) // 2

    result.alpha_composite(fitted, (x, y))

    return result


def image_to_pixmap(image, checker=False):
    image = image.convert("RGBA")

    if checker:
        background = Image.new(
            "RGBA", image.size, "#eeeeee"
        )

        draw = ImageDraw.Draw(background)
        tile = 20

        for y in range(0, image.height, tile):
            for x in range(0, image.width, tile):
                if (x // tile + y // tile) % 2:
                    draw.rectangle(
                        (x, y, x + tile - 1, y + tile - 1),
                        fill="#cccccc"
                    )

        background.alpha_composite(image)
        image = background

    data = image.tobytes("raw", "RGBA")

    qimage = QImage(
        data,
        image.width,
        image.height,
        image.width * 4,
        QImage.Format.Format_RGBA8888
    ).copy()

    return QPixmap.fromImage(qimage)


class BatchWorker(QThread):
    progress = Signal(int, int)
    completed = Signal(str, str)
    failed = Signal(str, str)
    status = Signal(str)

    def __init__(
        self, images, output_dir, width, height,
        mode="offline", api_key="", color_boost=100,
        transparent=False, sharpness=False, denoise=False,
        detail=False, quality="High"
    ):
        super().__init__()

        self.images = list(images)
        self.output_dir = Path(output_dir)
        self.width = width
        self.height = height
        self.mode = mode
        self.api_key = api_key
        self.color_boost = color_boost
        self.transparent = transparent
        self.sharpness = sharpness
        self.denoise = denoise
        self.detail = detail
        self.quality = quality

        self.resume_event = threading.Event()
        self.resume_event.set()

        self.stop_event = threading.Event()

    def pause(self):
        self.resume_event.clear()
        self.status.emit("Pause requested")

    def resume(self):
        self.resume_event.set()
        self.status.emit("Processing resumed")

    def stop(self):
        self.stop_event.set()
        self.resume_event.set()
        self.status.emit("Stopping after current image")

    def run(self):
        try:
            self.output_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            if self.mode == "offline":
                self.status.emit("Loading local BiRefNet model...")
                session = new_session("birefnet-general")
            else:
                # requests is only loaded when cloud mode is explicitly selected.
                import requests
                session = None
                self.status.emit("Live AI: ready to upload selected images")

        except Exception as error:
            self.failed.emit(
                "AI initialization",
                str(error)
            )
            return

        total = len(self.images)

        for index, image_path in enumerate(self.images):
            if self.stop_event.is_set():
                break

            if not self.resume_event.is_set():
                self.status.emit("Paused")

            self.resume_event.wait()

            if self.stop_event.is_set():
                break

            try:
                self.status.emit(
                    f"Processing image {index + 1}/{total}"
                )

                with Image.open(image_path) as img:
                    img = ImageOps.exif_transpose(img)
                    img = img.convert("RGBA")

                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG")

                if self.mode == "live":
                    # Images leave this PC ONLY when the user selected Live AI.
                    import requests
                    with open(image_path, "rb") as image_file:
                        response = requests.post(
                            "https://api.remove.bg/v1.0/removebg",
                            headers={"X-Api-Key": self.api_key},
                            files={"image_file": (
                                Path(image_path).name, image_file
                            )},
                            data={"size": "auto"},
                            timeout=(15, 180),
                        )
                    if response.status_code != 200:
                        raise RuntimeError(
                            "Live AI service returned HTTP "
                            + str(response.status_code)
                            + ". Check API credits, key, connection, and image format."
                        )
                    result_data = response.content
                else:
                    result_data = remove(
                        buffer.getvalue(),
                        session=session
                    )

                with Image.open(
                    io.BytesIO(result_data)
                ) as processed:
                    result = processed.convert("RGBA")

                result = resize_image(
                    result,
                    self.width,
                    self.height
                )

                # Color boost affects foreground before white compositing.
                if self.color_boost != 100:
                    alpha = result.getchannel("A")
                    rgb = ImageEnhance.Color(
                        result.convert("RGB")
                    ).enhance(self.color_boost / 100.0)
                    result = rgb.convert("RGBA")
                    result.putalpha(alpha)

                # Optional image enhancement; preserve the alpha mask.
                if self.denoise or self.sharpness or self.detail:
                    alpha = result.getchannel("A")
                    rgb = result.convert("RGB")
                    if self.denoise:
                        rgb = rgb.filter(ImageFilter.MedianFilter(size=3))
                    if self.sharpness:
                        rgb = ImageEnhance.Sharpness(rgb).enhance(
                            1.25 if self.quality == "High" else 1.5
                        )
                    if self.detail:
                        rgb = rgb.filter(ImageFilter.UnsharpMask(
                            radius=1.2, percent=115 if self.quality == "High" else 160,
                            threshold=3
                        ))
                    result = rgb.convert("RGBA")
                    result.putalpha(alpha)

                # User-selectable PNG alpha or pure-white background.
                if not self.transparent:
                    white = Image.new("RGBA", result.size, "#FFFFFF")
                    white.alpha_composite(result)
                    result = white.convert("RGB")

                output = output_filename(
                    self.output_dir,
                    Path(image_path).stem
                )

                temp_file = output.with_suffix(".part")

                try:
                    result.save(
                        temp_file,
                        format="PNG",
                        dpi=(DPI, DPI)
                    )
                    temp_file.replace(output)
                finally:
                    if temp_file.exists():
                        temp_file.unlink()

                self.completed.emit(
                    image_path,
                    str(output)
                )

            except Exception as error:
                self.failed.emit(
                    image_path,
                    str(error)
                )

            self.progress.emit(index + 1, total)

        if self.stop_event.is_set():
            self.status.emit("Batch stopped")
        else:
            self.status.emit("Batch completed")


class EditablePreview(QLabel):
    changed = Signal()

    def __init__(self):
        super().__init__()

        self.original = None
        self.processed = None
        self.tool = "View"
        self.brush_size = 25
        self.zoom = 1.0

        self.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.setStyleSheet(
            "background:#0b1420;"
        )
        self.setMinimumSize(300, 300)

    def set_images(self, original, processed):
        self.original = original
        self.processed = processed
        self.refresh()

    def refresh(self):
        if self.processed is None:
            self.clear()
            return

        image = self.processed

        scale = min(
            650 / max(1, image.width),
            600 / max(1, image.height),
            1.0
        ) * self.zoom

        width = max(1, int(image.width * scale))
        height = max(1, int(image.height * scale))

        self.setFixedSize(width, height)

        pixmap = image_to_pixmap(
            image, checker=True
        )

        self.setPixmap(
            pixmap.scaled(
                width,
                height,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )

    def mousePressEvent(self, event):
        self.edit_at(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.edit_at(event)

    def edit_at(self, event):
        if (
            self.processed is None
            or self.original is None
            or self.tool == "View"
        ):
            return

        x = int(
            event.position().x()
            * self.processed.width
            / max(1, self.width())
        )

        y = int(
            event.position().y()
            * self.processed.height
            / max(1, self.height())
        )

        if not (
            0 <= x < self.processed.width
            and 0 <= y < self.processed.height
        ):
            return

        radius = self.brush_size // 2

        mask = Image.new(
            "L",
            self.processed.size,
            0
        )

        draw = ImageDraw.Draw(mask)

        draw.ellipse(
            (
                x-radius, y-radius,
                x+radius, y+radius
            ),
            fill=255
        )

        if self.tool == "Erase":
            alpha = self.processed.getchannel("A")
            alpha.paste(0, (0, 0), mask)
            self.processed.putalpha(alpha)

        elif self.tool == "Restore":
            self.processed.paste(
                self.original,
                (0, 0),
                mask
            )

        self.refresh()
        self.changed.emit()


class BackgroundRemoverPro(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(APP_NAME)
        self.resize(1500, 900)

        self.images = []
        self.outputs = {}
        self.errors = set()
        self.worker = None
        self.loaded_source = None
        self.selected_path = None
        self.paused = False

        self.output_dir = (
            Path.home()
            / "Pictures"
            / "Background Remover Pro"
            / "Output"
        )

        self.build_interface()
        self.update_controls()

    def create_button(self, title, callback):
        button = QPushButton(title)
        button.clicked.connect(callback)
        return button

    def build_interface(self):
        self.setStyleSheet("""
            QWidget {
                background:#142131;
                color:#e6eef9;
                font-family:'Segoe UI';
                font-size:12px;
            }

            QPushButton {
                background:#263b55;
                border:1px solid #385576;
                border-radius:6px;
                padding:10px;
            }

            QPushButton:hover {
                background:#326198;
            }

            QPushButton:disabled {
                color:#66788b;
                background:#202b3b;
            }

            QListWidget {
                background:#0e1928;
                border:1px solid #33465e;
            }

            QScrollArea {
                background:#0b1420;
                border:1px solid #33465e;
            }

            QSpinBox, QComboBox {
                background:#23364d;
                padding:8px;
                border:1px solid #385576;
            }

            QGroupBox {
                border:1px solid #385576;
                border-radius:6px;
                margin-top:12px;
                padding:12px;
                font-weight:bold;
            }

            QProgressBar {
                background:#0c1826;
                border:1px solid #385576;
                text-align:center;                height:20px;
            }

            QProgressBar::chunk {
                background:#20ae83;
            }
        """)

        main = QWidget()
        self.setCentralWidget(main)

        root = QVBoxLayout(main)

        heading = QLabel(
            "BACKGROUND REMOVER PRO"
        )

        heading.setStyleSheet(
            "font-size:24px;"
            "font-weight:bold;"
            "color:#ffffff;"
        )

        root.addWidget(heading)

        subtitle = QLabel(
            "AI Background Removal  |  "
            "Batch Processing  |  "
            "Edit  |  Resize  |  Export"
        )

        subtitle.setStyleSheet(
            "color:#94aecb;"
        )

        root.addWidget(subtitle)

        toolbar = QHBoxLayout()
        root.addLayout(toolbar)

        toolbar.addWidget(
            self.create_button(
                "Import Images",
                self.import_images
            )
        )

        toolbar.addWidget(
            self.create_button(
                "Import Folder",
                self.import_folder
            )
        )

        toolbar.addWidget(
            self.create_button(
                "Output Folder",
                self.choose_output
            )
        )

        toolbar.addWidget(
            self.create_button(
                "Open Output",
                self.open_output
            )
        )

        splitter = QSplitter(
            Qt.Orientation.Horizontal
        )
        root.addWidget(splitter, 1)

        # LEFT PANEL
        left = QWidget()
        left_layout = QVBoxLayout(left)

        left_layout.addWidget(
            QLabel("IMAGE LIBRARY")
        )

        self.library = QListWidget()
        self.library.currentRowChanged.connect(
            self.select_image
        )

        left_layout.addWidget(self.library)

        self.count = QLabel("0 images loaded")
        left_layout.addWidget(self.count)

        splitter.addWidget(left)

        # CENTER PANEL
        center = QWidget()
        center_layout = QVBoxLayout(center)

        preview_layout = QHBoxLayout()
        center_layout.addLayout(
            preview_layout, 1
        )

        original_layout = QVBoxLayout()
        original_layout.addWidget(
            QLabel("ORIGINAL IMAGE")
        )

        self.original_preview = QLabel()
        self.original_preview.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.original_preview.setMinimumSize(250, 250)
        self.original_preview.setStyleSheet(
            "background:#0b1420;"
        )

        original_layout.addWidget(
            self.original_preview
        )

        preview_layout.addLayout(
            original_layout
        )

        treated_layout = QVBoxLayout()
        treated_layout.addWidget(
            QLabel("BACKGROUND REMOVED")
        )

        self.editor = EditablePreview()

        self.editor_scroll = QScrollArea()
        self.editor_scroll.setWidget(
            self.editor
        )

        treated_layout.addWidget(
            self.editor_scroll
        )

        preview_layout.addLayout(
            treated_layout
        )

        splitter.addWidget(center)

        # RIGHT PANEL
        right = QWidget()
        right_layout = QVBoxLayout(right)

        resize_group = QGroupBox(
            "OUTPUT IMAGE SIZE"
        )

        resize_layout = QVBoxLayout(
            resize_group
        )

        resize_layout.addWidget(
            QLabel("Width (Pixels)")
        )

        self.width_input = QSpinBox()
        self.width_input.setRange(1, 16000)
        self.width_input.setValue(WIDTH)
        resize_layout.addWidget(
            self.width_input
        )

        resize_layout.addWidget(
            QLabel("Height (Pixels)")
        )

        self.height_input = QSpinBox()
        self.height_input.setRange(1, 16000)
        self.height_input.setValue(HEIGHT)
        resize_layout.addWidget(
            self.height_input
        )

        resize_layout.addWidget(
            QLabel("Resolution: 400 PPI")
        )

        resize_layout.addWidget(
            QLabel("Default Format: Transparent PNG")
        )

        right_layout.addWidget(
            resize_group
        )

        editing_group = QGroupBox(
            "EDITING TOOLS"
        )

        editing_layout = QVBoxLayout(
            editing_group
        )

        self.tool_select = QComboBox()
        self.tool_select.addItems(
            ["View", "Erase", "Restore"]
        )

        self.tool_select.currentTextChanged.connect(
            self.change_tool
        )

        editing_layout.addWidget(
            self.tool_select
        )

        editing_layout.addWidget(
            QLabel("Brush Size")
        )

        self.brush_input = QSpinBox()
        self.brush_input.setRange(2, 250)
        self.brush_input.setValue(25)

        self.brush_input.valueChanged.connect(
            self.change_brush
        )

        editing_layout.addWidget(
            self.brush_input
        )

        editing_layout.addWidget(
            QLabel("Zoom (%)")
        )

        self.zoom_input = QSpinBox()
        self.zoom_input.setRange(10, 400)
        self.zoom_input.setValue(100)

        self.zoom_input.valueChanged.connect(
            self.change_zoom
        )

        editing_layout.addWidget(
            self.zoom_input
        )

        right_layout.addWidget(
            editing_group
        )

        self.save_btn = self.create_button(
            "SAVE EDITED PNG",
            self.save_edited
        )

        right_layout.addWidget(
            self.save_btn
        )

        right_layout.addStretch()

        splitter.addWidget(right)

        splitter.setSizes(
            [270, 900, 300]
        )

        # BATCH CONTROLS
        controls = QHBoxLayout()
        root.addLayout(controls)

        self.start_btn = self.create_button(
            "PROCESS ALL IMAGES",
            self.start_processing
        )

        self.pause_btn = self.create_button(
            "PAUSE",
            self.pause_processing
        )

        self.resume_btn = self.create_button(
            "RESUME",
            self.resume_processing
        )

        self.stop_btn = self.create_button(
            "STOP",
            self.stop_processing
        )

        self.retry_btn = self.create_button(
            "RETRY FAILED",
            self.retry_failed
        )

        for button in (
            self.start_btn,
            self.pause_btn,
            self.resume_btn,
            self.stop_btn,
            self.retry_btn
        ):
            controls.addWidget(button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        root.addWidget(
            self.progress_bar
        )

        self.output_label = QLabel(
            f"Output Folder: {self.output_dir}"
        )

        root.addWidget(
            self.output_label
        )

        self.statusBar().showMessage(
            "Ready"
        )

    def import_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            "Images (*.jpg *.jpeg *.png "
            "*.webp *.bmp *.tif *.tiff)"
        )

        self.add_images(files)

    def import_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Input Folder"
        )

        if not folder:
            return

        files = [
            str(p)
            for p in Path(folder).rglob("*")
            if valid_image(p)
        ]

        self.add_images(
            sorted(files)
        )

    def add_images(self, files):
        existing = set(self.images)

        for path in files:
            if valid_image(path) and path not in existing:
                self.images.append(path)
                existing.add(path)
                self.library.addItem(
                    Path(path).name
                )

        self.count.setText(
            f"{len(self.images)} images loaded"
        )

        if (
            self.images
            and self.library.currentRow() < 0
        ):
            self.library.setCurrentRow(0)

        self.update_controls()

    def current_image(self):
        row = self.library.currentRow()

        if 0 <= row < len(self.images):
            return self.images[row]

        return None

    def select_image(self, *_):
        path = self.current_image()
        self.selected_path = path

        if path is None:
            return

        try:
            with Image.open(path) as img:
                source = ImageOps.exif_transpose(
                    img
                ).convert("RGBA")

            thumb = source.copy()
            thumb.thumbnail((600, 600))

            self.original_preview.setPixmap(
                image_to_pixmap(thumb)
            )

            output = self.outputs.get(path)

            if output and Path(output).exists():
                with Image.open(output) as img:
                    processed = img.convert("RGBA")

                restored_source = resize_image(
                    source,
                    processed.width,
                    processed.height
                )

                self.editor.set_images(
                    restored_source,
                    processed
                )
            else:
                self.editor.set_images(
                    None, None
                )

        except Exception as error:
            self.statusBar().showMessage(
                str(error)
            )

        self.update_controls()

    def choose_output(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            str(self.output_dir)
        )

        if folder:
            self.output_dir = Path(folder)
            self.output_label.setText(
                f"Output Folder: {folder}"
            )

    def open_output(self):
        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_dir)))

    def start_worker(self, files):
        if not files or self.worker is not None:
            return

        self.errors.clear()
        self.paused = False

        self.progress_bar.setValue(0)

        mode = (
            "live"
            if getattr(self, "processing_mode", None) is not None
            and self.processing_mode.currentIndex() == 1
            else "offline"
        )
        api_key = ""
        if mode == "live":
            from PySide6.QtWidgets import QMessageBox
            key_widget = getattr(self, "live_api_key", None)
            api_key = key_widget.text().strip() if key_widget else ""
            if not api_key:
                QMessageBox.warning(
                    self, "Live AI setup",
                    "Enter your remove.bg API key before starting Live AI."
                )
                return
            approval = QMessageBox.question(
                self, "Send images to cloud AI?",
                f"Live AI will upload {len(files)} image(s) to remove.bg. "
                "This may use paid API credits. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if approval != QMessageBox.StandardButton.Yes:
                return

        self.worker = BatchWorker(
            files,
            self.output_dir,
            self.width_input.value(),
            self.height_input.value(),
            mode=mode,
            api_key=api_key,
            color_boost=getattr(
                getattr(self, "color_boost", None), "value",
                lambda: 100
            )(),
            transparent=(
                getattr(self, "output_format", None) is not None
                and self.output_format.currentIndex() == 0
            ),
            sharpness=(
                getattr(self, "sharpness_check", None) is not None
                and self.sharpness_check.isChecked()
            ),
            denoise=(
                getattr(self, "denoise_check", None) is not None
                and self.denoise_check.isChecked()
            ),
            detail=(
                getattr(self, "detail_check", None) is not None
                and self.detail_check.isChecked()
            ),
            quality=getattr(self, "quality", "High"),
        )

        self.worker.progress.connect(
            self.update_progress
        )

        self.worker.completed.connect(
            self.image_completed
        )

        self.worker.failed.connect(
            self.image_failed
        )

        self.worker.status.connect(
            self.statusBar().showMessage
        )

        self.worker.finished.connect(
            self.batch_finished
        )

        self.worker.start()
        self.update_controls()

    def start_processing(self):
        self.start_worker(
            self.images
        )

    def retry_failed(self):
        self.start_worker(
            sorted(self.errors)
        )

    def pause_processing(self):
        if self.worker:
            self.worker.pause()
            self.paused = True
            self.update_controls()

    def resume_processing(self):
        if self.worker:
            self.worker.resume()
            self.paused = False
            self.update_controls()

    def stop_processing(self):
        if self.worker:
            self.worker.stop()
            self.update_controls()

    def update_progress(self, done, total):
        percentage = round(
            done * 100 / total
        )

        self.progress_bar.setValue(
            percentage
        )

        self.count.setText(
            f"{done} of {total} images attempted"
        )

    def image_completed(self, source, output):
        self.outputs[source] = output

        if self.current_image() == source:
            self.select_image()

    def image_failed(self, source, error):
        self.errors.add(source)

        self.statusBar().showMessage(
            f"Error: {Path(source).name}: {error}"
        )

    def batch_finished(self):
        self.worker = None
        self.paused = False
        self.update_controls()

    def change_tool(self, value):
        self.editor.tool = value

    def change_brush(self, value):
        self.editor.brush_size = value

    def change_zoom(self, value):
        self.editor.zoom = value / 100
        self.editor.refresh()

    def save_edited(self):
        path = self.current_image()

        if (
            path is None
            or self.editor.processed is None
        ):
            return

        output = self.outputs.get(path)

        if not output:
            return

        self.editor.processed.save(
            output,
            format="PNG",
            dpi=(DPI, DPI)
        )

        self.statusBar().showMessage(
            f"Saved: {output}"
        )

    def update_controls(self):
        running = self.worker is not None

        self.start_btn.setEnabled(
            bool(self.images) and not running
        )

        self.pause_btn.setEnabled(
            running and not self.paused
        )

        self.resume_btn.setEnabled(
            running and self.paused
        )

        self.stop_btn.setEnabled(
            running
        )
        if hasattr(self, "processing_mode"):
            self.processing_mode.setEnabled(not running)
        if hasattr(self, "live_api_key"):
            self.live_api_key.setEnabled(not running)
        if hasattr(self, "color_boost"):
            self.color_boost.setEnabled(not running)

        self.retry_btn.setEnabled(
            bool(self.errors) and not running
        )

        self.save_btn.setEnabled(
            self.current_image() in self.outputs
        )

    def closeEvent(self, event):
        if (
            self.worker
            and self.worker.isRunning()
        ):
            QMessageBox.warning(
                self,
                "Processing Active",
                "Stop processing before closing."
            )
            event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BackgroundRemoverPro()
    window.show()
    sys.exit(app.exec())