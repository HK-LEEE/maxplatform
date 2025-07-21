@echo off
echo Starting Jupyter Data Platform Backend with SQLite...

cd backend

REM SQLite 설정 파일로 교체
copy .env.sqlite .env

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

REM 의존성 설치
echo Installing dependencies...
pip install -r requirements.txt

REM 설치 확인
echo Verifying installation...
python -c "import fastapi, sqlalchemy; print('Dependencies OK')"

REM FastAPI 서버 시작
echo Starting FastAPI server with SQLite database...
echo API Documentation: http://localhost:8000/docs
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause 