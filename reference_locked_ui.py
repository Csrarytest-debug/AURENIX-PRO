"""Screenshot-locked AURENIX PRO Windows workspace.
Qt widgets are wired to the existing processing engine; no fake metrics or demo processing.
"""
from pathlib import Path
import platform
import shutil
import time
import psutil
from PySide6.QtCore import Qt, QSize, QTimer, QProcess
from PySide6.QtGui import QPixmap, QColor, QIcon
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QListWidget, QComboBox, QSpinBox, QLineEdit, QCheckBox, QSlider,
    QProgressBar, QDialog, QDialogButtonBox, QColorDialog, QRadioButton,
    QButtonGroup, QScrollArea, QFormLayout, QMessageBox
)
from royal_gold_ui import RoyalGoldMixin
from background_remover_pro import WIDTH, HEIGHT

REFERENCE_STYLE = """
QMainWindow, QWidget { background:#04111d; color:#f5f8fc; font-family:'Segoe UI'; font-size:12px; }
QFrame#header { background:#02101d; border-bottom:2px solid #d99518; }
QFrame#navigation, QFrame#processing, QFrame#statusstrip { background:#031725; border-bottom:1px solid #aa7819; }
QFrame#panel { background:#031a2b; border:1px solid #1684a9; border-radius:10px; }
QFrame#settings { background:#031a2b; border:1px solid #1684a9; border-radius:10px; }
QFrame#meter { background:#041522; border:1px solid #d2a01e; border-radius:9px; }
QLabel#appname { color:#ffcb46; font-size:35px; font-weight:900; }
QLabel#section { color:white; font-size:14px; font-weight:700; }
QLabel#gold { color:#ffcd2c; font-weight:700; }
QLabel#metric { color:#35f438; font-size:19px; font-weight:800; }
QLabel#muted { color:#b9c6d2; }
QPushButton { color:#f7faff; background:#071f31; border:1px solid #196e8b; border-radius:8px; padding:8px; min-height:28px; font-weight:600; }
QPushButton:hover { border:1px solid #ffd242; background:#123047; }
QPushButton[accent="true"], QPushButton:checked { background:#ffca28; color:#0c1117; border:1px solid #ffed88; font-weight:800; }
QPushButton:disabled { color:#788593; background:#0c1c28; border:1px solid #243747; }
QListWidget { background:#041525; border:0; padding:4px; }
QListWidget::item:selected { border:2px solid #ffcd1c; border-radius:5px; background:#16344a; }
QScrollArea { background:white; border:0; }
QSpinBox, QComboBox, QLineEdit { background:#0a2436; color:white; border:1px solid #2587b1; border-radius:5px; padding:4px; min-height:22px; }
QProgressBar { background:#344250; border:0; border-radius:7px; min-height:17px; max-height:17px; }
QProgressBar::chunk { background:#ffce2b; border-radius:7px; }
QRadioButton::indicator { width:16px; height:16px; }
QRadioButton::indicator:checked { background:#ffce00; border:2px solid #fff6b1; border-radius:9px; }
QCheckBox::indicator:checked { background:#ffc928; }
QSlider::groove:horizontal { background:#304658; height:6px; }
QSlider::sub-page:horizontal { background:#ffc928; }
QSlider::handle:horizontal { background:#fff; width:12px; margin:-4px 0; border-radius:6px; }
"""

