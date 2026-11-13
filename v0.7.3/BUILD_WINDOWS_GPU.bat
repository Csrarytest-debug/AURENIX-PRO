@echo off
setlocal
cd /d "%~dp0"
echo AURENIX PRO V0.7.3 - GPU standalone build
if not exist ".venv-gpu\Scripts\python.exe" (
  echo [FAILED] Isolated GPU environment is missing.
  echo Run CREATE_GPU_ENV.bat on the Windows build machine first.
  exit /b 1
)
".venv-gpu\Scripts\python.exe" CHECK_GPU.py
if errorlevel 1 (
  echo [FAILED] CUDA provider is not available in the GPU build environment.
  exit /b 1
)
for %%F in (test_*.py) do (
  ".venv-gpu\Scripts\python.exe" "%%F"
  if errorlevel 1 (
    echo [FAILED] Source regression: %%F
    exit /b 1
  )
)
".venv-gpu\Scripts\python.exe" PREPARE_MODEL.py
if errorlevel 1 (
  echo [FAILED] Model weights were not prepared. No incomplete installer will be produced.
  exit /b 1
)
".venv-gpu\Scripts\python.exe" -m PyInstaller --clean --noconfirm --windowed --onedir --name "AURENIX-PRO" --collect-all rembg --collect-all onnxruntime --collect-all pymatting --collect-all nvidia.cudnn --collect-all nvidia.cublas --collect-all nvidia.cuda_runtime --collect-all nvidia.cuda_nvrtc --add-data "assets;assets" --add-data "models;models" aurenix_pro.py
if errorlevel 1 (
  echo [FAILED] GPU EXE packaging failed. No installer will be produced.
  exit /b 1
)
if not exist "dist\AURENIX-PRO\AURENIX-PRO.exe" exit /b 1
set "MODEL_FOUND="
for /r "dist\AURENIX-PRO" %%F in (*.onnx) do set "MODEL_FOUND=1"
if not defined MODEL_FOUND (
  echo [FAILED] No ONNX weights were packaged; refusing to build installer.
  exit /b 1
)
echo [BUILT - NOT VALIDATED] dist\AURENIX-PRO\AURENIX-PRO.exe
REM Real packaged GPU smoke test is mandatory before installer creation.
".venv-gpu\Scripts\python.exe" VERIFY_WINDOWS_GPU.py "dist\AURENIX-PRO\AURENIX-PRO.exe"
if errorlevel 1 (
  echo [FAILED] Packaged GPU inference smoke test failed. Installer withheld.
  exit /b 1
)
echo [PASS] Packaged GPU inference smoke test passed on this build machine.
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
  "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "AURENIX-PRO.iss"
  if errorlevel 1 exit /b 1
  echo [BUILT - NOT VALIDATED] Installer\AURENIX-PRO-BG-Remover-V0.7.3-Setup.exe
) else (
  echo [INFO] Inno Setup 6 not found. Portable folder created, installer not built.
)
echo IMPORTANT: Run GPU inference, batch, and clean-PC tests before release.
exit /b 0
