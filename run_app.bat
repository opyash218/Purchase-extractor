@echo off
setlocal

if exist ".venv\pyvenv.cfg" (
    set "VENV_HOME="
    for /f "tokens=1,* delims==" %%A in ('findstr /b "home =" ".venv\pyvenv.cfg"') do set "VENV_HOME=%%B"
    if defined VENV_HOME set "VENV_HOME=%VENV_HOME:~1%"
    if exist "%VENV_HOME%\python.exe" (
        echo Starting app using existing virtual environment...
        ".venv\Scripts\python.exe" -m streamlit run app.py
        goto :eof
    )
    echo Existing virtual environment is broken and points to a missing Python install.
    echo Delete .venv after installing Python 3.10 or newer, then run this script again.
    exit /b 1
)

where python >nul 2>nul
if %errorlevel%==0 (
    python -m venv .venv
) else (
    py -3 -m venv .venv 2>nul
    if errorlevel 1 (
        echo Python is not installed or not available on PATH.
        echo Install Python 3.10 or newer, then run this script again.
        exit /b 1
    )
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
