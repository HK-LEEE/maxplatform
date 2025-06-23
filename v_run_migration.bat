@echo off
:: =================================================================
:: MySQL to MSSQL Migration Runner
:: GenbaX Platform Database Migration
:: =================================================================

echo.
echo ==========================================
echo  GenbaX MySQL to MSSQL Migration
echo ==========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.7+ and try again
    pause
    exit /b 1
)

:: Set environment variables for database connections
echo 📋 Setting up database configuration...

:: MySQL Configuration
set MYSQL_HOST=localhost
set MYSQL_PORT=3306
set MYSQL_USER=root
set MYSQL_DATABASE=jupyter_platform

:: MSSQL Configuration  
set MSSQL_SERVER=localhost
set MSSQL_DATABASE=jupyter_platform_mssql
set MSSQL_USERNAME=sa

:: Prompt for passwords
echo.
echo 🔐 Database Authentication Required
echo.
set /p MYSQL_PASSWORD="Enter MySQL password: "
set /p MSSQL_PASSWORD="Enter MSSQL password: "

echo.
echo 📊 Migration Configuration:
echo   MySQL:  %MYSQL_USER%@%MYSQL_HOST%:%MYSQL_PORT%/%MYSQL_DATABASE%
echo   MSSQL:  %MSSQL_USERNAME%@%MSSQL_SERVER%/%MSSQL_DATABASE%
echo.

:: Confirm before proceeding
set /p CONFIRM="⚠️  This will CLEAR all data in MSSQL database. Continue? (y/N): "
if /i not "%CONFIRM%"=="y" (
    echo Migration cancelled by user
    pause
    exit /b 0
)

:: Check if required Python packages are installed
echo.
echo 📦 Checking Python dependencies...
python -c "import pymysql, pyodbc" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Required Python packages not found
    echo Installing dependencies...
    pip install pymysql pyodbc
    if %ERRORLEVEL% neq 0 (
        echo ❌ Failed to install dependencies
        pause
        exit /b 1
    )
)

:: Create backup directory
if not exist "migration_backups" mkdir migration_backups

:: Run pre-migration SQL script (create MSSQL schema)
echo.
echo 🗂️  Creating MSSQL database schema...
echo Please run 'mysql_to_mssql_migration.sql' on your MSSQL server first
echo.
pause

:: Run Python migration script
echo.
echo 🚀 Starting data migration...
echo.
python mysql_to_mssql_migration.py

if %ERRORLEVEL% eq 0 (
    echo.
    echo ✅ Migration completed successfully!
    echo 📋 Check the log files for detailed results
    echo 📁 Migration logs saved in current directory
) else (
    echo.
    echo ❌ Migration failed!
    echo 📋 Check the error logs for details
)

echo.
echo 📊 Next Steps:
echo   1. Verify data in MSSQL database
echo   2. Update your application connection strings
echo   3. Test application functionality
echo   4. Update backup procedures
echo.

pause 