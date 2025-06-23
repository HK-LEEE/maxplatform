"""
데이터베이스 초기 데이터 설정 스크립트

관리자 계정, 기능, 그룹, 권한을 생성합니다.
"""

import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from .database import get_database_engine, get_db
from .models.user import User, Group, Role
from .models.permission import Permission, Feature
from .models.service import Service, ServiceCategory, UserServicePermission
from .models.workspace import Workspace

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """비밀번호 해싱"""
    return pwd_context.hash(password)

def init_features(db: Session):
    """시스템 기능 초기화"""
    features_data = [
        # 인증 관련 (페이지 없음 - 기능만)
        {
            "name": "AUTH_ACCESS",
            "display_name": "인증 접근",
            "description": "로그인/로그아웃 기능",
            "category": "Authentication",
            "url_path": "/login"
        },
        
        # 메인 페이지
        {
            "name": "MAIN_DASHBOARD",
            "display_name": "메인 대시보드",
            "description": "시스템 메인 대시보드",
            "category": "Main",
            "url_path": "/main"
        },
        
        # 워크스페이스 관리
        {
            "name": "WORKSPACE_MANAGE",
            "display_name": "워크스페이스 관리",
            "description": "워크스페이스 생성, 수정, 삭제",
            "category": "Workspace",
            "url_path": "/workspace"
        },
        
        # 주피터 노트북
        {
            "name": "JUPYTER_ACCESS",
            "display_name": "주피터 노트북",
            "description": "주피터 노트북 서비스 접근",
            "category": "Jupyter",
            "url_path": "/jupyter"
        },
        
        # 파일 관리
        {
            "name": "FILES_MANAGE",
            "display_name": "파일 관리",
            "description": "파일 업로드, 다운로드, 관리",
            "category": "Files",
            "url_path": "/files"
        },
        
        # LLM 채팅
        {
            "name": "LLM_CHAT_ACCESS",
            "display_name": "LLM 채팅",
            "description": "대화형 AI 채팅 서비스",
            "category": "LLM",
            "url_path": "/chat"
        },
        
        # LLMOps 플랫폼
        {
            "name": "LLMOPS_PLATFORM",
            "display_name": "LLMOps 플랫폼",
            "description": "LLMOps 플랫폼 전체 접근",
            "category": "LLMOps",
            "url_path": "/llmops"
        },
        
        # RAG 데이터소스 관리
        {
            "name": "RAG_DATASOURCES",
            "display_name": "RAG 데이터소스",
            "description": "RAG 데이터소스 생성 및 관리",
            "category": "LLMOps",
            "url_path": "/rag-datasources"
        },
        
        # Flow 스튜디오
        {
            "name": "FLOW_STUDIO",
            "display_name": "Flow 스튜디오",
            "description": "워크플로우 생성 및 편집",
            "category": "LLMOps",
            "url_path": "/flow-studio"
        },
        
        # 시크릿 관리
        {
            "name": "SECRETS_MANAGE",
            "display_name": "시크릿 관리",
            "description": "API 키 및 시크릿 관리",
            "category": "LLMOps",
            "url_path": "/secrets"
        },
        
        # 서비스 관리
        {
            "name": "SERVICES_MANAGE",
            "display_name": "서비스 관리",
            "description": "시스템 서비스 관리",
            "category": "Services",
            "url_path": "/services"
        },
        
        # 관리자 - 사용자 관리
        {
            "name": "ADMIN_USERS",
            "display_name": "사용자 관리",
            "description": "시스템 사용자 관리",
            "category": "Admin",
            "url_path": "/admin/users"
        },
        
        # 관리자 - 그룹 관리
        {
            "name": "ADMIN_GROUPS",
            "display_name": "그룹 관리",
            "description": "사용자 그룹 관리",
            "category": "Admin",
            "url_path": "/admin/groups"
        },
        
        # 관리자 - 권한 관리
        {
            "name": "ADMIN_PERMISSIONS",
            "display_name": "권한 관리",
            "description": "시스템 권한 관리",
            "category": "Admin",
            "url_path": "/admin/permissions"
        },
        
        # 관리자 - 시스템 모니터링
        {
            "name": "ADMIN_SYSTEM",
            "display_name": "시스템 모니터링",
            "description": "시스템 상태 모니터링",
            "category": "Admin",
            "url_path": "/admin/system"
        }
    ]
    
    print("📋 기능(Features) 생성 중...")
    for feature_data in features_data:
        # 중복 확인
        existing = db.query(Feature).filter(Feature.name == feature_data["name"]).first()
        if not existing:
            feature = Feature(
                name=feature_data["name"],
                display_name=feature_data["display_name"],
                description=feature_data["description"],
                category=feature_data["category"],
                url_path=feature_data["url_path"],
                is_active=True
            )
            db.add(feature)
            print(f"  ✅ {feature_data['name']} - {feature_data['display_name']}")
        else:
            print(f"  ⚠️ {feature_data['name']} - 이미 존재함")
    
    db.commit()
    print("✅ 기능 생성 완료\n")

