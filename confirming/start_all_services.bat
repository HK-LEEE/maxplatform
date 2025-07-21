@echo off
echo Starting All Services for Central Authentication System...
echo.

echo This will start:
echo - Auth Server (Port 8001)
echo - Backend API Server (Port 8000)
echo - Client Application (Port 3000)
echo.

echo Press any key to continue...
pause

echo.
echo Starting Auth Server...
start "Auth Server" cmd /k "start_auth_server.bat"

timeout /t 5

echo.
echo Starting Backend API Server...
start "Backend API" cmd /k "start_backend_api.bat"

timeout /t 5

echo.
echo Starting Client Application...
start "Client" cmd /k "start_client.bat"

echo.
echo All services are starting up...
echo.
echo You can access the application at:
echo http://localhost:3000
echo.
echo Auth Server API docs: http://localhost:8001/docs
echo Backend API docs: http://localhost:8000/docs
echo.

pause 