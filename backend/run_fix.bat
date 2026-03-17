
@echo off
echo Starting fix at %DATE% %TIME% > fix_log.txt
C:\Users\Playdata\miniconda3\python.exe manual_schema_fix.py >> fix_log.txt 2>&1
echo Finished fix at %DATE% %TIME% >> fix_log.txt
