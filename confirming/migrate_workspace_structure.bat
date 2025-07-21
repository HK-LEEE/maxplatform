@echo off
echo ========================================
echo 워크스페이스 폴더 구조 마이그레이션
echo 기존: data\users\{user_id}
echo 변경: data\users\{user_id}\{workspace_id}
echo ========================================
echo.

cd /d "%~dp0\backend"

echo 가상환경 활성화 중...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo 가상환경을 찾을 수 없습니다. venv 폴더를 확인해주세요.
    pause
    exit /b 1
)

echo.
echo 마이그레이션 실행 중...
python migrate_workspace_structure.py

echo.
echo 마이그레이션이 완료되었습니다.
echo 새로운 구조로 워크스페이스가 정리되었습니다.

pause 