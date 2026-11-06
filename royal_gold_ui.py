"""Approved AURENIX PRO Dark Royal Gold workspace.
Keeps the original processing, editing and image-library methods intact.
"""
from pathlib import Path
import time
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QListWidget, QComboBox, QSpinBox, QLineEdit, QCheckBox, QSlider,
    QButtonGroup, QMessageBox, QDialog, QDialogButtonBox
)
from background_remover_pro import WIDTH, HEIGHT, DPI


STYLE = """
QMainWindow, QWidget { background:#08111b; color:#edf0f5;
    font-family:'Segoe UI'; font-size:12px; }
QFrame#panel { background:#101b28; border:1px solid #364555; border-radius:8px; }
QFrame#top { background:#09121d; border-bottom:1px solid #68532c; }
QFrame#bar { background:#0d1825; border-bottom:1px solid #5b4a2b; }
QLabel#section { color:#f5f3ee; font-weight:700; font-size:13px; }
QLabel#muted { color:#a6b1bf; }
QPushButton { background:#192633; color:#edf0f5; border:1px solid #405064;
    border-radius:6px; padding:6px 8px; min-height:25px; }
QPushButton:hover { border-color:#edbd4c; background:#263748; }
QPushButton[accent="true"], QPushButton:checked {
    color:#171511; font-weight:700; background:#efb632; border:1px solid #ffdc83; }
QPushButton[tab="true"] { background:transparent; border:0; }
QPushButton[tab="true"]:checked { background:#745522; color:#fff0c6;
    border:1px solid #d8ab48; }
QPushButton:disabled { color:#778594; background:#14212c; border-color:#283847; }
QComboBox, QSpinBox, QLineEdit { background:#132231; color:#f4f4f5;
    border:1px solid #4c5b69; border-radius:5px; padding:5px; min-height:25px; }
QComboBox QAbstractItemView { background:#132231; color:white;
    selection-background-color:#70501b; }
QListWidget { background:#0b1520; border:0; padding:4px; }
QListWidget::item:selected { background:#6c5121; border:2px solid #ffd05d;
    border-radius:5px; }
QScrollArea { border:0; background:#131b23; }
QCheckBox { spacing:7px; }
QCheckBox::indicator { width:16px; height:16px; }
QCheckBox::indicator:checked { background:#e8b330; border-radius:3px; }
QSlider::groove:horizontal { height:6px; background:#374858; border-radius:3px; }
QSlider::sub-page:horizontal { background:#f0b52b; border-radius:3px; }
QSlider::handle:horizontal { background:#fff; width:14px; margin:-4px 0;
    border-radius:7px; }
QProgressBar { background:#283746; border:0; border-radius:5px;
    text-align:center; min-height:13px; max-height:15px; }
QProgressBar::chunk { background:#efb329; border-radius:5px; }
"""


