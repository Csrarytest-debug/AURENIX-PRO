@echo off
setlocal
cd /d "%~dp0"
call "%~dp0BUILD_WINDOWS_GPU.bat"
exit /b %errorlevel%