def init_service_categories(db: Session):
    """서비스 카테고리 초기화"""
    categories_data = [
        {
            "name": "Development",
            "display_name": "개발 도구 및 환경",
            "description": "개발 도구 및 환경"
        },
        {
            "name": "AI/ML",
            "display_name": "인공지능 및 머신러닝",
            "description": "인공지능 및 머신러닝"
        },
        {
            "name": "Data",
            "display_name": "데이터 처리 및 분석",
            "description": "데이터 처리 및 분석"
        },
        {
            "name": "Storage",
            "display_name": "저장소 및 데이터베이스",
            "description": "저장소 및 데이터베이스"
        }
    ]
    
    print("📂 서비스 카테고리 생성 중...")
    for cat_data in categories_data:
        existing = db.query(ServiceCategory).filter(ServiceCategory.name == cat_data["name"]).first()
        if not existing:
            category = ServiceCategory(
                name=cat_data["name"],
                display_name=cat_data["display_name"],
                description=cat_data["description"]
            )
            db.add(category)
            print(f"  ✅ {cat_data['name']} - {cat_data['display_name']}")
        else:
            print(f"  ⚠️ {cat_data['name']} - 이미 존재함")
    
    db.commit()
    print("✅ 서비스 카테고리 생성 완료\n")

def init_services(db: Session):
    """기본 서비스 초기화"""
    # 서비스 카테고리 조회
    dev_category = db.query(ServiceCategory).filter(ServiceCategory.name == "Development").first()
    ai_category = db.query(ServiceCategory).filter(ServiceCategory.name == "AI/ML").first()
    data_category = db.query(ServiceCategory).filter(ServiceCategory.name == "Data").first()
    
    # 관리자 사용자 조회 (created_by 필드용)
    admin_user = db.query(User).filter(User.email == "admin@test.com").first()
    if not admin_user:
        print("  ⚠️ 관리자 사용자를 찾을 수 없어 서비스 생성을 건너뜁니다.")
        return
    
    services_data = [
        {
            "name": "jupyter_notebook",
            "display_name": "Jupyter Notebook",
            "description": "데이터 분석 및 개발을 위한 주피터 노트북 서비스",
            "url": "/api/jupyter",
            "category": dev_category.name if dev_category else "Development",
            "is_active": True
        },
        {
            "name": "llmops_platform", 
            "display_name": "LLMOps Platform",
            "description": "대규모 언어모델 운영 플랫폼",
            "url": "/llmops",
            "category": ai_category.name if ai_category else "AI/ML",
            "is_active": True
        },
        {
            "name": "chroma_db",
            "display_name": "ChromaDB",
            "description": "벡터 데이터베이스 서비스",
            "url": "/api/llmops/rag-datasources",
            "category": data_category.name if data_category else "Data",
            "is_active": True
        }
    ]
    
    print("🚀 서비스 생성 중...")
    for service_data in services_data:
        existing = db.query(Service).filter(Service.name == service_data["name"]).first()
        if not existing:
            service = Service(
                name=service_data["name"],
                display_name=service_data["display_name"],
                description=service_data["description"],
                url=service_data["url"],
                category=service_data["category"],
                is_active=service_data["is_active"],
                created_by=admin_user.id
            )
            db.add(service)
            print(f"  ✅ {service_data['display_name']} - {service_data['description']}")
        else:
            print(f"  ⚠️ {service_data['display_name']} - 이미 존재함")
    
    db.commit()
    print("✅ 서비스 생성 완료\n")

