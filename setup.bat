@echo off
setlocal

REM ===============================================
REM PyPikachu Automated Setup for Windows
REM ===============================================

echo === [INFO] Checking for Python ===
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed.
    echo Download it from https://www.python.org/downloads/windows/
    pause
    exit /b 1
)
python --version

echo === [INFO] Checking GitHub connectivity ===
powershell -Command "try { Invoke-WebRequest -Uri 'https://api.github.com' -UseBasicParsing -TimeoutSec 5 } catch { exit 1 }"
if %errorlevel% neq 0 (
    echo [ERROR] Cannot reach GitHub. Check your network or VPN/firewall.
    pause
    exit /b 1
)

if defined GITHUB_TOKEN (
    echo [INFO] Found GITHUB_TOKEN. Verifying permissions...
    powershell -Command ^
      "$headers = @{ Authorization = 'token %GITHUB_TOKEN%' }; ^
       $r = Invoke-RestMethod -Uri 'https://api.github.com/user' -Headers $headers -UseBasicParsing; ^
       if (-not $r.login) { exit 1 }"
    if %errorlevel% neq 0 (
        echo [ERROR] GitHub token is invalid or lacks permission.
        pause
        exit /b 1
    )
    echo [INFO] GitHub token validated.
) else (
    echo [INFO] No GitHub token detected. Proceeding unauthenticated.
)

echo === [INFO] Cloning Repository ===
if not exist Pokemon (
    git clone https://github.com/HeIsOdin/Pokemon
    if errorlevel 1 (
        echo [ERROR] Failed to clone repository.
        pause
        exit /b 1
    )
) else (
    echo [INFO] Repository already exists. Skipping clone.
)

cd Pokemon

REM Ensure .kaggle exists
if not exist "%USERPROFILE%\.kaggle" (
    mkdir "%USERPROFILE%\.kaggle"
)

echo === [INFO] Checking for kaggle.json ===
set "KAGGLE_JSON=%USERPROFILE%\.kaggle\kaggle.json"
if not exist "%KAGGLE_JSON%" (
    echo [ERROR] kaggle.json not found at %KAGGLE_JSON%.
    echo Please download it from https://www.kaggle.com/account and place it there.
    pause
    exit /b 1
)

powershell -Command ^
    "try { ^
        $json = Get-Content '%KAGGLE_JSON%' | ConvertFrom-Json; ^
        if (-not $json.username -or -not $json.key) { exit 1 } ^
    } catch { exit 1 }"

if %errorlevel% neq 0 (
    echo [ERROR] kaggle.json is invalid or incomplete.
    pause
    exit /b 1
) else (
    echo [INFO] kaggle.json is valid.
)

echo === [INFO] Creating virtual environment 'PyPikachu' ===
python -m venv PyPikachu
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    exit /b 1
)

echo === [INFO] Activating virtual environment ===
call PyPikachu\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    exit /b 1
)

echo === [INFO] Upgrading pip ===
python -m pip install --upgrade pip

if exist requirements.txt (
    echo === [INFO] Installing dependencies ===
    python -m pip install -r requirements.txt
) else (
    echo [WARNING] requirements.txt not found. Skipping pip install.
)

echo === [INFO] Setup complete. Project is ready to run. ===
echo ===============================================
echo [INFO] Launching setup.py, app.py, and messenger.py in separate windows...
echo ===============================================

start "Setup Script" cmd /k "call PyPikachu\Scripts\activate.bat && python setup.py"
start "App Script" cmd /k "call PyPikachu\Scripts\activate.bat && python app.py"
start "Messenger Script" cmd /k "call PyPikachu\Scripts\activate.bat && python messenger.py"

echo [INFO] All scripts launched in new terminals.
echo [INFO] Keep these windows open while running the project.
pause
