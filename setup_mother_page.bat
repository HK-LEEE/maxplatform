@echo off
echo ========================================
echo Mother Page Setup Script
echo ========================================
echo.

echo 1. 데이터베이스 마이그레이션 실행 중...
cd backend

echo.
echo MySQL 마이그레이션 파일 위치: backend/migrations/mysql_migration_001_add_service_system.sql
echo MSSQL 마이그레이션 파일 위치: backend/migrations/mssql_migration_001_add_service_system.sql
echo.
echo 데이터베이스 종류에 따라 해당 마이그레이션 파일을 실행해주세요.
echo.

echo 2. 서비스 시스템 초기화 중...
python init_service_system.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ 서비스 시스템 초기화에 실패했습니다.
    echo 다음을 확인해주세요:
    echo - 데이터베이스가 실행 중인지 확인
    echo - 마이그레이션이 정상적으로 실행되었는지 확인
    echo - 관리자 계정이 존재하는지 확인
    pause
    exit /b 1
)

echo.
echo 3. 서비스 시스템 상태 확인 중...
python init_service_system.py check

echo.
echo ========================================
echo ✅ Mother Page 설정 완료!
echo ========================================
echo.
echo 다음 단계:
echo 1. 백엔드 서버 시작: start_backend.bat
echo 2. 프론트엔드 서버 시작: start_frontend.bat  
echo 3. 브라우저에서 접속: http://localhost:3000
echo 4. 로그인 후 Mother 페이지 확인
echo.
echo 추가 서비스를 등록하려면 관리자 계정으로 로그인하여
echo API를 통해 서비스를 추가할 수 있습니다.
echo.
pause 