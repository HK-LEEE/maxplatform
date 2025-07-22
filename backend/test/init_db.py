#!/usr/bin/env python3
"""
데이터베이스 초기화 스크립트
테이블 생성 및 기본 데이터 삽입
"""

import sys
import os

# 현재 스크립트의 디렉토리를 기준으로 app 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database_init import init_database

if __name__ == "__main__":
    print("🚀 Jupyter Data Platform 데이터베이스 초기화 시작...")
    print("=" * 60)
    
    try:
        init_database()
        print("=" * 60)
        print("🎉 데이터베이스 초기화가 성공적으로 완료되었습니다!")
        print("\n✨ 이제 백엔드 서버를 시작할 수 있습니다:")
        print("   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ 데이터베이스 초기화 중 오류가 발생했습니다: {e}")
        print("\n🔧 문제 해결:")
        print("1. MySQL 서버가 실행 중인지 확인")
        print("2. 데이터베이스 연결 정보가 올바른지 확인")
        print("3. 필요한 Python 패키지가 설치되어 있는지 확인")
        sys.exit(1) 