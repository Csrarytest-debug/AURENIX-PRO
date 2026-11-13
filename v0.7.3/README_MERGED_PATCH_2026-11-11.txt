AURENIX PRO V0.7.3 — MERGED SOURCE PATCH (2026-11-11)

This package combines the uploaded corrected V0.7.3 ZIP with the two newer standalone Python files:
  aurenix_pro29.py -> aurenix_pro.py
  background_remover_pro29.py -> background_remover_pro.py

Included changes from the uploaded files:
- Output monitor follows the most recently completed batch item.
- Windows cuDNN 9 DLL availability check before attempting CUDA model initialization.
- RAM guard before model loading and per image (90% threshold).
- Memory cleanup after images and after batches.
- App core version label updated to V0.7.3.

Also updated two outdated source tests to match the current call signatures/formatting.
Added RUN_GPU_WINDOWS.bat to launch the source using the separate GPU environment.

VERIFIED IN NON-WINDOWS TEST ENVIRONMENT:
- Python syntax compilation for all included .py files.
- Seven source/export/diagnostics regression scripts (these do not test native Windows GUI, GPU inference or background-removal quality).

NOT VERIFIED:
- Windows application startup and native layout.
- Actual RTX 4050 CUDA execution, BiRefNet model availability, batch speed/stability.
- Quality of white-background processing, product-tag preservation, wire inpainting.
- Windows portable EXE, Setup EXE, clean-PC offline operation.

UPDATE: BUILD_WINDOWS.bat now invokes BUILD_WINDOWS_GPU.bat, which uses .venv-gpu and checks for bundled AI weights. The AI weights are not included in this source archive. See RELEASE_CANDIDATE_STATUS_2026-11-11.txt.

To test source on Windows, extract into a NEW folder. Never overwrite the current installed app without backing it up. Use the README_FIRST.txt instructions for CPU or CREATE_GPU_ENV.bat followed by RUN_GPU_WINDOWS.bat for GPU environment testing.
