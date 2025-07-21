#!/bin/bash

# macOS용 프론트엔드 서버 시작 스크립트
# MAX (Manufacturing AI & DX) Platform Frontend Startup Script for macOS

echo "🚀 MAX Platform Frontend 시작 중... (macOS)"
echo "======================================"

# 프론트엔드 디렉토리로 이동
cd "$(dirname "$0")/frontend"

# Node.js 버전 확인
node_version=$(node --version 2>&1)
if [ $? -eq 0 ]; then
    echo "✅ Node.js 버전: $node_version"
else
    echo "❌ Node.js가 설치되지 않았습니다. Node.js 18 이상을 설치해주세요."
    echo "   설치: brew install node"
    exit 1
fi

# npm 버전 확인
npm_version=$(npm --version 2>&1)
echo "✅ npm 버전: $npm_version"

# package.json 존재 확인
if [ ! -f "package.json" ]; then
    echo "❌ package.json 파일을 찾을 수 없습니다."
    exit 1
fi

# node_modules 디렉토리가 없으면 의존성 설치
if [ ! -d "node_modules" ]; then
    echo "📦 npm 패키지 설치 중..."
    npm install
    
    if [ $? -eq 0 ]; then
        echo "✅ 모든 패키지가 성공적으로 설치되었습니다."
    else
        echo "❌ 패키지 설치 중 오류가 발생했습니다."
        echo "💡 다음 명령어로 수동 설치를 시도해보세요:"
        echo "   npm install"
        exit 1
    fi
else
    echo "✅ node_modules 디렉토리가 존재합니다."
fi

echo ""
echo "🎯 프론트엔드 시작 전 체크리스트:"
echo "  - 백엔드 서버(port 8000)가 실행 중인지 확인하세요"
echo "  - 네트워크 연결을 확인하세요"
echo ""

# 개발 서버 시작
echo "🚀 React 개발 서버 시작..."
echo "   서버 주소: http://localhost:3000"
echo ""
echo "   서버를 중지하려면 Ctrl+C를 누르세요"
echo ""

npm start