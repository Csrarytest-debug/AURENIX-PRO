@echo off
setlocal
cd /d "%~dp0"
echo This CUDA12 release uses ONE_CLICK_WINDOWS_BUILD.bat.
echo For a new short-path installation run START_FIXED_BUILD.cmd instead.
call "%~dp0ONE_CLICK_WINDOWS_BUILD.bat"
pause
exit /b %errorlevel%
