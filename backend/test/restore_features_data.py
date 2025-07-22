#!/usr/bin/env python3
"""
기본 기능(Features) 데이터 복구 스크립트

사용법:
python restore_features_data.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import get_db, engine
from app.models.permission import Feature, FeatureCategory, Permission
from app.models.user import User, Role

def restore_feature_categories(db: Session):
    """기능 카테고리 데이터 복구"""
    print("📂 기능 카테고리 복구 중...")
    
    categories_data = [
        {
            "name": "core",
            "display_name": "핵심 기능",
            "description": "시스템의 핵심 기능들",
            "icon": "⚙️",
            "color": "#3B82F6",
            "sort_order": 1
        },
        {
            "name": "analysis",
            "display_name": "데이터 분석",
            "description": "데이터 분석 및 처리 기능",
            "icon": "📊",
            "color": "#10B981",
            "sort_order": 2
        },
        {
            "name": "ai",
            "display_name": "AI 기능",
            "description": "인공지능 관련 기능",
            "icon": "🤖",
            "color": "#8B5CF6",
            "sort_order": 3
        },
        {
            "name": "admin",
            "display_name": "관리 기능",
            "description": "시스템 관리 기능",
            "icon": "🔧",
            "color": "#EF4444",
            "sort_order": 4
        },
        {
            "name": "collaboration",
            "display_name": "협업 도구",
            "description": "팀 협업 및 공유 기능",
            "icon": "👥",
            "color": "#F59E0B",
            "sort_order": 5
        }
    ]
    
    for category_data in categories_data:
        existing = db.query(FeatureCategory).filter(FeatureCategory.name == category_data["name"]).first()
        if not existing:
            category = FeatureCategory(**category_data)
            db.add(category)
            print(f"  ✅ 카테고리 생성: {category_data['display_name']}")
        else:
            print(f"  ⚠️ 카테고리 존재: {category_data['display_name']}")
    
    db.commit()

def restore_features(db: Session):
    """기본 기능 데이터 복구"""
    print("🔧 기본 기능 복구 중...")
    
    # 카테고리 ID 매핑 생성
    categories = {cat.name: cat.id for cat in db.query(FeatureCategory).all()}
    
    features_data = [
        # 핵심 기능
        {
            "name": "dashboard",
            "display_name": "대시보드",
            "description": "메인 대시보드 - 시스템 개요 및 주요 지표",
            "category_id": categories.get("core"),
            "icon": "📊",
            "url_path": "/dashboard",
            "requires_approval": False,
            "sort_order": 1
        },
        {
            "name": "profile_management",
            "display_name": "프로필 관리",
            "description": "개인 프로필 정보 관리",
            "category_id": categories.get("core"),
            "icon": "👤",
            "url_path": "/profile",
            "requires_approval": False,
            "sort_order": 2
        },
        
        # 데이터 분석
        {
            "name": "jupyter_workspace",
            "display_name": "쥬피터 워크스페이스",
            "description": "데이터 분석을 위한 쥬피터 노트북 환경",
            "category_id": categories.get("analysis"),
            "icon": "📓",
            "url_path": "/workspaces",
            "requires_approval": False,
            "sort_order": 1
        },
        {
            "name": "data_visualization",
            "display_name": "데이터 시각화",
            "description": "차트 및 그래프 생성 도구",
            "category_id": categories.get("analysis"),
            "icon": "📈",
            "url_path": "/visualization",
            "requires_approval": True,
            "sort_order": 2
        },
        {
            "name": "apex_analysis",
            "display_name": "APEX 분석",
            "description": "공정분석 시스템",
            "category_id": categories.get("analysis"),
            "icon": "🏭",
            "url_path": "/apex",
            "requires_approval": True,
            "sort_order": 3
        },
        
        # AI 기능
        {
            "name": "llm_chat",
            "display_name": "AI 채팅",
            "description": "LLM을 활용한 AI 채팅",
            "category_id": categories.get("ai"),
            "icon": "🤖",
            "url_path": "/llm",
            "requires_approval": True,
            "sort_order": 1
        },
        {
            "name": "flow_studio",
            "display_name": "Flow Studio",
            "description": "AI 워크플로우 설계 및 실행",
            "category_id": categories.get("ai"),
            "icon": "🔄",
            "url_path": "/flow-studio",
            "requires_approval": True,
            "sort_order": 2
        },
        {
            "name": "rag_management",
            "display_name": "RAG 데이터소스",
            "description": "문서 검색 및 RAG 데이터소스 관리",
            "category_id": categories.get("ai"),
            "icon": "📚",
            "url_path": "/rag",
            "requires_approval": True,
            "sort_order": 3
        },
        
        # 관리 기능
        {
            "name": "admin_tools",
            "display_name": "관리자 도구",
            "description": "시스템 관리 도구",
            "category_id": categories.get("admin"),
            "icon": "⚙️",
            "url_path": "/admin",
            "requires_approval": False,
            "sort_order": 1
        },
        {
            "name": "user_management",
            "display_name": "사용자 관리",
            "description": "사용자 계정 및 권한 관리",
            "category_id": categories.get("admin"),
            "icon": "👥",
            "url_path": "/admin/users",
            "requires_approval": False,
            "sort_order": 2
        },
        {
            "name": "system_monitoring",
            "display_name": "시스템 모니터링",
            "description": "시스템 상태 및 성능 모니터링",
            "category_id": categories.get("admin"),
            "icon": "📊",
            "url_path": "/admin/monitoring",
            "requires_approval": False,
            "sort_order": 3
        },
        
        # 협업 도구
        {
            "name": "file_sharing",
            "display_name": "파일 공유",
            "description": "팀 내 파일 공유 및 관리",
            "category_id": categories.get("collaboration"),
            "icon": "📁",
            "url_path": "/files",
            "requires_approval": True,
            "sort_order": 1
        },
        {
            "name": "workspace_collaboration",
            "display_name": "워크스페이스 협업",
            "description": "공동 작업 환경",
            "category_id": categories.get("collaboration"),
            "icon": "🤝",
            "url_path": "/collaboration",
            "requires_approval": True,
            "sort_order": 2
        }
    ]
    
    for feature_data in features_data:
        existing = db.query(Feature).filter(Feature.name == feature_data["name"]).first()
        if not existing:
            feature = Feature(**feature_data)
            db.add(feature)
            print(f"  ✅ 기능 생성: {feature_data['display_name']}")
        else:
            print(f"  ⚠️ 기능 존재: {feature_data['display_name']}")
    
    db.commit()

def assign_features_to_roles(db: Session):
    """역할별 기능 할당"""
    print("🔗 역할별 기능 할당 중...")
    
    # admin 역할 - 모든 기능
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role:
        all_features = db.query(Feature).filter(Feature.is_active == True).all()
        admin_role.features = all_features
        print(f"  ✅ admin 역할에 {len(all_features)}개 기능 할당")
    
    # user 역할 - 기본 기능만
    user_role = db.query(Role).filter(Role.name == "user").first()
    if user_role:
        basic_features = db.query(Feature).filter(
            Feature.name.in_([
                "dashboard",
                "profile_management", 
                "jupyter_workspace"
            ])
        ).all()
        user_role.features = basic_features
        print(f"  ✅ user 역할에 {len(basic_features)}개 기본 기능 할당")
    
    # manager 역할 - 중간 권한
    manager_role = db.query(Role).filter(Role.name == "manager").first()
    if manager_role:
        manager_features = db.query(Feature).filter(
            Feature.name.in_([
                "dashboard",
                "profile_management",
                "jupyter_workspace",
                "data_visualization",
                "llm_chat",
                "file_sharing",
                "workspace_collaboration"
            ])
        ).all()
        manager_role.features = manager_features
        print(f"  ✅ manager 역할에 {len(manager_features)}개 기능 할당")
    
    db.commit()

def main():
    """메인 실행 함수"""
    print("🚀 기능 데이터 복구 시작\n")
    
    try:
        # 데이터베이스 세션 생성
        db = next(get_db())
        
        # 1. 기능 카테고리 복구
        restore_feature_categories(db)
        print()
        
        # 2. 기본 기능 복구
        restore_features(db)
        print()
        
        # 3. 역할별 기능 할당
        assign_features_to_roles(db)
        print()
        
        print("✅ 기능 데이터 복구 완료!")
        print("\n📋 복구된 기능 목록:")
        
        # 복구된 기능 목록 출력
        features = db.query(Feature).order_by(Feature.category_id, Feature.sort_order).all()
        current_category = None
        
        for feature in features:
            if feature.feature_category and feature.feature_category.display_name != current_category:
                current_category = feature.feature_category.display_name
                print(f"\n📂 {current_category}")
            
            approval_text = " (승인 필요)" if feature.requires_approval else ""
            print(f"  • {feature.display_name}{approval_text}")
        
        # 관리자 페이지 접근 방법 안내
        print(f"\n🔧 관리자 페이지 접근:")
        print(f"  • URL: http://localhost:8000/admin")
        print(f"  • 기능 관리: http://localhost:8000/admin/features")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    main() 