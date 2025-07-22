#!/usr/bin/env python3
"""
라우터 파일들을 기반으로 features 데이터를 생성하고 데이터베이스에 추가하는 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.permission import Feature, FeatureCategory
from app.models.user import Group
import logging

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass

def create_feature_categories(db: Session):
    """기능 카테고리 생성"""
    categories = [
        {
            "name": "ai",
            "display_name": "AI/ML",
            "description": "인공지능 및 머신러닝 관련 기능",
            "icon": "🤖",
            "color": "#3B82F6",
            "sort_order": 1
        },
        {
            "name": "data",
            "display_name": "데이터 관리",
            "description": "데이터 저장, 관리 및 분석 기능",
            "icon": "💾",
            "color": "#10B981",
            "sort_order": 2
        },
        {
            "name": "development",
            "display_name": "개발 도구",
            "description": "개발 및 협업 도구",
            "icon": "💻",
            "color": "#F59E0B",
            "sort_order": 3
        },
        {
            "name": "analysis",
            "display_name": "분석 도구",
            "description": "데이터 분석 및 시각화 도구",
            "icon": "📊",
            "color": "#8B5CF6",
            "sort_order": 4
        },
        {
            "name": "admin",
            "display_name": "관리",
            "description": "시스템 관리 및 설정",
            "icon": "⚙️",
            "color": "#EF4444",
            "sort_order": 5
        },
        {
            "name": "collaboration",
            "display_name": "협업",
            "description": "협업 및 커뮤니케이션 도구",
            "icon": "👥",
            "color": "#EC4899",
            "sort_order": 6
        }
    ]
    
    for cat_data in categories:
        existing_category = db.query(FeatureCategory).filter(
            FeatureCategory.name == cat_data["name"]
        ).first()
        
        if not existing_category:
            category = FeatureCategory(**cat_data)
            db.add(category)
            logger.info(f"카테고리 생성: {cat_data['display_name']}")
        else:
            logger.info(f"카테고리 이미 존재: {cat_data['display_name']}")
    
    db.commit()

def create_features_from_routes(db: Session):
    """라우터 파일들을 기반으로 features 생성"""
    
    # 카테고리 ID 매핑
    categories = {cat.name: cat.id for cat in db.query(FeatureCategory).all()}
    
    features = [
        # AI/ML 관련 기능
        {
            "name": "llm_chat",
            "display_name": "LLM 채팅",
            "description": "대형 언어 모델과의 대화형 인터페이스",
            "category_id": categories.get("ai"),
            "icon": "💬",
            "url_path": "/llm-chat",
            "is_external": False,
            "open_in_new_tab": False,
            "sort_order": 1
        },
        {
            "name": "llmops",
            "display_name": "LLMOps",
            "description": "LLM 운영 관리 도구",
            "category_id": categories.get("ai"),
            "icon": "🎯",
            "url_path": "/llmops",
            "is_external": False,
            "open_in_new_tab": False,
            "sort_order": 2
        },
        {
            "name": "flow_studio",
            "display_name": "플로우 스튜디오",
            "description": "시각적 워크플로우 설계 도구",
            "category_id": categories.get("ai"),
            "icon": "🎨",
            "url_path": "/flow-studio",
            "is_external": False,
            "open_in_new_tab": False,
            "sort_order": 3
        },
        
        # 데이터 관리 기능
        {
            "name": "chroma_db",
            "display_name": "벡터 데이터베이스",
            "description": "Chroma 벡터 데이터베이스 관리",
            "category_id": categories.get("data"),
            "icon": "🗄️",
            "url_path": "/chroma",
            "is_external": False,
            "open_in_new_tab": False,
            "sort_order": 1
        },
        {
            "name": "file_manager",
            "display_name": "파일 관리자",
            "description": "파일 업로드, 다운로드 및 관리",
            "category_id": categories.get("data"),
            "icon": "📁",
            "url_path": "/files",
            "is_external": False,
            "open_in_new_tab": False,
            "sort_order": 2
        },
        {
            "name": "rag_datasource",
            "display_name": "RAG 데이터소스",
            "description": "RAG 시스템용 데이터소스 관리",
            "category_id": categories.get("data"),
            "icon": "📚",
            "url_path": "/rag-datasource",
            "is_external": False,
            "open_in_new_tab": False,
            "sort_order": 3
        },
        
        # 개발 도구
        {
            "name": "jupyter",
            "display_name": "Jupyter 노트북",
            "description": "Jupyter 노트북 환경",
            "category_id": categories.get("development"),
            "icon": "📔",
            "url_path": "/jupyter",
            "is_external": False,
            "open_in_new_tab": True,
            "sort_order": 1
        },
        {
            "name": "workspace",
            "display_name": "워크스페이스",
            "description": "개발 워크스페이스 관리",
            "category_id": categories.get("development"),
            "icon": "🛠️",
            "url_path": "/workspace",
            "is_external": False,
            "open_in_new_tab": False,
            "sort_order": 2
        },
        
        # 분석 도구
        {
            "name": "dashboard",
            "display_name": "대시보드",
            "description": "시스템 현황 및 통계 대시보드",
            "category_id": categories.get("analysis"),
            "icon": "📈",
            "url_path": "/dashboard",
            "is_external": False,
            "open_in_new_tab": False,
            "sort_order": 1
        },
        
        # 관리 기능
        {
            "name": "admin_panel",
            "display_name": "관리자 패널",
            "description": "시스템 관리 및 설정",
            "category_id": categories.get("admin"),
            "icon": "🔧",
            "url_path": "/admin",
            "is_external": False,
            "open_in_new_tab": False,
            "sort_order": 1
        },
        {
            "name": "user_management",
            "display_name": "사용자 관리",
            "description": "사용자 계정 및 권한 관리",
            "category_id": categories.get("admin"),
            "icon": "👤",
            "url_path": "/admin/users",
            "is_external": False,
            "open_in_new_tab": False,
            "sort_order": 2
        },
        
        # 협업 도구
        {
            "name": "team_chat",
            "display_name": "팀 채팅",
            "description": "팀 내 실시간 채팅 및 협업",
            "category_id": categories.get("collaboration"),
            "icon": "💬",
            "url_path": "/chat",
            "is_external": False,
            "open_in_new_tab": False,
            "sort_order": 1
        }
    ]
    
    for feature_data in features:
        existing_feature = db.query(Feature).filter(
            Feature.name == feature_data["name"]
        ).first()
        
        if not existing_feature:
            feature = Feature(**feature_data)
            db.add(feature)
            logger.info(f"기능 생성: {feature_data['display_name']}")
        else:
            # 기존 기능 업데이트
            for key, value in feature_data.items():
                if hasattr(existing_feature, key):
                    setattr(existing_feature, key, value)
            logger.info(f"기능 업데이트: {feature_data['display_name']}")
    
    db.commit()

def assign_features_to_default_group(db: Session):
    """기본 그룹에 모든 기능 할당"""
    # 'users' 그룹 찾기 (기본 사용자 그룹)
    default_group = db.query(Group).filter(Group.name == "users").first()
    
    if not default_group:
        logger.warning("기본 사용자 그룹 'users'를 찾을 수 없습니다.")
        return
    
    # 모든 활성 기능 조회
    active_features = db.query(Feature).filter(Feature.is_active == True).all()
    
    # 그룹에 기능 할당
    for feature in active_features:
        if feature not in default_group.features:
            default_group.features.append(feature)
            logger.info(f"기본 그룹에 기능 할당: {feature.display_name}")
    
    db.commit()

def main():
    """메인 실행 함수"""
    logger.info("라우터 기반 features 초기화 시작")
    
    db = get_db()
    
    try:
        # 1. 기능 카테고리 생성
        logger.info("1. 기능 카테고리 생성")
        create_feature_categories(db)
        
        # 2. 라우터 기반 기능 생성
        logger.info("2. 라우터 기반 기능 생성")
        create_features_from_routes(db)
        
        # 3. 기본 그룹에 기능 할당
        logger.info("3. 기본 그룹에 기능 할당")
        assign_features_to_default_group(db)
        
        logger.info("라우터 기반 features 초기화 완료")
        
    except Exception as e:
        logger.error(f"초기화 중 오류 발생: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main() 