@echo off
cd /d "%~dp0"
echo ========================================
echo INSTANCIA 2 - Puerto 6667
echo ========================================
echo.
python test_local_auto.py --instance 2 --gui
pause
