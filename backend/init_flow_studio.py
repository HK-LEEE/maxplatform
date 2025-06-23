#!/usr/bin/env python3
"""
Flow Studio 초기화 스크립트
- 데이터베이스 테이블 생성
- 기본 컴포넌트 템플릿 초기화
"""

import sys
import os
import logging
from pathlib import Path

# 프로젝트 루트 경로를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import get_database_url
from app.models.flow_studio import Base
from app.services.flow_component_initializer import FlowComponentInitializer

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_flow_studio_tables():
    """Flow Studio 테이블 생성"""
    try:
        # 데이터베이스 연결
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        # 테이블 생성
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Flow Studio 테이블 생성 완료")
        
        return engine
        
    except Exception as e:
        logger.error(f"❌ Flow Studio 테이블 생성 실패: {e}")
        raise

async def initialize_component_templates(engine):
    """기본 컴포넌트 템플릿 초기화"""
    try:
        # 세션 생성
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # 컴포넌트 초기화
        initializer = FlowComponentInitializer(db)
        created_count = await initializer.initialize_builtin_components()
        
        db.close()
        
        logger.info(f"✅ 기본 컴포넌트 템플릿 {created_count}개 초기화 완료")
        
    except Exception as e:
        logger.error(f"❌ 컴포넌트 템플릿 초기화 실패: {e}")
        raise

async def create_default_project(engine, user_id: str = "admin"):
    """기본 프로젝트 생성"""
    try:
        from app.models.flow_studio import Project
        from app.schemas.flow_studio import ProjectCreate
        from app.services.flow_studio_service import FlowStudioService
        
        # 세션 생성
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # 기본 프로젝트가 이미 있는지 확인
        existing_project = db.query(Project).filter(
            Project.user_id == user_id,
            Project.name == "Starter Project"
        ).first()
        
        if existing_project:
            logger.info("기본 프로젝트가 이미 존재합니다.")
            db.close()
            return
        
        # Flow Studio 서비스 생성
        service = FlowStudioService(db)
        
        # 기본 프로젝트 생성
        project_data = ProjectCreate(
            name="Starter Project",
            description="Flow Studio 시작을 위한 기본 프로젝트",
            is_default=True
        )
        
        project = await service.create_project(user_id, project_data)
        
        db.close()
        
        logger.info(f"✅ 기본 프로젝트 생성 완료: {project.name}")
        
    except Exception as e:
        logger.error(f"❌ 기본 프로젝트 생성 실패: {e}")
        raise

async def main():
    """메인 초기화 함수"""
    try:
        logger.info("🚀 Flow Studio 초기화 시작")
        
        # 1. 테이블 생성
        logger.info("1️⃣ 데이터베이스 테이블 생성 중...")
        engine = create_flow_studio_tables()
        
        # 2. 컴포넌트 템플릿 초기화
        logger.info("2️⃣ 기본 컴포넌트 템플릿 초기화 중...")
        await initialize_component_templates(engine)
        
        # 3. 기본 프로젝트 생성
        logger.info("3️⃣ 기본 프로젝트 생성 중...")
        await create_default_project(engine)
        
        logger.info("🎉 Flow Studio 초기화 완료!")
        
    except Exception as e:
        logger.error(f"💥 Flow Studio 초기화 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 