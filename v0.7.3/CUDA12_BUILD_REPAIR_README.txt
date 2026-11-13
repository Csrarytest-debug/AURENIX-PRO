AURENIX PRO V0.7.3 - Windows build dependency repair (12 Nov 2026)

ISSUE: The earlier auto-wire build attempted a large pip install that failed
with OSError [Errno 22] Invalid argument during nvidia-cuda-runtime installation.
A partially created .venv-gpu caused the old one-click script to skip retry.

CHANGES:
1. CUDA 12 / cuDNN 9 explicitly selected (onnxruntime-gpu==1.22.0),
   avoiding the automatic CUDA 13 dependencies previously observed.
2. A short, separate D:\AURENIX73_CUDA12_BUILD source and environment path.
3. A short D:\AURENIX_TMP pip temporary directory and no pip wheel cache.
4. A dependency-ready marker written only after installation + pip check.
5. Error messages and GPU_INSTALL_LOG.txt on failure.
6. Existing working EXE, source photos and installed CUDA repair untouched.

TO USE: Extract the ZIP into any folder on D:, open its single source folder,
and double-click START_FIXED_BUILD.cmd. The script copies source files to the
short build path and starts the corrected one-click GPU build. Python 3.12,
Windows and network access are required. This can download gigabytes of wheels
and AI models. Inno Setup 6 is needed for an installer.

NOT A COMPILED EXE: This source patch is not yet Windows-tested. Even after
compilation, GPU inference, RAM/VRAM safety and wire cleanup on real product
photos must pass before calling the application a final release.
