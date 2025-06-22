@echo off
setlocal EnableDelayedExpansion

echo ===============================================
echo   PyPikachu Enhanced Setup for Windows
echo ===============================================

REM === Python Check ===
echo === [INFO] Checking for Python ===
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed.
    echo Download it from https://www.python.org/downloads/windows/
    pause
    exit /b 1
)
python --version

REM === GitHub Check ===
echo === [INFO] Checking GitHub connectivity ===
powershell -Command "try { Invoke-WebRequest -Uri 'https://api.github.com' -UseBasicParsing -TimeoutSec 5 } catch { exit 1 }"
if %errorlevel% neq 0 (
    echo [ERROR] Cannot reach GitHub. Check your internet connection or proxy.
    pause
    exit /b 1
)

REM === Optional: GitHub Token Check ===
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

REM === Clone Repository ===
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

REM === Check for kaggle.json ===
echo === [INFO] Checking for kaggle.json ===
set "KAGGLE_DIR=%USERPROFILE%\.kaggle"
set "KAGGLE_JSON=%KAGGLE_DIR%\kaggle.json"

if not exist "%KAGGLE_DIR%" (
    mkdir "%KAGGLE_DIR%"
)

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

REM === PostgreSQL or Docker Check ===
echo === [INFO] Checking for PostgreSQL ===
where psql >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] PostgreSQL is installed.
    psql --version
) else (
    echo [WARNING] PostgreSQL not found. Checking for Docker...
    where docker >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Docker is not installed. Cannot continue without PostgreSQL or Docker.
        pause
        exit /b 1
    )
    echo [INFO] Docker is installed.

    REM Check if PostgreSQL container is running
    for /f "tokens=*" %%i in ('docker ps --filter "ancestor=postgres" --format "{{.Names}}"') do (
        set "CONTAINER_RUNNING=1"
    )
    if defined CONTAINER_RUNNING (
        echo [INFO] A PostgreSQL container is running.
    ) else (
        echo [WARNING] No running PostgreSQL containers found.
        for /f "tokens=*" %%i in ('docker images --format "{{.Repository}}"') do (
            if "%%i"=="postgres" set "IMAGE_FOUND=1"
        )
        if defined IMAGE_FOUND (
            echo [INFO] PostgreSQL image found. You can start it with:
            echo     docker run --name pg_container -e POSTGRES_PASSWORD=yourpassword -d -p 5432:5432 postgres
        ) else (
            echo [INFO] Pull and run PostgreSQL with:
            echo     docker pull postgres
            echo     docker run --name pg_container -e POSTGRES_PASSWORD=yourpassword -d -p 5432:5432 postgres
        )
    )
)

REM === Create Virtual Environment ===
echo === [INFO] Creating virtual environment 'PyPikachu' ===
python -m venv PyPikachu
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

REM === Activate Virtual Environment ===
echo === [INFO] Activating virtual environment ===
call PyPikachu\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

REM === Upgrade pip ===
python -m pip install --upgrade pip

REM === Install dependencies ===
if exist requirements.txt (
    echo === [INFO] Installing dependencies ===
    python -m pip install -r requirements.txt
) else (
    echo [WARNING] requirements.txt not found. Skipping pip install.
)

REM === Ensure logs directory ===
if not exist logs (
    mkdir logs
)

REM === Launch Scripts in New Terminals ===
echo === [INFO] Setup complete. Launching scripts in new terminals ===
start "Setup Script" cmd /k "call PyPikachu\Scripts\activate.bat && python setup.py > logs/setup.log 2>&1"
start "App Script" cmd /k "call PyPikachu\Scripts\activate.bat && python app.py > logs/app.log 2>&1"
start "Messenger Script" cmd /k "call PyPikachu\Scripts\activate.bat && python messenger.py > logs/messenger.log 2>&1"

echo [INFO] All scripts launched. Check logs in the 'logs' directory.
pause
