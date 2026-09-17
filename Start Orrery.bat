@echo off
setlocal
chcp 65001 >nul
set PYTHONDONTWRITEBYTECODE=1
set PYTHONUTF8=1
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>nul
  if not errorlevel 1 (
    py -3 -B "%~dp0launch.py" %*
    if errorlevel 1 pause
    exit /b
  )
)
where python >nul 2>nul
if not errorlevel 1 (
  python -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>nul
  if not errorlevel 1 (
    python -B "%~dp0launch.py" %*
    if errorlevel 1 pause
    exit /b
  )
)
where uv >nul 2>nul
if not errorlevel 1 (
  for /f "delims=" %%D in ('uv tool dir 2^>nul') do (
    if exist "%%D\linecast\Scripts\python.exe" (
      "%%D\linecast\Scripts\python.exe" -B "%~dp0launch.py" %*
      if errorlevel 1 pause
      exit /b
    )
  )
)
echo.
echo Could not locate the Python environment used by Linecast.
echo Run this from the terminal where your existing Linecast works.
echo Use Windows Terminal for the best display.
pause
exit /b 1
