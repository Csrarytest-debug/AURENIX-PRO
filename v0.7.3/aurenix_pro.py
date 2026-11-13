"""AURENIX PRO — approved navy/gold workspace, built on recovered processing core.
This is a source test build, not an independently verified native release.
"""
import sys
import os
from pathlib import Path

# Configure packaged model weights BEFORE dispatching the AI subprocess.
# Previously this happened AFTER the worker dispatch, so the frozen child could
# miss the bundled models and try to download weights on a customer's PC.
_bundle_root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
_bundled_models = _bundle_root / 'models'
if getattr(sys, 'frozen', False) or any(_bundled_models.rglob('*.onnx')):
    os.environ['U2NET_HOME'] = str(_bundled_models)

# Dispatch the isolated AI process before importing GUI, Pillow or Qt.
# The GUI and ONNX/CUDA runtime must not share an OS process.
if __name__ == '__main__' and len(sys.argv) >= 3 and sys.argv[1] == '--aurenix-worker':
    from inference_worker import main as _inference_main
    sys.exit(_inference_main(sys.argv[2]))

from PIL import Image, ImageOps
from PySide6.QtCore import Qt, QSize, QTimer, QSettings, QThread, Signal
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter, QFont
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QGroupBox, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QScrollArea, QSpinBox, QComboBox, QProgressBar,
    QSizePolicy, QVBoxLayout, QWidget, QRadioButton, QButtonGroup,
    QColorDialog, QMessageBox, QStackedWidget, QSlider, QLineEdit, QSplashScreen, QCheckBox
)
from background_remover_pro import BackgroundRemoverPro, EditablePreview, DPI, WIDTH, HEIGHT, image_to_pixmap
from diagnostics import configure_logging, record_error, install_exception_hooks, export_report, log_directory
from image_export import normalized_format

GOLD = '#ffbf2b'
BG = '#050d17'
PANEL = '#071c2d'
BLUE = '#1f6b97'

