#!/usr/bin/env python3
"""
기본 Features와 권한을 데이터베이스에 추가하는 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import get_db, engine
from app.models.permission import Feature, FeatureCategory
from app.models.user import User, Group, Role
from app.models.tables import group_features, role_features, user_features

def create_feature_categories(db: Session):
    """기능 카테고리 생성"""
    categories = [
        {
            "name": "core",
            "display_name": "핵심 기능",
            "description": "시스템의 핵심 기능들",
            "icon": "home",
            "color": "#6B7280",
            "sort_order": 1
        },
        {
            "name": "ai",
            "display_name": "AI/ML",
            "description": "인공지능 및 머신러닝 도구",
            "icon": "brain",
            "color": "#8B5CF6",
            "sort_order": 2
        },
        {
            "name": "data",
            "display_name": "데이터 관리",
            "description": "데이터 저장 및 관리 도구",
            "icon": "database",
            "color": "#10B981",
            "sort_order": 3
        },
        {
            "name": "analysis",
            "display_name": "분석 도구",
            "description": "데이터 분석 및 시각화 도구",
            "icon": "chart-bar",
            "color": "#3B82F6",
            "sort_order": 4
        },
        {
            "name": "development",
            "display_name": "개발 도구",
            "description": "개발 및 코딩 환경",
            "icon": "code",
            "color": "#F59E0B",
            "sort_order": 5
        },
        {
            "name": "admin",
            "display_name": "관리 도구",
            "description": "시스템 관리 및 설정",
            "icon": "settings",
            "color": "#EF4444",
            "sort_order": 6
        }
    ]
    
    for cat_data in categories:
        existing = db.query(FeatureCategory).filter(FeatureCategory.name == cat_data["name"]).first()
        if not existing:
            category = FeatureCategory(**cat_data)
            db.add(category)
            print(f"카테고리 생성: {cat_data['display_name']}")
    
    db.commit()

def create_features(db: Session):
    """기본 기능들 생성"""
    # 카테고리 ID 매핑
    categories = {cat.name: cat.id for cat in db.query(FeatureCategory).all()}
    
    features = [
        # 핵심 기능
        {
            "name": "dashboard",
            "display_name": "대시보드",
            "description": "메인 대시보드 및 시스템 개요",
            "category_id": categories.get("core"),
            "icon": "home",
            "url_path": "/dashboard",
            "auto_grant": True,
            "requires_approval": False,
            "is_external": False,
            "open_in_new_tab": False,
            "sort_order": 1
        },
        
        # AI/ML 도구
        {
            "name": "llmops",
            "display_name": "LLMOps",
            "description": "대규모 언어 모델 운영 및 관리",
            "category_id": categories.get("ai"),
            "icon": "brain",
            "url_path": "/dashboard/llmops",
            "auto_grant": False,
            "requires_approval": True,
            "is_external": False,
            "open_in_new_tab": False,
            "sort_order": 1
        },
        {
            "name": "flow-studio",
            "display_name": "Flow Studio",
            "description": "AI 워크플로우 설계 및 실행",
            "category_id": categories.get("ai"),
            "icon": "workflow",
            "url_path": "/dashboard/flow-studio",
            "auto_grant": False,
            "requires_approval": True,
            "is_external": False,
            "open_in_new_tab": False,
            "sort_order": 2
        },
        
        # 데이터 관리
        {
            "name": "rag-datasources",
            "display_name": "RAG 데이터소스",
            "description": "벡터 데이터베이스 및 RAG 시스템",
            "category_id": categories.get("data"),
            "icon": "database",
            "url_path": "/dashboard/rag-datasources",
            "auto_grant": False,
            "requires_approval": True,
            "is_external": False,
            "open_in_new_tab": False,
            "sort_order": 1
        },
        
        # 개발 도구
        {
            "name": "jupyter",
            "display_name": "Jupyter Lab",
            "description": "대화형 노트북 개발 환경",
            "category_id": categories.get("development"),
            "icon": "code",
            "url_path": "http://localhost:8888",
            "auto_grant": False,
            "requires_approval": True,
            "is_external": True,
            "open_in_new_tab": True,
            "sort_order": 1
        },
        {
            "name": "vscode",
            "display_name": "VS Code Server",
            "description": "웹 기반 VS Code 편집기",
            "category_id": categories.get("development"),
            "icon": "code",
            "url_path": "http://localhost:8080",
            "auto_grant": False,
            "requires_approval": True,
            "is_external": True,
            "open_in_new_tab": True,
            "sort_order": 2
        },
        
        # 관리 도구
        {
            "name": "admin",
            "display_name": "시스템 관리",
            "description": "사용자 및 시스템 관리",
            "category_id": categories.get("admin"),
            "icon": "settings",
            "url_path": "/admin",
            "auto_grant": False,
            "requires_approval": True,
            "is_external": False,
            "open_in_new_tab": False,
            "sort_order": 1
        },
        {
            "name": "workspace-manager",
            "display_name": "워크스페이스 관리",
            "description": "워크스페이스 생성 및 관리",
            "category_id": categories.get("admin"),
            "icon": "layers",
            "url_path": "/workspaces",
            "auto_grant": False,
            "requires_approval": True,
            "is_external": False,
            "open_in_new_tab": False,
            "sort_order": 2
        }
    ]
    
    for feature_data in features:
        existing = db.query(Feature).filter(Feature.name == feature_data["name"]).first()
        if not existing:
            feature = Feature(**feature_data)
            db.add(feature)
            print(f"기능 생성: {feature_data['display_name']}")
    
    db.commit()

def grant_features_to_admin(db: Session):
    """관리자에게 모든 기능 권한 부여"""
    # admin 역할 찾기
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        print("admin 역할을 찾을 수 없습니다.")
        return
    
    # 모든 기능 가져오기
    features = db.query(Feature).filter(Feature.is_active == True).all()
    
    # 기존 권한 확인 및 추가
    for feature in features:
        # 이미 권한이 있는지 확인
        existing = db.execute(
            role_features.select().where(
                role_features.c.role_id == admin_role.id,
                role_features.c.feature_id == feature.id
            )
        ).first()
        
        if not existing:
            db.execute(
                role_features.insert().values(
                    role_id=admin_role.id,
                    feature_id=feature.id
                )
            )
            print(f"admin 역할에 {feature.display_name} 권한 부여")
    
    db.commit()

def grant_basic_features_to_users(db: Session):
    """일반 사용자에게 기본 기능 권한 부여"""
    # user 역할 찾기
    user_role = db.query(Role).filter(Role.name == "user").first()
    if not user_role:
        print("user 역할을 찾을 수 없습니다.")
        return
    
    # 기본 기능들 (auto_grant=True인 기능들)
    basic_features = db.query(Feature).filter(
        Feature.auto_grant == True,
        Feature.is_active == True
    ).all()
    
    for feature in basic_features:
        # 이미 권한이 있는지 확인
        existing = db.execute(
            role_features.select().where(
                role_features.c.role_id == user_role.id,
                role_features.c.feature_id == feature.id
            )
        ).first()
        
        if not existing:
            db.execute(
                role_features.insert().values(
                    role_id=user_role.id,
                    feature_id=feature.id
                )
            )
            print(f"user 역할에 {feature.display_name} 권한 부여")
    
    db.commit()

def main():
    """메인 실행 함수"""
    print("기본 Features 및 권한 설정을 시작합니다...")
    
    db = next(get_db())
    
    try:
        # 1. 기능 카테고리 생성
        print("\n1. 기능 카테고리 생성 중...")
        create_feature_categories(db)
        
        # 2. 기본 기능들 생성
        print("\n2. 기본 기능들 생성 중...")
        create_features(db)
        
        # 3. 관리자에게 모든 기능 권한 부여
        print("\n3. 관리자 권한 설정 중...")
        grant_features_to_admin(db)
        
        # 4. 일반 사용자에게 기본 기능 권한 부여
        print("\n4. 일반 사용자 기본 권한 설정 중...")
        grant_basic_features_to_users(db)
        
        print("\n✅ 기본 Features 및 권한 설정이 완료되었습니다!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main() 
