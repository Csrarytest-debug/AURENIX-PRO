@echo off
setlocal
cd /d "%~dp0"
call "%~dp0RUN_GPU_WINDOWS.bat"
exit /b %errorlevel%
