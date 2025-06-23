@echo off
echo Setting up PostgreSQL Database and Migrating from MySQL...
echo.

cd database

echo Installing Python dependencies for migration...
pip install -r requirements.txt

echo.
echo Creating PostgreSQL schema...
psql -U postgres -d auth_system -f schema.sql

echo.
echo Running data migration from MySQL to PostgreSQL...
python migrate_users.py

echo.
echo Database setup completed!
pause 