def init_admin_user(db: Session):
    """관리자 계정 생성"""
    print("👤 관리자 계정 생성 중...")
    
    # 관리자 계정 확인
    admin_user = db.query(User).filter(User.email == "admin@test.com").first()
    if admin_user:
        print("  ⚠️ admin@test.com 계정이 이미 존재합니다.")
        return admin_user
    
    # 관리자 계정 생성
    admin_user = User(
        email="admin@test.com",
        hashed_password=hash_password("admin123"),
        display_name="시스템 관리자",
        real_name="관리자",
        is_active=True,
        is_admin=True,
        is_verified=True,
        approval_status="approved",
        created_at=datetime.utcnow()
    )
    
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    print("  ✅ 관리자 계정 생성 완료")
    print(f"     이메일: admin@test.com")
    print(f"     비밀번호: admin123")
    print(f"     사용자 ID: {admin_user.id}\n")
    
    return admin_user

def init_groups_and_roles(db: Session, admin_user: User):
    """그룹 및 역할 초기화"""
    print("👥 그룹 및 역할 생성 중...")
    
    # 기본 역할 생성
    roles_data = [
        {
            "name": "ADMIN",
            "description": "시스템 관리자"
        },
        {
            "name": "DEVELOPER",
            "description": "개발자"
        },
        {
            "name": "ANALYST",
            "description": "데이터 분석가"
        },
        {
            "name": "USER",
            "description": "일반 사용자"
        }
    ]
    
    created_roles = {}
    for role_data in roles_data:
        existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing_role:
            role = Role(
                name=role_data["name"],
                description=role_data["description"]
            )
            db.add(role)
            db.commit()
            db.refresh(role)
            created_roles[role.name] = role
            print(f"  ✅ 역할: {role_data['name']} - {role_data['description']}")
        else:
            created_roles[existing_role.name] = existing_role
            print(f"  ⚠️ 역할: {role_data['name']} - 이미 존재함")
    
    # 기본 그룹 생성
    groups_data = [
        {
            "name": "관리자 그룹",
            "description": "시스템 전체 관리 권한을 가진 그룹"
        },
        {
            "name": "개발자 그룹",
            "description": "개발 도구 및 환경에 접근할 수 있는 그룹"
        },
        {
            "name": "분석가 그룹",
            "description": "데이터 분석 및 ML 도구에 접근할 수 있는 그룹"
        },
        {
            "name": "사용자 그룹",
            "description": "기본 사용자 그룹"
        }
    ]
    
    created_groups = {}
    for group_data in groups_data:
        existing_group = db.query(Group).filter(Group.name == group_data["name"]).first()
        if not existing_group:
            group = Group(
                name=group_data["name"],
                description=group_data["description"],
                created_by=admin_user.id,
                created_at=datetime.utcnow()
            )
            db.add(group)
            db.commit()
            db.refresh(group)
            created_groups[group.name] = group
            print(f"  ✅ 그룹: {group_data['name']}")
        else:
            created_groups[existing_group.name] = existing_group
            print(f"  ⚠️ 그룹: {group_data['name']} - 이미 존재함")
    
    # 관리자를 관리자 그룹에 추가 (role_id와 group_id 설정)
    admin_group = created_groups["관리자 그룹"]
    admin_role = created_roles["ADMIN"]
    
    # 관리자 사용자의 역할과 그룹 설정
    admin_user.role_id = admin_role.id
    admin_user.group_id = admin_group.id
    db.commit()
    
    print(f"  ✅ {admin_user.email}을 관리자 그룹에 추가")
    print("✅ 그룹 및 역할 생성 완료\n")
    return created_groups, created_roles

