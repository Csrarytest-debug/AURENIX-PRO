@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo [AURENIX PRO] Windows Dark Royal Gold build

if not exist "aurenix_pro.py" (echo [FAIL] Missing aurenix_pro.py & exit /b 10)
if not exist "background_remover_pro.py" (echo [FAIL] Missing background_remover_pro.py & exit /b 11)
if not exist "windows_runtime_hook.py" (echo [FAIL] Missing Windows runtime hook & exit /b 12)

if not exist ".venv_build\Scripts\python.exe" (
  python -m venv .venv_build
  if errorlevel 1 (echo [FAIL] Python 3.11 environment creation failed & exit /b 13)
)
set "PYTHON=.venv_build\Scripts\python.exe"
"%PYTHON%" -c "import sys,struct; assert sys.version_info[:2]==(3,11) and struct.calcsize('P')*8==64, 'Python 3.11 x64 required'"
if errorlevel 1 exit /b 14
"%PYTHON%" -m pip install --upgrade pip
if errorlevel 1 exit /b 15
"%PYTHON%" -m pip install -r requirements-windows-build.txt
if errorlevel 1 exit /b 16
"%PYTHON%" -m pip check
if errorlevel 1 exit /b 17
"%PYTHON%" -m pip freeze > build-dependencies-lock.txt
"%PYTHON%" -m py_compile aurenix_pro.py background_remover_pro.py windows_runtime_hook.py
if errorlevel 1 exit /b 18
set "QT_QPA_PLATFORM=offscreen"
"%PYTHON%" -m unittest discover -s tests -p "test_aurenix_gui.py" -v
if errorlevel 1 (echo [FAIL] GUI startup or image-library tests failed & exit /b 19)
set "QT_QPA_PLATFORM="

if not exist "models" mkdir models
set "U2NET_HOME=%CD%\models"
echo [MODEL] Download/validate BiRefNet General offline model
"%PYTHON%" -c "from rembg import new_session; new_session('birefnet-general'); print('BiRefNet model ready')"
if errorlevel 1 (echo [FAIL] Model download or initialization failed & exit /b 20)

"%PYTHON%" -m PyInstaller --noconfirm --clean --windowed --onedir --name "AURENIX PRO" --runtime-hook windows_runtime_hook.py --add-data "models;models" --collect-all rembg --collect-all onnxruntime --collect-all pymatting aurenix_pro.py
if errorlevel 1 (echo [FAIL] PyInstaller build failed & exit /b 30)

"%PYTHON%" "tests\verify_windows_package.py"
if errorlevel 1 (echo [FAIL] Package verification failed & exit /b 31)

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo [BLOCKED] Inno Setup 6 is not installed. App folder is in dist\AURENIX PRO.
  exit /b 40
)
"%ISCC%" "AURENIX-PRO-Windows-Setup.iss"
if errorlevel 1 exit /b 41
if not exist "Installer\AURENIX-PRO-Dark-Royal-Gold-Windows-Setup.exe" exit /b 42

echo [BUILD COMPLETE] Installer\AURENIX-PRO-Dark-Royal-Gold-Windows-Setup.exe
echo [TEST REQUIRED] Install on a clean Windows PC and test offline BiRefNet and Live AI.
endlocal
exit /b 0
