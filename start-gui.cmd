@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -m tools.gui_installer
  if errorlevel 1 pause
  exit /b
)
where python >nul 2>nul
if not errorlevel 1 (
  python -m tools.gui_installer
  if errorlevel 1 pause
  exit /b
)
echo Python 3.11+ with Tk is required. Install from https://www.python.org/downloads/windows/
echo No dependencies were downloaded or installed. Run this launcher again after setup.
pause
exit /b 2
