import sys
from pathlib import Path
from PySide6.QtCore import QTimer

from PIL import Image, ImageOps
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFrame, QGroupBox, QHBoxLayout,
    QLabel, QListWidget, QPushButton, QScrollArea,
    QSpinBox, QComboBox, QProgressBar, QSizePolicy,
    QVBoxLayout, QWidget
)

from background_remover_pro import (
    BackgroundRemoverPro, EditablePreview, DPI,
    WIDTH, HEIGHT, image_to_pixmap
)


class FitPreview(QLabel):
    def __init__(self):
        super().__init__()
        self.source_pixmap = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(280, 250)
        self.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Expanding
        )
        self.setStyleSheet("background:#ffffff;")

    def setPixmap(self, pixmap):
        self.source_pixmap = pixmap
        self.fit_image()

    def fit_image(self):
        if self.source_pixmap is None:
            return
        scaled = self.source_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        super().setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_image()

    def clear(self):
        self.source_pixmap = None
        super().clear()


class SafeFitEditablePreview(EditablePreview):
    """Fit the whole image in the available Output monitor."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(1, 1)
        self.setFixedSize(1, 1)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background:#0b1725;")

    def refresh(self):
        if self.processed is None:
            self.clear()
            self.setFixedSize(1, 1)
            return

        parent = self.parentWidget()

        if parent is None:
            available_w = 500
            available_h = 400
        else:
            available_w = max(1, parent.width() - 16)
            available_h = max(1, parent.height() - 16)

        image = self.processed.convert("RGBA")

        display = Image.new(
            "RGBA",
            image.size,
            (255, 255, 255, 255)
        )
        display.alpha_composite(image)

        fit = min(
            available_w / max(1, image.width),
            available_h / max(1, image.height)
        )

        scale = max(0.001, fit * self.zoom)

        width = max(1, round(image.width * scale))
        height = max(1, round(image.height * scale))

        pixmap = image_to_pixmap(display).scaled(
            width,
            height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.setFixedSize(pixmap.size())
        self.setPixmap(pixmap)


class SafeFitScrollArea(QScrollArea):
    """Keep preview fitted after monitor resize."""

    def resizeEvent(self, event):
        super().resizeEvent(event)
        widget = self.widget()

        if isinstance(widget, SafeFitEditablePreview):
            QTimer.singleShot(0, widget.refresh)


class AurenixPro(BackgroundRemoverPro):
    def create_button(self, title, callback, accent=False):
        button = QPushButton(title)
        button.clicked.connect(callback)
        if accent:
            button.setProperty("accent", True)
        return button

    def make_panel(self):
        frame = QFrame()
        frame.setObjectName("panel")
        return frame

    def nav_focus(self, widget):
        widget.setFocus()
        if isinstance(widget, QComboBox):
            widget.showPopup()

    def build_interface(self):
        self.setWindowTitle("AURENIX PRO")
        self.resize(1550, 920)
        self.setMinimumSize(1150, 700)

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background:#101c2c;
                color:#eaf2fc;
                font-family:"Segoe UI";
                font-size:12px;
            }
            QFrame#panel, QGroupBox {
                background:#14273b;
                border:1px solid #31506d;
                border-radius:8px;
            }
            QGroupBox {
                font-weight:600;
                margin-top:12px;
                padding:12px;
            }
            QGroupBox::title {
                subcontrol-origin:margin;
                left:12px;
                padding:0 5px;
            }
            QPushButton {
                background:#243d56;
                border:1px solid #42627c;
                border-radius:5px;
                min-height:26px;
                padding:5px 9px;
            }
            QPushButton:hover {
                background:#315474;
            }
            QPushButton[accent="true"] {
                background:#086ac3;
                border:1px solid #2595fa;
                color:white;
                font-weight:600;
            }
            QPushButton:disabled {
                background:#203045;
                color:#71859a;
                border-color:#32445a;
            }
            QListWidget {
                background:#0c1929;
                border:1px solid #31506d;
                border-radius:5px;
                padding:5px;
            }
            QListWidget::item:selected {
                background:#1267ae;
                border:1px solid #59b6ff;
                border-radius:5px;
            }
            QScrollArea {
                border:0;
                background:#0b1725;
            }
            QSpinBox, QComboBox {
                background:#20394f;
                border:1px solid #45617a;
                border-radius:4px;
                padding:6px;
            }
            QProgressBar {
                background:#0b1725;
                border:1px solid #31506d;
                border-radius:4px;
                text-align:center;
                min-height:15px;
            }
            QProgressBar::chunk {
                background:#0786e4;
            }
        """)

        main = QWidget()
        self.setCentralWidget(main)
        root = QVBoxLayout(main)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # HEADER
        header = self.make_panel()
        top = QHBoxLayout(header)

        mark = QLabel("A")
        mark.setFixedWidth(55)
        mark.setStyleSheet(
            "font-size:43px;font-weight:900;color:#38baff;"
            "border:0;background:transparent;"
        )
        top.addWidget(mark)

        brand = QVBoxLayout()
        brand.setSpacing(0)
        brand_name = QLabel("AURENIX PRO")
        brand_name.setStyleSheet(
            "font-size:25px;font-weight:800;color:#ffffff;"
            "border:0;background:transparent;"
        )
        brand_tag = QLabel("AI Precision Imaging")
        brand_tag.setStyleSheet(
            "color:#79b9e9;font-size:11px;"
            "border:0;background:transparent;"
        )
        brand.addWidget(brand_name)
        brand.addWidget(brand_tag)
        top.addLayout(brand)
        top.addStretch()

        top.addWidget(self.create_button(
            "Import Images", self.import_images
        ))
        top.addWidget(self.create_button(
            "Import Folder", self.import_folder
        ))
        top.addWidget(self.create_button(
            "Output Folder", self.choose_output
        ))
        top.addWidget(self.create_button(
            "Open Output", self.open_output
        ))
        root.addWidget(header)

        # WORKSPACE
        workspace = QHBoxLayout()
        workspace.setSpacing(8)
        root.addLayout(workspace, 1)

        # LEFT NAVIGATION
        rail = self.make_panel()
        rail.setFixedWidth(112)
        nav = QVBoxLayout(rail)
        nav.setSpacing(8)

        nav_title = QLabel("WORKSPACE")
        nav_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(nav_title)

        def add_nav(text, callback):
            button = self.create_button(text, callback)
            button.setMinimumHeight(53)
            nav.addWidget(button)

        add_nav(
            "AI Processing",
            lambda: self.nav_focus(self.model_info)
        )
        add_nav(
            "Image Library",
            lambda: self.library.setFocus()
        )
        add_nav(
            "Output Settings",
            lambda: self.width_input.setFocus()
        )
        add_nav(
            "Editing Tools",
            lambda: self.nav_focus(self.tool_select)
        )
        add_nav(
            "Batch Controls",
            lambda: self.start_btn.setFocus()
        )
        nav.addStretch()
        workspace.addWidget(rail)

        # AI / OUTPUT SETTINGS
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFixedWidth(268)
        settings_content = self.make_panel()
        settings = QVBoxLayout(settings_content)

        settings.addWidget(QLabel("AI MODEL"))
        self.model_info = QLabel(
            "BiRefNet General\n"
            "High-quality product segmentation"
        )
        self.model_info.setWordWrap(True)
        self.model_info.setStyleSheet(
            "color:#8fd0ff;font-weight:600;"
            "padding:10px;background:#1b3851;"
            "border-radius:5px;"
        )
        settings.addWidget(self.model_info)

        quality_note = QLabel(
            "Preserves fine equipment details.\n"
            "Processing time depends on image size."
        )
        quality_note.setWordWrap(True)
        settings.addWidget(quality_note)

        output_group = QGroupBox("OUTPUT SETTINGS")
        output_form = QVBoxLayout(output_group)

        output_form.addWidget(QLabel(
            "Background: Pure White (#FFFFFF)"
        ))
        output_form.addWidget(QLabel(
            "Format: PNG (White Background)"
        ))
        output_form.addWidget(QLabel(
            "Filenames: Preserve originals"
        ))

        output_form.addWidget(QLabel("Width (Pixels)"))
        self.width_input = QSpinBox()
        self.width_input.setRange(1, 16000)
        self.width_input.setValue(WIDTH)
        output_form.addWidget(self.width_input)

        output_form.addWidget(QLabel("Height (Pixels)"))
        self.height_input = QSpinBox()
        self.height_input.setRange(1, 16000)
        self.height_input.setValue(HEIGHT)
        output_form.addWidget(self.height_input)

        output_form.addWidget(QLabel(
            f"Resolution: {DPI} PPI"
        ))
        settings.addWidget(output_group)

        edit_group = QGroupBox("EDITING TOOLS")
        edit_form = QVBoxLayout(edit_group)

        self.tool_select = QComboBox()
        self.tool_select.addItems(
            ["View", "Erase", "Restore"]
        )
        self.tool_select.currentTextChanged.connect(
            self.change_tool
        )
        edit_form.addWidget(self.tool_select)

        edit_form.addWidget(QLabel("Brush Size"))
        self.brush_input = QSpinBox()
        self.brush_input.setRange(2, 250)
        self.brush_input.setValue(25)
        self.brush_input.valueChanged.connect(
            self.change_brush
        )
        edit_form.addWidget(self.brush_input)

        edit_form.addWidget(QLabel("Zoom (%)"))
        self.zoom_input = QSpinBox()
        self.zoom_input.setRange(10, 400)
        self.zoom_input.setValue(100)
        self.zoom_input.valueChanged.connect(
            self.change_zoom
        )
        edit_form.addWidget(self.zoom_input)

        self.save_btn = self.create_button(
            "SAVE EDITED PNG", self.save_edited
        )
        edit_form.addWidget(self.save_btn)
        settings.addWidget(edit_group)
        settings.addStretch()

        settings_scroll.setWidget(settings_content)
        workspace.addWidget(settings_scroll)

        # MAIN EDITOR AREA
        editor_area = QWidget()
        editor_main = QVBoxLayout(editor_area)
        editor_main.setContentsMargins(0, 0, 0, 0)
        editor_main.setSpacing(8)
        workspace.addWidget(editor_area, 1)

        previews = QHBoxLayout()
        previews.setSpacing(8)
        editor_main.addLayout(previews, 1)

        original_frame = self.make_panel()
        original_layout = QVBoxLayout(original_frame)
        original_layout.addWidget(QLabel(
            "ORIGINAL IMAGE"
        ))

        self.original_preview = FitPreview()
        original_layout.addWidget(
            self.original_preview, 1
        )
        previews.addWidget(original_frame, 1)

        result_frame = self.make_panel()
        result_layout = QVBoxLayout(result_frame)
        result_layout.addWidget(QLabel(
            "BACKGROUND REMOVED"
        ))

        self.editor = SafeFitEditablePreview()
        self.editor.setStyleSheet(
            "background:#0b1725;"
        )

        self.editor_scroll = SafeFitScrollArea()
        self.editor_scroll.setWidget(self.editor)
        # AURENIX_WHITE_PREVIEW_FIX
        self.editor_scroll.setStyleSheet(
            "QScrollArea { background: white; border: 0; }"
        )
        self.editor_scroll.viewport().setStyleSheet(            "background: white;"
        )
        self.editor.setStyleSheet("background: white;")
        self.editor_scroll.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        result_layout.addWidget(
            self.editor_scroll, 1
        )
        previews.addWidget(result_frame, 1)

        # HORIZONTAL THUMBNAIL LIBRARY
        library_frame = self.make_panel()
        library_layout = QVBoxLayout(library_frame)
        library_header = QHBoxLayout()

        library_header.addWidget(QLabel(
            "IMAGE LIBRARY"
        ))
        library_header.addStretch()

        self.add_more_btn = self.create_button(
            "Add Images", self.import_images,
            accent=True
        )
        self.remove_btn = self.create_button(
            "Remove Selected",
            self.remove_selected_image
        )
        self.clear_btn = self.create_button(
            "Clear Library",
            self.clear_image_library
        )

        library_header.addWidget(self.add_more_btn)
        library_header.addWidget(self.remove_btn)
        library_header.addWidget(self.clear_btn)
        library_layout.addLayout(library_header)

        self.library = QListWidget()
        self.library.setViewMode(
            QListWidget.ViewMode.IconMode
        )
        self.library.setFlow(
            QListWidget.Flow.LeftToRight
        )
        self.library.setWrapping(False)
        self.library.setMovement(
            QListWidget.Movement.Static
        )
        self.library.setResizeMode(
            QListWidget.ResizeMode.Adjust
        )
        self.library.setIconSize(QSize(125, 76))
        self.library.setGridSize(QSize(150, 112))
        self.library.setFixedHeight(137)
        self.library.currentRowChanged.connect(
            self.select_image
        )
        library_layout.addWidget(self.library)

        self.count = QLabel("0 images loaded")
        library_layout.addWidget(self.count)
        editor_main.addWidget(library_frame)

        # BOTTOM PROCESSING CONTROLS
        bottom = self.make_panel()
        bottom_layout = QVBoxLayout(bottom)

        controls = QHBoxLayout()
        self.start_btn = self.create_button(
            "START PROCESSING",
            self.start_processing,
            accent=True
        )
        self.pause_btn = self.create_button(
            "PAUSE", self.pause_processing
        )
        self.resume_btn = self.create_button(
            "RESUME", self.resume_processing
        )
        self.stop_btn = self.create_button(
            "STOP", self.stop_processing
        )
        self.retry_btn = self.create_button(
            "RETRY FAILED", self.retry_failed
        )

        for button in (
            self.start_btn, self.pause_btn,
            self.resume_btn, self.stop_btn,
            self.retry_btn
        ):
            controls.addWidget(button)

        bottom_layout.addLayout(controls)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        bottom_layout.addWidget(self.progress_bar)

        self.output_label = QLabel(
            f"Output Folder: {self.output_dir}"
        )
        self.output_label.setWordWrap(True)
        bottom_layout.addWidget(self.output_label)
        root.addWidget(bottom)

        self.statusBar().showMessage(
            "AURENIX PRO ready"
        )

    def add_images(self, files):
        old_count = len(self.images)
        super().add_images(files)

        # Apply thumbnails to newly added library items.
        for index in range(old_count, len(self.images)):
            path = self.images[index]
            try:
                with Image.open(path) as image:
                    preview = ImageOps.exif_transpose(image)
                    preview = preview.convert("RGBA")
                    preview.thumbnail((125, 76))

                    canvas = Image.new(
                        "RGBA",
                        (125, 76),
                        (255, 255, 255, 255)
                    )
                    x = (125 - preview.width) // 2
                    y = (76 - preview.height) // 2
                    canvas.alpha_composite(
                        preview, (x, y)
                    )

                    pixmap = image_to_pixmap(canvas)
                    self.library.item(index).setIcon(
                        QIcon(pixmap)
                    )
            except Exception:
                pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AurenixPro()
    window.show()
    sys.exit(app.exec())