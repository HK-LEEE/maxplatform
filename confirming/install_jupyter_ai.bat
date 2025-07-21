@echo off
title Jupyter AI 환경 설치
echo ========================================
echo     🤖 Jupyter AI 환경 설치 시작
echo ========================================

echo.
echo 📦 기존 패키지 정리 중...
pip uninstall jupyter-ai jupyter-ai-magics langchain -y 2>nul

echo.
echo 📥 최신 패키지 설치 중...
cd backend
pip install -r requirements.txt

echo.
echo 🔧 Jupyter AI Extension 활성화...
jupyter labextension enable jupyter-ai

echo.
echo ✅ 설치 완료! 다음 단계:
echo.
echo 1. backend/.env 파일에서 API 키 설정:
echo    OPENAI_API_KEY=your-openai-key-here
echo    ANTHROPIC_API_KEY=your-anthropic-key-here
echo    GOOGLE_API_KEY=your-google-key-here
echo.
echo 2. 백엔드 서버 시작:
echo    cd backend
echo    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
echo.
echo 3. 워크스페이스 생성 후 JupyterLab에서 AI 사용
echo.
pause 