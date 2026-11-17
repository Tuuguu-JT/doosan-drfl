@echo off
cd /d "%~dp0"
python simulator_motion_demo.py %*
exit /b %ERRORLEVEL%
