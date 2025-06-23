import asyncio
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from .models import User, Role, Group
from .database import get_database_url, Base

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def init_database():
    """데이터베이스 테이블 생성 및 기본 데이터 삽입"""
    
    # 데이터베이스 연결
    database_url = get_database_url()
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    print("📊 데이터베이스 테이블 생성 중...")
    # 모든 테이블 생성
    Base.metadata.create_all(bind=engine)
    print("✅ 테이블 생성 완료")
    
    # 세션 생성
    db = SessionLocal()
    
    try:
        # 기본 역할(Role) 생성
        print("🔐 기본 역할 생성 중...")
        
        # Admin 역할
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(
                name="admin",
                description="시스템 관리자",
                permissions=json.dumps({
                    "can_manage_users": True,
                    "can_manage_workspaces": True,
                    "can_manage_system": True,
                    "can_view_all_workspaces": True
                })
            )
            db.add(admin_role)
            print("  ✅ Admin 역할 생성")
        
        # User 역할
        user_role = db.query(Role).filter(Role.name == "user").first()
        if not user_role:
            user_role = Role(
                name="user",
                description="일반 사용자",
                permissions=json.dumps({
                    "can_create_workspace": True,
                    "can_manage_own_workspace": True,
                    "can_upload_files": True,
                    "can_run_jupyter": True
                })
            )
            db.add(user_role)
            print("  ✅ User 역할 생성")
        
        # Manager 역할
        manager_role = db.query(Role).filter(Role.name == "manager").first()
        if not manager_role:
            manager_role = Role(
                name="manager",
                description="프로젝트 관리자",
                permissions=json.dumps({
                    "can_create_workspace": True,
                    "can_manage_own_workspace": True,
                    "can_manage_group_workspaces": True,
                    "can_manage_users_in_group": True,
                    "can_upload_files": True,
                    "can_run_jupyter": True
                })
            )
            db.add(manager_role)
            print("  ✅ Manager 역할 생성")
        
        # 기본 그룹 생성
        print("👥 기본 그룹 생성 중...")
        
        # 먼저 커밋하여 role들을 저장
        db.commit()
        
        # 기본 Admin 사용자 생성
        print("👤 기본 Admin 사용자 생성 중...")
        admin_user = db.query(User).filter(User.email == "admin@jupyter-platform.com").first()
        if not admin_user:
            admin_user = User(
                real_name="시스템 관리자",
                display_name="Admin",
                email="admin@jupyter-platform.com",
                hashed_password=hash_password("admin123!"),
                is_active=True,
                is_admin=True,
                role_id=admin_role.id  # 역할 직접 할당
            )
            db.add(admin_user)
            print("  ✅ Admin 사용자 생성 (email: admin@jupyter-platform.com, password: admin123!)")
        
        # 기본 그룹 생성
        default_group = db.query(Group).filter(Group.name == "Default Users").first()
        if not default_group:
            default_group = Group(
                name="Default Users",
                description="모든 신규 사용자가 자동으로 가입되는 기본 그룹",
                created_by=admin_user.id if admin_user else None
            )
            db.add(default_group)
            db.commit()  # 그룹을 먼저 커밋
            db.refresh(default_group)
            print("  ✅ 기본 그룹 생성")
        
        # 개발자 그룹 생성
        dev_group = db.query(Group).filter(Group.name == "Developers").first()
        if not dev_group:
            dev_group = Group(
                name="Developers",
                description="데이터 과학자 및 개발자 그룹",
                created_by=admin_user.id if admin_user else None
            )
            db.add(dev_group)
            print("  ✅ 개발자 그룹 생성")
        
        # Admin 사용자의 그룹 할당
        if admin_user and not admin_user.group_id:
            admin_user.group_id = default_group.id
        
        # 테스트 사용자 생성
        print("🧪 테스트 사용자 생성 중...")
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        if not test_user:
            test_user = User(
                real_name="테스트 사용자",
                display_name="Test User",
                email="test@example.com",
                hashed_password=hash_password("test123!"),
                is_active=True,
                is_admin=False,
                role_id=user_role.id,  # 역할 직접 할당
                group_id=default_group.id  # 그룹 직접 할당
            )
            db.add(test_user)
            print("  ✅ 테스트 사용자 생성 (email: test@example.com, password: test123!)")
        
        # 최종 커밋
        db.commit()
        print("\n🎉 데이터베이스 초기화 완료!")
        print("\n📋 생성된 계정:")
        print("  👑 Admin: admin@jupyter-platform.com / admin123!")
        print("  👤 Test User: test@example.com / test123!")
        print("\n🔐 생성된 역할:")
        print("  - admin: 시스템 관리자")
        print("  - manager: 프로젝트 관리자") 
        print("  - user: 일반 사용자")
        print("\n👥 생성된 그룹:")
        print("  - Default Users: 기본 사용자 그룹")
        print("  - Developers: 개발자 그룹")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_database() 