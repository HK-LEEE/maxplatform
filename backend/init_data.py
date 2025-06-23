"""
기본 데이터 초기화 스크립트
"""
from app.database import get_db
from app.models import User, Role, Permission, Feature, Group
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

def init_basic_data():
    db = next(get_db())
    
    try:
        # 기본 역할 생성 (중복 체크)
        admin_role = db.query(Role).filter(Role.name == 'admin').first()
        if not admin_role:
            admin_role = Role(
                name='admin',
                description='시스템 관리자 역할',
                is_active=True
            )
            db.add(admin_role)
        
        user_role = db.query(Role).filter(Role.name == 'user').first()
        if not user_role:
            user_role = Role(
                name='user',
                description='일반 사용자 역할',
                is_active=True
            )
            db.add(user_role)
        
        db.commit()
        
        # 기본 권한 생성 (중복 체크)
        permissions_data = [
            ('read', '읽기', '데이터 읽기 권한', 'basic'),
            ('write', '쓰기', '데이터 쓰기 권한', 'basic'),
            ('admin', '관리자', '시스템 관리 권한', 'admin'),
        ]
        
        for name, display_name, description, category in permissions_data:
            existing = db.query(Permission).filter(Permission.name == name).first()
            if not existing:
                perm = Permission(
                    name=name,
                    display_name=display_name,
                    description=description,
                    category=category,
                    is_active=True
                )
                db.add(perm)
        
        db.commit()
        
        # 기본 기능 생성 (중복 체크)
        features_data = [
            ('dashboard', '대시보드', '데이터 대시보드', '분석 도구', '📊', '/dashboard', False, False),
            ('jupyter', 'Jupyter Lab', '데이터 분석을 위한 Jupyter Lab', '분석 도구', '🔬', '/jupyter', False, True),
            ('file_manager', '파일 관리자', '파일 업로드 및 관리', '데이터 관리', '📁', '/files', False, False),
        ]
        
        for name, display_name, description, category, icon, url_path, is_external, open_in_new_tab in features_data:
            existing = db.query(Feature).filter(Feature.name == name).first()
            if not existing:
                feat = Feature(
                    name=name,
                    display_name=display_name,
                    description=description,
                    category=category,
                    icon=icon,
                    url_path=url_path,
                    is_external=is_external,
                    open_in_new_tab=open_in_new_tab,
                    requires_approval=False,
                    is_active=True
                )
                db.add(feat)
        
        db.commit()
        
        # 관리자 사용자 생성 (그룹보다 먼저 생성)
        admin_user = db.query(User).filter(User.email == 'admin@example.com').first()
        if not admin_user:
            admin_user = User(
                email='admin@example.com',
                real_name='관리자',
                display_name='시스템 관리자',
                hashed_password=pwd_context.hash('admin123'),
                is_active=True,
                is_admin=True,
                approval_status='approved',
                role_id=admin_role.id,
                approved_at=datetime.utcnow()
            )
            db.add(admin_user)
            db.commit()
        
        # 기본 그룹 생성 (관리자 사용자 생성 후)
        default_group = db.query(Group).filter(Group.name == '기본 그룹').first()
        if not default_group:
            default_group = Group(
                name='기본 그룹',
                description='모든 사용자의 기본 그룹',
                created_by=admin_user.id,
                created_at=datetime.utcnow()
            )
            db.add(default_group)
            db.commit()
            
            # 관리자 사용자의 그룹 설정
            admin_user.group_id = default_group.id
            db.commit()
        
        print('✅ 기본 데이터 초기화 완료')
        print('관리자 계정: admin@example.com / admin123')
        
    except Exception as e:
        print(f'❌ 초기화 실패: {e}')
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_basic_data() 