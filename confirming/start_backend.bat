@echo off
echo Starting Jupyter Data Platform Backend...

cd backend

REM 가상환경이 없으면 생성
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM 가상환경 활성화
call venv\Scripts\activate

REM pip 업그레이드
echo Upgrading pip...
python -m pip install --upgrade pip

REM 충돌하는 packages 패키지가 있으면 제거
echo Checking for conflicting packages...
pip uninstall -y databases --quiet 2>nul

REM 의존성 설치
echo Installing dependencies...
pip install -r requirements.txt

REM 설치 확인
echo Verifying installation...
python -c "import fastapi, sqlalchemy; print('Dependencies OK')"

REM FastAPI 서버 시작
echo Starting FastAPI server on http://localhost:8000...
echo API Documentation: http://localhost:8000/docs
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause 