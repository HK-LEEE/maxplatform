"""
워크스페이스 서비스 URL 경로 업데이트 스크립트
"""
from app.database import get_db
from app.models import Service
from sqlalchemy.orm import Session

def update_workspace_service():
    """워크스페이스 서비스 URL 경로 업데이트"""
    db = next(get_db())
    
    try:
        # jupyter_workspace 서비스의 URL 경로 업데이트
        service = db.query(Service).filter(Service.service_name == 'jupyter_workspace').first()
        if service:
            service.url = '/workspaces'
            service.requires_approval = False
            db.commit()
            print(f'✅ 워크스페이스 서비스 업데이트 완료: {service.service_display_name} -> {service.url}')
            print(f'   승인 필요: {service.requires_approval}')
        else:
            print('❌ jupyter_workspace 서비스를 찾을 수 없습니다.')
            
        # 모든 서비스 조회하여 현재 상태 확인
        print('\n📋 현재 등록된 서비스 목록:')
        services = db.query(Service).all()
        for svc in services:
            print(f'  - {svc.service_name}: {svc.service_display_name} -> {svc.url} (승인필요: {svc.requires_approval})')
            
    except Exception as e:
        print(f'❌ 업데이트 실패: {e}')
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_workspace_service() 