def init_permissions(db: Session, groups: dict):
    """그룹별 기능 권한 설정"""
    print("🔐 그룹별 기능 권한 설정 중...")
    
    # 모든 기능 조회
    all_features = db.query(Feature).all()
    feature_map = {f.name: f for f in all_features}
    
    # 그룹별 기능 권한 매핑
    group_features_mapping = {
        "관리자 그룹": [f.name for f in all_features],  # 모든 기능
        "개발자 그룹": [
            "AUTH_ACCESS",
            "MAIN_DASHBOARD", 
            "WORKSPACE_MANAGE",
            "JUPYTER_ACCESS",
            "FILES_MANAGE",
            "LLM_CHAT_ACCESS",
            "LLMOPS_PLATFORM",
            "RAG_DATASOURCES",
            "FLOW_STUDIO", 
            "SECRETS_MANAGE",
            "SERVICES_MANAGE"
        ],
        "분석가 그룹": [
            "AUTH_ACCESS",
            "MAIN_DASHBOARD",
            "JUPYTER_ACCESS", 
            "FILES_MANAGE",
            "LLM_CHAT_ACCESS",
            "LLMOPS_PLATFORM",
            "RAG_DATASOURCES",
            "FLOW_STUDIO"
        ],
        "사용자 그룹": [
            "AUTH_ACCESS",
            "MAIN_DASHBOARD",
            "JUPYTER_ACCESS",
            "FILES_MANAGE", 
            "LLM_CHAT_ACCESS"
        ]
    }
    
    for group_name, feature_names in group_features_mapping.items():
        group = groups.get(group_name)
        if not group:
            continue
            
        print(f"  🔑 {group_name} 기능 권한 설정 중...")
        
        # 기존 그룹-기능 관계 클리어 (중복 방지)
        group.features.clear()
        
        for feature_name in feature_names:
            feature = feature_map.get(feature_name)
            if not feature:
                print(f"    ❌ {feature_name} - 기능을 찾을 수 없음")
                continue
                
            # 그룹에 기능 추가
            if feature not in group.features:
                group.features.append(feature)
                print(f"    ✅ {feature_name}")
            else:
                print(f"    ⚠️ {feature_name} - 이미 권한 있음")
    
    db.commit()
    print("✅ 그룹별 기능 권한 설정 완료\n")

def init_default_workspace(db: Session, admin_user: User):
    """기본 워크스페이스 생성"""
    print("🏢 기본 워크스페이스 생성 중...")
    
    existing_workspace = db.query(Workspace).filter(Workspace.name == "기본 워크스페이스").first()
    if existing_workspace:
        print("  ⚠️ 기본 워크스페이스가 이미 존재합니다.")
        return existing_workspace
    
    workspace = Workspace(
        name="기본 워크스페이스",
        description="시스템 기본 워크스페이스",
        owner_id=admin_user.id,
        created_at=datetime.utcnow()
    )
    
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    
    print(f"  ✅ 기본 워크스페이스 생성 완료 (ID: {workspace.id})")
    return workspace

def main():
    """메인 초기화 함수"""
    print("🚀 데이터베이스 초기화 시작...\n")
    
    # 데이터베이스 연결
    from .database import SessionLocal
    db = SessionLocal()
    
    try:
        # 1. 기능 생성
        init_features(db)
        
        # 2. 서비스 카테고리 생성
        init_service_categories(db)
        
        # 3. 서비스 생성
        init_services(db)
        
        # 4. 관리자 계정 생성
        admin_user = init_admin_user(db)
        
        # 5. 그룹 및 역할 생성
        groups, roles = init_groups_and_roles(db, admin_user)
        
        # 6. 권한 설정
        init_permissions(db, groups)
        
        # 7. 기본 워크스페이스 생성
        init_default_workspace(db, admin_user)
        
        print("🎉 데이터베이스 초기화 성공!")
        print("\n📋 생성된 계정 정보:")
        print("   이메일: admin@test.com")
        print("   비밀번호: admin123")
        print("   권한: 시스템 관리자 (모든 기능 접근 가능)")
        
    except Exception as e:
        print(f"❌ 초기화 중 오류 발생: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main() 