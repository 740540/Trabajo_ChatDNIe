@echo off
cd /d "%~dp0"
echo ========================================
echo INSTANCIA 1 - Puerto 6666
echo ========================================
echo.
python test_local_auto.py --instance 1 --gui
pause
