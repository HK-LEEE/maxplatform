#!/bin/bash

# macOS용 백엔드 서버 시작 스크립트
# MAX (Manufacturing AI & DX) Platform Backend Startup Script for macOS

echo "🚀 MAX Platform Backend 시작 중... (macOS)"
echo "======================================"

# 백엔드 디렉토리로 이동
cd "$(dirname "$0")/backend"

# Python 버전 확인
python_version=$(python3 --version 2>&1)
if [ $? -eq 0 ]; then
    echo "✅ Python 버전: $python_version"
else
    echo "❌ Python3가 설치되지 않았습니다. Python 3.8 이상을 설치해주세요."
    echo "   설치: brew install python3"
    exit 1
fi

# 가상환경 생성 및 활성화
if [ ! -d "venv" ]; then
    echo "📦 가상환경 생성 중..."
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        echo "✅ 가상환경 created successfully"
    else
        echo "❌ 가상환경 생성에 실패했습니다."
        exit 1
    fi
fi

echo "🔧 가상환경 활성화..."
source venv/bin/activate

# pip 업그레이드
echo "📦 pip 업그레이드..."
pip install --upgrade pip

# 의존성 설치
echo "📦 Python 패키지 설치 중..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ 모든 패키지가 성공적으로 설치되었습니다."
else
    echo "❌ 패키지 설치 중 오류가 발생했습니다."
    echo "💡 다음 명령어로 수동 설치를 시도해보세요:"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# 환경 변수 파일 확인
if [ ! -f ".env" ]; then
    echo "⚠️  .env 파일이 없습니다. .env.macos를 .env로 복사합니다..."
    cp .env.macos .env
    echo "✅ macOS용 환경 설정이 적용되었습니다."
fi

# 데이터 디렉토리 생성
echo "📁 데이터 디렉토리 생성..."
mkdir -p data/users
mkdir -p file_storage
mkdir -p chroma_data

echo ""
echo "🎯 서버 시작 전 체크리스트:"
echo "  - PostgreSQL 또는 MySQL 서버가 실행 중인지 확인하세요"
echo "  - .env 파일의 데이터베이스 설정을 확인하세요"
echo "  - API 키가 필요한 경우 .env 파일에 설정하세요"
echo ""

# 서버 시작
echo "🚀 FastAPI 서버 시작..."
echo "   서버 주소: http://localhost:8000"
echo "   API 문서: http://localhost:8000/docs"
echo ""
echo "   서버를 중지하려면 Ctrl+C를 누르세요"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000