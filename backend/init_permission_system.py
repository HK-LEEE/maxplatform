#!/usr/bin/env python3
"""
권한 관리 시스템 초기화 스크립트
새로운 테이블 생성 및 기본 데이터 삽입
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, get_database_url
from app.models.user import User, Role, Group
from app.models.permission import Permission, Feature

def create_tables():
    """새로운 테이블들을 생성합니다."""
    print("데이터베이스 테이블 생성 중...")
    
    # 데이터베이스 연결
    engine = create_engine(get_database_url())
    
    # 모든 테이블 생성
    Base.metadata.create_all(bind=engine)
    
    print("✅ 테이블 생성 완료")

def init_basic_data():
    """기본 권한, 기능, 역할 데이터를 생성합니다."""
    print("기본 데이터 초기화 중...")
    
    engine = create_engine(get_database_url())
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 기본 권한 생성
        basic_permissions = [
            {"name": "read_profile", "display_name": "프로필 읽기", "description": "자신의 프로필 정보를 읽을 수 있습니다", "category": "basic"},
            {"name": "edit_profile", "display_name": "프로필 편집", "description": "자신의 프로필 정보를 편집할 수 있습니다", "category": "basic"},
            {"name": "view_workspace", "display_name": "워크스페이스 보기", "description": "워크스페이스를 볼 수 있습니다", "category": "workspace"},
            {"name": "create_workspace", "display_name": "워크스페이스 생성", "description": "새로운 워크스페이스를 생성할 수 있습니다", "category": "workspace"},
            {"name": "edit_workspace", "display_name": "워크스페이스 편집", "description": "워크스페이스를 편집할 수 있습니다", "category": "workspace"},
            {"name": "delete_workspace", "display_name": "워크스페이스 삭제", "description": "워크스페이스를 삭제할 수 있습니다", "category": "workspace"},
            {"name": "upload_file", "display_name": "파일 업로드", "description": "파일을 업로드할 수 있습니다", "category": "file"},
            {"name": "download_file", "display_name": "파일 다운로드", "description": "파일을 다운로드할 수 있습니다", "category": "file"},
            {"name": "delete_file", "display_name": "파일 삭제", "description": "파일을 삭제할 수 있습니다", "category": "file"},
            {"name": "use_jupyter", "display_name": "Jupyter 사용", "description": "Jupyter 노트북을 사용할 수 있습니다", "category": "jupyter"},
            {"name": "use_llm", "display_name": "LLM 사용", "description": "LLM 기능을 사용할 수 있습니다", "category": "llm"},
            {"name": "admin_panel", "display_name": "관리자 패널", "description": "관리자 패널에 접근할 수 있습니다", "category": "admin"},
            {"name": "manage_users", "display_name": "사용자 관리", "description": "사용자를 관리할 수 있습니다", "category": "admin"},
            {"name": "manage_permissions", "display_name": "권한 관리", "description": "권한을 관리할 수 있습니다", "category": "admin"},
        ]
        
        for perm_data in basic_permissions:
            existing = db.query(Permission).filter(Permission.name == perm_data["name"]).first()
            if not existing:
                permission = Permission(**perm_data)
                db.add(permission)
                print(f"  ✅ 권한 생성: {perm_data['display_name']}")
        
        # 기본 기능 생성
        basic_features = [
            {"name": "dashboard", "display_name": "대시보드", "description": "메인 대시보드", "category": "core", "icon": "📊", "url_path": "/dashboard", "requires_approval": False},
            {"name": "workspace", "display_name": "워크스페이스", "description": "데이터 분석 워크스페이스", "category": "analysis", "icon": "💻", "url_path": "/workspace", "requires_approval": True},
            {"name": "jupyter", "display_name": "Jupyter 노트북", "description": "Jupyter 노트북 환경", "category": "analysis", "icon": "📓", "url_path": "/jupyter", "requires_approval": True},
            {"name": "file_manager", "display_name": "파일 관리", "description": "파일 업로드/다운로드 관리", "category": "utility", "icon": "📁", "url_path": "/files", "requires_approval": False},
            {"name": "llm_chat", "display_name": "AI 채팅", "description": "LLM을 활용한 AI 채팅", "category": "ai", "icon": "🤖", "url_path": "/llm", "requires_approval": True},
            {"name": "data_visualization", "display_name": "데이터 시각화", "description": "차트 및 그래프 생성", "category": "analysis", "icon": "📈", "url_path": "/visualization", "requires_approval": True},
            {"name": "report_generator", "display_name": "보고서 생성", "description": "분석 보고서 자동 생성", "category": "reporting", "icon": "📋", "url_path": "/reports", "requires_approval": True},
            {"name": "collaboration", "display_name": "협업 도구", "description": "팀 협업 기능", "category": "collaboration", "icon": "👥", "url_path": "/collaboration", "requires_approval": True},
            {"name": "api_access", "display_name": "API 접근", "description": "RESTful API 사용", "category": "integration", "icon": "🔌", "url_path": "/api", "requires_approval": True},
            {"name": "admin_tools", "display_name": "관리 도구", "description": "시스템 관리 도구", "category": "admin", "icon": "⚙️", "url_path": "/admin", "requires_approval": False},
        ]
        
        for feature_data in basic_features:
            existing = db.query(Feature).filter(Feature.name == feature_data["name"]).first()
            if not existing:
                feature = Feature(**feature_data)
                db.add(feature)
                print(f"  ✅ 기능 생성: {feature_data['display_name']}")
        
        # 기본 역할 생성
        basic_roles = [
            {"name": "guest", "description": "게스트 사용자 - 최소한의 권한만 보유"},
            {"name": "user", "description": "일반 사용자 - 기본적인 기능 사용 가능"},
            {"name": "analyst", "description": "분석가 - 데이터 분석 관련 기능 사용 가능"},
            {"name": "admin", "description": "관리자 - 모든 권한 보유"},
            {"name": "super_admin", "description": "최고 관리자 - 시스템 전체 관리 권한"},
        ]
        
        for role_data in basic_roles:
            existing = db.query(Role).filter(Role.name == role_data["name"]).first()
            if not existing:
                role = Role(**role_data)
                db.add(role)
                print(f"  ✅ 역할 생성: {role_data['name']}")
        
        # 첫 번째 커밋 (기본 데이터 저장)
        db.commit()
        
        # 관리자 사용자 찾기 (첫 번째 관리자 사용자 사용)
        admin_user = db.query(User).filter(User.is_admin == True).first()
        if not admin_user:
            print("⚠️  관리자 사용자가 없습니다. 기본 그룹 생성을 건너뜁니다.")
        else:
            # 기본 그룹 생성
            basic_groups = [
                {"name": "Default Users", "description": "기본 사용자 그룹", "created_by": admin_user.id},
                {"name": "Analysts", "description": "데이터 분석가 그룹", "created_by": admin_user.id},
                {"name": "Administrators", "description": "관리자 그룹", "created_by": admin_user.id},
            ]
            
            for group_data in basic_groups:
                existing = db.query(Group).filter(Group.name == group_data["name"]).first()
                if not existing:
                    group = Group(**group_data)
                    db.add(group)
                    print(f"  ✅ 그룹 생성: {group_data['name']}")
        
        # 두 번째 커밋 (그룹 저장)
        db.commit()
        
        # 역할에 권한과 기능 할당
        print("역할에 권한과 기능 할당 중...")
        
        # 게스트 역할
        guest_role = db.query(Role).filter(Role.name == "guest").first()
        if guest_role:
            guest_permissions = db.query(Permission).filter(Permission.name.in_(["read_profile"])).all()
            guest_features = db.query(Feature).filter(Feature.name.in_(["dashboard"])).all()
            guest_role.permissions = guest_permissions
            guest_role.features = guest_features
            print("  ✅ 게스트 역할 권한 할당")
        
        # 일반 사용자 역할
        user_role = db.query(Role).filter(Role.name == "user").first()
        if user_role:
            user_permissions = db.query(Permission).filter(Permission.name.in_([
                "read_profile", "edit_profile", "view_workspace", "upload_file", "download_file"
            ])).all()
            user_features = db.query(Feature).filter(Feature.name.in_([
                "dashboard", "file_manager"
            ])).all()
            user_role.permissions = user_permissions
            user_role.features = user_features
            print("  ✅ 일반 사용자 역할 권한 할당")
        
        # 분석가 역할
        analyst_role = db.query(Role).filter(Role.name == "analyst").first()
        if analyst_role:
            analyst_permissions = db.query(Permission).filter(Permission.name.in_([
                "read_profile", "edit_profile", "view_workspace", "create_workspace", 
                "edit_workspace", "upload_file", "download_file", "use_jupyter", "use_llm"
            ])).all()
            analyst_features = db.query(Feature).filter(Feature.name.in_([
                "dashboard", "workspace", "jupyter", "file_manager", "llm_chat", 
                "data_visualization", "report_generator"
            ])).all()
            analyst_role.permissions = analyst_permissions
            analyst_role.features = analyst_features
            print("  ✅ 분석가 역할 권한 할당")
        
        # 관리자 역할
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role:
            admin_permissions = db.query(Permission).all()
            admin_features = db.query(Feature).all()
            admin_role.permissions = admin_permissions
            admin_role.features = admin_features
            print("  ✅ 관리자 역할 권한 할당")
        
        # 최종 커밋
        db.commit()
        print("✅ 기본 데이터 초기화 완료")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def update_existing_users():
    """기존 사용자들의 승인 상태를 업데이트합니다."""
    print("기존 사용자 승인 상태 업데이트 중...")
    
    engine = create_engine(get_database_url())
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 기존 사용자들을 승인된 상태로 변경
        users = db.query(User).filter(User.approval_status == None).all()
        for user in users:
            user.approval_status = 'approved'
            print(f"  ✅ 사용자 승인: {user.real_name} ({user.email})")
        
        db.commit()
        print("✅ 기존 사용자 승인 상태 업데이트 완료")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    """메인 실행 함수"""
    print("🚀 권한 관리 시스템 초기화 시작")
    print("=" * 50)
    
    try:
        # 1. 테이블 생성
        create_tables()
        
        # 2. 기본 데이터 초기화
        init_basic_data()
        
        # 3. 기존 사용자 업데이트
        update_existing_users()
        
        print("=" * 50)
        print("🎉 권한 관리 시스템 초기화 완료!")
        print("\n다음 단계:")
        print("1. 백엔드 서버 재시작")
        print("2. 관리자 계정으로 로그인")
        print("3. /admin 페이지에서 사용자 권한 관리")
        
    except Exception as e:
        print(f"❌ 초기화 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 