class RoyalGoldMixin:
    def label(self, text, kind="section"):
        result = QLabel(text)
        result.setObjectName(kind)
        return result

    def btn(self, text, callback, accent=False):
        button = QPushButton(text)
        button.clicked.connect(callback)
        if accent:
            button.setProperty("accent", True)
        return button

    def panel(self):
        result = QFrame()
        result.setObjectName("panel")
        return result

    def build_interface(self):
        self.setWindowTitle("AURENIX PRO — Dark Royal Gold Edition")
        self.resize(1530, 870)
        self.setMinimumSize(1160, 700)
        self.setStyleSheet(STYLE)
        self.quality = "High"
        self.batch_started_at = None
        # Prefer the approved D: output path only when that drive exists.
        if Path("D:/").is_dir():
            self.output_dir = Path("D:/AURENIX PRO/Output")

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top = QFrame()
        top.setObjectName("top")
        h = QHBoxLayout(top)
        h.setContentsMargins(20, 6, 18, 6)
        mark = QLabel("A")
        mark.setStyleSheet("color:#f2c353;font-size:42px;font-weight:900;")
        h.addWidget(mark)
        brand = QVBoxLayout()
        brand.setSpacing(0)
        name = QLabel("AURENIX PRO")
        name.setStyleSheet("font-size:23px;font-weight:800;color:white;")
        brand.addWidget(name)
        edition = QLabel("Dark Royal Gold Edition")
        edition.setStyleSheet("color:#efbd52;font-size:11px;")
        brand.addWidget(edition)
        h.addLayout(brand)
        h.addSpacing(24)
        h.addWidget(self.label("AI Background Remover & Photo Enhancer"))
        h.addStretch()
        h.addWidget(self.btn("ⓘ Help", self.show_help))
        h.addWidget(self.btn("⚙ Settings", self.show_settings))
        root.addWidget(top)

        tabs = QFrame()
        tabs.setObjectName("bar")
        n = QHBoxLayout(tabs)
        n.setContentsMargins(12, 3, 12, 3)
        n.setSpacing(5)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for index, (text, callback) in enumerate((
            ("⌂ Home", lambda: self.library.setFocus()),
            ("▣ Batch Processing", lambda: self.library.setFocus()),
            ("✎ Editor", lambda: self.tool_select.setFocus()),
            ("⚒ Tools", lambda: self.sharpness_check.setFocus()),
            ("▤ Export History", self.show_export_history),
        )):
            b = self.btn(text, callback)
            b.setProperty("tab", True)
            b.setCheckable(True)
            b.setChecked(index == 0)
            self.nav_group.addButton(b, index)
            n.addWidget(b)
        n.addStretch()
        root.addWidget(tabs)

        body = QHBoxLayout()
        body.setContentsMargins(10, 8, 10, 8)
        body.setSpacing(9)
        root.addLayout(body, 1)

        left_frame = self.panel()
        left_frame.setFixedWidth(205)
        left = QVBoxLayout(left_frame)
        left.setContentsMargins(9, 10, 9, 10)
        left.setSpacing(7)
        left.addWidget(self.label("Workflow"))
        for text, callback in (
            ("①  Add Images", self.import_images),
            ("②  AI Settings", lambda: self.processing_mode.setFocus()),
            ("③  Preview & Adjust", lambda: self.tool_select.setFocus()),
            ("④  Process & Export", lambda: self.start_btn.setFocus()),
        ):
            left.addWidget(self.btn(text, callback, text.startswith("①")))
        left.addSpacing(9)
        left.addWidget(self.label("Quick Actions"))
        left.addWidget(self.btn("▧  Add Images", self.import_images))
        left.addWidget(self.btn("▱  Add Folder", self.import_folder))
        left.addWidget(self.btn("▤  Clear All", self.clear_image_library))
        left.addSpacing(9)
        left.addWidget(self.label("Output Folder"))
        self.output_label = self.label(str(self.output_dir), "muted")
        self.output_label.setWordWrap(True)
        left.addWidget(self.output_label)
        left.addWidget(self.btn("Choose Output Folder", self.choose_output))
        left.addWidget(self.btn("Open Output Folder", self.open_output))
        left.addStretch()
        body.addWidget(left_frame)

        center = QVBoxLayout()
        center.setSpacing(8)
        body.addLayout(center, 1)
        monitors = QHBoxLayout()
        monitors.setSpacing(8)
        center.addLayout(monitors, 1)

        original = self.panel()
        original_box = QVBoxLayout(original)
        original_box.setContentsMargins(8, 8, 8, 8)
        original_header = QHBoxLayout()
        original_header.addWidget(self.label("Original Image"))
        original_header.addStretch()
        original_header.addWidget(self.label("Source Preview", "muted"))
        original_box.addLayout(original_header)
        self.original_preview = self.FitPreviewClass()
        self.original_preview.setStyleSheet("background:#17212b;")
        original_box.addWidget(self.original_preview, 1)
        original_box.addWidget(self.label("Safe Fit • Original Image", "muted"))
        monitors.addWidget(original, 1)

        processed = self.panel()
        processed_box = QVBoxLayout(processed)
        processed_box.setContentsMargins(8, 8, 8, 8)
        result_header = QHBoxLayout()
        result_header.addWidget(self.label("Processed Result (Background Removed)"))
        result_header.addStretch()
        result_header.addWidget(self.label("PNG Preview", "muted"))
        processed_box.addLayout(result_header)
        self.editor = self.EditablePreviewClass()
        self.editor_scroll = self.ScrollAreaClass()
        self.editor_scroll.setWidget(self.editor)
        self.editor_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.editor_scroll.viewport().setStyleSheet("background:#c6cbd0;")
        processed_box.addWidget(self.editor_scroll, 1)
        edit = QHBoxLayout()
        self.tool_select = QComboBox()
        self.tool_select.addItems(["View", "Erase", "Restore"])
        self.tool_select.currentTextChanged.connect(self.change_tool)
        edit.addWidget(self.tool_select)
        self.brush_input = QSpinBox()
        self.brush_input.setRange(2, 250)
        self.brush_input.setValue(25)
        self.brush_input.setPrefix("Brush ")
        self.brush_input.valueChanged.connect(self.change_brush)
        edit.addWidget(self.brush_input)
        self.zoom_input = QSpinBox()
        self.zoom_input.setRange(10, 400)
        self.zoom_input.setValue(100)
        self.zoom_input.setSuffix("%")
        self.zoom_input.valueChanged.connect(self.change_zoom)
        edit.addWidget(self.zoom_input)
        self.save_btn = self.btn("Save Edit", self.save_edited)
        edit.addWidget(self.save_btn)
        processed_box.addLayout(edit)
        monitors.addWidget(processed, 1)

        queue_panel = self.panel()
        queue_box = QVBoxLayout(queue_panel)
        queue_box.setContentsMargins(8, 6, 8, 6)
        qhead = QHBoxLayout()
        qhead.addWidget(self.label("☑  Image Queue"))
        qhead.addStretch()
        self.count = self.label("0 images loaded", "muted")
        qhead.addWidget(self.count)
        queue_box.addLayout(qhead)
        self.library = QListWidget()
        self.library.setViewMode(QListWidget.ViewMode.IconMode)
        self.library.setFlow(QListWidget.Flow.LeftToRight)
        self.library.setWrapping(False)
        self.library.setMovement(QListWidget.Movement.Static)
        self.library.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.library.setIconSize(QSize(105, 77))
        self.library.setGridSize(QSize(120, 108))
        self.library.setFixedHeight(119)
        self.library.currentRowChanged.connect(self.select_image)
        queue_box.addWidget(self.library)
        queue_actions = QHBoxLayout()
        queue_actions.addWidget(self.btn("Add Images", self.import_images))
        queue_actions.addWidget(self.btn("Remove Selected", self.remove_selected_image))
        queue_actions.addWidget(self.btn("Clear", self.clear_image_library))
        queue_actions.addStretch()
        queue_box.addLayout(queue_actions)
        center.addWidget(queue_panel)

        right_frame = self.panel()
        right_frame.setFixedWidth(280)
        right = QVBoxLayout(right_frame)
        right.setContentsMargins(9, 9, 9, 9)
        right.setSpacing(7)
        right.addWidget(self.label("AI Processing Engine"))
        self.processing_mode = QComboBox()
        self.processing_mode.addItems([
            "◉ Offline AI (Local) — BiRefNet",
            "◯ Live AI (Online) — remove.bg",
        ])
        right.addWidget(self.processing_mode)
        self.model_info = self.label("Installed model: BiRefNet General", "muted")
        right.addWidget(self.model_info)
        self.live_api_key = QLineEdit()
        self.live_api_key.setPlaceholderText("remove.bg API key")
        self.live_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.live_api_key.setVisible(False)
        right.addWidget(self.live_api_key)
        self.live_notice = self.label(
            "Cloud mode uploads images and may consume paid API credits.", "muted"
        )
        self.live_notice.setWordWrap(True)
        self.live_notice.setVisible(False)
        right.addWidget(self.live_notice)
        self.processing_mode.currentIndexChanged.connect(
            lambda i: (self.live_api_key.setVisible(i == 1),
                       self.live_notice.setVisible(i == 1))
        )
        right.addSpacing(4)
        right.addWidget(self.label("Processing Quality"))
        qrow = QHBoxLayout()
        self.quality_group = QButtonGroup(self)
        self.quality_group.setExclusive(True)
        for text in ("Standard", "High", "Ultra"):
            b = self.btn(text, lambda checked=False, q=text: self.set_quality(q))
            b.setCheckable(True)
            b.setChecked(text == "High")
            self.quality_group.addButton(b)
            qrow.addWidget(b)
        right.addLayout(qrow)
        right.addSpacing(4)
        right.addWidget(self.label("Enhancement (Optional)"))
        self.color_check = QCheckBox("Color Enhancement")
        self.color_check.setChecked(True)
        right.addWidget(self.color_check)
        self.color_boost = QSlider(Qt.Orientation.Horizontal)
        self.color_boost.setRange(100, 200)
        self.color_boost.setValue(145)
        right.addWidget(self.color_boost)
        self.color_value = self.label("+45% intensity", "muted")
        right.addWidget(self.color_value)
        self.color_boost.valueChanged.connect(
            lambda v: self.color_value.setText(f"+{v - 100}% intensity")
        )
        self.color_check.toggled.connect(self.color_boost.setEnabled)
        self.sharpness_check = QCheckBox("Sharpness Enhancement")
        self.sharpness_check.setChecked(True)
        right.addWidget(self.sharpness_check)
        self.denoise_check = QCheckBox("Noise Reduction")
        self.denoise_check.setChecked(True)
        right.addWidget(self.denoise_check)
        self.detail_check = QCheckBox("Detail Recovery")
        self.detail_check.setChecked(True)
        right.addWidget(self.detail_check)
        right.addSpacing(7)
        right.addWidget(self.label("Output Format"))
        self.output_format = QComboBox()
        self.output_format.addItems([
            "PNG (Transparent)", "PNG (Pure White #FFFFFF)"
        ])
        right.addWidget(self.output_format)
        dimensions = QHBoxLayout()
        self.width_input = QSpinBox()
        self.width_input.setRange(1, 16000)
        self.width_input.setValue(WIDTH)
        self.width_input.setPrefix("W ")
        self.height_input = QSpinBox()
        self.height_input.setRange(1, 16000)
        self.height_input.setValue(HEIGHT)
        self.height_input.setPrefix("H ")
        dimensions.addWidget(self.width_input)
        dimensions.addWidget(self.height_input)
        right.addLayout(dimensions)
        right.addWidget(self.label(f"PNG • {DPI} DPI • Original filenames", "muted"))
        right.addStretch()
        self.start_btn = self.btn("▶  Process Images", self.start_processing, True)
        self.start_btn.setMinimumHeight(40)
        right.addWidget(self.start_btn)
        extra = QHBoxLayout()
        self.pause_btn = self.btn("Pause", self.pause_processing)
        self.resume_btn = self.btn("Resume", self.resume_processing)
        self.retry_btn = self.btn("Retry Failed", self.retry_failed)
        for button in (self.pause_btn, self.resume_btn, self.retry_btn):
            extra.addWidget(button)
        right.addLayout(extra)
        body.addWidget(right_frame)

        footer = QFrame()
        footer.setObjectName("bar")
        f = QHBoxLayout(footer)
        f.setContentsMargins(13, 4, 13, 4)
        self.processing_label = self.label("Ready to process images")
        f.addWidget(self.processing_label)
        self.progress_bar = self.ProgressBarClass()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        f.addWidget(self.progress_bar, 1)
        self.stop_btn = self.btn("■ Stop", self.stop_processing)
        f.addWidget(self.stop_btn)
        root.addWidget(footer)
        self.statusBar().showMessage("AURENIX PRO ready")

    def set_quality(self, quality):
        self.quality = quality
        self.statusBar().showMessage(f"Quality: {quality} (post-processing strength)")

    def show_settings(self):
        self.processing_mode.setFocus()
        self.statusBar().showMessage("AI and output settings are on the right.")

    def show_help(self):
        QMessageBox.information(
            self, "AURENIX PRO Help",
            "Add images or a folder, select Offline AI or Live AI, "
            "choose transparent or white PNG, and click Process Images. "
            "Use Editor controls to refine a processed image."
        )

    def start_processing(self):
        self.batch_started_at = time.monotonic()
        self.processing_label.setText("Initializing AI processing…")
        super().start_processing()

    def retry_failed(self):
        self.batch_started_at = time.monotonic()
        super().retry_failed()

    def update_progress(self, done, total):
        super().update_progress(done, total)
        elapsed = max(0.001, time.monotonic() - self.batch_started_at) if self.batch_started_at else 0
        rate = done / elapsed if elapsed and done else 0
        remaining = (total - done) / rate if rate else 0
        if rate:
            self.processing_label.setText(
                f"{done}/{total} images • {rate * 60:.1f} img/min • "
                f"ETA {int(remaining // 60):02d}:{int(remaining % 60):02d}"
            )
        else:
            self.processing_label.setText(f"Processing: {done}/{total} images")

    def image_completed(self, source, output):
        super().image_completed(source, output)
        self.processing_label.setText(f"Saved: {Path(output).name}")

    def batch_finished(self):
        super().batch_finished()
        self.processing_label.setText(
            "Batch complete" if not self.errors else
            f"Batch complete — {len(self.errors)} failed"
        )
        self.batch_started_at = None

    def show_export_history(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("AURENIX PRO — Export History")
        dialog.resize(600, 420)
        layout = QVBoxLayout(dialog)
        layout.addWidget(self.label("Exported Images"))
        history = QListWidget()
        outputs = sorted(
            (p for p in self.output_dir.glob("*.png") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        ) if self.output_dir.is_dir() else []
        for file in outputs:
            history.addItem(file.name)
        if not outputs:
            history.addItem("No exported PNG files in the current output folder.")
            history.setEnabled(False)
        layout.addWidget(history)
        def open_selected():
            index = history.currentRow()
            if 0 <= index < len(outputs):
                from PySide6.QtCore import QUrl
                from PySide6.QtGui import QDesktopServices
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(outputs[index])))
        history.itemDoubleClicked.connect(lambda item: open_selected())
        open_button = QPushButton("Open Selected Image")
        open_button.setEnabled(bool(outputs))
        open_button.clicked.connect(open_selected)
        layout.addWidget(open_button)
        folder_button = QPushButton("Open Output Folder")
        folder_button.clicked.connect(self.open_output)
        layout.addWidget(folder_button)
        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_buttons.rejected.connect(dialog.reject)
        layout.addWidget(close_buttons)
        dialog.exec()

