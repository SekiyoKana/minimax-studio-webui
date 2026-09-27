@echo off
chcp 65001 >nul
setlocal
set "ENTRY_SCRIPT=%~dp0install_minimax_comfyui.ps1"
if not exist "%ENTRY_SCRIPT%" (
  echo Missing PowerShell installer: "%ENTRY_SCRIPT%"
  pause
  exit /b 2
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%ENTRY_SCRIPT%" %*
set "INSTALL_EXIT_CODE=%ERRORLEVEL%"
if not "%INSTALL_EXIT_CODE%"=="0" (
  echo.
  echo Installation stopped with exit code %INSTALL_EXIT_CODE%.
)
echo.
pause
exit /b %INSTALL_EXIT_CODE%
