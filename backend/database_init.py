"""
MySQL 데이터베이스 초기화 및 시드 데이터 삽입 스크립트
UUID 기반 사용자 시스템
"""
import uuid
from datetime import datetime
from passlib.context import CryptContext
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import User, Role, Group, Workspace
from app.database import Base

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_database_and_tables():
    """데이터베이스와 테이블 생성"""
    # MySQL 연결 설정
    MYSQL_URL = "mysql+pymysql://test:test@localhost:3306/jupyter_platform"
    
    try:
        engine = create_engine(MYSQL_URL)
        print("MySQL 데이터베이스에 연결되었습니다.")
        
        # 모든 테이블 삭제 후 재생성
        print("기존 테이블을 삭제하고 새로 생성합니다...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("테이블이 성공적으로 생성되었습니다.")
        
        return engine
        
    except Exception as e:
        print(f"데이터베이스 연결 실패: {e}")
        raise

def insert_seed_data(engine):
    """시드 데이터 삽입"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("시드 데이터를 삽입합니다...")
        
        # 1. 역할(Role) 생성
        roles_data = [
            {"name": "admin", "description": "시스템 관리자", "permissions": '{"all": true}'},
            {"name": "manager", "description": "매니저", "permissions": '{"manage_users": true, "manage_workspaces": true}'},
            {"name": "user", "description": "일반 사용자", "permissions": '{"create_workspace": true, "manage_own_workspace": true}'},
            {"name": "developer", "description": "개발자", "permissions": '{"create_workspace": true, "manage_own_workspace": true, "debug": true}'},
            {"name": "viewer", "description": "읽기 전용 사용자", "permissions": '{"view_only": true}'}
        ]
        
        for role_data in roles_data:
            role = Role(**role_data)
            db.add(role)
        
        db.commit()
        print("역할 데이터가 생성되었습니다.")
        
        # 2. 사용자(User) 생성 먼저 (UUID 기반)
        admin_id = str(uuid.uuid4())
        
        users_data = [
            {
                "id": admin_id,
                "real_name": "시스템 관리자",
                "display_name": "Admin",
                "email": "admin@jupyter-platform.com",
                "phone_number": "010-1234-5678",
                "department": "IT팀",
                "position": "시스템 관리자",
                "hashed_password": hash_password("admin123!"),
                "is_active": True,
                "is_admin": True,
                "is_verified": True,
                "login_count": 0
            },
            {
                "id": str(uuid.uuid4()),
                "real_name": "홍길동",
                "display_name": "길동이",
                "email": "test@example.com",
                "phone_number": "010-9876-5432",
                "department": "개발팀",
                "position": "개발자",
                "hashed_password": hash_password("test123!"),
                "is_active": True,
                "is_admin": False,
                "is_verified": True,
                "login_count": 0
            },
            {
                "id": str(uuid.uuid4()),
                "real_name": "김매니저",
                "display_name": "매니저 김",
                "email": "manager1@jupyter-platform.com",
                "phone_number": "010-1111-2222",
                "department": "경영팀",
                "position": "매니저",
                "hashed_password": hash_password("manager123!"),
                "is_active": True,
                "is_admin": False,
                "is_verified": True,
                "login_count": 0
            },
            {
                "id": str(uuid.uuid4()),
                "real_name": "이사용자",
                "display_name": "사용자",
                "email": "user1@jupyter-platform.com",
                "phone_number": "010-3333-4444",
                "department": "마케팅팀",
                "position": "주임",
                "hashed_password": hash_password("user123!"),
                "is_active": True,
                "is_admin": False,
                "is_verified": False,
                "login_count": 0
            },
            {
                "id": str(uuid.uuid4()),
                "real_name": "박개발자",
                "display_name": "Dev 박",
                "email": "dev1@jupyter-platform.com",
                "phone_number": "010-5555-6666",
                "department": "개발팀",
                "position": "시니어 개발자",
                "hashed_password": hash_password("dev123!"),
                "is_active": True,
                "is_admin": False,
                "is_verified": True,
                "login_count": 0
            }
        ]
        
        for user_data in users_data:
            user = User(**user_data)
            db.add(user)
        
        db.commit()
        print("사용자 데이터가 생성되었습니다.")
        
        # 3. 그룹(Group) 생성 (admin 사용자가 생성한 것으로)
        groups_data = [
            {"name": "Default Users", "description": "기본 사용자 그룹", "created_by": admin_id},
            {"name": "Developers", "description": "개발팀", "created_by": admin_id},
            {"name": "Data Scientists", "description": "데이터 사이언티스트 팀", "created_by": admin_id},
            {"name": "Managers", "description": "관리자 그룹", "created_by": admin_id},
        ]
        
        for group_data in groups_data:
            group = Group(**group_data)
            db.add(group)
        
        db.commit()
        print("그룹 데이터가 생성되었습니다.")
        
        # 4. 사용자-역할 및 그룹 매핑
        users = db.query(User).all()
        roles = {role.name: role for role in db.query(Role).all()}
        groups = {group.name: group for group in db.query(Group).all()}
        
        # 사용자별 역할 및 그룹 할당
        user_mappings = {
            "admin@jupyter-platform.com": {"role": "admin", "group": "Managers"},
            "test@example.com": {"role": "user", "group": "Default Users"},
            "manager1@jupyter-platform.com": {"role": "manager", "group": "Managers"},
            "user1@jupyter-platform.com": {"role": "user", "group": "Default Users"},
            "dev1@jupyter-platform.com": {"role": "user", "group": "Developers"}  # 개발자도 user 역할
        }
        
        for user in users:
            if user.email in user_mappings:
                mapping = user_mappings[user.email]
                
                # 역할 할당
                if mapping["role"] in roles:
                    user.role_id = roles[mapping["role"]].id
                    
                # 그룹 할당
                if mapping["group"] in groups:
                    user.group_id = groups[mapping["group"]].id
        
        db.commit()
        print("사용자-역할 및 그룹 매핑이 완료되었습니다.")
        
        # 5. 샘플 워크스페이스 생성
        admin_user = db.query(User).filter(User.email == "admin@jupyter-platform.com").first()
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        
        workspaces_data = [
            {
                "name": "관리자 워크스페이스",
                "description": "시스템 관리용 워크스페이스",
                "owner_id": admin_user.id,
                "is_active": True,
                "is_public": False,
                "workspace_path": "/workspaces/admin",
                "max_storage_mb": 5000
            },
            {
                "name": "테스트 워크스페이스",
                "description": "개발 및 테스트용 워크스페이스",
                "owner_id": test_user.id,
                "is_active": True,
                "is_public": True,
                "workspace_path": "/workspaces/test",
                "max_storage_mb": 2000
            }
        ]
        
        for workspace_data in workspaces_data:
            workspace = Workspace(**workspace_data)
            db.add(workspace)
        
        db.commit()
        print("워크스페이스 데이터가 생성되었습니다.")
        
        print("\n=== 시드 데이터 삽입 완료 ===")
        print("생성된 계정 정보:")
        print("1. admin@jupyter-platform.com / admin123! / 010-1234-5678 (관리자)")
        print("2. test@example.com / test123! / 010-9876-5432 (일반 사용자)")
        print("3. manager1@jupyter-platform.com / manager123! / 010-1111-2222 (매니저)")
        print("4. user1@jupyter-platform.com / user123! / 010-3333-4444 (일반 사용자)")
        print("5. dev1@jupyter-platform.com / dev123! / 010-5555-6666 (개발자)")
        
    except Exception as e:
        print(f"시드 데이터 삽입 실패: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    """메인 실행 함수"""
    print("=== Jupyter Platform 데이터베이스 초기화 (UUID 기반) ===")
    
    try:
        # 1. 데이터베이스 및 테이블 생성
        engine = create_database_and_tables()
        
        # 2. 시드 데이터 삽입
        insert_seed_data(engine)
        
        print("\n데이터베이스 초기화가 완료되었습니다!")
        
    except Exception as e:
        print(f"초기화 실패: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main() 