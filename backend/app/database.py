import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from fastapi import HTTPException, status
from .config import settings

# .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 베이스 클래스 생성
Base = declarative_base()

def get_database_url():
    """현재 설정된 데이터베이스 URL 반환"""
    return settings.database_url

def get_database_engine():
    """PostgreSQL 엔진 생성"""
    database_url = settings.database_url
    
    # PostgreSQL 엔진 설정
    common_args = {
        "echo": False,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
        "pool_timeout": 30,
        "max_overflow": 0
    }
    
    try:
        # PostgreSQL 전용 설정
        engine = create_engine(
            database_url,
            connect_args={
                "connect_timeout": 60,
                "options": "-c timezone=UTC"
            },
            **common_args
        )
        logger.info(f"PostgreSQL 데이터베이스 연결 시도: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
        
        # 연결 테스트
        with engine.connect() as connection:
            logger.info("✅ PostgreSQL 데이터베이스 연결 성공")
                
        return engine
        
    except Exception as e:
        logger.error(f"❌ PostgreSQL 연결 실패: {e}")
        
        logger.info("PostgreSQL 서버가 실행되고 있는지 확인하세요.")
        logger.info("설치 방법:")
        logger.info("1. PostgreSQL 공식 사이트에서 다운로드")
        logger.info("2. Docker: docker run -d -p 5432:5432 -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=jupyter_platform postgres:15")
        logger.info("3. 또는 local 서버 설치 후 데이터베이스 생성")
        
        # 연결 실패시에도 실제 PostgreSQL 엔진 사용 (재시도)
        raise

# 데이터베이스 엔진 생성
engine = get_database_engine()

# 비동기 엔진 생성 (마이그레이션용)
async_database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
async_engine = create_async_engine(async_database_url, echo=False)

# 세션 팩토리 생성
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

# 비동기 세션 팩토리 생성
AsyncSessionLocal = sessionmaker(
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    bind=async_engine
)

# 데이터베이스 세션 의존성
def get_db():
    """데이터베이스 세션 생성 및 관리"""
    db = None
    try:
        db = SessionLocal()
        yield db
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy 오류: {str(e)}")
        if db:
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터베이스 연결 오류가 발생했습니다."
        )
    except HTTPException:
        # HTTPException은 그대로 재발생 (인증 에러 등)
        if db:
            db.rollback()
        raise
    except Exception as e:
        logger.error(f"데이터베이스 세션 생성 실패: {str(e)}")
        # 더 상세한 에러 정보 출력
        import traceback
        logger.error(f"세부 에러: {traceback.format_exc()}")
        if db:
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다."
        )
    finally:
        if db:
            try:
                db.close()
            except Exception as e:
                logger.error(f"데이터베이스 세션 종료 실패: {str(e)}")

async def get_async_session():
    """비동기 데이터베이스 세션 생성 및 관리"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            logger.error(f"비동기 SQLAlchemy 오류: {str(e)}")
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="데이터베이스 연결 오류가 발생했습니다."
            )
        except HTTPException:
            # HTTPException은 그대로 재발생 (인증 에러 등)
            await session.rollback()
            raise
        except Exception as e:
            logger.error(f"비동기 데이터베이스 세션 생성 실패: {str(e)}")
            import traceback
            logger.error(f"세부 에러: {traceback.format_exc()}")
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="서버 내부 오류가 발생했습니다."
            )

def create_tables():
    """모든 테이블 생성"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 데이터베이스 테이블 생성 완료")
    except Exception as e:
        logger.error(f"❌ 테이블 생성 실패: {e}")
        raise

def test_connection():
    """데이터베이스 연결 테스트"""
    try:
        from sqlalchemy import text
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).fetchone()
            return True
    except Exception as e:
        logger.error(f"연결 테스트 실패: {e}")
        return False

def drop_and_recreate_tables():
    """개발 환경에서 테이블을 삭제하고 재생성"""
    try:
        logger.info("🗑️ 기존 테이블 삭제 중...")
        
        # 메타데이터 생성
        from sqlalchemy import MetaData
        metadata = MetaData()
        
        # 엔진 생성
        engine = get_database_engine()
        
        # 모든 테이블 메타데이터 로드
        metadata.reflect(bind=engine)
        
        # 모든 테이블 삭제 (외래 키 제약 조건 때문에 역순으로)
        metadata.drop_all(bind=engine)
        logger.info("✅ 기존 테이블 삭제 완료")
        
        # 새 테이블 생성
        create_tables()
        logger.info("✅ 새 테이블 생성 완료")
        
    except Exception as e:
        logger.error(f"❌ 테이블 재생성 실패: {str(e)}")
        raise e 

