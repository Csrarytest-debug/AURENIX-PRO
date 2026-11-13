AURENIX PRO V0.7.3 - Startup RAM / Auto-shutdown mitigation

Changes:
- rembg/ONNX Runtime is not imported until Start Processing is pressed.
- GPU monitoring runs in a short-lived background Qt thread, after the window appears.
- Removed repeated ONNX Runtime provider imports from the 5-second GUI timer.
- System RAM monitor runs every 15 seconds; GPU check times out after 2 seconds.
- Safe default model is U2Net, chosen to reduce memory pressure on 16GB RAM / 6GB VRAM machines.
- Optional high-quality BiRefNet: set AURENIX_MODEL=birefnet-general; requires >=12GB available system RAM.
- Reject outputs >16MP; downscale inputs >8MP for processing, preserving original source files.
- Library previews decode bounded thumbnails instead of full-size RGBA images.
- PREPARE_MODEL.py now prepares BOTH models for the future standalone Windows build.

IMPORTANT: U2Net may give lower edge/matting quality than BiRefNet. No actual Windows
startup or GPU inference test is possible in this Linux environment. This ZIP contains
source code, not a compiled Windows EXE. A native Windows test is still required.

Technical scope: fixes reduce startup and image-processing memory pressure, but cannot
guarantee protection against native ONNX/CUDA out-of-memory process termination.

2026-11-11 ISOLATION UPDATE: See START_HERE_STABILITY_FIX.txt. The AI now runs in a disposable child process.
