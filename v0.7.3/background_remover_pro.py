
import io
import sys
import os
import threading
import time
import gc
from pathlib import Path

from PIL import Image, ImageOps, ImageDraw
# Load rembg/ONNX only after Start Processing, never during GUI startup.
from diagnostics import record_error
from image_export import save_image_atomic, unique_output_path, normalized_format

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

# Keep DLL directory handles alive for the lifetime of the process.
_CUDA_DLL_HANDLES = []
_CUDA_DLL_READY = False


def register_cuda_libraries():
    """Expose CUDA/cuDNN runtime DLLs installed in the active environment."""
    global _CUDA_DLL_READY
    if _CUDA_DLL_READY or os.name != "nt":
        return

    import site
    candidates = []
    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        candidates.extend([Path(cuda_path) / "bin" / "x64", Path(cuda_path) / "bin"])

    # PyInstaller bundles wheels under _MEIPASS; development wheels live in
    # site-packages. Search both CUDA 12 and 13 layouts without a hardcoded
    # toolkit installation path.
    roots = [Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))]
    try:
        roots.extend(Path(p) for p in site.getsitepackages())
    except (AttributeError, OSError):
        pass
    roots.append(Path(site.getusersitepackages()))
    for root in roots:
        for name in ("nvidia", "nvidia_cudnn_cu12", "nvidia_cudnn_cu13",
                     "nvidia_cublas", "nvidia_cuda_runtime", "nvidia_cuda_nvrtc"):
            package = root / name
            if package.is_dir():
                candidates.extend(dll.parent for dll in package.rglob("*.dll"))

    for directory in dict.fromkeys(candidates):
        if directory.is_dir():
            _CUDA_DLL_HANDLES.append(os.add_dll_directory(str(directory)))
    _CUDA_DLL_READY = True


def verify_cudnn_runtime():
    """Fail before inference if the CUDA provider cannot find cuDNN 9."""
    if os.name != "nt":
        return
    import ctypes
    try:
        ctypes.WinDLL("cudnn64_9.dll")
    except OSError as exc:
        raise RuntimeError(
            "GPU processing requires cuDNN 9 (cudnn64_9.dll), which Windows cannot load. "
            "Install a compatible NVIDIA cuDNN 9 runtime and make its bin folder "
            "visible to this process, then restart AURENIX. No images were modified."
        ) from exc


