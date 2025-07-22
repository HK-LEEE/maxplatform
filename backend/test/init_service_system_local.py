#!/usr/bin/env python3
"""
서비스 시스템 초기화 스크립트 (backend 디렉토리용)
Mother 페이지를 위한 서비스 관리 시스템을 초기화합니다.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import get_database_url
from app.models.service import Service, ServiceCategory, UserServicePermission
from app.models.user import User, Role
from app.services.service_service import ServiceService

def init_service_system():
    """서비스 시스템 초기화"""
    print("🚀 서비스 시스템 초기화를 시작합니다...")
    
    # 데이터베이스 연결
    database_url = get_database_url()
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 1. 관리자 계정 확인
        admin_user = db.query(User).filter(User.is_admin == True).first()
        if not admin_user:
            print("❌ 관리자 계정이 없습니다. 먼저 관리자 계정을 생성해주세요.")
            return False
        
        print(f"✅ 관리자 계정 확인: {admin_user.real_name} ({admin_user.email})")
        
        # 2. 기본 서비스 생성
        services_data = [
            {
                "name": "jupyter_workspace",
                "display_name": "쥬피터 워크스페이스",
                "description": "데이터 분석을 위한 쥬피터 노트북 환경",
                "url": "/dashboard",
                "category": "analytics",
                "sort_order": 1,
                "icon_url": None,
                "is_external": False,
                "requires_auth": True,
                "open_in_new_tab": False
            },
            {
                "name": "file_manager",
                "display_name": "파일 관리자", 
                "description": "워크스페이스 파일 관리 도구",
                "url": "/files",
                "category": "development",
                "sort_order": 2,
                "icon_url": None,
                "is_external": False,
                "requires_auth": True,
                "open_in_new_tab": False
            },
            {
                "name": "admin_panel",
                "display_name": "관리자 패널",
                "description": "시스템 관리 및 사용자 관리 도구",
                "url": "/admin",
                "category": "management", 
                "sort_order": 10,
                "icon_url": None,
                "is_external": False,
                "requires_auth": True,
                "open_in_new_tab": False
            }
        ]
        
        print("🔧 기본 서비스 생성 중...")
        for service_data in services_data:
            existing_service = db.query(Service).filter(
                Service.name == service_data["name"]
            ).first()
            
            if not existing_service:
                service = Service(
                    **service_data,
                    created_by=admin_user.id
                )
                db.add(service)
                print(f"  ✅ 서비스 생성: {service_data['display_name']}")
            else:
                print(f"  ⏭️  서비스 존재: {service_data['display_name']}")
        
        db.commit()
        
        # 3. 기본 권한 설정
        print("🔐 기본 권한 설정 중...")
        
        # 일반 사용자 역할 확인
        user_role = db.query(Role).filter(Role.name == "user").first()
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        
        if user_role:
            # 일반 사용자에게 쥬피터 워크스페이스 권한 부여
            jupyter_service = db.query(Service).filter(
                Service.name == "jupyter_workspace"
            ).first()
            
            if jupyter_service:
                # role_services 테이블에 권한 추가
                existing_permission = db.execute(text("""
                    SELECT 1 FROM role_services 
                    WHERE role_id = :role_id AND service_id = :service_id
                """), {
                    "role_id": user_role.id,
                    "service_id": jupyter_service.id
                }).fetchone()
                
                if not existing_permission:
                    db.execute(text("""
                        INSERT INTO role_services (role_id, service_id, granted_by)
                        VALUES (:role_id, :service_id, :granted_by)
                    """), {
                        "role_id": user_role.id,
                        "service_id": jupyter_service.id,
                        "granted_by": admin_user.id
                    })
                    print("  ✅ 일반 사용자에게 쥬피터 워크스페이스 권한 부여")
                else:
                    print("  ⏭️  일반 사용자 쥬피터 권한 이미 존재")
        
        if admin_role:
            # 관리자에게 모든 서비스 권한 부여
            all_services = db.query(Service).filter(Service.is_active == True).all()
            
            for service in all_services:
                existing_permission = db.execute(text("""
                    SELECT 1 FROM role_services 
                    WHERE role_id = :role_id AND service_id = :service_id
                """), {
                    "role_id": admin_role.id,
                    "service_id": service.id
                }).fetchone()
                
                if not existing_permission:
                    db.execute(text("""
                        INSERT INTO role_services (role_id, service_id, granted_by)
                        VALUES (:role_id, :service_id, :granted_by)
                    """), {
                        "role_id": admin_role.id,
                        "service_id": service.id,
                        "granted_by": admin_user.id
                    })
            
            print(f"  ✅ 관리자에게 모든 서비스 권한 부여 ({len(all_services)}개)")
        
        db.commit()
        
        # 4. 초기화 완료 확인
        service_count = db.query(Service).filter(Service.is_active == True).count()
        category_count = db.query(ServiceCategory).filter(ServiceCategory.is_active == True).count()
        
        print("")
        print("🎉 서비스 시스템 초기화 완료!")
        print(f"   📊 생성된 카테고리: {category_count}개")
        print(f"   🔧 생성된 서비스: {service_count}개")
        print(f"   👤 관리자: {admin_user.real_name}")
        print("")
        print("✨ 이제 Mother 페이지에 로그인하여 서비스를 확인해보세요!")
        print("   URL: http://localhost:3000/mother")
        
        return True
        
    except Exception as e:
        print(f"❌ 초기화 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    try:
        success = init_service_system()
        if not success:
            print("\n💡 문제가 발생했습니다. 로그를 확인해주세요.")
            sys.exit(1)
        else:
            print("\n🎊 모든 설정이 완료되었습니다!")
    except KeyboardInterrupt:
        print("\n⏹️  사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 예상치 못한 오류: {e}")
        sys.exit(1) 