async def recreate_feature_tables_with_categories():
    """기능 카테고리 테이블 추가 및 기존 데이터 마이그레이션"""
    logger.info("Starting feature table recreation with categories...")
    
    async with async_engine.begin() as conn:
        try:
            # 1. 기존 Feature 데이터 백업
            logger.info("Backing up existing feature data...")
            result = await conn.execute(text("SELECT * FROM features"))
            existing_features = result.fetchall()
            
            # 2. 관계 테이블 데이터 백업
            logger.info("Backing up relationship data...")
            group_features_result = await conn.execute(text("SELECT * FROM group_features"))
            group_features_data = group_features_result.fetchall()
            
            role_features_result = await conn.execute(text("SELECT * FROM role_features")) 
            role_features_data = role_features_result.fetchall()
            
            user_features_result = await conn.execute(text("SELECT * FROM user_features"))
            user_features_data = user_features_result.fetchall()
            
            # 3. 외래키 제약조건 삭제
            try:
                await conn.execute(text("ALTER TABLE group_features DROP CONSTRAINT IF EXISTS group_features_feature_id_fkey"))
                await conn.execute(text("ALTER TABLE role_features DROP CONSTRAINT IF EXISTS role_features_feature_id_fkey"))
                await conn.execute(text("ALTER TABLE user_features DROP CONSTRAINT IF EXISTS user_features_feature_id_fkey"))
            except Exception as e:
                logger.warning(f"Foreign key constraint removal warning: {e}")
            
            # 4. 관계 테이블 데이터 삭제
            await conn.execute(text("DELETE FROM group_features"))
            await conn.execute(text("DELETE FROM role_features"))
            await conn.execute(text("DELETE FROM user_features"))
            
            # 5. 기존 테이블 삭제
            await conn.execute(text("DROP TABLE IF EXISTS features"))
            
            # 6. 새 테이블 생성
            from .models import FeatureCategory, Feature
            await conn.run_sync(Base.metadata.create_all, tables=[
                FeatureCategory.__table__,
                Feature.__table__
            ])
            
            # 7. 기본 카테고리 생성
            categories = [
                {
                    "name": "authentication",
                    "display_name": "인증 및 계정",
                    "description": "로그인, 회원가입, 프로필 관리",
                    "icon": "shield-check",
                    "color": "#3B82F6",
                    "sort_order": 1
                },
                {
                    "name": "workspace",
                    "display_name": "워크스페이스",
                    "description": "작업 공간 관리",
                    "icon": "briefcase",
                    "color": "#10B981",
                    "sort_order": 2
                },
                {
                    "name": "development",
                    "display_name": "개발 도구",
                    "description": "Jupyter, 파일 관리 등 개발 도구",
                    "icon": "code",
                    "color": "#F59E0B",
                    "sort_order": 3
                },
                {
                    "name": "ai_ml",
                    "display_name": "AI/ML",
                    "description": "LLM, LLMOps, RAG 등 AI/ML 기능",
                    "icon": "cpu-chip",
                    "color": "#8B5CF6",
                    "sort_order": 4
                },
                {
                    "name": "admin",
                    "display_name": "시스템 관리",
                    "description": "사용자, 권한, 시스템 관리",
                    "icon": "cog-8-tooth",
                    "color": "#EF4444",
                    "sort_order": 5
                }
            ]
            
            category_mapping = {}
            for category in categories:
                result = await conn.execute(
                    text("""
                        INSERT INTO feature_categories (name, display_name, description, icon, color, sort_order, is_active, created_at, updated_at)
                        VALUES (:name, :display_name, :description, :icon, :color, :sort_order, true, now(), now())
                        RETURNING id
                    """),
                    category
                )
                category_id = result.fetchone()[0]
                category_mapping[category["name"]] = category_id
            
            # 8. 기존 Feature 데이터 복원 (카테고리 매핑 포함)
            old_to_new_feature_id = {}
            if existing_features:
                logger.info(f"Restoring {len(existing_features)} features with category mapping...")
                
                # 카테고리 매핑 규칙
                def get_category_id(feature_name, url_path=None):
                    if feature_name in ["AUTH_ACCESS"]:
                        return category_mapping["authentication"]
                    elif feature_name in ["MAIN_DASHBOARD", "WORKSPACE_MANAGE"]:
                        return category_mapping["workspace"]
                    elif feature_name in ["JUPYTER_ACCESS", "FILES_MANAGE"]:
                        return category_mapping["development"]
                    elif feature_name in ["LLM_CHAT_ACCESS", "LLMOPS_PLATFORM", "RAG_DATASOURCES", "FLOW_STUDIO", "SECRETS_MANAGE"]:
                        return category_mapping["ai_ml"]
                    elif feature_name in ["ADMIN_SYSTEM"]:
                        return category_mapping["admin"]
                    else:
                        return category_mapping["workspace"]  # 기본값
                
                for feature in existing_features:
                    category_id = get_category_id(feature.name, feature.url_path if hasattr(feature, 'url_path') else None)
                    
                    result = await conn.execute(
                        text("""
                            INSERT INTO features (name, display_name, description, category_id, icon, url_path, 
                                                auto_grant, is_active, requires_approval, is_external, open_in_new_tab, 
                                                sort_order, created_at, updated_at)
                            VALUES (:name, :display_name, :description, :category_id, :icon, :url_path,
                                    :auto_grant, :is_active, :requires_approval, :is_external, :open_in_new_tab,
                                    :sort_order, :created_at, :updated_at)
                            RETURNING id
                        """),
                        {
                            "name": feature.name,
                            "display_name": feature.display_name,
                            "description": getattr(feature, 'description', None),
                            "category_id": category_id,
                            "icon": getattr(feature, 'icon', None),
                            "url_path": getattr(feature, 'url_path', None),
                            "auto_grant": getattr(feature, 'auto_grant', False),
                            "is_active": getattr(feature, 'is_active', True),
                            "requires_approval": getattr(feature, 'requires_approval', False),
                            "is_external": getattr(feature, 'is_external', False),
                            "open_in_new_tab": getattr(feature, 'open_in_new_tab', False),
                            "sort_order": 0,
                            "created_at": getattr(feature, 'created_at', 'now()'),
                            "updated_at": getattr(feature, 'updated_at', 'now()')
                        }
                    )
                    new_feature_id = result.fetchone()[0]
                    old_to_new_feature_id[feature.id] = new_feature_id
            
            # 9. 관계 테이블 데이터 복원
            logger.info("Restoring relationship data...")
            
            # group_features 복원
            for group_feature in group_features_data:
                old_feature_id = group_feature.feature_id
                if old_feature_id in old_to_new_feature_id:
                    new_feature_id = old_to_new_feature_id[old_feature_id]
                    await conn.execute(
                        text("INSERT INTO group_features (group_id, feature_id) VALUES (:group_id, :feature_id)"),
                        {"group_id": group_feature.group_id, "feature_id": new_feature_id}
                    )
            
            # role_features 복원
            for role_feature in role_features_data:
                old_feature_id = role_feature.feature_id
                if old_feature_id in old_to_new_feature_id:
                    new_feature_id = old_to_new_feature_id[old_feature_id]
                    await conn.execute(
                        text("INSERT INTO role_features (role_id, feature_id) VALUES (:role_id, :feature_id)"),
                        {"role_id": role_feature.role_id, "feature_id": new_feature_id}
                    )
            
            # user_features 복원
            for user_feature in user_features_data:
                old_feature_id = user_feature.feature_id
                if old_feature_id in old_to_new_feature_id:
                    new_feature_id = old_to_new_feature_id[old_feature_id]
                    await conn.execute(
                        text("INSERT INTO user_features (user_id, feature_id) VALUES (:user_id, :feature_id)"),
                        {"user_id": user_feature.user_id, "feature_id": new_feature_id}
                    )
            
            # 10. 외래키 제약조건 재생성
            await conn.execute(text("""
                ALTER TABLE group_features 
                ADD CONSTRAINT group_features_feature_id_fkey 
                FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE CASCADE
            """))
            
            await conn.execute(text("""
                ALTER TABLE role_features 
                ADD CONSTRAINT role_features_feature_id_fkey 
                FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE CASCADE
            """))
            
            await conn.execute(text("""
                ALTER TABLE user_features 
                ADD CONSTRAINT user_features_feature_id_fkey 
                FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE CASCADE
            """))
            
            await conn.commit()
            logger.info("Feature tables recreation with categories completed successfully!")
            
        except Exception as e:
            await conn.rollback()
            logger.error(f"Error recreating feature tables: {e}")
            raise 