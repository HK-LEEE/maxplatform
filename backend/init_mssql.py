"""
MSSQL(SQL Server) 데이터베이스 초기화 스크립트

데이터베이스 생성은 제외하고, 테이블 생성 및 기본 데이터만 삽입합니다.
데이터베이스는 미리 생성되어 있어야 합니다.

사용법:
1. SQL Server에서 데이터베이스 생성: CREATE DATABASE jupyter_platform
2. .env 파일 설정:
   DATABASE_TYPE=mssql
   MSSQL_DATABASE_URL=mssql+pyodbc://sa:YourPassword123@localhost:1433/jupyter_platform?driver=ODBC+Driver+17+for+SQL+Server
3. 스크립트 실행: python init_mssql.py
"""

import os
import sys
import uuid
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
import pyodbc

# 현재 파일의 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from app.models.user import User, Role, Group, Base
from app.models.workspace import Workspace
from app.config import settings

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def generate_user_id() -> str:
    """UUID 기반 사용자 ID 생성"""
    return str(uuid.uuid4())

def check_sql_server_connection():
    """SQL Server 연결 테스트"""
    try:
        print("🔍 SQL Server 연결 테스트 중...")
        
        # pyodbc로 직접 연결 테스트
        connection_string = settings.mssql_database_url
        if "mssql+pyodbc://" in connection_string:
            # SQLAlchemy URL에서 pyodbc 연결 문자열 추출
            parts = connection_string.replace("mssql+pyodbc://", "").split("?")
            base_part = parts[0]
            driver_part = parts[1] if len(parts) > 1 else ""
            
            # 사용자:비밀번호@서버:포트/데이터베이스 분해
            auth_server = base_part.split("@")
            if len(auth_server) == 2:
                auth = auth_server[0]
                server_db = auth_server[1]
                
                username = auth.split(":")[0]
                password = auth.split(":")[1]
                
                server_port = server_db.split("/")[0]
                database = server_db.split("/")[1]
                
                server = server_port.split(":")[0]
                port = server_port.split(":")[1] if ":" in server_port else "1433"
                
                driver = "ODBC Driver 17 for SQL Server"
                if "driver=" in driver_part:
                    driver = driver_part.split("driver=")[1].replace("+", " ")
                
                odbc_conn_str = f"DRIVER={{{driver}}};SERVER={server},{port};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;Encrypt=no"
                
                print(f"연결 문자열: DRIVER={{{driver}}};SERVER={server},{port};DATABASE={database};UID={username};PWD=***")
                
                conn = pyodbc.connect(odbc_conn_str)
                cursor = conn.cursor()
                cursor.execute("SELECT @@VERSION")
                version = cursor.fetchone()[0]
                print(f"✅ SQL Server 연결 성공!")
                print(f"📋 버전: {version}")
                conn.close()
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ SQL Server 연결 실패: {e}")
        print("\n🔧 해결 방법:")
        print("1. SQL Server가 실행 중인지 확인")
        print("2. 데이터베이스가 존재하는지 확인")
        print("3. 사용자 계정과 비밀번호 확인")
        print("4. ODBC Driver 17 for SQL Server 설치 확인")
        print("5. 방화벽에서 1433 포트 허용 확인")
        return False

def create_database_and_tables():
    """테이블 생성"""
    try:
        print("📊 데이터베이스 테이블 생성 중...")
        
        # SQLAlchemy 엔진 생성
        engine = create_engine(
            settings.mssql_database_url,
            connect_args={
                "TrustServerCertificate": "yes",
                "Encrypt": "no"
            },
            echo=False
        )
        
        # 모든 테이블 생성
        Base.metadata.create_all(bind=engine)
        print("✅ 테이블 생성 완료")
        
        return engine
        
    except Exception as e:
        print(f"❌ 테이블 생성 실패: {e}")
        raise

