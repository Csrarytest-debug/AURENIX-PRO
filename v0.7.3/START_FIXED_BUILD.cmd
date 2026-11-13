@echo off
setlocal EnableExtensions
set "DEST=D:\AURENIX73_CUDA12_BUILD"
set "SOURCE=%~dp0"
REM Remove trailing backslash: ROBOCOPY may interpret \" as an escaped quote.
if "%SOURCE:~-1%"=="\" set "SOURCE=%SOURCE:~0,-1%"

echo ================================================================
echo AURENIX PRO V0.7.3 - Corrected CUDA 12 Windows build launcher
echo ================================================================
echo Source: "%SOURCE%"
echo Destination: "%DEST%"
if not exist "D:\" (
 echo [FAILED] D: drive not found.
 pause
 exit /b 1
)
if not exist "%SOURCE%\ONE_CLICK_WINDOWS_BUILD.bat" (
 echo [FAILED] ONE_CLICK_WINDOWS_BUILD.bat is missing beside this script.
 echo Place START_FIXED_BUILD.cmd inside the extracted source folder.
 pause
 exit /b 1
)
if not exist "%DEST%" mkdir "%DEST%"
if errorlevel 1 (
 echo [FAILED] Cannot create "%DEST%".
 pause
 exit /b 1
)
echo [1/2] Copying source to short Windows path...
robocopy "%SOURCE%" "%DEST%" /E /R:1 /W:1 /XD .venv-gpu dist build __pycache__ .git /XF *.pyc *.pyo GPU_INSTALL_LOG.txt .cuda12_deps_ready /NFL /NDL /NJH /NJS /NP
set "COPY_RESULT=%errorlevel%"
if %COPY_RESULT% GEQ 8 (
 echo [FAILED] ROBOCOPY exit code %COPY_RESULT%.
 echo Check source and destination paths above.
 pause
 exit /b %COPY_RESULT%
)
if not exist "%DEST%\ONE_CLICK_WINDOWS_BUILD.bat" (
 echo [FAILED] Build script was not copied to "%DEST%".
 pause
 exit /b 1
)
echo [2/2] Running CUDA 12 build workflow...
cd /d "%DEST%"
call "ONE_CLICK_WINDOWS_BUILD.bat"
set "RESULT=%errorlevel%"
echo.
if not "%RESULT%"=="0" (
 echo [FAILED] Build stopped with exit code %RESULT%.
 echo Review D:\AURENIX73_CUDA12_BUILD\GPU_INSTALL_LOG.txt if dependency installation failed.
) else (
 echo [BUILD SCRIPT COMPLETED] Check dist\AURENIX-PRO\AURENIX-PRO.exe
 echo GPU inference, wire cleanup, and clean-PC portability still require validation.
)
echo.
pause
exit /b %RESULT%
