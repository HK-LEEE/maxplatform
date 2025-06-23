from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from ..models.service import Service, ServiceCategory, UserServicePermission
from ..models.user import User, Role
from ..models.permission import Feature
from ..schemas.service import (
    ServiceCreate, ServiceUpdate, ServicePermissionCreate,
    UserAccessibleService, MotherPageResponse
)
import json

class ServiceService:
    
    @staticmethod
    def get_user_accessible_features(db: Session, user_id: str) -> List[Dict[str, Any]]:
        """사용자가 접근 가능한 기능 목록 조회 (그룹 기반)"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        
        accessible_features = set()
        
        # 그룹 기반 기능 조회 (주요 권한 확인 방식)
        if user.group:
            for feature in user.group.features:
                if feature.is_active:
                    accessible_features.add(feature.id)
        
        # 개별 사용자 기능 조회 (추가 권한)
        for feature in user.features:
            if feature.is_active:
                accessible_features.add(feature.id)
        
        # 기능 정보 조회 및 변환 (카테고리 관계 포함)
        from sqlalchemy.orm import joinedload
        features = db.query(Feature).options(
            joinedload(Feature.feature_category)
        ).filter(
            Feature.id.in_(accessible_features),
            Feature.is_active == True
        ).all()
        
        feature_list = []
        for feature in features:
            # 외부 URL인지 내부 경로인지 판단
            is_external = feature.url_path and feature.url_path.startswith('http')
            
            # 카테고리 정보 가져오기 (관계를 통해)
            category_name = None
            if feature.feature_category:
                category_name = feature.feature_category.name
            
            feature_list.append({
                "service_id": feature.id,
                "service_name": feature.name,
                "service_display_name": feature.display_name,
                "description": feature.description,
                "url": feature.url_path,
                "icon_url": feature.icon,  # 이모지를 icon_url로 사용
                "thumbnail_url": None,
                "is_external": is_external,
                "open_in_new_tab": is_external,  # 외부 URL은 새 탭에서
                "category": category_name or "기타",
                "sort_order": feature.sort_order or 0
            })
        
        return sorted(feature_list, key=lambda x: (x['category'], x['service_display_name']))
    
    @staticmethod
    def get_user_accessible_services(db: Session, user_id: str) -> List[UserAccessibleService]:
        """사용자가 접근 가능한 서비스 목록 조회 (기능 기반으로 변경)"""
        feature_list = ServiceService.get_user_accessible_features(db, user_id)
        
        services = []
        for feature_data in feature_list:
            services.append(UserAccessibleService(
                service_id=feature_data["service_id"],
                service_name=feature_data["service_name"],
                service_display_name=feature_data["service_display_name"],
                description=feature_data["description"],
                url=feature_data["url"],
                icon_url=feature_data["icon_url"],
                thumbnail_url=feature_data["thumbnail_url"],
                is_external=feature_data["is_external"],
                open_in_new_tab=feature_data["open_in_new_tab"],
                category=feature_data["category"],
                sort_order=feature_data["sort_order"]
            ))
        
        return services
    
    @staticmethod
    def get_mother_page_data(db: Session, user_id: str) -> MotherPageResponse:
        """Mother 페이지에 필요한 모든 데이터 조회"""
        # 사용자 정보 조회
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("사용자를 찾을 수 없습니다.")
        
        user_info = {
            "id": user.id,
            "real_name": user.real_name,
            "display_name": user.display_name or user.real_name,
            "email": user.email,
            "department": user.department,
            "position": user.position,
            "role": user.role.name if user.role else None,
            "group": user.group.name if user.group else None
        }
        
        # 접근 가능한 기능 목록 조회 (그룹 기반)
        services = ServiceService.get_user_accessible_services(db, user_id)
        
        # 실제 FeatureCategory 테이블에서 카테고리 정보 조회
        from ..models.permission import FeatureCategory
        
        # 서비스에서 사용 중인 카테고리들 추출
        categories_from_features = set()
        for service in services:
            if service.category:
                categories_from_features.add(service.category)
        
        # FeatureCategory 테이블에서 해당 카테고리들의 정보 조회
        feature_categories = db.query(FeatureCategory).filter(
            FeatureCategory.name.in_(categories_from_features),
            FeatureCategory.is_active == True
        ).order_by(FeatureCategory.sort_order).all()
        
        # 카테고리 정보를 딕셔너리로 매핑
        category_info_map = {}
        for cat in feature_categories:
            category_info_map[cat.name] = {
                "name": cat.name,
                "display_name": cat.display_name,
                "description": cat.description or f"{cat.display_name} 관련 기능들",
                "sort_order": cat.sort_order,
                "icon": cat.icon,
                "color": cat.color
            }
        
        # 카테고리 목록 생성 (FeatureCategory의 sort_order 기준으로 정렬)
        category_list = []
        for cat_name in categories_from_features:
            if cat_name in category_info_map:
                category_list.append(category_info_map[cat_name])
            else:
                # FeatureCategory에 없는 카테고리의 경우 기본값 사용
                category_list.append({
                    "name": cat_name,
                    "display_name": cat_name.title(),
                    "description": f"{cat_name.title()} 관련 기능들",
                    "sort_order": 99,
                    "icon": None,
                    "color": None
                })
        
        # sort_order 기준으로 정렬
        category_list.sort(key=lambda x: x['sort_order'])
        
        return MotherPageResponse(
            user_info=user_info,
            services=services,
            categories=category_list
        )
    
    @staticmethod
    def create_service(db: Session, service_data: ServiceCreate, created_by: str) -> Service:
        """새 서비스 생성"""
        db_service = Service(
            **service_data.dict(),
            created_by=created_by
        )
        db.add(db_service)
        db.commit()
        db.refresh(db_service)
        return db_service
    
    @staticmethod
    def update_service(db: Session, service_id: int, service_data: ServiceUpdate) -> Optional[Service]:
        """서비스 정보 업데이트"""
        db_service = db.query(Service).filter(Service.id == service_id).first()
        if not db_service:
            return None
        
        update_data = service_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_service, field, value)
        
        db.commit()
        db.refresh(db_service)
        return db_service
    
    @staticmethod
    def delete_service(db: Session, service_id: int) -> bool:
        """서비스 삭제 (비활성화)"""
        db_service = db.query(Service).filter(Service.id == service_id).first()
        if not db_service:
            return False
        
        db_service.is_active = False
        db.commit()
        return True
    
    @staticmethod
    def grant_service_permission(
        db: Session, 
        user_id: str, 
        service_id: int, 
        granted_by: str,
        permission_level: str = "read"
    ) -> bool:
        """사용자에게 서비스 권한 부여"""
        try:
            # user_services 테이블에 권한 추가 (이미 있으면 무시)
            query = text("""
            INSERT IGNORE INTO user_services (user_id, service_id, granted_by)
            VALUES (:user_id, :service_id, :granted_by)
            """)
            db.execute(query, {
                "user_id": user_id,
                "service_id": service_id,
                "granted_by": granted_by
            })
            
            # 상세 권한 설정
            existing_permission = db.query(UserServicePermission).filter(
                UserServicePermission.user_id == user_id,
                UserServicePermission.service_id == service_id
            ).first()
            
            if existing_permission:
                existing_permission.permission_level = permission_level
                existing_permission.granted_by = granted_by
                existing_permission.is_active = True
            else:
                new_permission = UserServicePermission(
                    user_id=user_id,
                    service_id=service_id,
                    permission_level=permission_level,
                    granted_by=granted_by
                )
                db.add(new_permission)
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error granting permission: {e}")
            return False
    
    @staticmethod
    def revoke_service_permission(db: Session, user_id: str, service_id: int) -> bool:
        """사용자의 서비스 권한 회수"""
        try:
            # user_services에서 삭제
            query = text("""
            DELETE FROM user_services 
            WHERE user_id = :user_id AND service_id = :service_id
            """)
            db.execute(query, {"user_id": user_id, "service_id": service_id})
            
            # 상세 권한 비활성화
            permission = db.query(UserServicePermission).filter(
                UserServicePermission.user_id == user_id,
                UserServicePermission.service_id == service_id
            ).first()
            
            if permission:
                permission.is_active = False
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error revoking permission: {e}")
            return False
    
    @staticmethod
    def get_all_services(db: Session, include_inactive: bool = False) -> List[Service]:
        """모든 서비스 목록 조회"""
        query = db.query(Service)
        if not include_inactive:
            query = query.filter(Service.is_active == True)
        
        return query.order_by(Service.sort_order, Service.display_name).all()
    
    @staticmethod
    def get_service_by_id(db: Session, service_id: int) -> Optional[Service]:
        """서비스 ID로 조회"""
        return db.query(Service).filter(Service.id == service_id).first()
    
    @staticmethod
    def get_service_by_name(db: Session, service_name: str) -> Optional[Service]:
        """서비스명으로 조회"""
        return db.query(Service).filter(Service.name == service_name).first()
    
    @staticmethod
    def get_service_categories(db: Session) -> List[ServiceCategory]:
        """서비스 카테고리 목록 조회"""
        return db.query(ServiceCategory).filter(
            ServiceCategory.is_active == True
        ).order_by(ServiceCategory.sort_order).all()
    
    @staticmethod
    def check_user_service_access(db: Session, user_id: str, service_name: str) -> bool:
        """사용자의 특정 서비스 접근 권한 확인"""
        accessible_services = ServiceService.get_user_accessible_services(db, user_id)
        return any(service.service_name == service_name for service in accessible_services) 