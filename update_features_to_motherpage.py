#!/usr/bin/env python3
"""
기능 목록을 Mother Page 기반으로 업데이트하는 스크립트
- 기존 기능들을 삭제하고 mother page 기능들로 교체
- 파일 관리자를 APEX로 변경
"""

import sys
import os
sys.path.append('backend')

from backend.app.database import engine, SessionLocal
from backend.app.models.permission import Feature
from backend.app.models.user import Role
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

def update_features_to_motherpage():
    """기능 목록을 Mother Page 기반으로 업데이트"""
    
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        print("🔄 관련 테이블 정리 중...")
        
        # 외래 키 제약조건 때문에 관련 테이블들을 먼저 정리
        print("  - user_features 테이블 정리...")
        db.execute(text("DELETE FROM user_features"))
        
        print("  - role_features 테이블 정리...")
        db.execute(text("DELETE FROM role_features"))
        
        print("  - group_features 테이블 정리...")
        db.execute(text("DELETE FROM group_features"))
        
        db.commit()
        print("✅ 관련 테이블 정리 완료")
        
        print("\n🔄 기존 기능 목록 삭제 중...")
        # 이제 기존 모든 기능 삭제
        db.query(Feature).delete()
        db.commit()
        print("✅ 기존 기능 목록 삭제 완료")
        
        print("\n🚀 Mother Page 기반 기능 목록 추가 중...")
        
        # Mother Page 기반 기능 목록
        motherpage_features = [
            {
                "name": "dashboard", 
                "display_name": "대시보드", 
                "description": "메인 대시보드 및 현황 모니터링", 
                "category": "core", 
                "icon": "📊", 
                "url_path": "/dashboard", 
                "requires_approval": False,
                "is_active": True
            },
            {
                "name": "jupyter_workspace", 
                "display_name": "쥬피터 워크스페이스", 
                "description": "데이터 분석을 위한 쥬피터 노트북 환경", 
                "category": "analysis", 
                "icon": "📓", 
                "url_path": "/workspace", 
                "requires_approval": True,
                "is_active": True
            },
            {
                "name": "apex", 
                "display_name": "APEX", 
                "description": "공정분석 시스템", 
                "category": "analysis", 
                "icon": "🏭", 
                "url_path": "/apex", 
                "requires_approval": True,
                "is_active": True
            },
            {
                "name": "llm_chat", 
                "display_name": "AI 채팅", 
                "description": "LLM을 활용한 AI 채팅 서비스", 
                "category": "ai", 
                "icon": "🤖", 
                "url_path": "/llm", 
                "requires_approval": True,
                "is_active": True
            },
            {
                "name": "admin_tools", 
                "display_name": "관리 도구", 
                "description": "시스템 관리 및 사용자 관리 도구", 
                "category": "admin", 
                "icon": "⚙️", 
                "url_path": "/admin", 
                "requires_approval": False,
                "is_active": True
            }
        ]
        
        # 새로운 기능들 추가
        for feature_data in motherpage_features:
            feature = Feature(**feature_data)
            db.add(feature)
            print(f"  - {feature_data['display_name']} 추가")
        
        db.commit()
        print("\n✅ Mother Page 기반 기능 목록 업데이트 완료!")
        
        print("\n🔧 관리자 역할에 모든 기능 할당 중...")
        # 관리자 역할에 모든 기능 할당
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role:
            features = db.query(Feature).all()
            admin_role.features = features
            db.commit()
            print(f"  - 관리자 역할에 {len(features)}개 기능 할당 완료")
        
        # 결과 확인
        print("\n📋 현재 등록된 기능 목록:")
        features = db.query(Feature).all()
        for feature in features:
            print(f"  - {feature.name}: {feature.display_name} ({feature.description})")
        
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Mother Page 기반 기능 목록 업데이트")
    print("=" * 60)
    
    success = update_features_to_motherpage()
    
    if success:
        print("\n🎉 업데이트가 성공적으로 완료되었습니다!")
        print("이제 Mother Page에서 업데이트된 기능들을 확인할 수 있습니다.")
    else:
        print("\n💥 업데이트 중 오류가 발생했습니다.")
        sys.exit(1) 