APP_NAME = "AURENIX PRO BG Remover V0.7.3"
# Cache model sessions across sequential batches to avoid repeated heavy initialization.
_SESSION_CACHE = {}
_SESSION_LOCK = threading.Lock()
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
        self, images, output_dir, width, height
    ):
        super().__init__()

        self.images = list(images)
        self.output_dir = Path(output_dir)
        self.width = width
        self.height = height
        self.bg_mode = "white"
        self.bg_color = "#ffffff"
        self.export_format = "PNG"
        self.export_quality = 95
        self.export_dpi = DPI
        self.model_name = os.environ.get("AURENIX_MODEL", "u2net").strip().lower()
        self.auto_wire_cleanup = True

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

            # Reject extreme output dimensions before allocating large RGBA buffers.
            if self.width * self.height > 16_000_000:
                raise MemoryError("Output exceeds the safe 16-megapixel processing limit. Reduce width or height.")
            # Check host memory BEFORE loading the large model, not only per image.
            try:
                import psutil
                memory = psutil.virtual_memory()
                if memory.percent >= 85 or memory.available < 2 * 1024**3:
                    raise MemoryError(
                        f"System RAM is already {memory.percent:.0f}% used. "
                        "Close memory-heavy programs before starting BiRefNet."
                    )
            except ImportError:
                pass
            self.status.emit("Loading AI model...")
            model = self.model_name
            if model not in ("birefnet-general", "u2net"):
                raise ValueError("AURENIX_MODEL must be birefnet-general or u2net")
            if model == "birefnet-general":
                # High-quality model can exhaust 16 GB PCs, especially on 6 GB GPUs.
                try:
                    import psutil
                    if psutil.virtual_memory().available < 12 * 1024**3:
                        raise MemoryError("BiRefNet requires at least 12 GB free RAM in safe mode. Use the default u2net model.")
                except ImportError:
                    raise RuntimeError("psutil is required for safe BiRefNet memory checks")
            self.status.emit(f"Loading AI model: {model}")
            # Heavy inference libraries are imported ONLY inside this worker thread.
            from rembg import remove, new_session
            with _SESSION_LOCK:
                session = _SESSION_CACHE.get(model)
                if session is None:
                    register_cuda_libraries()
                    import onnxruntime as ort
                    if hasattr(ort, 'preload_dlls'):
                        # ONNX Runtime 1.21+ supports loading NVIDIA pip-wheel
                        # CUDA/cuDNN DLLs before the CUDA provider starts.
                        try:
                            ort.preload_dlls(directory='')
                        except Exception as exc:
                            record_error('CUDA DLL preload warning', exc)
                    available = ort.get_available_providers()
                    requested = (["CUDAExecutionProvider", "CPUExecutionProvider"]
                                 if "CUDAExecutionProvider" in available
                                 else ["CPUExecutionProvider"])
                    if "CUDAExecutionProvider" in requested:
                        verify_cudnn_runtime()
                    session = new_session(model, providers=requested)
                    active = session.inner_session.get_providers()
                    if "CUDAExecutionProvider" in requested and "CUDAExecutionProvider" not in active:
                        raise RuntimeError("CUDA provider failed to initialize; CPU fallback refused. Check CUDA/cuDNN DLLs.")
                    _SESSION_CACHE[model] = session
            providers = getattr(session, "inner_session", None)
            if providers is not None and hasattr(providers, "get_providers"):
                self.status.emit("AI execution provider: " + ", ".join(providers.get_providers()))

        except Exception as error:
            record_error("AI initialization", error)
            self.failed.emit(
                "AI initialization",
                str(error)
            )
            return

        total = len(self.images)
        batch_start = time.perf_counter()
        succeeded = 0
        failed_count = 0

        for index, image_path in enumerate(self.images):
            if self.stop_event.is_set():
                break

            if not self.resume_event.is_set():
                self.status.emit("Paused")

            self.resume_event.wait()

            if self.stop_event.is_set():
                break

            try:
                # Avoid worsening an already exhausted 16 GB machine.
                try:
                    import psutil
                    if (psutil.virtual_memory().percent >= 85 or
                            psutil.virtual_memory().available < 2 * 1024**3):
                        raise MemoryError(
                            "System RAM is near its safety limit. Batch stopped to prevent "
                            "Windows from becoming unresponsive. Close other memory-heavy "
                            "programs or use a lighter model before retrying."
                        )
                except ImportError:
                    pass
                image_start = time.perf_counter()
                self.status.emit(f"Processing image {index + 1}/{total}")

                # rembg accepts a Pillow image directly. Avoid the expensive
                # RGBA -> PNG encode -> PNG decode -> RGBA round-trip.
                with Image.open(image_path) as source:
                    # Decode only a bounded working image. Preserve source files.
                    source.draft("RGB", (3200, 3200))
                    source_image = ImageOps.exif_transpose(source)
                    if source_image.width * source_image.height > 8_000_000:
                        from math import sqrt
                        factor = sqrt(8_000_000 / (source_image.width * source_image.height))
                        source_image.thumbnail((max(1, int(source_image.width * factor)),
                                                max(1, int(source_image.height * factor))),
                                               Image.Resampling.LANCZOS)
                    if source_image.mode not in ("RGB", "RGBA"):
                        source_image = source_image.convert("RGB")
                    source_image.load()

                result = remove(source_image, session=session)
                if not isinstance(result, Image.Image):
                    raise TypeError("AI model returned an unexpected image type")
                result = result.convert("RGBA")
                if self.auto_wire_cleanup:
                    # Only trim thin, exposed alpha-mask strands. No second AI
                    # model, no extra GPU memory and no edits to product RGB.
                    from wire_cleanup import remove_loose_wires
                    result, removed_pixels = remove_loose_wires(result)
                    self.status.emit(
                        f"Loose-wire cleanup: {removed_pixels} foreground pixels removed "
                        "(conservative mode)"
                    )

                result = resize_image(result, self.width, self.height)

                if self.bg_mode != "transparent":
                    background = Image.new(
                        "RGBA", result.size,
                        self.bg_color if self.bg_mode == "custom" else "#ffffff"
                    )
                    background.alpha_composite(result)
                    result = background

                output = unique_output_path(
                    self.output_dir, Path(image_path).stem, self.export_format
                )
                save_image_atomic(
                    result, output, self.export_format,
                    self.export_dpi, self.export_quality,
                    self.bg_color if self.bg_mode == "custom" else "#ffffff"
                )
                succeeded += 1
                self.completed.emit(image_path, str(output))
                elapsed = time.perf_counter() - image_start
                del source_image, result
                gc.collect()
                self.status.emit(
                    f"Saved {index + 1}/{total} | {elapsed:.1f}s/image | "
                    f"{succeeded} saved, {failed_count} failed"
                )

            except Exception as error:
                failed_count += 1
                record_error(f"Image processing failed: {Path(image_path).name}", error)
                self.failed.emit(image_path, str(error))
                if isinstance(error, MemoryError):
                    self.stop_event.set()
                gc.collect()

            self.progress.emit(index + 1, total)

        elapsed = time.perf_counter() - batch_start
        summary = (
            f"{succeeded} saved, {failed_count} failed / {total} queued "
            f"in {elapsed:.1f}s"
        )
        if self.stop_event.is_set():
            self.status.emit("Batch stopped | " + summary)
        else:
            self.status.emit("Batch completed | " + summary)

        # Drop the heavyweight ONNX session after each batch to avoid keeping
        # GPU/host allocations alive while the application is idle.
        with _SESSION_LOCK:
            _SESSION_CACHE.pop(model, None)
        del session
        gc.collect()


