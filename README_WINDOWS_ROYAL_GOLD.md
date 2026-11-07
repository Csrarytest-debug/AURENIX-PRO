# AURENIX PRO — Dark Royal Gold Edition (Windows)

## Screenshot-matched interface update (2026-11-07)

The approved image is a **design reference**, not a screenshot from the installed application. The current branch now launches `RoyalGoldApp` from `royal_gold_ui.py`, with the dark royal gold header, navigation, workflow rail, dual previews, image queue, AI engine panel and live processing bar. Existing edit controls remain accessible beneath the result preview.

The output selector offers **transparent PNG** (checkerboard preview) and **pure-white PNG**. Both use the configured dimensions (default 1080 × 810), 400 DPI and original source stems. Color, sharpness, median denoise and unsharp-mask detail controls are actual PIL post-processing; quality levels vary post-processing strength, not the BiRefNet segmentation model. The UI has no fabricated processing numbers.

The build script now runs `tests/smoke_royal_gold.py` (headless Qt startup and mocked segmentation PNG export) before bundling. A passing CI build does not certify that the installed GUI is pixel-identical to the reference, that real segmentation preserves every fine detail, or that the app is portable on an unrelated clean Windows PC. Those remain manual release gates.


This branch packages the existing AURENIX PRO image background-removal application as a **Windows x64 EXE and Inno Setup installer**. It does not contain a precompiled installer. It does not change the approved workspace layout. The theme changes are confined to the UI palette in `aurenix_pro.py`.

## Current app functions
- Offline BiRefNet General background removal (bundled ONNX model)
- Optional Live AI via remove.bg (requires an API key, internet, user confirmation and possibly paid credits)
- Adjustable saturation/color enhancement
- 1080 × 810 pixel, 400 DPI, pure-white PNG output, preserving filenames
- Two preview monitors, image library, batch workflow, and editing tools

## Build on Windows
Use Windows 10/11 x64, Python **3.11 x64**, internet for dependency/model download, and Inno Setup 6. Extract this ZIP and run:

    BUILD_AURENIX_WINDOWS.bat

The script creates its own `.venv_build`, downloads the BiRefNet General model to `models/`, compiles the onedir application with PyInstaller, performs static package checks and invokes Inno Setup.

Expected output **after successful compilation**:

    Installer/AURENIX-PRO-Dark-Royal-Gold-Windows-Setup.exe

The installed application uses the EXE plus its adjacent `_internal` folder. The installer includes both, so target PCs should not need Python. **Actual clean-PC portability has not been verified.**

## GitHub Actions
The manual Windows workflow is at `.github/workflows/build-windows.yml`. Select the `windows-royal-gold-installer` branch and run the workflow; after a successful run, download the Windows installer artifact from that run. GitHub Actions must be enabled for the repository.

## Release acceptance tests
1. Inspect the real installed UI and verify Dark Royal Gold theme and original control placement.
2. Verify output 1080 × 810 pixels, 400 DPI, pure-white background and original filename handling.
3. Process a difficult dark broadcast-camera image with cables/accessories and compare all object boundaries.
4. Test multiple-image batch, pause/resume/cancel and UI responsiveness during processing.
5. Test offline on a clean Windows PC without Python, internet or manually installed AI model.
6. Test Live AI separately with an authorized remove.bg key, confirm cloud upload consent, output and billing.
7. Verify packaged application launch, Windows shortcuts and uninstaller.
8. Check package licenses, signed binaries and security scanning before public distribution.

## Limitations
- The current offline engine uses CPU ONNX Runtime; this packaging does **not** guarantee faster processing or GPU acceleration.
- Color enhancement currently adjusts saturation, not exposure/contrast.
- This pipeline is source and build automation. Neither the EXE nor the installer has been compiled or tested in this chat.
- No application credentials or API keys are included in the package.


## Approved release refinements (November 2026)

- Window title and visible header now read **AURENIX PRO — AI Background Remover**, without the words “Dark Royal Gold Edition” in the top text. The approved dark-and-gold visual theme is retained.
- Upper-right resource readout shows live CPU/RAM, and NVIDIA GPU utilization/VRAM when `nvidia-smi` is available. Apple Silicon GPU load is shown as unavailable rather than a fabricated value.
- Default export removes the source background and composites onto **pure white (#FFFFFF)**. Users may alternatively select a custom HEX background or transparent PNG.
- Original BS Broadcast artwork is exclusive to AURENIX PRO. It must be provided at `assets/bs_broadcast_logo.png`. **The original PNG is not yet checked into the repository**; an installer without it is not the final branded release. See `assets/README.md`.
- CI smoke tests do not replace installation, offline AI inference, and visual inspection on clean Windows and macOS machines.