class GpuMonitor(QThread):
    """nvidia-smi runs off the GUI thread and never imports ONNX at startup."""
    metrics = Signal(str, int)

    def run(self):
        try:
            import subprocess
            cmd = ['nvidia-smi', '--query-gpu=name,utilization.gpu,memory.used,memory.total',
                   '--format=csv,noheader,nounits']
            cp = subprocess.run(cmd, capture_output=True, text=True, timeout=2,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if cp.returncode:
                raise RuntimeError(cp.stderr.strip())
            name, usage, used, total = [x.strip() for x in cp.stdout.strip().splitlines()[0].rsplit(',', 3)]
            percent = min(100, max(0, int(float(usage))))
            self.metrics.emit(f'GPU  {percent}%  |  {name}\nVRAM {int(float(used))} / {int(float(total))} MiB', percent)
        except Exception:
            self.metrics.emit('GPU / VRAM\nUnavailable', 0)


class FitPreview(QLabel):
    def __init__(self):
        super().__init__()
        self.source = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(250,220)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.setStyleSheet('background: white;')
    def setPixmap(self, pixmap):
        self.source = pixmap
        self._fit()
    def _fit(self):
        if self.source is not None:
            super().setPixmap(self.source.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
    def resizeEvent(self,event):
        super().resizeEvent(event)
        self._fit()
    def clear(self):
        self.source = None
        super().clear()

class FitEditor(EditablePreview):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(1,1)
        self.setFixedSize(1,1)
        self.setStyleSheet('background: white;')
    def refresh(self):
        if self.processed is None:
            self.clear()
            self.setFixedSize(1,1)
            return
        area = self.parentWidget()
        w = max(1,(area.width() if area else 560)-24)
        h = max(1,(area.height() if area else 440)-24)
        # Keep the editable master image at full resolution, but only render the
        # viewport-sized preview. A full-size QPixmap can exhaust RAM/VRAM on
        # large images and is unnecessary for the output monitor.
        img = self.processed
        scale = min(w / img.width, h / img.height) * self.zoom
        display_w = max(1, round(img.width * scale))
        display_h = max(1, round(img.height * scale))
        size = QSize(display_w, display_h)
        if self.size() != size:
            self.setFixedSize(size)
        preview = img.resize((display_w, display_h), Image.Resampling.BILINEAR)
        canvas = Image.new('RGBA', preview.size, (255, 255, 255, 255))
        canvas.alpha_composite(preview)
        self.setPixmap(image_to_pixmap(canvas))

class FitArea(QScrollArea):
    def resizeEvent(self,event):
        super().resizeEvent(event)
        widget=self.widget()
        if isinstance(widget,FitEditor):
            QTimer.singleShot(0,widget.refresh)

class AurenixPro(BackgroundRemoverPro):
    def button(self,label,fn,primary=False):
        b=QPushButton(label)
        b.clicked.connect(fn)
        if primary: b.setProperty('gold',True)
        return b
    def panel(self):
        p=QFrame();p.setObjectName('panel');return p
    def heading(self,text):
        l=QLabel(text);l.setProperty('heading',True);return l
    def navigate(self,index):
        self.views.setCurrentIndex(index)
        self.nav_buttons[index].setChecked(True)
    def _page(self,title,description,actions):
        pane=self.panel(); layout=QVBoxLayout(pane)
        layout.addWidget(self.heading(title))
        caption=QLabel(description);caption.setWordWrap(True)
        layout.addWidget(caption)
        for name,callback in actions:
            layout.addWidget(self.button(name,callback))
        layout.addStretch()
        return pane
    def choose_custom(self):
        color=QColorDialog.getColor(parent=self,title='Select output background color')
        if color.isValid():
            self.bg_color=color.name()
            self.custom_bg.setChecked(True)
            self.statusBar().showMessage('Selected background: '+self.bg_color)
    def resolution_changed(self,idx):
        options=[(1280,720),(1920,1080),(WIDTH,HEIGHT),(3840,2160)]
        if idx<4:
            self.width_input.setValue(options[idx][0]);self.height_input.setValue(options[idx][1])
    def zoom_change(self,v):
        self.change_zoom(v)
    def build_interface(self):
        self.setWindowTitle(' ')
        self.resize(1648,930)
        self.setMinimumSize(1150,720)
        self.bg_color='#ffffff'
        self.setStyleSheet('''
            QMainWindow,QWidget { background:#050d17;color:#f4f6fa;font-family:'Segoe UI';font-size:12px; }
            QFrame#panel,QGroupBox {background:#071c2d;border:1px solid #1f6b97;border-radius:10px;}
            QLabel[heading="true"] {font-size:15px;font-weight:800;color:white;}
            QPushButton {background:#082035;border:1px solid #266c90;border-radius:9px;color:white;padding:9px 13px;font-weight:700;min-height:22px;}
            QPushButton:hover {background:#153850;border-color:#6bc3fa;}
            QPushButton:checked, QPushButton[gold="true"] {background:#d8930d;border:2px solid #ffd04a;color:#10121b;font-weight:900;}
            QPushButton:disabled {color:#8293a3;background:#152434;border-color:#1e3b51;}
            QGroupBox {font-weight:bold;margin-top:10px;padding:11px;}
            QGroupBox::title {subcontrol-origin:margin;left:13px;color:#ffc52b;}
            QListWidget {background:#071521;border:1px solid #174d73;border-radius:9px;}
            QListWidget::item:selected {background:#35502e;border:2px solid #ffca2a;border-radius:6px;}
            QSpinBox,QComboBox {background:#0b2c45;border:1px solid #357ca8;color:white;border-radius:5px;padding:5px;min-height:24px;}
            QScrollArea {border:0;background:white;}
            QProgressBar {background:#152436;border:1px solid #2e6385;border-radius:8px;text-align:right;min-height:19px;color:white;}
            QProgressBar::chunk {background:#ffbc21;border-radius:7px;}
            QRadioButton {padding:5px;min-height:20px;}
            QRadioButton::indicator:checked {background:#ffbd16;border:2px solid #ffd943;border-radius:7px;}
        ''')
        center=QWidget();self.setCentralWidget(center)
        root=QVBoxLayout(center);root.setContentsMargins(11,9,11,7);root.setSpacing(9)
        header=self.panel();hl=QHBoxLayout(header)
        # Equal-width wings keep the product title centered in the WINDOW,
        # even when GPU/RAM panel widths change with their measured values.
        left_wing=QWidget(); left_wing.setFixedWidth(430)
        left_layout=QHBoxLayout(left_wing);left_layout.setContentsMargins(0,0,0,0)
        brand=QLabel(); brand.setFixedSize(250,112)
        logo_path=Path(__file__).resolve().parent/'assets'/'bs_broadcast_glow.png'
        if logo_path.exists():
            brand.setPixmap(QPixmap(str(logo_path)).scaled(250,112,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        else:
            brand.setText('BS BROADCAST')
        left_layout.addStretch();left_layout.addWidget(brand);left_layout.addStretch()
        hl.addWidget(left_wing)
        name=QLabel('AURENIX PRO BG Remover V0.7.3')
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet('color:#ffcb55;font-size:26px;font-weight:900;font-style:italic;')
        hl.addWidget(name,1)
        right_wing=QWidget();right_wing.setFixedWidth(430)
        right_layout=QHBoxLayout(right_wing);right_layout.setContentsMargins(0,0,0,0)
        # Larger live monitoring surfaces, balanced by equal-width left/right wings.
        # This only reports usage. It does not enable GPU inference.
        right_layout.setSpacing(7)
        gpu_box=QFrame();gpu_box.setObjectName('telemetry')
        gpu_layout=QVBoxLayout(gpu_box);gpu_layout.setContentsMargins(10,7,10,7);gpu_layout.setSpacing(2)
        self.gpu_label=QLabel('GPU: checking…')
        self.gpu_label.setWordWrap(True)
        self.gpu_bar=QProgressBar();self.gpu_bar.setRange(0,100)
        self.gpu_bar.setTextVisible(False);self.gpu_bar.setValue(0)
        self.gpu_bar.setFixedHeight(10)
        self.ai_provider_label=QLabel('AI model: U2Net (safe default)')
        self.ai_provider_label.setWordWrap(True)
        gpu_layout.addWidget(self.gpu_label);gpu_layout.addWidget(self.gpu_bar)
        gpu_layout.addWidget(self.ai_provider_label)
        ram_box=QFrame();ram_box.setObjectName('telemetry')
        ram_layout=QVBoxLayout(ram_box);ram_layout.setContentsMargins(10,7,10,7);ram_layout.setSpacing(2)
        self.ram_label=QLabel('RAM: checking…')
        self.ram_label.setWordWrap(True)
        self.ram_bar=QProgressBar();self.ram_bar.setRange(0,100)
        self.ram_bar.setTextVisible(False);self.ram_bar.setValue(0)
        self.ram_bar.setFixedHeight(10)
        ram_layout.addWidget(self.ram_label);ram_layout.addWidget(self.ram_bar)
        for box in (gpu_box,ram_box):
            box.setStyleSheet('QFrame#telemetry{background:#071726;border:1px solid #bd8b0d;border-radius:8px;} QFrame#telemetry QLabel{background:transparent;border:none;color:#e7f1fc;font-weight:700;font-size:11px;}')
            right_layout.addWidget(box,1)
        hl.addWidget(right_wing)
        root.addWidget(header)
        self.views=QStackedWidget()
        nav=QHBoxLayout();nav.setSpacing(8)
        self.nav_buttons=[]
        for i,label in enumerate(('Background Remover','Batch Processing','Image Enhancer','Resize & Export','Tools','Settings')):
            b=self.button(label,lambda checked=False,j=i:self.navigate(j));b.setCheckable(True)
            self.nav_buttons.append(b);nav.addWidget(b,1)
        root.addLayout(nav)
        # Primary workspace
        workspace=QWidget();body=QHBoxLayout(workspace);body.setContentsMargins(0,0,0,0);body.setSpacing(8)
        left=self.panel();left.setFixedWidth(205);ll=QVBoxLayout(left)
        ll.addWidget(self.button('▣  Add Images',self.import_images,True))
        ll.addWidget(self.button('▤  Add Folder',self.import_folder))
        ll.addWidget(self.button('Remove',self.remove_selected_image))
        ll.addWidget(self.button('Clear All',self.clear_image_library))
        self.count=self.heading('Image List (0)');ll.addWidget(self.count)
        self.library=QListWidget();self.library.setViewMode(QListWidget.ViewMode.IconMode)
        self.library.setIconSize(QSize(130,90));self.library.setGridSize(QSize(160,120))
        self.library.setFlow(QListWidget.Flow.TopToBottom);self.library.setWrapping(False)
        self.library.currentRowChanged.connect(self.select_image)
        ll.addWidget(self.library,1)
        body.addWidget(left)
        previews=QHBoxLayout();previews.setSpacing(8)
        a=self.panel();al=QVBoxLayout(a);al.addWidget(self.heading('▣  Original Image'))
        self.original_preview=FitPreview();al.addWidget(self.original_preview,1)
        previews.addWidget(a,1)
        b=self.panel();bl=QVBoxLayout(b);bl.addWidget(self.heading('▣  Output (Background Removed)'))
        self.editor=FitEditor();self.editor_scroll=FitArea();self.editor_scroll.setWidget(self.editor)
        self.editor_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.editor_scroll.viewport().setStyleSheet('background:white;')
        bl.addWidget(self.editor_scroll,1)
        previews.addWidget(b,1)
        body.addLayout(previews,1)
        right=self.panel();right.setFixedWidth(350);rl=QVBoxLayout(right)
        rl.setContentsMargins(8,8,8,8)
        rl.setSpacing(7)
        rl.addWidget(self.heading('⚙  Output Settings'))
        # A dedicated vertically scrolling settings surface prevents Qt from
        # compressing the group boxes until the spin boxes become unreadable.
        self.settings_scroll=QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.settings_scroll.setObjectName('settings_scroll')
        self.settings_scroll.setStyleSheet('QScrollArea#settings_scroll {background:#071c2d;border:0;} QScrollArea#settings_scroll > QWidget > QWidget {background:#071c2d;}')
        settings_content=QWidget()
        settings_layout=QVBoxLayout(settings_content)
        settings_layout.setContentsMargins(4,8,8,8)
        settings_layout.setSpacing(12)
        self.settings_scroll.setWidget(settings_content)
        rl.addWidget(self.settings_scroll,1)
        resolution=QGroupBox('Image Resolution');rr=QVBoxLayout(resolution)
        self.presets=QComboBox();self.presets.addItems(['HD — 1280 × 720','Full HD — 1920 × 1080','Current — 1080 × 810 (Default)','4K UHD — 3840 × 2160','Custom dimensions'])
        self.presets.setCurrentIndex(2);self.presets.currentIndexChanged.connect(self.resolution_changed)
        rr.addWidget(self.presets)
        size=QHBoxLayout();self.width_input=QSpinBox();self.height_input=QSpinBox()
        for v,default in ((self.width_input,WIDTH),(self.height_input,HEIGHT)):
            v.setRange(1,16000);v.setValue(default)
        size.addWidget(QLabel('W:'));size.addWidget(self.width_input);size.addWidget(QLabel('H:'));size.addWidget(self.height_input)
        rr.addLayout(size);rr.addWidget(QLabel(f'Resolution: {DPI} PPI'))
        settings_layout.addWidget(resolution)
        colors=QGroupBox('Color Scheme (Background)');cl=QVBoxLayout(colors)
        self.bg_group=QButtonGroup(self)
        self.white_bg=QRadioButton('Pure White (Default)')
        self.custom_bg=QRadioButton('Custom Background Color')
        self.transparent_bg=QRadioButton('Transparent (PNG)')
        for r in (self.white_bg,self.custom_bg,self.transparent_bg):
            self.bg_group.addButton(r);cl.addWidget(r)
        self.white_bg.setChecked(True)
        cl.addWidget(self.button('Choose Custom Color',self.choose_custom))
        settings_layout.addWidget(colors)
        cleanup_box=QGroupBox('Automatic Wire Cleanup')
        cleanup_layout=QVBoxLayout(cleanup_box)
        self.auto_wire_checkbox=QCheckBox('Remove loose background wires automatically')
        self.auto_wire_checkbox.setChecked(True)
        self.auto_wire_checkbox.setToolTip(
            'Conservative thin-strand cleanup after AI background removal. '
            'Wires crossing the product may still require the Wire Mask tool.')
        cleanup_layout.addWidget(self.auto_wire_checkbox)
        note=QLabel('Protects equipment detail. Complex or overlapping cables may need manual cleanup.')
        note.setWordWrap(True)
        cleanup_layout.addWidget(note)
        settings_layout.addWidget(cleanup_box)
        exporting=QGroupBox('Export Format & Quality'); exl=QVBoxLayout(exporting)
        exl.addWidget(QLabel('Output Format'))
        self.export_format=QComboBox()
        self.export_format.addItems(['PNG', 'JPEG', 'WebP', 'TIFF', 'BMP'])
        self.export_format.setToolTip('JPEG and BMP cannot store transparency; white/custom background is applied instead')
        exl.addWidget(self.export_format)
        exl.addWidget(QLabel('JPEG / WebP Quality'))
        self.export_quality=QSpinBox(); self.export_quality.setRange(1,100);self.export_quality.setValue(95)
        exl.addWidget(self.export_quality)
        exl.addWidget(QLabel('Output DPI'))
        self.export_dpi=QSpinBox(); self.export_dpi.setRange(72,1200);self.export_dpi.setValue(DPI)
        exl.addWidget(self.export_dpi)
        settings_layout.addWidget(exporting)
        self.export_format.currentTextChanged.connect(self.export_selection_changed)
        editing=QGroupBox('Editing Tools');el=QVBoxLayout(editing)
        self.tool_select=QComboBox();self.tool_select.addItems(['View','Erase','Restore','Wire Mask'])
        self.tool_select.currentTextChanged.connect(self.change_tool);el.addWidget(self.tool_select)
        el.addWidget(QLabel('Brush Size'))
        self.brush_input=QSpinBox();self.brush_input.setRange(2,250);self.brush_input.setValue(25)
        self.brush_input.valueChanged.connect(self.change_brush);el.addWidget(self.brush_input)
        el.addWidget(self.button('Apply Wire Cleanup (paint mask first)', self.apply_wire_cleanup))
        el.addWidget(self.button('Undo Wire Cleanup', self.undo_wire_cleanup))
        self.save_btn=self.button('Save Edited Image',self.save_edited);el.addWidget(self.save_btn)
        settings_layout.addWidget(editing);settings_layout.addStretch()
        body.addWidget(right)
        self.views.addWidget(workspace)
        self.views.addWidget(self._page('Batch Processing','Process multiple imported images with pause, resume and retry. Requires an installed AI model.', [('Import Folder',self.import_folder),('Start Batch',self.start_processing),('Pause',self.pause_processing),('Resume',self.resume_processing),('Retry Failed',self.retry_failed)]))
        self.views.addWidget(self._page('Image Enhancer','Background removal is available. A separate image super-resolution model is not included in this source build.', [('Open Background Remover',lambda:self.navigate(0))]))
        self.views.addWidget(self._page('Resize & Export','Choose the dimensions on the Background Remover panel, process the batch and open the output directory.', [('Open Output Settings',lambda:self.navigate(0)),('Open Export Folder',self.open_output)]))
        self.views.addWidget(self._page('Tools','Select Wire Mask to paint unwanted cables, then Apply Wire Cleanup and Save Edited Image. This is guided inpainting, not automatic object removal.', [('Open Editing Tools',lambda:self.navigate(0)),('Open Output Folder',self.open_output)]))
        self.views.addWidget(self._page('Settings','AI model: U2Net safe default to reduce RAM usage. BiRefNet General is optional via AURENIX_MODEL=birefnet-general and needs at least 12 GB free RAM. Models must be bundled for offline use.', [('Choose Output Folder',self.choose_output),('Open Output Folder',self.open_output),('Export Error Report',self.save_error_report),('Open Error Logs',self.open_error_logs)]))
        root.addWidget(self.views,1)
        ctl=self.panel();cr=QHBoxLayout(ctl)
        self.start_btn=self.button('▶  Start Processing',self.start_processing,True)
        self.pause_btn=self.button('Pause',self.pause_processing)
        self.resume_btn=self.button('Resume',self.resume_processing)
        self.stop_btn=self.button('■  Stop',self.stop_processing)
        self.retry_btn=self.button('Retry Failed',self.retry_failed)
        for x in (self.start_btn,self.pause_btn,self.resume_btn,self.stop_btn,self.retry_btn):cr.addWidget(x)
        self.progress_bar=QProgressBar();self.progress_bar.setRange(0,100);self.progress_bar.setValue(0)
        cr.addWidget(self.progress_bar,1)
        root.addWidget(ctl)
        # Always-visible, editable destination on the PRIMARY SCREEN.
        # Qt settings persist the user's last selected folder across launches.
        self.settings=QSettings('BS Broadcast','AURENIX PRO')
        previous=self.settings.value('output_destination','',type=str)
        if previous:
            self.output_dir=Path(previous).expanduser()
        destination=self.panel();dest_layout=QHBoxLayout(destination)
        dest_layout.setContentsMargins(12,8,12,8)
        label=QLabel('Output Destination:');label.setStyleSheet('color:#ffcc49;font-weight:800;')
        dest_layout.addWidget(label)
        self.output_path_edit=QLineEdit(str(self.output_dir))
        self.output_path_edit.setMinimumWidth(330)
        self.output_path_edit.setToolTip('Select an output folder with Browse, or type its full path and press Enter')
        self.output_path_edit.setStyleSheet('QLineEdit{background:#0b2c45;border:1px solid #357ca8;color:white;border-radius:6px;padding:8px;}')
        self.output_path_edit.editingFinished.connect(self.apply_output_path)
        dest_layout.addWidget(self.output_path_edit,1)
        dest_layout.addWidget(self.button('Browse…',self.choose_output))
        dest_layout.addWidget(self.button('Open Folder',self.open_output))
        root.addWidget(destination)
        self.output_label=QLabel('Output Folder: '+str(self.output_dir))
        self.output_label.setVisible(False)  # for compatibility with the recovered base worker

        self.statusBar().showMessage('Ready — low-memory mode (U2Net) | AI loads only after Start Processing')
        self.navigate(0)
        self._gpu_monitor = GpuMonitor(self)
        self._gpu_monitor.metrics.connect(self._gpu_metrics_ready)
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.update_monitors)
        self.monitor_timer.start(15000)
        # The window paints first; no GPU probing or inference imports at startup.
        QTimer.singleShot(2500, self.update_monitors)
    def _gpu_metrics_ready(self, message, percent):
        self.gpu_label.setText(message)
        self.gpu_bar.setValue(percent)

    def update_monitors(self):
        """Low-overhead RAM telemetry; GPU subprocess runs in a separate thread."""
        try:
            import psutil
            m = psutil.virtual_memory()
            used = (m.total - m.available) / (1024**3)
            total = m.total / (1024**3)
            app_mb = psutil.Process(os.getpid()).memory_info().rss / (1024**2)
            self.ram_label.setText(
                f'RAM {m.percent:.0f}% (system)\nApp: {app_mb:.0f} MB | {used:.1f}/{total:.1f} GB')
            self.ram_bar.setValue(round(m.percent))
        except Exception:
            self.ram_label.setText('RAM\nUnavailable')
            self.ram_bar.setValue(0)
        if not self._gpu_monitor.isRunning():
            self._gpu_monitor.start()

    def closeEvent(self, event):
        if self._gpu_monitor.isRunning():
            self._gpu_monitor.wait(3000)
        super().closeEvent(event)

    def add_images(self,files):
        previous=len(self.images)
        super().add_images(files)
        for idx in range(previous,len(self.images)):
            try:
                with Image.open(self.images[idx]) as img:
                    thumb=ImageOps.exif_transpose(img).convert('RGBA');thumb.thumbnail((130,90))
                canvas=Image.new('RGBA',(130,90),'white');canvas.alpha_composite(thumb,((130-thumb.width)//2,(90-thumb.height)//2))
                self.library.item(idx).setIcon(QIcon(image_to_pixmap(canvas)))
            except Exception:
                pass
        self.count.setText(f'Image List ({len(self.images)})')
    def remove_selected_image(self):
        """Remove the selected input from the queue; never delete source or output files."""
        if self.worker is not None:
            self.statusBar().showMessage('Stop the current batch before editing the image list')
            return
        row = self.library.currentRow()
        if row < 0 or row >= len(self.images):
            return
        source = self.images.pop(row)
        self.library.takeItem(row)
        self.outputs.pop(source, None)
        self.errors.discard(source)
        self.count.setText(f'Image List ({len(self.images)})')
        if not self.images:
            self.original_preview.clear()
            self.editor.set_images(None, None)
            self.selected_path = None
        else:
            self.library.setCurrentRow(min(row, len(self.images) - 1))
        self.update_controls()

    def clear_image_library(self):
        """Clear the import queue without deleting any images on disk."""
        if self.worker is not None:
            self.statusBar().showMessage('Stop the current batch before clearing the list')
            return
        self.library.clear()
        self.images.clear()
        self.outputs.clear()
        self.errors.clear()
        self.selected_path = None
        self.original_preview.clear()
        self.editor.set_images(None, None)
        self.count.setText('Image List (0)')
        self.progress_bar.setValue(0)
        self.update_controls()

    def image_failed(self, source, error):
        # Initialization errors are not image paths; do not pass them to Retry Failed.
        if source == 'AI initialization':
            self.statusBar().showMessage('AI model could not be loaded. Open Settings > Error Logs.')
            QMessageBox.critical(self, 'AI Model Error',
                'AURENIX PRO could not load the AI model.\n\n'
                + str(error) + '\n\nSee Settings > Open Error Logs for details.')
            return
        super().image_failed(source, error)
        self.statusBar().showMessage('An image failed. Use Retry Failed or export an error report.')

    def apply_wire_cleanup(self):
        try:
            self.editor.apply_wire_cleanup()
            self.statusBar().showMessage('Wire cleanup applied to preview. Click Save Edited Image to save.')
        except Exception as exc:
            QMessageBox.warning(self, 'Wire Cleanup', str(exc))

    def undo_wire_cleanup(self):
        try:
            self.editor.undo_wire_cleanup()
            self.statusBar().showMessage('Wire cleanup undone')
        except Exception as exc:
            QMessageBox.warning(self, 'Undo Wire Cleanup', str(exc))

    def save_error_report(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Export Error Report', 'AURENIX-PRO-Error-Report.log', 'Log files (*.log);;Text files (*.txt)')
        if not filename:
            return
        try:
            target = export_report(filename)
            QMessageBox.information(self, 'Report Saved',
                f'Local report saved to:\n{target}\n\nReview paths and personal information before sharing.')
        except Exception as exc:
            record_error('Report export failed', exc)
            QMessageBox.warning(self, 'Export Failed', str(exc))

    def open_error_logs(self):
        try:
            import os
            import subprocess
            folder = log_directory()
            if sys.platform == 'win32':
                os.startfile(str(folder))
            else:
                subprocess.Popen(['xdg-open', str(folder)])
        except Exception as exc:
            record_error('Opening log directory failed', exc)
            QMessageBox.warning(self, 'Log Folder', f'Logs: {log_directory()}\n{exc}')

    def apply_output_path(self):
        raw=self.output_path_edit.text().strip().strip('\"')
        if not raw:
            self.output_path_edit.setText(str(self.output_dir))
            QMessageBox.warning(self,'Output Destination','Please select a destination folder.')
            return False
        folder=Path(raw).expanduser()
        if not folder.is_absolute():
            self.output_path_edit.setText(str(self.output_dir))
            QMessageBox.warning(self,'Output Destination','Please use a full path, such as D:\\AURENIX-PRO\\Output.')
            return False
        if folder.exists() and not folder.is_dir():
            self.output_path_edit.setText(str(self.output_dir))
            QMessageBox.warning(self,'Output Destination','The selected path is a file, not a folder.')
            return False
        self.output_dir=folder
        self.output_path_edit.setText(str(folder))
        self.settings.setValue('output_destination',str(folder))
        self.output_label.setText('Output Folder: '+str(folder))
        self.statusBar().showMessage('Output destination: '+str(folder))
        return True

    def start_worker(self,files):
        if not files or self.worker is not None:return
        if not self.apply_output_path():return
        self.current_export_format = self.export_format.currentText()
        self.current_export_quality = self.export_quality.value()
        self.current_export_dpi = self.export_dpi.value()
        self.current_auto_wire_cleanup = self.auto_wire_checkbox.isChecked()
        if self.export_format.currentText() in ('JPEG', 'BMP') and self.transparent_bg.isChecked():
            self.white_bg.setChecked(True)
        self.current_bg_mode = ('transparent' if self.transparent_bg.isChecked() else
                                'custom' if self.custom_bg.isChecked() else 'white')
        self.ai_provider_label.setText('AI model: ' + os.environ.get('AURENIX_MODEL', 'u2net') + ' (isolated engine on Start)')
        super().start_worker(files)
    def export_selection_changed(self, fmt):
        if fmt in ('JPEG', 'BMP') and self.transparent_bg.isChecked():
            self.white_bg.setChecked(True)
            self.statusBar().showMessage(f'{fmt} cannot save transparency; using white background')
        self.current_export_format = fmt
        self.current_export_quality = self.export_quality.value()
        self.current_export_dpi = self.export_dpi.value()

    def image_completed(self, source, output):
        super().image_completed(source, output)
        # Follow the most recently completed batch item, rather than leaving
        # the output monitor stuck on the first imported image.
        if source in self.images:
            row = self.images.index(source)
            if self.library.currentRow() != row:
                # Qt emits currentRowChanged, which loads the new output once.
                self.library.setCurrentRow(row)
            else:
                self.select_image()
        self.statusBar().showMessage(f'Saved: {output}')

    def choose_output(self):
        folder=QFileDialog.getExistingDirectory(self,'Select Output Destination',str(self.output_dir))
        if folder:
            self.output_path_edit.setText(folder)
            self.apply_output_path()


if __name__=='__main__':
    configure_logging()
    install_exception_hooks()
    app=QApplication(sys.argv)
    splash_image=QPixmap(800,340)
    splash_image.fill(QColor('#061321'))
    painter=QPainter(splash_image)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    logo=Path(__file__).resolve().parent/'assets'/'bs_broadcast_glow.png'
    if logo.is_file():
        graphic=QPixmap(str(logo))
        painter.drawPixmap(26,28,285,158,graphic)
    painter.setPen(QColor('#ffd05b'))
    font=QFont('Segoe UI',26,QFont.Weight.Bold);font.setItalic(True)
    painter.setFont(font);painter.drawText(36,242,'AURENIX PRO BG Remover V0.7.3')
    painter.setPen(QColor('#dcecf7'));painter.setFont(QFont('Segoe UI',15))
    painter.drawText(39,284,'AI Precision Imaging')
    painter.setPen(QColor('#8daec7'));painter.setFont(QFont('Segoe UI',10))
    painter.drawText(39,321,'BS BROADCAST  •  BUY & SELL BROADCAST')
    painter.end()
    splash=QSplashScreen(splash_image)
    splash.show();app.processEvents()
    window=AurenixPro();window.show()
    splash.finish(window)
    sys.exit(app.exec())
