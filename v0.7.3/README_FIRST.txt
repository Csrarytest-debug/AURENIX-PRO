LATEST 2026-11-11: Read RELEASE_CANDIDATE_STATUS_2026-11-11.txt first.
BUILD_WINDOWS.bat now invokes the GPU build pipeline, not the older CPU build.
No model weights or Windows EXE are included in this source archive.

AURENIX PRO — SOURCE TEST BUILD 0.6.0 (2026-11-08)
=================================================

THIS IS NOT A COMPILED WINDOWS EXE OR INSTALLER.
This package contains the recovered Python application with a rebuilt navy/gold
workspace inspired by the approved visual reference and a corrected BiRefNet model
selection. The Windows GUI has NOT been run or visually validated on this machine.

WHAT IS CONNECTED:
- Import Images / Import Folder, library selection and thumbnail previews
- Real BiRefNet General background removal through rembg's new_session
- U2Net optional via AURENIX_MODEL=u2net; no silent fallback
- Batch start, pause, resume, stop, retry failed
- HD/FHD/current/4K/custom pixel sizes, output folder, PNG with white/custom/transparent background
- Manual edit View/Erase/Restore and Save Edited PNG
- Real GPU % via nvidia-smi if installed; RAM via psutil
- Navigational panels. Image Enhancer is clearly marked NOT IMPLEMENTED; no fake upscaling.

KNOWN LIMITATIONS:
- The interface approximates the design; official logo artwork and pixel-perfect comparison
  require native Windows visual review. This is a functional prototype, not final approved fidelity.
- BiRefNet ONNX weight is NOT included. rembg can download it when internet is connected.
  Offline operation requires pre-staged genuine model weights, ordinarily in ~/.u2net;
  the setup EXE does NOT currently include the weights. Do NOT advertise offline-ready yet.
- GPU telemetry does not imply that onnxruntime's CUDA provider is enabled.
- Transparent output exported from the batch is RGBA; white/custom outputs are flattened.
- Edits are saved by the recovered core's save_edited method; verify mode compatibility.
- Clean-PC installer, batch quality, RTX acceleration and Apple Silicon DMG NOT validated.

QUICK WINDOWS SOURCE TEST:
  1. Extract package into NEW project folder, without overwriting an existing installation.
  2. In PowerShell in this folder:
      py -3.12 -m venv .venv
      .\.venv\Scripts\python.exe -m pip install -r requirements.txt
      .\.venv\Scripts\python.exe aurenix_pro.py
  3. Test Add Images, start batch, Save Edited PNG, white and transparent outputs.
     The first BiRefNet run may download a large ONNX model; verify model license.
  4. After actual Windows source test passes, run BUILD_WINDOWS.bat to create
     dist\AURENIX-PRO\AURENIX-PRO.exe and compile installer if Inno Setup exists.
  5. Keep the complete dist folder (EXE and supporting _internal files) together.
  6. Verify installer with clean system and offline model before distributing.

APPROVED DESIGN:
User-supplied AURENIX PRO gold/navy BS Broadcast reference remains authoritative.
Its gold/navy layout is being implemented without replacing real processing with mockups.

BEFORE SHARING OR SELLING:
Check both the rembg package license and the license/redistribution terms for
BiRefNet model weights and any product/brand artwork independently.

V0.6.1 HOTFIX (2026-11-08)
-------------------------
- Fixed two missing GUI callbacks: Remove and Clear All (present in the approved UI
  but absent from the recovered base class), which otherwise cause startup errors.
- Removal and clearing do NOT delete any original or exported files.
- Both actions are guarded while a batch worker is active.
- Added regression checks for 17 UI callback methods and Python compilation.
- This is still a SOURCE test build. Native Windows startup, visual fidelity,
  full AI processing, model packaging and installer portability are NOT verified.

V0.6.3 FRONTEND DELIVERY FIX (2026-11-09)
---------------------------------------
- Always-visible editable Output Destination field on the main workspace, plus
  Browse and Open Folder buttons. Selection is used by the worker at batch start.
- Path persists per Windows user across launches using QSettings.
- Added official BS Broadcast artwork based on the user's supplied BS.jpg, with
  a subtle blue glow. Branding and AURENIX PRO title use equal-width header wings
  so the title stays horizontally centered across the application window.
- Windows PyInstaller script includes the new logo asset.
- Startup remains SOURCE-ONLY; native V0.6.3 GUI, AI speed, full BiRefNet and
  standalone installed/offline operation have NOT been verified.
- No changes to your original source images or old Windows installation.

V0.6.4 WINDOWS SOURCE UPDATE (2026-11-09)
-----------------------------------------
- Added a real, branded startup splash with the supplied glowing BS BROADCAST
  artwork, AURENIX PRO title and AI Precision Imaging subtitle.
- Added main-window export selection: PNG, JPEG, WebP, TIFF, BMP; JPEG/WebP
  quality 1..100 and PNG/JPEG/TIFF output DPI 72..1200. JPEG/BMP flatten
  transparent image areas to white or selected custom background.
- Exports now use an atomic temporary-file commit in the selected output
  destination; duplicate filenames are renamed instead of overwritten.
- Batch worker and manual-edits Save use the selected export format.
- BiRefNet/U2Net session cached across batches in the same app process, so
  repeated batches avoid the expensive model reload. This DOES NOT guarantee
  faster first-image inference or enabled CUDA GPU processing.
- Worker reports actual ONNX execution provider if discoverable.
- Existing main-front Output Destination Browse/Open, remembered folder,
  BS logo and centered title remain unchanged from V0.6.3.
- Verified locally: Python syntax, static frontend callbacks, diagnostics,
  5 actual PIL format write/read tests, duplicate output names.
- NOT verified locally: PySide6 runtime (unavailable here), native Windows
  startup, GPU provider, BiRefNet segmentation quality, offline model weights,
  final installer. Do not treat this ZIP as a finished EXE.

WINDOWS V0.6.4 TEST WITHOUT REINSTALLING V0.6.2 DEPENDENCIES:
  1) Extract the entire V0.6.4 ZIP into a NEW folder.
  2) Open PowerShell in its aurenix_work folder.
  3) If dependencies are not already available in a V0.6.4 virtual env,
     create one with Python 3.12 and pip install -r requirements.txt.
     Do not copy an unrelated/partially installed virtual environment.
  4) Run: .\.venv\Scripts\python.exe aurenix_pro.py
  5) Verify main-screen Output Destination > Browse, 5 formats, and splash.
  6) Test source image and saved output with your own equipment photographs.
  7) Do not run Windows installer build until GUI and AI processing pass.
