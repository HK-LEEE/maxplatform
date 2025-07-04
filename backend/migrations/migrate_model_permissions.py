"""
LLM 모델 권한 시스템 마이그레이션 스크립트
- maxllm_models.id를 Integer에서 UUID4로 변경
- 새로운 maxllm_model_permissions 테이블 생성
- 기존 데이터 보존 및 마이그레이션
"""

import uuid
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database import Base
from app.models.llm_chat import MAXLLM_Model, MAXLLM_Model_Permission

def create_migration_engine():
    """마이그레이션용 데이터베이스 엔진 생성"""
    database_url = settings.database_url
    engine = create_engine(database_url)
    return engine

def check_table_exists(engine, table_name):
    """테이블 존재 여부 확인"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def backup_existing_data(engine):
    """기존 데이터 백업"""
    print("📦 기존 maxllm_models 데이터 백업 중...")
    
    with engine.connect() as conn:
        # 기존 데이터 조회
        result = conn.execute(text("SELECT * FROM maxllm_models"))
        existing_data = result.fetchall()
        
        if not existing_data:
            print("ℹ️ 기존 데이터가 없습니다.")
            return []
        
        print(f"📊 {len(existing_data)}개의 기존 모델 데이터를 발견했습니다.")
        
        # 백업 테이블 생성 (이미 존재하면 삭제 후 재생성)
        conn.execute(text("DROP TABLE IF EXISTS maxllm_models_migration_backup"))
        conn.execute(text("""
            CREATE TABLE maxllm_models_migration_backup AS 
            SELECT * FROM maxllm_models
        """))
        conn.commit()
        
        print("✅ 백업 완료: maxllm_models_migration_backup 테이블에 저장됨")
        return existing_data

def migrate_model_table(engine, existing_data):
    """모델 테이블 마이그레이션"""
    print("🔄 maxllm_models 테이블 마이그레이션 중...")
    
    with engine.connect() as conn:
        # 기존 테이블 구조 확인
        inspector = inspect(engine)
        columns = inspector.get_columns('maxllm_models')
        id_column = next((col for col in columns if col['name'] == 'id'), None)
        
        if id_column and 'varchar' in str(id_column['type']).lower():
            print("ℹ️ 이미 UUID 타입으로 마이그레이션되어 있습니다.")
            return
        
        # 외래 키 제약 조건 확인 및 처리
        print("🔍 외래 키 제약 조건 확인 중...")
        
        # maxllm_chats 테이블에서 model_id 참조 확인
        chat_refs = conn.execute(text("""
            SELECT COUNT(*) as count 
            FROM information_schema.columns 
            WHERE table_name = 'maxllm_chats' AND column_name = 'model_id'
        """)).fetchone()
        
        if chat_refs and chat_refs.count > 0:
            print("⚠️ maxllm_chats.model_id가 참조하고 있습니다. 수동 처리가 필요할 수 있습니다.")
        
        # 1. 새로운 테이블 구조로 임시 테이블 생성
        conn.execute(text("DROP TABLE IF EXISTS maxllm_models_new"))
        conn.execute(text("""
            CREATE TABLE maxllm_models_new (
                id VARCHAR(36) PRIMARY KEY,
                model_name VARCHAR(255) NOT NULL,
                model_type VARCHAR(50) NOT NULL,
                model_id VARCHAR(255) NOT NULL,
                description TEXT,
                config JSONB NOT NULL,
                owner_type VARCHAR(50) NOT NULL,
                owner_id VARCHAR(255) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        
        # 2. 인덱스 생성
        conn.execute(text("CREATE INDEX idx_maxllm_models_new_id ON maxllm_models_new(id)"))
        conn.execute(text("CREATE INDEX idx_maxllm_models_new_model_name ON maxllm_models_new(model_name)"))
        conn.execute(text("CREATE INDEX idx_maxllm_models_new_model_type ON maxllm_models_new(model_type)"))
        conn.execute(text("CREATE INDEX idx_maxllm_models_new_model_id ON maxllm_models_new(model_id)"))
        conn.execute(text("CREATE INDEX idx_maxllm_models_new_owner_id ON maxllm_models_new(owner_id)"))
        
        # 3. 기존 데이터를 UUID와 함께 새 테이블로 복사
        if existing_data:
            print("📋 기존 데이터를 새로운 UUID와 함께 마이그레이션 중...")
            id_mapping = {}  # 기존 ID -> 새 UUID 매핑
            
            for row in existing_data:
                old_id = row.id
                new_uuid = str(uuid.uuid4())
                id_mapping[old_id] = new_uuid
                
                import json
                config_json = json.dumps(row.config) if isinstance(row.config, dict) else row.config
                
                conn.execute(text("""
                    INSERT INTO maxllm_models_new 
                    (id, model_name, model_type, model_id, description, config, 
                     owner_type, owner_id, is_active, created_at, updated_at)
                    VALUES 
                    (:id, :model_name, :model_type, :model_id, :description, :config,
                     :owner_type, :owner_id, :is_active, :created_at, :updated_at)
                """), {
                    'id': new_uuid,
                    'model_name': row.model_name,
                    'model_type': row.model_type,
                    'model_id': row.model_id,
                    'description': row.description,
                    'config': config_json,
                    'owner_type': row.owner_type,
                    'owner_id': row.owner_id,
                    'is_active': row.is_active,
                    'created_at': row.created_at,
                    'updated_at': row.updated_at
                })
            
            # ID 매핑 정보 저장
            conn.execute(text("DROP TABLE IF EXISTS model_id_mapping"))
            conn.execute(text("""
                CREATE TABLE model_id_mapping (
                    old_id INTEGER,
                    new_uuid VARCHAR(36),
                    migrated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            for old_id, new_uuid in id_mapping.items():
                conn.execute(text("""
                    INSERT INTO model_id_mapping (old_id, new_uuid) 
                    VALUES (:old_id, :new_uuid)
                """), {'old_id': old_id, 'new_uuid': new_uuid})
            
            print(f"✅ {len(existing_data)}개 레코드 마이그레이션 완료")
            print("📋 ID 매핑 정보가 model_id_mapping 테이블에 저장되었습니다.")
        
        # 4. 기존 테이블 삭제 및 새 테이블 이름 변경
        conn.execute(text("DROP TABLE maxllm_models"))
        conn.execute(text("ALTER TABLE maxllm_models_new RENAME TO maxllm_models"))
        
        conn.commit()
        print("✅ maxllm_models 테이블 마이그레이션 완료")

def create_permission_table(engine):
    """권한 테이블 생성"""
    print("🔄 maxllm_model_permissions 테이블 생성 중...")
    
    if check_table_exists(engine, 'maxllm_model_permissions'):
        print("ℹ️ maxllm_model_permissions 테이블이 이미 존재합니다.")
        return
    
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE maxllm_model_permissions (
                id VARCHAR(36) PRIMARY KEY,
                model_id VARCHAR(36) NOT NULL,
                grantee_type VARCHAR(50) NOT NULL,
                grantee_id VARCHAR(255) NOT NULL,
                granted_by UUID NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                CONSTRAINT fk_model_permissions_model_id 
                    FOREIGN KEY (model_id) REFERENCES maxllm_models(id) ON DELETE CASCADE,
                CONSTRAINT fk_model_permissions_granted_by 
                    FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE CASCADE
            )
        """))
        
        # 인덱스 생성
        conn.execute(text("CREATE INDEX idx_maxllm_model_permissions_id ON maxllm_model_permissions(id)"))
        conn.execute(text("CREATE INDEX idx_maxllm_model_permissions_model_id ON maxllm_model_permissions(model_id)"))
        conn.execute(text("CREATE INDEX idx_maxllm_model_permissions_grantee_type ON maxllm_model_permissions(grantee_type)"))
        conn.execute(text("CREATE INDEX idx_maxllm_model_permissions_grantee_id ON maxllm_model_permissions(grantee_id)"))
        conn.execute(text("CREATE INDEX idx_maxllm_model_permissions_granted_by ON maxllm_model_permissions(granted_by)"))
        
        # 복합 인덱스 (중복 권한 방지)
        conn.execute(text("""
            CREATE UNIQUE INDEX idx_maxllm_model_permissions_unique 
            ON maxllm_model_permissions(model_id, grantee_type, grantee_id)
        """))
        
        conn.commit()
        print("✅ maxllm_model_permissions 테이블 생성 완료")

def verify_migration(engine):
    """마이그레이션 결과 검증"""
    print("🔍 마이그레이션 결과 검증 중...")
    
    with engine.connect() as conn:
        # 테이블 존재 확인
        if not check_table_exists(engine, 'maxllm_models'):
            raise Exception("❌ maxllm_models 테이블이 존재하지 않습니다.")
        
        if not check_table_exists(engine, 'maxllm_model_permissions'):
            raise Exception("❌ maxllm_model_permissions 테이블이 존재하지 않습니다.")
        
        # 데이터 개수 확인
        models_count = conn.execute(text("SELECT COUNT(*) FROM maxllm_models")).scalar()
        permissions_count = conn.execute(text("SELECT COUNT(*) FROM maxllm_model_permissions")).scalar()
        
        print(f"📊 마이그레이션 결과:")
        print(f"   - maxllm_models: {models_count}개 레코드")
        print(f"   - maxllm_model_permissions: {permissions_count}개 레코드")
        
        # ID 타입 확인
        inspector = inspect(engine)
        columns = inspector.get_columns('maxllm_models')
        id_column = next((col for col in columns if col['name'] == 'id'), None)
        
        if id_column:
            print(f"   - maxllm_models.id 타입: {id_column['type']}")
        
        print("✅ 마이그레이션 검증 완료")

def main():
    """마이그레이션 실행"""
    print("🚀 LLM 모델 권한 시스템 마이그레이션 시작")
    print("=" * 50)
    
    try:
        # 데이터베이스 연결
        engine = create_migration_engine()
        print("✅ 데이터베이스 연결 성공")
        
        # 기존 데이터 백업
        existing_data = backup_existing_data(engine)
        
        # 모델 테이블 마이그레이션
        migrate_model_table(engine, existing_data)
        
        # 권한 테이블 생성
        create_permission_table(engine)
        
        # 검증
        verify_migration(engine)
        
        print("=" * 50)
        print("🎉 마이그레이션 완료!")
        print("\n📋 다음 단계:")
        print("1. 애플리케이션 재시작")
        print("2. 모델 권한 관리 API 테스트")
        print("3. 백업 테이블들 정리 (필요시)")
        
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        print("\n🔧 문제 해결:")
        print("1. 데이터베이스 연결 정보 확인")
        print("2. 백업 테이블에서 데이터 복구 가능")
        print("3. 로그 확인 후 다시 시도")
        raise

if __name__ == "__main__":
    main()