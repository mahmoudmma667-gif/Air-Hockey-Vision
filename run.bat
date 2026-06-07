@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
echo.
echo  ======================================
echo    AIR HOCKEY VISION - Starting...
echo  ======================================
echo.
"C:\Users\DELL\Desktop\مشاريع\HCC_V7_COMPLETE_PROJECT\tools\python312\python.exe" main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Game crashed. Check the output above.
    pause
)
