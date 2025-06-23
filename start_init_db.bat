@echo off
echo ==============================================
echo   Jupyter Data Platform - Database Setup
echo ==============================================
echo.

cd backend

echo 📦 Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo 🗄️ Initializing database...
python init_db.py
if errorlevel 1 (
    echo ❌ Database initialization failed
    pause
    exit /b 1
)

echo.
echo ✅ Database setup completed successfully!
echo.
echo 📋 Default accounts created:
echo   👑 Admin: admin@jupyter-platform.com / admin123!
echo   👤 Test User: test@example.com / test123!
echo.
echo 🚀 You can now start the backend server with:
echo   start_backend_sqlite.bat
echo.
pause 