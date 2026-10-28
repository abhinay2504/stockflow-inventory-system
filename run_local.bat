@echo off
setlocal

if not exist .venv (
  py -m venv .venv
)
if errorlevel 1 (
  echo Failed to create virtual environment.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo Failed to activate virtual environment.
  pause
  exit /b 1
)

python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed. Check your internet connection and Python installation.
  pause
  exit /b 1
)

if not defined SECRET_KEY (
  for /f %%i in ('python -c "import secrets; print(secrets.token_hex(32))"') do set "SECRET_KEY=%%i"
)

if not defined SECRET_KEY (
  echo ERROR: Could not generate SECRET_KEY.
  pause
  exit /b 1
)

echo Starting StockFlow...
python app.py
pause
