@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-gpu\Scripts\python.exe" (
  echo [FAILED] GPU environment missing. Run CREATE_GPU_ENV.bat first.
  pause
  exit /b 1
)
".venv-gpu\Scripts\python.exe" CHECK_GPU.py
if errorlevel 1 (
  echo [FAILED] GPU provider check. See message above.
  pause
  exit /b 1
)
".venv-gpu\Scripts\python.exe" aurenix_pro.py
if errorlevel 1 pause
