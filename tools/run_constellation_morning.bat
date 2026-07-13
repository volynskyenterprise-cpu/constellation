@echo off
setlocal

set "REPO=C:\Users\stanv\Documents\Codex\2026-06-30\you-are-the-chief-software-architect\outputs\constellation"
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
) else (
    echo Status: FAILED>> "%LOGFILE%"
    echo Exit code: %EXIT_CODE%>> "%LOGFILE%"
)

echo Completed: %DATE% %TIME%>> "%LOGFILE%"
echo ============================================================>> "%LOGFILE%"

endlocal & exit /b %EXIT_CODE%