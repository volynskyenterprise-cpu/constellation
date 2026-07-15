@echo off
setlocal EnableDelayedExpansion

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
        set "REAL_ESTATE_DAILY=%REPO%\outputs\real-estate\daily\latest-real-estate-daily-run.json"
        set "REAL_ESTATE_REPORT=%REPO%\outputs\real-estate\daily\real-estate-daily-report.md"
        set "REAL_ESTATE_REVIEW=%REPO%\outputs\real-estate\canonical\review-queue.md"
        set "OPEN_REAL_ESTATE="
        if exist "!REAL_ESTATE_DAILY!" (
            for /f "usebackq delims=" %%S in (`powershell -NoProfile -Command "$p='!REAL_ESTATE_DAILY!'; try { $j=Get-Content -LiteralPath $p -Raw | ConvertFrom-Json; if (($j.artifacts_imported + $j.artifacts_updated + $j.canonical_assignments_created + $j.canonical_assignments_updated + $j.assignments_built + $j.review_item_count + $j.warning_count + $j.error_count) -gt 0) { 'yes' } else { 'no' } } catch { 'no' }"`) do set "OPEN_REAL_ESTATE=%%S"
        )
        if /I "!OPEN_REAL_ESTATE!"=="yes" (
            start "" code -r "%REPO%\outputs\ai-markets\briefings\morning-brief.md" "%REPO%\outputs\performance\learning-loop.md" "!REAL_ESTATE_REPORT!" "!REAL_ESTATE_REVIEW!"
            echo Review files launched in VS Code.>> "%LOGFILE%"
            echo Review files launched in VS Code including Real Estate daily outputs.>> "%LOGFILE%"
        ) else (
            start "" code -r "%REPO%\outputs\ai-markets\briefings\morning-brief.md" "%REPO%\outputs\performance\learning-loop.md"
            echo Review files launched in VS Code.>> "%LOGFILE%"
            echo Review files launched in VS Code; Real Estate daily outputs skipped because no review activity was detected.>> "%LOGFILE%"
        )
    )
) else (
    echo Status: FAILED>> "%LOGFILE%"
    echo Exit code: %EXIT_CODE%>> "%LOGFILE%"
)

echo Completed: %DATE% %TIME%>> "%LOGFILE%"
echo ============================================================>> "%LOGFILE%"

endlocal & exit /b %EXIT_CODE%
