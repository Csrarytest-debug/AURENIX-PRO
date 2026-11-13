AURENIX PRO V0.7.3 - Automatic Loose Wire Cleanup (Source Patch)
12 November 2026

WHAT CHANGED
- Automatic Wire Cleanup is ON by default under Output Settings.
- Each image receives conservative thin-strand alpha cleanup AFTER the AI
  background removal and BEFORE white/transparent background composition.
- Works in the isolated AI worker and batch processing.
- Preserves original RGB data and protects substantial product regions.
- Keeps the existing manual Wire Mask / Undo tool for complex cases.
- Uses existing OpenCV dependency; no additional GPU AI model.
- No changes to BS Broadcast branding, approved interface placement or CUDA runtime.

LIMITATIONS
This is geometric thin-strand cleanup, not object-aware wire recognition.
It is designed for thin loose cables protruding into the white background,
like the cable in the supplied Ultra-Curve Pro screenshots. It cannot safely
remove every cable crossing the equipment itself, or guarantee the exact
appearance of an AI-generated reference image. Those cases still require
manual Wire Mask, or a separately validated segmentation/inpainting model.

BUILD
1. Extract this source ZIP into a NEW directory on D:; do not overwrite the
   working EXE or the CUDA runtime that has been repaired on the PC.
2. Run ONE_CLICK_WINDOWS_BUILD.bat from this new source directory on Windows.
   Windows Python 3.12, model weights and compatible CUDA/cuDNN libraries are
   required; a build may download large dependencies.
3. Test a single image before using bulk mode; compare wires, product tags,
   physical RAM/VRAM, output monitor and saved file.

STATUS
Synthetic cleanup regression tests can pass on Linux; actual background
segmentation and Windows GPU operation cannot be verified in this environment.
This ZIP is SOURCE, not a compiled Windows EXE or final installer.