def insert_seed_data(engine):
    """기본 데이터 삽입"""
    print("📝 기본 데이터 삽입 중...")
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 1. 역할(Role) 생성
        print("🔐 기본 역할 생성 중...")
        
        roles_data = [
            {
                "name": "admin",
                "description": "시스템 관리자",
                "permissions": json.dumps({
                    "can_manage_users": True,
                    "can_manage_workspaces": True,
                    "can_manage_system": True,
                    "can_view_all_workspaces": True
                })
            },
            {
                "name": "manager", 
                "description": "프로젝트 관리자",
                "permissions": json.dumps({
                    "can_create_workspace": True,
                    "can_manage_own_workspace": True,
                    "can_manage_group_workspaces": True,
                    "can_manage_users_in_group": True,
                    "can_upload_files": True,
                    "can_run_jupyter": True
                })
            },
            {
                "name": "user",
                "description": "일반 사용자", 
                "permissions": json.dumps({
                    "can_create_workspace": True,
                    "can_manage_own_workspace": True,
                    "can_upload_files": True,
                    "can_run_jupyter": True
                })
            }
        ]
        
        for role_data in roles_data:
            existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
            if not existing_role:
                role = Role(**role_data)
                db.add(role)
                print(f"  ✅ {role_data['name']} 역할 생성")
        
        db.commit()
        print("역할 데이터가 생성되었습니다.")
        
        # 2. 관리자 사용자 생성 (임시)
        print("👤 관리자 사용자 생성 중...")
        admin_id = generate_user_id()
        
        admin_user = db.query(User).filter(User.email == "admin@jupyter-platform.com").first()
        if not admin_user:
            admin_role = db.query(Role).filter(Role.name == "admin").first()
            admin_user = User(
                id=admin_id,
                real_name="시스템 관리자",
                display_name="Admin",
                email="admin@jupyter-platform.com",
                phone_number="010-1234-5678",
                department="IT팀",
                position="시스템 관리자",
                hashed_password=hash_password("admin123!"),
                is_active=True,
                is_admin=True,
                is_verified=True,
                login_count=0,
                role_id=admin_role.id if admin_role else None
            )
            db.add(admin_user)
            print("  ✅ 관리자 사용자 생성")
        
        db.commit()
        
        # 3. 그룹(Group) 생성
        print("👥 기본 그룹 생성 중...")
        
        groups_data = [
            {"name": "Managers", "description": "관리자 그룹", "created_by": admin_user.id},
            {"name": "Default Users", "description": "기본 사용자 그룹", "created_by": admin_user.id},
            {"name": "Developers", "description": "개발팀", "created_by": admin_user.id},
            {"name": "Data Scientists", "description": "데이터 사이언티스트 팀", "created_by": admin_user.id},
        ]
        
        for group_data in groups_data:
            existing_group = db.query(Group).filter(Group.name == group_data["name"]).first()
            if not existing_group:
                group = Group(**group_data)
                db.add(group)
                print(f"  ✅ {group_data['name']} 그룹 생성")
        
        db.commit()
        print("그룹 데이터가 생성되었습니다.")
        
        # 관리자 사용자의 그룹 할당
        if admin_user and not admin_user.group_id:
            managers_group = db.query(Group).filter(Group.name == "Managers").first()
            if managers_group:
                admin_user.group_id = managers_group.id
                db.commit()
        
        # 4. 샘플 사용자들 생성
        print("👥 샘플 사용자 생성 중...")
        
        roles = {role.name: role for role in db.query(Role).all()}
        groups = {group.name: group for group in db.query(Group).all()}
        
        sample_users = [
            {
                "id": generate_user_id(),
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
                "login_count": 0,
                "role": "user",
                "group": "Default Users"
            },
            {
                "id": generate_user_id(),
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
                "login_count": 0,
                "role": "manager",
                "group": "Managers"
            },
            {
                "id": generate_user_id(),
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
                "login_count": 0,
                "role": "user", 
                "group": "Default Users"
            },
            {
                "id": generate_user_id(),
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
                "login_count": 0,
                "role": "user",
                "group": "Developers"
            }
        ]
        
        for user_data in sample_users:
            existing_user = db.query(User).filter(User.email == user_data["email"]).first()
            if not existing_user:
                role_name = user_data.pop("role")
                group_name = user_data.pop("group")
                
                user = User(**user_data)
                
                # 역할 할당
                if role_name in roles:
                    user.role_id = roles[role_name].id
                
                # 그룹 할당
                if group_name in groups:
                    user.group_id = groups[group_name].id
                
                db.add(user)
                print(f"  ✅ {user_data['real_name']} ({user_data['email']}) 생성")
        
        db.commit()
        print("샘플 사용자 생성 완료")
        
        # 5. 샘플 워크스페이스 생성
        print("🗂️ 샘플 워크스페이스 생성 중...")
        
        admin_user = db.query(User).filter(User.email == "admin@jupyter-platform.com").first()
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        
        workspaces_data = [
            {
                "name": "관리자 워크스페이스",
                "description": "시스템 관리용 워크스페이스",
                "path": "/workspaces/admin",
                "owner_id": admin_user.id,
                "is_active": True,
                "is_public": False,
                "max_storage_mb": 5000
            },
            {
                "name": "테스트 워크스페이스", 
                "description": "개발 및 테스트용 워크스페이스",
                "path": "/workspaces/test",
                "owner_id": test_user.id if test_user else admin_user.id,
                "is_active": True,
                "is_public": True,
                "max_storage_mb": 2000
            }
        ]
        
        for workspace_data in workspaces_data:
            existing_workspace = db.query(Workspace).filter(Workspace.name == workspace_data["name"]).first()
            if not existing_workspace:
                workspace = Workspace(**workspace_data)
                db.add(workspace)
                print(f"  ✅ {workspace_data['name']} 워크스페이스 생성")
        
        db.commit()
        print("워크스페이스 데이터가 생성되었습니다.")
        
        print("\n=== MSSQL 시드 데이터 삽입 완료 ===")
        print("생성된 계정 정보:")
        print("1. admin@jupyter-platform.com / admin123! / 010-1234-5678 (관리자)")
        print("2. test@example.com / test123! / 010-9876-5432 (일반 사용자)")
        print("3. manager1@jupyter-platform.com / manager123! / 010-1111-2222 (매니저)")
        print("4. user1@jupyter-platform.com / user123! / 010-3333-4444 (일반 사용자)")
        print("5. dev1@jupyter-platform.com / dev123! / 010-5555-6666 (개발자)")
        
    except Exception as e:
        print(f"시드 데이터 삽입 실패: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    """메인 실행 함수"""
    print("=== Jupyter Platform MSSQL 데이터베이스 초기화 ===")
    print(f"📝 데이터베이스 타입: {settings.database_type}")
    print(f"🔗 연결 URL: {settings.mssql_database_url.split('://')[0]}://***@{settings.mssql_database_url.split('@')[1] if '@' in settings.mssql_database_url else 'localhost'}")
    
    try:
        # 1. SQL Server 연결 테스트
        if not check_sql_server_connection():
            print("❌ SQL Server 연결 실패로 초기화를 중단합니다.")
            return False
        
        # 2. 테이블 생성
        engine = create_database_and_tables()
        
        # 3. 시드 데이터 삽입
        insert_seed_data(engine)
        
        print("\n🎉 MSSQL 데이터베이스 초기화가 완료되었습니다!")
        print("\n📝 다음 단계:")
        print("1. backend 폴더에서 서버 실행: python main.py")
        print("2. 브라우저에서 접속: http://localhost:8000")
        print("3. 위의 계정 정보로 로그인 테스트")
        
        return True
        
    except Exception as e:
        print(f"❌ 초기화 실패: {e}")
        return False

if __name__ == "__main__":
    main() 