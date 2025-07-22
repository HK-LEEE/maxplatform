#!/usr/bin/env python3
"""
카테고리 마이그레이션 스크립트
Features 테이블에 FeatureCategory 관계를 추가합니다.
"""

import asyncio
import sys
import os

# 현재 스크립트의 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import recreate_feature_tables_with_categories

async def main():
    """마이그레이션 실행"""
    try:
        print("🚀 카테고리 마이그레이션 시작...")
        await recreate_feature_tables_with_categories()
        print("✅ 카테고리 마이그레이션 완료!")
        return 0
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 