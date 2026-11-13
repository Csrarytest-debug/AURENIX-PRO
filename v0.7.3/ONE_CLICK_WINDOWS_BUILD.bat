@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ================================================================
echo AURENIX PRO V0.7.3 - CUDA 12 / cuDNN 9 Windows build
 echo ================================================================
if not exist "D:\" (
 echo [FAILED] D: drive is required for the short-path repair build.
 exit /b 1
)
if not exist "D:\AURENIX_TMP" mkdir "D:\AURENIX_TMP"
set "TMP=D:\AURENIX_TMP"
set "TEMP=D:\AURENIX_TMP"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_NO_CACHE_DIR=1"
set "PIP_DEFAULT_TIMEOUT=120"
if not exist ".venv-gpu\Scripts\python.exe" (
 echo [1/5] Creating a fresh GPU environment...
 py -3.12 -m venv .venv-gpu
 if errorlevel 1 (
  echo [FAILED] Python 3.12 is required. No existing application changed.
  exit /b 1
 )
)
if not exist ".cuda12_deps_ready" (
 echo [2/5] Installing pinned CUDA 12 dependencies. This may take time...
 ".venv-gpu\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
 if errorlevel 1 exit /b 1
 ".venv-gpu\Scripts\python.exe" -m pip --log "GPU_INSTALL_LOG.txt" install --prefer-binary --no-cache-dir -r requirements-gpu.txt
 if errorlevel 1 (
  echo [FAILED] Dependency installation. See GPU_INSTALL_LOG.txt
  echo [INFO] The environment will be retried on the next run.
  exit /b 1
 )
 ".venv-gpu\Scripts\python.exe" -m pip check
 if errorlevel 1 (
  echo [FAILED] Incompatible installed packages. See GPU_INSTALL_LOG.txt
  exit /b 1
 )
 ".venv-gpu\Scripts\python.exe" -c "import onnxruntime as o; assert o.__version__.startswith('1.22.'), o.__version__"
 if errorlevel 1 (
  echo [FAILED] Expected ONNX Runtime GPU 1.22.x, not a CUDA 13 runtime.
  exit /b 1
 )
 > ".cuda12_deps_ready" echo CUDA12_CUDNN9_PINNED
) else (
 echo [2/5] Previously verified CUDA 12 environment found.
)
echo [3/5] Checking GPU provider...
".venv-gpu\Scripts\python.exe" CHECK_GPU.py
if errorlevel 1 (
 echo [FAILED] CUDA provider check. See CUDA logs. No installer built.
 exit /b 1
)
echo [4/5] Building application and testing packaged inference...
call "%~dp0BUILD_WINDOWS_GPU.bat"
if errorlevel 1 (
 echo [FAILED] EXE build or GPU smoke test. No release certified.
 exit /b 1
)
echo [5/5] Build workflow finished. Check dist and Installer folders.
exit /b 0
