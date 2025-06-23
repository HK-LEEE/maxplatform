@echo off
echo Starting Central Authentication Server...
echo.

cd auth-server

echo Installing Python dependencies...
pip install -r requirements.txt

echo.
echo Starting Auth Server on port 8001...
python main.py

pause 