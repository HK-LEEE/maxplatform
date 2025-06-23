@echo off
echo Starting Backend API Server...
echo.

cd backend-api

echo Installing Python dependencies...
pip install -r requirements.txt

echo.
echo Starting Backend API Server on port 8000...
python main.py

pause 