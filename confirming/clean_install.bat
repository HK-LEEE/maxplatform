@echo off
echo Cleaning and reinstalling Jupyter Data Platform Backend...

cd backend

REM 기존 가상환경 삭제
if exist venv (
    echo Removing existing virtual environment...
    rmdir /s /q venv
)

REM 새 가상환경 생성
echo Creating fresh virtual environment...
python -m venv venv

REM 가상환경 활성화
call venv\Scripts\activate

REM pip 업그레이드
echo Upgrading pip...
python -m pip install --upgrade pip

REM 기존 패키지 제거 (databases 패키지 포함)
echo Uninstalling potentially conflicting packages...
pip uninstall -y databases sqlalchemy

REM requirements.txt에서 의존성 설치
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

REM 설치 완료 확인
echo Checking installed packages...
pip list

echo.
echo Installation completed! You can now run the backend with:
echo uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause 