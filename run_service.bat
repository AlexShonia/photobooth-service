@echo off
SETLOCAL

cd /d "D:\photobooth-service"

timeout /t 10 /nobreak >nul

call "venv\Scripts\activate"

echo Service is ready.

fastapi dev main.py --host 0.0.0.0 --port 8011
