AURENIX PRO BG Remover V0.7.3 — GPU + Guided Wire Cleanup SOURCE CANDIDATE

NOT a compiled or clean-PC-tested Windows EXE/installer. No GPU inference or automatic wire removal claim.

NEW: Wire Mask tool in Editing Tools. After processing an image, select Wire Mask, paint only unwanted wires, click Apply Wire Cleanup, inspect the result, then Save Edited Image. Undo Wire Cleanup is available. Uses OpenCV local inpainting and may create artifacts on complex backgrounds. It does NOT automatically identify cables, reconstruct missing objects, or guarantee the supplied Sony reference quality. For isolated unwanted wires on white backgrounds, use small brush sizes. Do not mask genuine camera cables unless they should be removed.

GPU: Run CREATE_GPU_ENV.bat to create an isolated .venv-gpu, then CHECK_GPU.py reports available ONNX providers. The driver-reported CUDA 13.1 is a maximum supported API version, not proof the correct CUDA/cuDNN runtime is installed. Actual BiRefNet inference must still be tested on Windows. The CPU requirements and existing environments remain untouched.

Build only after Windows UI, image quality, and CUDA session validation. Existing BUILD_WINDOWS.bat uses .venv and is NOT a GPU release pipeline.

RESOURCE PATCH 2026-11-11: default U2Net for lower memory; lazy AI startup; asynchronous GPU monitoring. See RESOURCE_FIX_README.txt. Windows runtime still unverified.

ISOLATED WORKER PATCH: This source ZIP now includes an isolated inference child, memory watchdog, file IPC and a packaged-GPU smoke-test build gate. Native Windows verification is still pending.