class EditablePreview(QLabel):
    changed = Signal()

    def __init__(self):
        super().__init__()

        self.original = None
        self.processed = None
        self.tool = "View"
        self.brush_size = 25
        self.zoom = 1.0
        self.wire_mask = None
        self.wire_undo = None

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
        self.wire_mask = Image.new("L", processed.size, 0) if processed is not None else None
        self.wire_undo = None
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

        if self.tool == "Wire Mask":
            if self.wire_mask is None:
                self.wire_mask = Image.new("L", self.processed.size, 0)
            self.wire_mask.paste(255, (0, 0), mask)

        elif self.tool == "Erase":
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

    def apply_wire_cleanup(self):
        """User-guided local inpainting; not automatic cable detection."""
        if self.processed is None or self.wire_mask is None or not self.wire_mask.getbbox():
            raise ValueError("Choose Wire Mask and paint over unwanted cables first.")
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("Wire cleanup needs opencv-python-headless and numpy.") from exc
        self.wire_undo = self.processed.copy()
        rgba = np.array(self.processed.convert("RGBA"))
        mask = np.array(self.wire_mask)
        # Inpaint RGB while keeping existing alpha; user can use Erase for transparent cutouts.
        rgb = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2BGR)
        filled = cv2.inpaint(rgb, mask, 3, cv2.INPAINT_TELEA)
        rgba[:, :, :3] = cv2.cvtColor(filled, cv2.COLOR_BGR2RGB)
        self.processed = Image.fromarray(rgba, "RGBA")
        self.wire_mask = Image.new("L", self.processed.size, 0)
        self.refresh()
        self.changed.emit()

    def undo_wire_cleanup(self):
        if self.wire_undo is None:
            raise ValueError("No wire cleanup to undo.")
        self.processed = self.wire_undo
        self.wire_undo = None
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
                text-align:center;
                height:20px;
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
                img.draft("RGB", (1200, 1200))
                source = ImageOps.exif_transpose(img)
                source.thumbnail((1200, 1200))
                source = source.convert("RGBA")

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

        import os
        os.startfile(
            str(self.output_dir)
        )

    def start_worker(self, files):
        if not files or self.worker is not None:
            return

        self.errors.clear()
        self.paused = False

        self.progress_bar.setValue(0)

        # Never run ONNX/CUDA in the GUI process. Native inference failures
        # must be confined to a disposable child process.
        from isolated_worker import IsolatedBatchWorker
        self.worker = IsolatedBatchWorker(
            files,
            self.output_dir,
            self.width_input.value(),
            self.height_input.value(),
            parent=self,
        )

        # Configure worker before start() to avoid a thread startup race.
        self.worker.bg_mode = getattr(self, "current_bg_mode", "white")
        self.worker.bg_color = getattr(self, "bg_color", "#ffffff")
        self.worker.export_format = getattr(self, "current_export_format", "PNG")
        self.worker.export_quality = getattr(self, "current_export_quality", 95)
        self.worker.export_dpi = getattr(self, "current_export_dpi", DPI)
        self.worker.auto_wire_cleanup = getattr(self, "current_auto_wire_cleanup", True)

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
        old_worker = self.worker
        self.worker = None
        self.paused = False
        self.update_controls()
        if old_worker is not None:
            old_worker.deleteLater()

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

        try:
            save_image_atomic(self.editor.processed, Path(output),
                              Path(output).suffix, getattr(self, "current_export_dpi", DPI),
                              getattr(self, "current_export_quality", 95),
                              getattr(self, "bg_color", "#ffffff"))
        except Exception as error:
            record_error("Edited output save failed", error)
            QMessageBox.warning(self, "Save Failed", str(error))
            return

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
