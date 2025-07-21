#!/bin/bash

# macOS용 전체 서비스 시작 스크립트
# MAX (Manufacturing AI & DX) Platform - All Services Startup Script for macOS

echo "🚀 MAX Platform 전체 서비스 시작 중... (macOS)"
echo "================================================="

# 현재 디렉토리 확인
SCRIPT_DIR="$(dirname "$0")"
echo "📁 프로젝트 디렉토리: $SCRIPT_DIR"

# 실행 권한 부여
echo "🔧 스크립트 실행 권한 설정..."
chmod +x "$SCRIPT_DIR/start_backend_macos.sh"
chmod +x "$SCRIPT_DIR/start_frontend_macos.sh"

# 필수 도구 확인
echo ""
echo "🔍 필수 도구 확인 중..."

# Python 확인
if command -v python3 &> /dev/null; then
    echo "✅ Python3: $(python3 --version)"
else
    echo "❌ Python3가 설치되지 않았습니다."
    echo "   설치: brew install python3"
    exit 1
fi

# Node.js 확인
if command -v node &> /dev/null; then
    echo "✅ Node.js: $(node --version)"
else
    echo "❌ Node.js가 설치되지 않았습니다."
    echo "   설치: brew install node"
    exit 1
fi

# 데이터베이스 서비스 확인
echo ""
echo "🗄️  데이터베이스 서비스 확인..."

# PostgreSQL 확인
if command -v psql &> /dev/null; then
    echo "✅ PostgreSQL 설치됨"
    # PostgreSQL 서비스 상태 확인
    if brew services list | grep postgresql | grep started &> /dev/null; then
        echo "✅ PostgreSQL 서비스 실행 중"
    else
        echo "⚠️  PostgreSQL 서비스가 중지되어 있습니다."
        echo "   시작: brew services start postgresql"
    fi
else
    echo "⚠️  PostgreSQL이 설치되지 않았습니다."
    echo "   설치: brew install postgresql"
fi

# MySQL 확인 (선택사항)
if command -v mysql &> /dev/null; then
    echo "✅ MySQL 설치됨"
    if brew services list | grep mysql | grep started &> /dev/null; then
        echo "✅ MySQL 서비스 실행 중"
    else
        echo "⚠️  MySQL 서비스가 중지되어 있습니다."
        echo "   시작: brew services start mysql"
    fi
fi

echo ""
echo "🎯 서비스 시작 준비 완료!"
echo ""

# 백엔드 서버를 백그라운드에서 시작
echo "🚀 백엔드 서버 시작 중..."
osascript -e 'tell app "Terminal" to do script "cd '"$SCRIPT_DIR"' && ./start_backend_macos.sh"'

# 백엔드 서버가 시작될 때까지 잠시 대기
echo "⏳ 백엔드 서버 준비 중... (10초 대기)"
sleep 10

# 프론트엔드 서버를 새 터미널에서 시작
echo "🚀 프론트엔드 서버 시작 중..."
osascript -e 'tell app "Terminal" to do script "cd '"$SCRIPT_DIR"' && ./start_frontend_macos.sh"'

echo ""
echo "✅ 모든 서비스가 시작되었습니다!"
echo ""
echo "📱 서비스 접속 정보:"
echo "   - 프론트엔드: http://localhost:3000"
echo "   - 백엔드 API: http://localhost:8000"
echo "   - API 문서: http://localhost:8000/docs"
echo ""
echo "🛑 서비스를 중지하려면 각 터미널에서 Ctrl+C를 누르세요"
echo ""
echo "💡 문제가 발생하면 다음을 확인하세요:"
echo "   1. 데이터베이스 서비스가 실행 중인지"
echo "   2. 포트 8000, 3000이 사용 가능한지"
echo "   3. .env 파일의 설정이 올바른지"