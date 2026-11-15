@echo off
echo ===================================================
echo     Starting AnemiaWatch Healthcare Application
echo         "Your health, one scan at a time."
echo ===================================================
echo.
echo [1/2] Verifying Python Environment & Trained ML Models...
python backend/train_models.py
echo.
echo [2/2] Launching AnemiaWatch Server at http://127.0.0.1:8000 ...
start http://127.0.0.1:8000
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
pause
