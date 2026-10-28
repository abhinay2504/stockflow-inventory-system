@echo off
setlocal
call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
  echo Creating test virtual environment...
  py -m venv .venv
  call .venv\Scripts\activate.bat
)
python -m pip install -r requirements-test.txt
if errorlevel 1 goto failed
python -m playwright install chromium
if errorlevel 1 goto failed
python -m unittest -v test_app.py
if errorlevel 1 goto failed
echo.
echo Unit/integration tests passed. Start the app with run_local.bat, then run tests\e2e_playwright.py in another terminal.
pause
exit /b 0
:failed
echo Test setup or tests failed. Read the error above and fix it before deployment.
pause
exit /b 1