class ReferenceLockedMixin(RoyalGoldMixin):
    def _text(self, text, kind=None):
        widget = QLabel(text)
        if kind:
            widget.setObjectName(kind)
        return widget

    def _button(self, text, callback, accent=False):
        widget = QPushButton(text)
        widget.clicked.connect(callback)
        if accent:
            widget.setProperty("accent", True)
        return widget

    def _panel(self, name="panel"):
        widget = QFrame()
        widget.setObjectName(name)
        return widget

    def _nav_action(self, name):
        if name == "Background Remover":
            self.library.setFocus()
        elif name == "Batch Processing":
            self.library.setFocus()
        elif name == "Resize & Export":
            self.width_input.setFocus()
        elif name in ("Image Enhancer", "Tools", "Settings"):
            self._show_advanced(name)

    def _show_advanced(self, name):
        """Real advanced controls, without changing the approved main workspace."""
        dialog = QDialog(self)
        dialog.setWindowTitle("AURENIX PRO — " + name)
        dialog.resize(440, 540)
        layout = QVBoxLayout(dialog)
        layout.addWidget(self._text("AI Processing Engine", "section"))
        self.processing_mode.setParent(dialog)
        layout.addWidget(self.processing_mode)
        self.model_info.setParent(dialog)
        layout.addWidget(self.model_info)
        self.live_api_key.setParent(dialog)
        layout.addWidget(self.live_api_key)
        self.live_notice.setParent(dialog)
        layout.addWidget(self.live_notice)
        layout.addWidget(self._text("Processing Quality", "section"))
        quality = QComboBox(dialog)
        quality.addItems(["Standard", "High", "Ultra"])
        quality.setCurrentText(self.quality)
        quality.currentTextChanged.connect(self.set_quality)
        layout.addWidget(quality)
        layout.addWidget(self._text("Image Enhancement", "section"))
        for widget in (self.color_check, self.color_boost, self.sharpness_check,
                       self.denoise_check, self.detail_check):
            widget.setParent(dialog)
            layout.addWidget(widget)
        layout.addWidget(self._text("Retouching Tools", "section"))
        for widget in (self.tool_select, self.brush_input, self.zoom_input, self.save_btn):
            widget.setParent(dialog)
            layout.addWidget(widget)
        for widget in (self.pause_btn, self.resume_btn, self.retry_btn):
            widget.setParent(dialog)
            layout.addWidget(widget)
        layout.addWidget(self._button("Choose Output Folder", self.choose_output))
        layout.addWidget(self._button("Open Output Folder", self.open_output))
        layout.addWidget(self.output_label)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(dialog.reject)
        layout.addWidget(close)
        dialog.exec()
        # Widgets are returned to a persistent hidden owner, never destroyed with dialog.
        for widget in (self.processing_mode, self.model_info, self.live_api_key,
                       self.live_notice, self.color_check, self.color_boost,
                       self.sharpness_check, self.denoise_check, self.detail_check,
                       self.tool_select, self.brush_input, self.zoom_input,
                       self.save_btn, self.pause_btn, self.resume_btn,
                       self.retry_btn, self.output_label):
            widget.setParent(self._hidden_controls)
            widget.hide()

    def build_interface(self):
        self.setWindowTitle("AURENIX PRO — BS Broadcast")
        self.resize(1648, 928)
        self.setMinimumSize(1280, 720)
        self.setStyleSheet(REFERENCE_STYLE)
        self.quality = "High"
        self.batch_started_at = None
        if Path("D:/").is_dir():
            self.output_dir = Path("D:/AURENIX PRO/Output")
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._hidden_controls = QWidget(self)
        self._hidden_controls.hide()

        header = self._panel("header")
        header.setMinimumHeight(108)
        head = QHBoxLayout(header)
        head.setContentsMargins(20, 5, 20, 5)
        head.setSpacing(16)
        logo = QLabel()
        logo.setFixedSize(210, 94)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = Path(__file__).resolve().parent / "assets" / "bs_broadcast_logo.png"
        if logo_path.is_file():
            pixmap = QPixmap(str(logo_path))
            if not pixmap.isNull():
                logo.setPixmap(pixmap.scaled(205, 90, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation))
        if logo.pixmap() is None or logo.pixmap().isNull():
            logo.setText("BS\nBROADCAST")
            logo.setStyleSheet("font-size:21px;color:#47bfff;font-weight:900;")
            logo.setToolTip("Approved logo image asset not yet bundled")
        head.addWidget(logo)
        divider = QFrame()
        divider.setFixedWidth(3)
        divider.setStyleSheet("background:#ffcb36;")
        head.addWidget(divider)
        head.addWidget(self._text("AURENIX PRO", "appname"), 1)

        self.gpu_meter = self._panel("meter")
        self.gpu_meter.setFixedSize(235, 73)
        gm = QVBoxLayout(self.gpu_meter)
        gm.setContentsMargins(10, 5, 10, 5)
        gm.addWidget(self._text("◉  GPU Process", "section"))
        self.gpu_value = self._text("Checking…", "metric")
        gm.addWidget(self.gpu_value)
        head.addWidget(self.gpu_meter)
        self.ram_meter = self._panel("meter")
        self.ram_meter.setFixedSize(230, 73)
        rm = QVBoxLayout(self.ram_meter)
        rm.setContentsMargins(10, 5, 10, 5)
        rm.addWidget(self._text("▣  RAM Process", "section"))
        self.ram_value = self._text("Checking…", "metric")
        rm.addWidget(self.ram_value)
        head.addWidget(self.ram_meter)
        root.addWidget(header)

        navigation = self._panel("navigation")
        nav = QHBoxLayout(navigation)
        nav.setContentsMargins(12, 9, 12, 9)
        nav.setSpacing(12)
        for index, label in enumerate(("Background Remover", "Batch Processing",
                                        "Image Enhancer", "Resize & Export",
                                        "Tools", "Settings")):
            b = self._button(label, lambda checked=False, key=label: self._nav_action(key),
                             accent=index == 0)
            b.setMinimumHeight(42)
            nav.addWidget(b, 1)
        root.addWidget(navigation)

        body = QHBoxLayout()
        body.setContentsMargins(8, 9, 8, 8)
        body.setSpacing(10)
        root.addLayout(body, 1)

        # Left sidebar: action buttons AND vertical image list, exactly as reference.
        left = self._panel()
        left.setFixedWidth(213)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(8, 8, 8, 8)
        ll.setSpacing(8)
        for label, callback, accent in (
            ("▣  Add Images", self.import_images, True),
            ("▱  Add Folder", self.import_folder, False),
            ("▤  Remove", self.remove_selected_image, False),
            ("×  Clear All", self.clear_image_library, False),
        ):
            ll.addWidget(self._button(label, callback, accent))
        self.count = self._text("Image List (0)", "section")
        ll.addWidget(self.count)
        self.library = QListWidget()
        self.library.setViewMode(QListWidget.ViewMode.IconMode)
        self.library.setFlow(QListWidget.Flow.TopToBottom)
        self.library.setWrapping(False)
        self.library.setMovement(QListWidget.Movement.Static)
        self.library.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.library.setIconSize(QSize(110, 78))
        self.library.setGridSize(QSize(180, 108))
        self.library.currentRowChanged.connect(self.select_image)
        ll.addWidget(self.library, 1)
        body.addWidget(left)

        # Two equal, large, full-image safe-fit preview monitors.
        for which in ("original", "output"):
            frame = self._panel()
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(2, 3, 2, 3)
            fl.setSpacing(0)
            top = QHBoxLayout()
            top.setContentsMargins(10, 4, 10, 4)
            title = "▣  Original Image" if which == "original" else "▣  Output (Background Removed)"
            top.addWidget(self._text(title, "section"))
            top.addStretch()
            top.addWidget(self._text("1080 × 810  |  " + ("JPG" if which == "original" else "PNG"), "muted"))
            fl.addLayout(top)
            if which == "original":
                self.original_preview = self.FitPreviewClass()
                self.original_preview.setStyleSheet("background:#15212d;")
                fl.addWidget(self.original_preview, 1)
            else:
                self.editor = self.EditablePreviewClass()
                self.editor_scroll = self.ScrollAreaClass()
                self.editor_scroll.setWidget(self.editor)
                self.editor_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.editor_scroll.viewport().setStyleSheet("background:#ffffff;")
                fl.addWidget(self.editor_scroll, 1)
            zoom = QHBoxLayout()
            zoom.setContentsMargins(5, 4, 5, 4)
            zoom.addStretch()
            zoom.addWidget(self._button("−", lambda: self._change_zoom(-10)))
            zlabel = self._text("100%", "section")
            if which == "original":
                self.original_zoom_label = zlabel
            else:
                self.output_zoom_label = zlabel
            zoom.addWidget(zlabel)
            zoom.addWidget(self._button("+", lambda: self._change_zoom(10)))
            zoom.addWidget(self._button("⛶", self._fit_zoom))
            zoom.addStretch()
            fl.addLayout(zoom)
            body.addWidget(frame, 1)

        # Right-side output controls, with selected radio buttons as in reference.
        right = self._panel("settings")
        right.setFixedWidth(330)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(12, 9, 12, 9)
        rl.setSpacing(8)
        rl.addWidget(self._text("⚙  Output Settings", "section"))
        rl.addWidget(self._text("▧  Image Resolution", "section"))
        self.resolution_preset = QComboBox(self._hidden_controls)
        self.resolution_preset.addItems(["Current — 1080 × 810 (Default)",
                                         "HD — 1280 × 720", "Full HD — 1920 × 1080",
                                         "4K UHD — 3840 × 2160", "Custom"])
        self.resolution_group = QButtonGroup(self)
        self.resolution_group.setExclusive(True)
        for index, label in ((1, "HD — 1280 × 720"), (2, "Full HD — 1920 × 1080"),
                             (0, "Current — 1080 × 810 (Default)"),
                             (3, "4K UHD — 3840 × 2160"), (4, "Custom — Custom Dimensions")):
            radio = QRadioButton(label)
            radio.setChecked(index == 0)
            radio.toggled.connect(lambda checked, i=index: checked and self.resolution_preset.setCurrentIndex(i))
            self.resolution_group.addButton(radio, index)
            rl.addWidget(radio)
        dimensions = QHBoxLayout()
        self.width_input = QSpinBox()
        self.width_input.setRange(1, 16000)
        self.width_input.setValue(WIDTH)
        self.width_input.setPrefix("W: ")
        self.height_input = QSpinBox()
        self.height_input.setRange(1, 16000)
        self.height_input.setValue(HEIGHT)
        self.height_input.setPrefix("H: ")
        dimensions.addWidget(self.width_input)
        dimensions.addWidget(self.height_input)
        rl.addLayout(dimensions)
        self.resolution_preset.currentIndexChanged.connect(self.update_resolution_preset)
        self.update_resolution_preset(0)
        rl.addSpacing(8)
        rl.addWidget(self._text("●  Color Scheme (Background)", "section"))
        self.output_format = QComboBox(self._hidden_controls)
        self.output_format.addItems(["PNG (Pure White #FFFFFF)", "PNG (Custom Color)",
                                      "PNG (Transparent)"])
        self.background_color_hex = "#FFFFFF"
        self.background_group = QButtonGroup(self)
        self.background_group.setExclusive(True)
        for index, label in enumerate(("Pure White (Default)", "Custom Background Color",
                                        "Transparent (PNG)")):
            row = QHBoxLayout()
            radio = QRadioButton(label)
            radio.setChecked(index == 0)
            radio.toggled.connect(lambda checked, i=index: checked and self.output_format.setCurrentIndex(i))
            self.background_group.addButton(radio, index)
            row.addWidget(radio)
            row.addStretch()
            if index == 0:
                swatch = self._text("■")
                swatch.setStyleSheet("color:white;font-size:23px;")
                row.addWidget(swatch)
            elif index == 1:
                self.custom_color_button = self._button("■", self.select_custom_background_color)
                self.custom_color_button.setStyleSheet("color:#219dff;")
                row.addWidget(self.custom_color_button)
            else:
                row.addWidget(self._text("▦"))
            rl.addLayout(row)
        rl.addStretch()
        self.output_format.currentIndexChanged.connect(self.update_background_option)
        body.addWidget(right)

        # Actual engine options live in the Tools/Settings dialog, not dummy controls.
        self.processing_mode = QComboBox(self._hidden_controls)
        self.processing_mode.addItems(["Offline AI (Local) — BiRefNet",
                                       "Live AI (Online) — remove.bg"])
        self.model_info = self._text("Model: BiRefNet General", "muted")
        self.model_info.setParent(self._hidden_controls)
        self.live_api_key = QLineEdit(self._hidden_controls)
        self.live_api_key.setPlaceholderText("remove.bg API key")
        self.live_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.live_notice = self._text("Online mode uploads images and may incur charges.", "muted")
        self.live_notice.setParent(self._hidden_controls)
        self.live_notice.setWordWrap(True)
        self.live_api_key.hide()
        self.live_notice.hide()
        self.processing_mode.currentIndexChanged.connect(
            lambda i: (self.live_api_key.setVisible(i == 1),
                       self.live_notice.setVisible(i == 1)))
        self.color_check = QCheckBox("Color Enhancement", self._hidden_controls)
        self.color_check.setChecked(True)
        self.color_boost = QSlider(Qt.Orientation.Horizontal, self._hidden_controls)
        self.color_boost.setRange(100, 200)
        self.color_boost.setValue(145)
        self.sharpness_check = QCheckBox("Sharpness Enhancement", self._hidden_controls)
        self.sharpness_check.setChecked(True)
        self.denoise_check = QCheckBox("Noise Reduction", self._hidden_controls)
        self.denoise_check.setChecked(True)
        self.detail_check = QCheckBox("Detail Recovery", self._hidden_controls)
        self.detail_check.setChecked(True)
        self.tool_select = QComboBox(self._hidden_controls)
        self.tool_select.addItems(["View", "Erase", "Restore"])
        self.tool_select.currentTextChanged.connect(self.change_tool)
        self.brush_input = QSpinBox(self._hidden_controls)
        self.brush_input.setRange(2, 250)
        self.brush_input.setValue(25)
        self.brush_input.valueChanged.connect(self.change_brush)
        self.zoom_input = QSpinBox(self._hidden_controls)
        self.zoom_input.setRange(10, 400)
        self.zoom_input.setValue(100)
        self.zoom_input.valueChanged.connect(self.change_zoom)
        self.save_btn = self._button("Save Edited PNG", self.save_edited)
        self.save_btn.setParent(self._hidden_controls)
        self.pause_btn = self._button("Pause", self.pause_processing)
        self.pause_btn.setParent(self._hidden_controls)
        self.resume_btn = self._button("Resume", self.resume_processing)
        self.resume_btn.setParent(self._hidden_controls)
        self.retry_btn = self._button("Retry Failed", self.retry_failed)
        self.retry_btn.setParent(self._hidden_controls)
        self.output_label = self._text("Output Folder: " + str(self.output_dir), "muted")
        self.output_label.setParent(self._hidden_controls)

        # Fixed screenshot-style bottom processing bar and status strip.
        processing = self._panel("processing")
        pr = QHBoxLayout(processing)
        pr.setContentsMargins(16, 8, 16, 8)
        self.start_btn = self._button("▶  Start Processing", self.start_processing, True)
        self.start_btn.setMinimumHeight(39)
        pr.addWidget(self.start_btn)
        self.stop_btn = self._button("■  Stop", self.stop_processing)
        pr.addWidget(self.stop_btn)
        progress_col = QVBoxLayout()
        self.processing_label = self._text("Ready to process images", "section")
        progress_col.addWidget(self.processing_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_col.addWidget(self.progress_bar)
        pr.addLayout(progress_col, 1)
        self.elapsed_label = self._text("Elapsed: 00:00:00\nRemaining: —", "muted")
        pr.addWidget(self.elapsed_label)
        root.addWidget(processing)
        status = self._panel("statusstrip")
        st = QHBoxLayout(status)
        st.setContentsMargins(20, 7, 20, 7)
        self.footer_text = self._text("AURENIX PRO    |    Mode: AI Precision    |    Output: PNG    |    Size: 1080 × 810    |    Background: White    |    Ready")
        st.addWidget(self.footer_text)
        root.addWidget(status)
        self.statusBar().showMessage("AURENIX PRO ready")

        # Asynchronous GPU query; system RAM from psutil. Never show made-up percentages.
        self.resource_label = QLabel(self._hidden_controls)
        self._gpu_text = "GPU: unavailable"
        self._gpu_process = QProcess(self)
        self._gpu_process.finished.connect(self._gpu_query_finished)
        self._gpu_executable = shutil.which("nvidia-smi")
        if not self._gpu_executable and platform.system() == "Windows":
            candidate = Path("C:/Program Files/NVIDIA Corporation/NVSMI/nvidia-smi.exe")
            if candidate.is_file():
                self._gpu_executable = str(candidate)
        self._resource_timer = QTimer(self)
        self._resource_timer.setInterval(3000)
        self._resource_timer.timeout.connect(self.refresh_resources)
        self._resource_timer.start()
        self.refresh_resources()

    def _change_zoom(self, step):
        self.zoom_input.setValue(max(10, min(400, self.zoom_input.value() + step)))
        self.original_preview.zoom_factor = self.zoom_input.value() / 100.0
        self.original_preview.fit_image()
        self.original_zoom_label.setText(str(self.zoom_input.value()) + "%")
        self.output_zoom_label.setText(str(self.zoom_input.value()) + "%")

    def _fit_zoom(self):
        self.zoom_input.setValue(100)
        self.original_preview.zoom_factor = 1.0
        self.original_preview.fit_image()
        self.original_zoom_label.setText("100%")
        self.output_zoom_label.setText("100%")

    def select_custom_background_color(self):
        old = self.background_color_hex
        super().select_custom_background_color()
        if self.background_color_hex != old:
            self.background_group.button(1).setChecked(True)

    def update_background_option(self, index):
        self.footer_text.setText(
            "AURENIX PRO    |    Mode: AI Precision    |    Output: PNG    |    Size: "
            + str(self.width_input.value()) + " × " + str(self.height_input.value())
            + "    |    Background: " + ("White" if index == 0 else "Custom" if index == 1 else "Transparent")
            + "    |    Ready")

    def refresh_resources(self):
        super().refresh_resources()
        ram = psutil.virtual_memory()
        self.ram_value.setText(f"{ram.percent:.0f}%   {ram.used / 2**30:.1f} / {ram.total / 2**30:.1f} GB")
        self.gpu_value.setText(self._gpu_text)

    def _gpu_query_finished(self, exit_code, exit_status):
        super()._gpu_query_finished(exit_code, exit_status)
        self.gpu_value.setText(self._gpu_text)

    def update_progress(self, done, total):
        super().update_progress(done, total)
        if self.batch_started_at is not None:
            elapsed = max(0, time.monotonic() - self.batch_started_at)
            rate = done / elapsed if elapsed > 0 and done else 0
            remain = (total - done) / rate if rate else None
            def fmt(seconds):
                return f"{int(seconds//3600):02d}:{int(seconds//60)%60:02d}:{int(seconds)%60:02d}"
            self.elapsed_label.setText("Elapsed: " + fmt(elapsed) +
                                       "\nRemaining: " + (fmt(remain) if remain is not None else "—"))
        self.footer_text.setText(f"AURENIX PRO    |    Mode: AI Precision    |    Output: PNG    |    Size: {self.width_input.value()} × {self.height_input.value()}    |    Background: {('White','Custom','Transparent')[self.output_format.currentIndex()]}    |    Processing {done}/{total}")
