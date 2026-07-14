@echo off
setlocal

for %%I in ("%~dp0..") do set "REPO=%%~fI"

set "LOGDIR=%REPO%\outputs\automation"
set "LOGFILE=%LOGDIR%\morning-run.log"

cd /d "%REPO%"

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

set "PYTHONPATH=src"

echo.>> "%LOGFILE%"
echo ============================================================>> "%LOGFILE%"
echo Constellation Morning Run>> "%LOGFILE%"
echo Started: %DATE% %TIME%>> "%LOGFILE%"
echo Repository: %REPO%>> "%LOGFILE%"
echo ============================================================>> "%LOGFILE%"

python -m constellation workflow run Morning >> "%LOGFILE%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

if "%EXIT_CODE%"=="0" (
    echo Status: SUCCESS>> "%LOGFILE%"
    where code >nul 2>&1
    if errorlevel 1 (
        echo Review launch warning: VS Code command not available.>> "%LOGFILE%"
    ) else (
        start "" code -r "%REPO%\outputs\ai-markets\briefings\morning-brief.md" "%REPO%\outputs\performance\learning-loop.md"
        echo Review files launched in VS Code.>> "%LOGFILE%"
    )
) else (
    echo Status: FAILED>> "%LOGFILE%"
    echo Exit code: %EXIT_CODE%>> "%LOGFILE%"
)

echo Completed: %DATE% %TIME%>> "%LOGFILE%"
echo ============================================================>> "%LOGFILE%"

endlocal & exit /b %EXIT_CODE%
