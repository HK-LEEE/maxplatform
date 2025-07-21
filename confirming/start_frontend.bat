@echo off
echo Starting Jupyter Data Platform Frontend...

cd frontend

REM Node.js 의존성 설치
echo Installing dependencies...
npm install

REM 개발 서버 시작
echo Starting development server...
npm start

pause 