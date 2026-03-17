@echo off
echo [1/3] Terminating any existing python/daphne processes...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM daphne.exe /T 2>nul

echo [2/3] Running surgical database fix...
python surgical_db_fix.py

echo [3/3] Verifying migrations...
python manage.py migrate

echo Done! Please restart your server now.
pause
