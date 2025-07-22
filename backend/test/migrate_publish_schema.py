#!/usr/bin/env python3
"""
Flow Studio Publish 기능을 위한 데이터베이스 마이그레이션 스크립트
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트 경로를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from app.database import get_database_url
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def migrate_database():
    """데이터베이스 마이그레이션 실행"""
    try:
        # 데이터베이스 연결
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        logger.info("🔄 Flow Studio Publish 기능 마이그레이션 시작...")
        
        with engine.connect() as conn:
            # 트랜잭션 시작
            trans = conn.begin()
            
            try:
                # 1. flow_studio_projects 테이블명 변경 (flow_projects -> flow_studio_projects)
                logger.info("1. 프로젝트 테이블명 확인 및 변경...")
                
                # 테이블 존재 확인
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('flow_projects', 'flow_studio_projects')
                """))
                
                existing_tables = [row[0] for row in result.fetchall()]
                logger.info(f"기존 테이블: {existing_tables}")
                
                if 'flow_projects' in existing_tables and 'flow_studio_projects' not in existing_tables:
                    logger.info("flow_projects -> flow_studio_projects 테이블명 변경...")
                    conn.execute(text("ALTER TABLE flow_projects RENAME TO flow_studio_projects"))
                    logger.info("✅ 테이블명 변경 완료")
                elif 'flow_studio_projects' in existing_tables:
                    logger.info("✅ flow_studio_projects 테이블이 이미 존재합니다")
                else:
                    logger.info("새 flow_studio_projects 테이블 생성...")
                    conn.execute(text("""
                        CREATE TABLE flow_studio_projects (
                            id VARCHAR(36) PRIMARY KEY,
                            name VARCHAR(255) NOT NULL,
                            description TEXT,
                            user_id VARCHAR(36) NOT NULL,
                            group_id VARCHAR(36),
                            owner_type VARCHAR(20) NOT NULL DEFAULT 'user',
                            is_default BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    
                    # 인덱스 생성
                    conn.execute(text("CREATE INDEX idx_flow_studio_projects_name ON flow_studio_projects(name)"))
                    conn.execute(text("CREATE INDEX idx_flow_studio_projects_user_id ON flow_studio_projects(user_id)"))
                    conn.execute(text("CREATE INDEX idx_flow_studio_projects_group_id ON flow_studio_projects(group_id)"))
                    logger.info("✅ flow_studio_projects 테이블 생성 완료")
                
                # 2. flow_studio_flows 테이블에 Publish 관련 컬럼 추가
                logger.info("2. flow_studio_flows 테이블에 Publish 컬럼 추가...")
                
                # 기존 컬럼 확인
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'flow_studio_flows' 
                    AND table_schema = 'public'
                """))
                
                existing_columns = [row[0] for row in result.fetchall()]
                logger.info(f"기존 컬럼: {existing_columns}")
                
                # publish_status 컬럼 추가
                if 'publish_status' not in existing_columns:
                    logger.info("publish_status 컬럼 추가...")
                    
                    # ENUM 타입 생성
                    conn.execute(text("""
                        DO $$ BEGIN
                            CREATE TYPE publishstatus AS ENUM ('draft', 'published', 'deprecated', 'archived');
                        EXCEPTION
                            WHEN duplicate_object THEN null;
                        END $$;
                    """))
                    
                    conn.execute(text("""
                        ALTER TABLE flow_studio_flows 
                        ADD COLUMN publish_status publishstatus NOT NULL DEFAULT 'draft'
                    """))
                    
                    # 인덱스 생성
                    conn.execute(text("CREATE INDEX idx_flow_studio_flows_publish_status ON flow_studio_flows(publish_status)"))
                    logger.info("✅ publish_status 컬럼 추가 완료")
                else:
                    logger.info("✅ publish_status 컬럼이 이미 존재합니다")
                
                # version 컬럼 추가
                if 'version' not in existing_columns:
                    logger.info("version 컬럼 추가...")
                    conn.execute(text("""
                        ALTER TABLE flow_studio_flows 
                        ADD COLUMN version VARCHAR(50) NOT NULL DEFAULT '1.0.0'
                    """))
                    logger.info("✅ version 컬럼 추가 완료")
                else:
                    logger.info("✅ version 컬럼이 이미 존재합니다")
                
                # is_latest_published 컬럼 추가
                if 'is_latest_published' not in existing_columns:
                    logger.info("is_latest_published 컬럼 추가...")
                    conn.execute(text("""
                        ALTER TABLE flow_studio_flows 
                        ADD COLUMN is_latest_published BOOLEAN NOT NULL DEFAULT FALSE
                    """))
                    
                    # 인덱스 생성
                    conn.execute(text("CREATE INDEX idx_flow_studio_flows_is_latest_published ON flow_studio_flows(is_latest_published)"))
                    logger.info("✅ is_latest_published 컬럼 추가 완료")
                else:
                    logger.info("✅ is_latest_published 컬럼이 이미 존재합니다")
                
                # 3. flow_studio_publishes 테이블 생성
                logger.info("3. flow_studio_publishes 테이블 생성...")
                
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'flow_studio_publishes'
                """))
                
                if not result.fetchone():
                    logger.info("flow_studio_publishes 테이블 생성...")
                    conn.execute(text("""
                        CREATE TABLE flow_studio_publishes (
                            id VARCHAR(36) PRIMARY KEY,
                            flow_id VARCHAR(36) NOT NULL,
                            version VARCHAR(50) NOT NULL,
                            publish_status publishstatus NOT NULL,
                            published_by VARCHAR(36) NOT NULL,
                            publish_message TEXT,
                            flow_data_snapshot JSONB NOT NULL,
                            webhook_url VARCHAR(500),
                            webhook_called BOOLEAN DEFAULT FALSE,
                            webhook_response JSONB,
                            target_environment VARCHAR(50) NOT NULL DEFAULT 'production',
                            deployment_config JSONB,
                            published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            deprecated_at TIMESTAMP,
                            FOREIGN KEY (flow_id) REFERENCES flow_studio_flows(id) ON DELETE CASCADE
                        )
                    """))
                    
                    # 인덱스 생성
                    conn.execute(text("CREATE INDEX idx_flow_studio_publishes_flow_id ON flow_studio_publishes(flow_id)"))
                    conn.execute(text("CREATE INDEX idx_flow_studio_publishes_status ON flow_studio_publishes(publish_status)"))
                    conn.execute(text("CREATE INDEX idx_flow_studio_publishes_published_by ON flow_studio_publishes(published_by)"))
                    conn.execute(text("CREATE INDEX idx_flow_studio_publishes_published_at ON flow_studio_publishes(published_at)"))
                    
                    logger.info("✅ flow_studio_publishes 테이블 생성 완료")
                else:
                    logger.info("✅ flow_studio_publishes 테이블이 이미 존재합니다")
                
                # 4. 외래키 제약조건 업데이트
                logger.info("4. 외래키 제약조건 확인 및 업데이트...")
                
                # flow_studio_flows의 project_id 외래키 확인
                result = conn.execute(text("""
                    SELECT constraint_name 
                    FROM information_schema.table_constraints 
                    WHERE table_name = 'flow_studio_flows' 
                    AND constraint_type = 'FOREIGN KEY'
                    AND table_schema = 'public'
                """))
                
                fk_constraints = [row[0] for row in result.fetchall()]
                logger.info(f"기존 외래키 제약조건: {fk_constraints}")
                
                # 기존 외래키가 flow_projects를 참조하는 경우 삭제하고 재생성
                for constraint in fk_constraints:
                    try:
                        # 제약조건 정보 확인
                        result = conn.execute(text(f"""
                            SELECT 
                                kcu.column_name,
                                ccu.table_name AS foreign_table_name,
                                ccu.column_name AS foreign_column_name
                            FROM information_schema.table_constraints AS tc 
                            JOIN information_schema.key_column_usage AS kcu
                                ON tc.constraint_name = kcu.constraint_name
                                AND tc.table_schema = kcu.table_schema
                            JOIN information_schema.constraint_column_usage AS ccu
                                ON ccu.constraint_name = tc.constraint_name
                                AND ccu.table_schema = tc.table_schema
                            WHERE tc.constraint_name = '{constraint}'
                        """))
                        
                        constraint_info = result.fetchone()
                        if constraint_info and constraint_info[1] == 'flow_projects':
                            logger.info(f"기존 제약조건 {constraint} 삭제 및 재생성...")
                            conn.execute(text(f"ALTER TABLE flow_studio_flows DROP CONSTRAINT {constraint}"))
                            
                            # 새 제약조건 생성
                            conn.execute(text("""
                                ALTER TABLE flow_studio_flows 
                                ADD CONSTRAINT fk_flow_studio_flows_project_id 
                                FOREIGN KEY (project_id) REFERENCES flow_studio_projects(id) ON DELETE CASCADE
                            """))
                            logger.info("✅ 외래키 제약조건 업데이트 완료")
                            break
                    except Exception as e:
                        logger.warning(f"제약조건 {constraint} 처리 중 오류 (무시됨): {e}")
                
                # 트랜잭션 커밋
                trans.commit()
                logger.info("✅ 모든 마이그레이션이 성공적으로 완료되었습니다!")
                
            except Exception as e:
                # 트랜잭션 롤백
                trans.rollback()
                logger.error(f"❌ 마이그레이션 중 오류 발생: {e}")
                raise
                
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        raise

if __name__ == "__main__":
    migrate_database() 