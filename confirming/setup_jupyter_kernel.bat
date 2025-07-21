@echo off
echo ========================================
echo Jupyter 커널 설정 도구
echo 커널 시작 문제 해결을 위한 설정
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
echo 필요한 패키지 업데이트 중...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Jupyter 커널 설정 실행 중...
python setup_jupyter_kernel.py

echo.
echo ========================================
echo 설정이 완료되었습니다.
echo 이제 워크스페이스에서 Jupyter Lab을 시작해보세요.
echo ========================================

pause 