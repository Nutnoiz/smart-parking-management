@echo off
setlocal
cd /d "%~dp0"

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker was not found. Please install Docker Desktop and run this file again.
  pause
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
    echo Starting Docker Desktop...
    start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
  ) else (
    echo Please start Docker Desktop, then run this file again.
    pause
    exit /b 1
  )
  echo Waiting for Docker Desktop to be ready...
  for /l %%i in (1,1,30) do (
    timeout /t 2 /nobreak >nul
    docker info >nul 2>&1
    if not errorlevel 1 goto docker_ready
  )
  echo Docker Desktop did not become ready. Please check Docker Desktop and try again.
  pause
  exit /b 1
)

:docker_ready
if not exist ".env" (
  echo Creating secure local configuration...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\initialize-local-env.ps1"
  if errorlevel 1 (
    echo Could not create the local configuration file.
    pause
    exit /b 1
  )
)

echo Starting Smart Parking...
docker compose up --build -d
if errorlevel 1 (
  echo Could not start Smart Parking. Check the Docker Desktop status and try again.
  pause
  exit /b 1
)

echo Waiting for the web page...
for /l %%i in (1,1,30) do (
  curl -fsS http://localhost:8080/ >nul 2>&1
  if not errorlevel 1 goto open_page
  timeout /t 2 /nobreak >nul
)

:open_page
start "" "http://localhost:8080"
echo Smart Parking is running at http://localhost:8080
endlocal
