from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models import User, Role, Group, Permission, Feature
from ..routers.auth import get_current_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/")
async def admin_dashboard(
    current_admin: User = Depends(get_current_admin_user)
):
    """관리자 대시보드 기본 정보"""
    return {
        "message": "Admin Dashboard",
        "admin_user": current_admin.real_name,
        "available_endpoints": [
            "/admin/users",
            "/admin/stats", 
            "/admin/features",
            "/admin/roles",
            "/admin/groups"
        ]
    }

# Pydantic 모델들
class UserListResponse(BaseModel):
    id: str
    real_name: str
    display_name: Optional[str] = None
    email: str
    phone_number: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool
    is_admin: bool
    approval_status: str
    created_at: datetime
    last_login_at: Optional[datetime] = None
    login_count: int = 0
    role_name: Optional[str] = None
    group_name: Optional[str] = None
    group: Optional[dict] = None
    permissions_count: int = 0
    features_count: int = 0

    class Config:
        from_attributes = True

class PermissionResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    category: str
    is_active: bool

    class Config:
        from_attributes = True

class FeatureResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    icon: Optional[str] = None
    url_path: Optional[str] = None
    is_external: bool = False
    open_in_new_tab: bool = False
    is_active: bool
    requires_approval: bool
    sort_order: int = 0
    
    # 카테고리 정보 (읽기 전용)
    category_name: Optional[str] = None
    category_display_name: Optional[str] = None

    class Config:
        from_attributes = True

def generate_feature_abbreviation(display_name: str) -> str:
    """기능명에서 약어를 자동 생성하는 함수"""
    import re
    
    # 공백이나 특수문자로 단어 분리
    words = re.split(r'[\s\-_\.]+', display_name)
    words = [word for word in words if word]
    
    abbreviation = ''
    
    # 영어 단어들의 첫 글자만 추출
    for word in words:
        if word:
            first_char = word[0].upper()
            # 영어 알파벳인지 확인
            if re.match(r'[A-Z]', first_char):
                abbreviation += first_char
                # 최대 3글자까지만
                if len(abbreviation) >= 3:
                    break
    
    # 약어가 없으면 첫 번째 영어 문자 사용
    if not abbreviation:
        for char in display_name:
            if re.match(r'[A-Za-z]', char):
                abbreviation = char.upper()
                break
    
    # 여전히 없으면 기본값
    return abbreviation or 'F'

def create_feature_response(feature):
    """Feature 모델을 FeatureResponse로 변환하는 헬퍼 함수"""
    return FeatureResponse(
        id=feature.id,
        name=feature.name,
        display_name=feature.display_name,
        description=feature.description,
        category_id=feature.category_id,
        icon=feature.icon,
        url_path=feature.url_path,
        is_external=feature.is_external,
        open_in_new_tab=feature.open_in_new_tab,
        is_active=feature.is_active,
        requires_approval=feature.requires_approval,
        sort_order=feature.sort_order or 0,
        category_name=feature.feature_category.name if feature.feature_category else None,
        category_display_name=feature.feature_category.display_name if feature.feature_category else None
    )

class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    permissions: List[PermissionResponse] = []
    features: List[FeatureResponse] = []
    users_count: int = 0

    class Config:
        from_attributes = True

class UserDetailResponse(BaseModel):
    id: str
    real_name: str
    display_name: Optional[str] = None
    email: str
    phone_number: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool
    is_admin: bool
    approval_status: str
    approval_note: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None
    login_count: int
    role: Optional[RoleResponse] = None
    group: Optional[dict] = None
    permissions: List[PermissionResponse] = []
    features: List[FeatureResponse] = []

    class Config:
        from_attributes = True

class UserApprovalRequest(BaseModel):
    user_id: str
    approval_status: str  # approved, rejected
    approval_note: str = None

class UserPermissionRequest(BaseModel):
    user_id: str
    permission_ids: List[int]

class UserFeatureRequest(BaseModel):
    user_id: str
    feature_ids: List[int]

class UserActivationRequest(BaseModel):
    user_id: str
    is_active: bool

class UserUpdateRequest(BaseModel):
    real_name: str
    display_name: str = ""
    phone_number: str = ""
    department: str = ""
    position: str = ""
    bio: str = ""
    group_id: Optional[int] = None

class UserPasswordChangeRequest(BaseModel):
    user_id: str
    new_password: str

class UserStatusUpdateRequest(BaseModel):
    approval_status: str
    is_active: bool

class FeatureCreateRequest(BaseModel):
    name: str
    display_name: str
    description: str = ""
    category_id: Optional[int] = None
    icon: str = ""
    url_path: str = ""
    is_external: bool = False
    open_in_new_tab: bool = False
    requires_approval: bool = False
    is_active: bool = True
    sort_order: int = 0

class FeatureUpdateRequest(BaseModel):
    display_name: str
    description: str = ""
    category_id: Optional[int] = None
    icon: str = ""
    url_path: str = ""
    is_external: bool = False
    open_in_new_tab: bool = False
    requires_approval: bool = False
    is_active: bool = True
    sort_order: int = 0

class RoleCreateRequest(BaseModel):
    name: str
    description: str = ""
    is_active: bool = True

class RoleUpdateRequest(BaseModel):
    description: str = ""
    is_active: bool = True

class RolePermissionRequest(BaseModel):
    role_id: int
    permission_ids: List[int]

class RoleFeatureRequest(BaseModel):
    role_id: int
    feature_ids: List[int]

class GroupCreateRequest(BaseModel):
    name: str
    description: str = ""

class GroupUpdateRequest(BaseModel):
    name: str
    description: str = ""

class GroupPermissionRequest(BaseModel):
    group_id: int
    permission_ids: List[int]

class GroupFeatureRequest(BaseModel):
    group_id: int
    feature_ids: List[int]

class UserGroupRequest(BaseModel):
    user_id: str
    group_id: Optional[int] = None

class GroupUserResponse(BaseModel):
    id: str
    real_name: str
    display_name: Optional[str] = None
    email: str
    phone_number: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    is_active: bool
    is_admin: bool
    is_verified: bool  # 인증 상태
    approval_status: str
    created_at: datetime
    last_login_at: Optional[datetime] = None
    login_count: int = 0
    role_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class GroupDetailResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_by: str
    created_at: datetime
    users_count: int = 0
    users: List[GroupUserResponse] = []
    permissions: List[PermissionResponse] = []
    features: List[FeatureResponse] = []

    class Config:
        from_attributes = True

# 사용자 목록 조회
@router.get("/users", response_model=List[UserListResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    approval_status: str = None,
    is_active: bool = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """사용자 목록 조회 (관리자용)"""
    query = db.query(User).options(
        joinedload(User.role),
        joinedload(User.group),
        joinedload(User.permissions),
        joinedload(User.features)
    )
    
    # 검색 조건
    if search:
        query = query.filter(
            or_(
                User.real_name.contains(search),
                User.display_name.contains(search),
                User.email.contains(search),
                User.department.contains(search),
                User.position.contains(search)
            )
        )
    
    if approval_status:
        query = query.filter(User.approval_status == approval_status)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    users = query.offset(skip).limit(limit).all()
    
    # 응답 데이터 구성
    result = []
    for user in users:
        # 그룹 정보 구성
        group_info = None
        if user.group:
            group_info = {
                "id": user.group.id,
                "name": user.group.name,
                "description": user.group.description or ""
            }
        
        result.append(UserListResponse(
            id=str(user.id),
            real_name=user.real_name,
            display_name=user.display_name,
            email=user.email,
            phone_number=user.phone_number,
            department=user.department,
            position=user.position,
            bio=user.bio,
            is_active=user.is_active,
            is_admin=user.is_admin,
            approval_status=user.approval_status,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            login_count=user.login_count,
            role_name=user.role.name if user.role else None,
            group_name=user.group.name if user.group else None,
            group=group_info,
            permissions_count=len(user.permissions),
            features_count=len(user.features)
        ))
    
    return result

# 사용자 상세 정보 조회
@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user_detail(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """사용자 상세 정보 조회"""
    user = db.query(User).options(
        joinedload(User.role).joinedload(Role.permissions),
        joinedload(User.role).joinedload(Role.features).joinedload(Feature.feature_category),
        joinedload(User.group),
        joinedload(User.permissions),
        joinedload(User.features).joinedload(Feature.feature_category),
        joinedload(User.approver)
    ).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    # 역할 정보 구성
    role_info = None
    if user.role:
        role_info = RoleResponse(
            id=user.role.id,
            name=user.role.name,
            description=user.role.description or "",
            is_active=user.role.is_active,
            permissions=[PermissionResponse.from_orm(p) for p in user.role.permissions],
            features=[create_feature_response(f) for f in user.role.features],
            users_count=len(user.role.users)
        )
    
    # 그룹 정보 구성
    group_info = None
    if user.group:
        group_info = {
            "id": user.group.id,
            "name": user.group.name,
            "description": user.group.description or ""
        }
    
    print(f"사용자 상세 정보 조회 - 그룹ID: {user.group_id}, Bio: {user.bio}")
    
    response = UserDetailResponse(
        id=str(user.id),
        real_name=user.real_name,
        display_name=user.display_name or "",
        email=user.email,
        phone_number=user.phone_number or "",
        department=user.department or "",
        position=user.position or "",
        bio=user.bio or "",
        is_active=user.is_active,
        is_admin=user.is_admin,
        approval_status=user.approval_status,
        approval_note=user.approval_note or "",
        approved_by=user.approver.real_name if user.approver else None,
        approved_at=user.approved_at,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        login_count=user.login_count,
        role=role_info,
        group=group_info,
        permissions=[PermissionResponse.from_orm(p) for p in user.permissions],
        features=[create_feature_response(f) for f in user.features]
    )
    
    print(f"응답 데이터 - 그룹: {group_info}, Bio: {response.bio}")
    
    return response

# 사용자 승인/거부
@router.post("/users/approve")
async def approve_user(
    request: UserApprovalRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """사용자 승인/거부"""
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    if request.approval_status not in ['approved', 'rejected']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="승인 상태는 'approved' 또는 'rejected'여야 합니다."
        )
    
    user.approval_status = request.approval_status
    user.approval_note = request.approval_note
    user.approved_by = current_admin.id
    user.approved_at = datetime.utcnow()
    
    # 승인된 경우 계정 활성화
    if request.approval_status == 'approved':
        user.is_active = True
    
    db.commit()
    
    return {"message": f"사용자가 {request.approval_status}되었습니다."}

# 사용자 계정 활성화/비활성화
@router.post("/users/activate")
async def activate_user(
    request: UserActivationRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """사용자 계정 활성화/비활성화"""
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    user.is_active = request.is_active
    db.commit()
    
    status_text = "활성화" if request.is_active else "비활성화"
    return {"message": f"사용자 계정이 {status_text}되었습니다."}

# 사용자 권한 부여/회수
@router.post("/users/permissions")
async def update_user_permissions(
    request: UserPermissionRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """사용자 권한 부여/회수"""
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    # 권한 조회
    permissions = db.query(Permission).filter(Permission.id.in_(request.permission_ids)).all()
    
    # 사용자 권한 업데이트
    user.permissions = permissions
    db.commit()
    
    return {"message": "사용자 권한이 업데이트되었습니다."}

# 사용자 기능 부여/회수
@router.post("/users/features")
async def update_user_features(
    request: UserFeatureRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """사용자 기능 부여/회수"""
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    # 기능 조회
    features = db.query(Feature).filter(Feature.id.in_(request.feature_ids)).all()
    
    # 사용자 기능 업데이트
    user.features = features
    db.commit()
    
    return {"message": "사용자 기능이 업데이트되었습니다."}

# 모든 권한 목록 조회
@router.get("/permissions", response_model=List[PermissionResponse])
async def get_permissions(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """모든 권한 목록 조회"""
    permissions = db.query(Permission).filter(Permission.is_active == True).all()
    return [PermissionResponse.from_orm(p) for p in permissions]

# 모든 기능 목록 조회
@router.get("/features", response_model=List[FeatureResponse])
async def get_features(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """모든 기능 목록 조회"""
    features = db.query(Feature).options(
        joinedload(Feature.feature_category)
    ).filter(Feature.is_active == True).all()
    
    result = []
    for feature in features:
        feature_data = FeatureResponse(
            id=feature.id,
            name=feature.name,
            display_name=feature.display_name,
            description=feature.description,
            category_id=feature.category_id,
            icon=feature.icon,
            url_path=feature.url_path,
            is_external=feature.is_external,
            open_in_new_tab=feature.open_in_new_tab,
            is_active=feature.is_active,
            requires_approval=feature.requires_approval,
            sort_order=feature.sort_order or 0,
            category_name=feature.feature_category.name if feature.feature_category else None,
            category_display_name=feature.feature_category.display_name if feature.feature_category else None
        )
        result.append(feature_data)
    
    return result

# 모든 역할 목록 조회
@router.get("/roles", response_model=List[RoleResponse])
async def get_roles(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """모든 역할 목록 조회"""
    roles = db.query(Role).options(
        joinedload(Role.permissions),
        joinedload(Role.features).joinedload(Feature.feature_category),
        joinedload(Role.users)
    ).filter(Role.is_active == True).all()
    
    result = []
    for role in roles:
        # Feature 정보를 수동으로 구성
        feature_responses = []
        for feature in role.features:
            feature_responses.append(FeatureResponse(
                id=feature.id,
                name=feature.name,
                display_name=feature.display_name,
                description=feature.description,
                category_id=feature.category_id,
                icon=feature.icon,
                url_path=feature.url_path,
                is_external=feature.is_external,
                open_in_new_tab=feature.open_in_new_tab,
                is_active=feature.is_active,
                requires_approval=feature.requires_approval,
                sort_order=feature.sort_order or 0,
                category_name=feature.feature_category.name if feature.feature_category else None,
                category_display_name=feature.feature_category.display_name if feature.feature_category else None
            ))
        
        result.append(RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description or "",
            is_active=role.is_active,
            permissions=[PermissionResponse.from_orm(p) for p in role.permissions],
            features=feature_responses,
            users_count=len(role.users)
        ))
    
    return result

# 통계 조회
@router.get("/stats")
async def get_admin_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """관리자 대시보드용 통계 조회"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    pending_users = db.query(User).filter(User.approval_status == 'pending').count()
    approved_users = db.query(User).filter(User.approval_status == 'approved').count()
    rejected_users = db.query(User).filter(User.approval_status == 'rejected').count()
    admin_users = db.query(User).filter(User.is_admin == True).count()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": total_users - active_users,
        "pending_users": pending_users,
        "approved_users": approved_users,
        "rejected_users": rejected_users,
        "admin_users": admin_users
    }

# 기본 데이터 초기화
@router.post("/init-data")
async def initialize_basic_data(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """기본 권한, 기능, 역할 데이터 초기화"""
    
    # 실제 화면 기반 권한 생성 (쥬피터 워크스페이스 버튼별)
    basic_permissions = [
        # 기본 권한
        {"name": "read_profile", "display_name": "프로필 읽기", "description": "자신의 프로필 정보를 읽을 수 있습니다", "category": "basic"},
        {"name": "edit_profile", "display_name": "프로필 편집", "description": "자신의 프로필 정보를 편집할 수 있습니다", "category": "basic"},
        
        # 쥬피터 워크스페이스 권한 (버튼별)
        {"name": "workspace_create", "display_name": "새 워크스페이스", "description": "새로운 워크스페이스를 생성할 수 있습니다", "category": "workspace"},
        {"name": "workspace_file_manage", "display_name": "파일관리", "description": "워크스페이스 파일을 관리할 수 있습니다", "category": "workspace"},
        {"name": "workspace_start", "display_name": "워크스페이스 시작", "description": "워크스페이스를 시작할 수 있습니다", "category": "workspace"},
        {"name": "workspace_delete", "display_name": "워크스페이스 삭제", "description": "워크스페이스를 삭제할 수 있습니다", "category": "workspace"},
        {"name": "workspace_open", "display_name": "워크스페이스 열기", "description": "워크스페이스를 열 수 있습니다", "category": "workspace"},
        
        # 관리자 권한
        {"name": "admin_panel", "display_name": "관리자 패널", "description": "관리자 패널에 접근할 수 있습니다", "category": "admin"},
        {"name": "manage_users", "display_name": "사용자 관리", "description": "사용자를 관리할 수 있습니다", "category": "admin"},
        {"name": "manage_permissions", "display_name": "권한 관리", "description": "권한을 관리할 수 있습니다", "category": "admin"},
        {"name": "manage_features", "display_name": "기능 관리", "description": "기능을 관리할 수 있습니다", "category": "admin"},
        {"name": "manage_roles", "display_name": "역할 관리", "description": "역할을 관리할 수 있습니다", "category": "admin"},
        {"name": "manage_groups", "display_name": "그룹 관리", "description": "그룹을 관리할 수 있습니다", "category": "admin"},
    ]
    
    for perm_data in basic_permissions:
        existing = db.query(Permission).filter(Permission.name == perm_data["name"]).first()
        if not existing:
            permission = Permission(**perm_data)
            db.add(permission)
    
    # motherpage 기반 기능 생성
    motherpage_features = [
        {"name": "dashboard", "display_name": "대시보드", "description": "메인 대시보드", "category": "core", "icon": "📊", "url_path": "/dashboard", "requires_approval": False},
        {"name": "jupyter_workspace", "display_name": "쥬피터 워크스페이스", "description": "데이터 분석을 위한 쥬피터 노트북 환경", "category": "analysis", "icon": "📓", "url_path": "/workspaces", "requires_approval": False},
        {"name": "apex", "display_name": "APEX", "description": "공정분석 시스템", "category": "analysis", "icon": "🏭", "url_path": "/apex", "requires_approval": True},
        {"name": "llm_chat", "display_name": "AI 채팅", "description": "LLM을 활용한 AI 채팅", "category": "ai", "icon": "🤖", "url_path": "/llm", "requires_approval": True},
        {"name": "admin_tools", "display_name": "관리 도구", "description": "시스템 관리 도구", "category": "admin", "icon": "⚙️", "url_path": "/admin", "requires_approval": False},
    ]
    
    for feature_data in motherpage_features:
        existing = db.query(Feature).filter(Feature.name == feature_data["name"]).first()
        if not existing:
            feature = Feature(**feature_data)
            db.add(feature)
    
    # 역할 생성 (admin, manager, user)
    roles_data = [
        {"name": "admin", "description": "시스템 관리자 - 모든 권한 보유"},
        {"name": "manager", "description": "중간 관리자 - 현재 미사용"},
        {"name": "user", "description": "일반 사용자 - 기본 기능 사용 가능"},
    ]
    
    for role_data in roles_data:
        existing = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing:
            role = Role(**role_data)
            db.add(role)
    
    # 기본 그룹 생성 (부서 개념)
    basic_groups = [
        {"name": "IT팀", "description": "정보기술팀", "created_by": current_admin.id},
        {"name": "분석팀", "description": "데이터분석팀", "created_by": current_admin.id},
        {"name": "운영팀", "description": "시스템운영팀", "created_by": current_admin.id},
        {"name": "연구개발팀", "description": "연구개발팀", "created_by": current_admin.id},
    ]
    
    for group_data in basic_groups:
        existing = db.query(Group).filter(Group.name == group_data["name"]).first()
        if not existing:
            group = Group(**group_data)
            db.add(group)
    
    db.commit()
    
    # 역할에 권한과 기능 할당
    # admin 역할 - 모든 권한과 기능
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role:
        all_permissions = db.query(Permission).all()
        all_features = db.query(Feature).all()
        admin_role.permissions = all_permissions
        admin_role.features = all_features
    
    # user 역할 - 기본 권한과 일부 기능
    user_role = db.query(Role).filter(Role.name == "user").first()
    if user_role:
        user_permissions = db.query(Permission).filter(Permission.name.in_([
            "read_profile", "edit_profile", "workspace_open"
        ])).all()
        user_features = db.query(Feature).filter(Feature.name.in_([
            "dashboard", "jupyter_workspace"
        ])).all()
        user_role.permissions = user_permissions
        user_role.features = user_features
    
    # manager 역할은 현재 미사용으로 비워둠
    
    db.commit()
    
    return {"message": "실제 데이터 기반으로 기본 데이터가 성공적으로 초기화되었습니다."}

# 가입 시 선택 가능한 권한과 기능 조회 (인증 불필요)
@router.get("/signup-options")
async def get_signup_options(db: Session = Depends(get_db)):
    """회원가입 시 선택 가능한 권한과 기능 목록 조회"""
    
    # 기본 권한과 승인이 필요하지 않은 권한만 조회
    available_permissions = db.query(Permission).filter(
        Permission.is_active == True,
        Permission.category.in_(["basic", "file", "workspace"])
    ).all()
    
    # 모든 기능 조회 (승인 필요 여부 표시)
    available_features = db.query(Feature).filter(Feature.is_active == True).all()
    
    return {
        "permissions": [
            {
                "id": p.id,
                "name": p.name,
                "display_name": p.display_name,
                "description": p.description,
                "category": p.category
            } for p in available_permissions
        ],
        "features": [
            {
                "id": f.id,
                "name": f.name,
                "display_name": f.display_name,
                "description": f.description,
                "category": f.category,
                "icon": f.icon,
                "requires_approval": f.requires_approval
            } for f in available_features
        ]
    }

# 사용자 기본 정보 업데이트
@router.put("/users/{user_id}")
async def update_user_info(
    user_id: str,
    request: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """사용자 기본 정보 업데이트 (관리자용)"""
    print(f"사용자 정보 업데이트 요청 - 사용자 ID: {user_id}")
    print(f"요청 데이터: {request.dict()}")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    print(f"업데이트 전 사용자 정보 - 그룹ID: {user.group_id}, Bio: {user.bio}")
    
    # 정보 업데이트
    user.real_name = request.real_name
    user.display_name = request.display_name
    user.phone_number = request.phone_number
    user.department = request.department
    user.position = request.position
    user.bio = request.bio
    
    # 그룹 할당 (hasattr를 사용하여 필드 존재 여부 확인)
    if hasattr(request, 'group_id') and request.group_id is not None:
        print(f"그룹 할당: {request.group_id}")
        # 그룹 존재 확인
        group = db.query(Group).filter(Group.id == request.group_id).first()
        if group:
            user.group_id = request.group_id
            print(f"그룹 할당 성공: {group.name}")
        else:
            print(f"그룹을 찾을 수 없음: {request.group_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="지정된 그룹을 찾을 수 없습니다."
            )
    elif hasattr(request, 'group_id') and request.group_id is None:
        print("그룹 제거")
        user.group_id = None
    
    print(f"업데이트 후 사용자 정보 - 그룹ID: {user.group_id}, Bio: {user.bio}")
    
    db.commit()
    
    print("데이터베이스 커밋 완료")
    
    return {"message": "사용자 정보가 업데이트되었습니다."}

# 사용자 상태 업데이트 (승인상태 + 활성상태)
@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    request: UserStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """사용자 승인상태 및 활성상태 업데이트"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    # 승인상태 유효성 체크
    if request.approval_status not in ['approved', 'pending', 'rejected']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="승인 상태는 'approved', 'pending', 'rejected' 중 하나여야 합니다."
        )
    
    # 상태 업데이트
    user.approval_status = request.approval_status
    user.is_active = request.is_active
    
    # 승인일 때 승인 정보 업데이트
    if request.approval_status == 'approved':
        user.approved_by = current_admin.id
        user.approved_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "사용자 상태가 업데이트되었습니다."}

# 사용자 비밀번호 변경 (관리자용)
@router.post("/users/change-password")
async def change_user_password(
    request: UserPasswordChangeRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """사용자 비밀번호 변경 (관리자용)"""
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    # 비밀번호 해시화
    from app.utils.auth import get_password_hash
    hashed_password = get_password_hash(request.new_password)
    user.hashed_password = hashed_password
    
    db.commit()
    
    return {"message": "사용자 비밀번호가 변경되었습니다."}

# 기능 관리 API
@router.post("/features", response_model=FeatureResponse)
async def create_feature(
    request: FeatureCreateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """새로운 기능 생성"""
    # 중복 체크
    existing = db.query(Feature).filter(Feature.name == request.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 기능명입니다."
        )
    
    # 아이콘이 제공되지 않았으면 자동 생성
    icon = request.icon if request.icon else generate_feature_abbreviation(request.display_name)
    
    feature = Feature(
        name=request.name,
        display_name=request.display_name,
        description=request.description,
        category_id=request.category_id,
        icon=icon,
        url_path=request.url_path,
        is_external=request.is_external,
        open_in_new_tab=request.open_in_new_tab,
        requires_approval=request.requires_approval,
        is_active=request.is_active,
        sort_order=request.sort_order
    )
    
    db.add(feature)
    db.commit()
    db.refresh(feature)
    
    # 카테고리 정보와 함께 응답
    feature = db.query(Feature).options(
        joinedload(Feature.feature_category)
    ).filter(Feature.id == feature.id).first()
    
    return FeatureResponse(
        id=feature.id,
        name=feature.name,
        display_name=feature.display_name,
        description=feature.description,
        category_id=feature.category_id,
        icon=feature.icon,
        url_path=feature.url_path,
        is_external=feature.is_external,
        open_in_new_tab=feature.open_in_new_tab,
        is_active=feature.is_active,
        requires_approval=feature.requires_approval,
        sort_order=feature.sort_order or 0,
        category_name=feature.feature_category.name if feature.feature_category else None,
        category_display_name=feature.feature_category.display_name if feature.feature_category else None
    )

@router.put("/features/{feature_id}", response_model=FeatureResponse)
async def update_feature(
    feature_id: int,
    request: FeatureUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """기능 정보 업데이트"""
    feature = db.query(Feature).filter(Feature.id == feature_id).first()
    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="기능을 찾을 수 없습니다."
        )
    
    # 아이콘이 제공되지 않았으면 자동 생성
    icon = request.icon if request.icon else generate_feature_abbreviation(request.display_name)
    
    feature.display_name = request.display_name
    feature.description = request.description
    feature.category_id = request.category_id
    feature.icon = icon
    feature.url_path = request.url_path
    feature.is_external = request.is_external
    feature.open_in_new_tab = request.open_in_new_tab
    feature.requires_approval = request.requires_approval
    feature.is_active = request.is_active
    feature.sort_order = request.sort_order
    
    db.commit()
    
    # 카테고리 정보와 함께 응답
    feature = db.query(Feature).options(
        joinedload(Feature.feature_category)
    ).filter(Feature.id == feature_id).first()
    
    return FeatureResponse(
        id=feature.id,
        name=feature.name,
        display_name=feature.display_name,
        description=feature.description,
        category_id=feature.category_id,
        icon=feature.icon,
        url_path=feature.url_path,
        is_external=feature.is_external,
        open_in_new_tab=feature.open_in_new_tab,
        is_active=feature.is_active,
        requires_approval=feature.requires_approval,
        sort_order=feature.sort_order or 0,
        category_name=feature.feature_category.name if feature.feature_category else None,
        category_display_name=feature.feature_category.display_name if feature.feature_category else None
    )

@router.delete("/features/{feature_id}")
async def delete_feature(
    feature_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """기능 삭제"""
    feature = db.query(Feature).filter(Feature.id == feature_id).first()
    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="기능을 찾을 수 없습니다."
        )
    
    db.delete(feature)
    db.commit()
    
    return {"message": "기능이 삭제되었습니다."}

# 역할 관리 API
@router.post("/roles", response_model=RoleResponse)
async def create_role(
    request: RoleCreateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """새로운 역할 생성"""
    # 중복 체크
    existing = db.query(Role).filter(Role.name == request.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 역할명입니다."
        )
    
    role = Role(
        name=request.name,
        description=request.description,
        is_active=request.is_active
    )
    
    db.add(role)
    db.commit()
    db.refresh(role)
    
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description or "",
        is_active=role.is_active,
        permissions=[],
        features=[],
        users_count=0
    )

@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    request: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """역할 정보 업데이트"""
    role = db.query(Role).options(
        joinedload(Role.permissions),
        joinedload(Role.features),
        joinedload(Role.users)
    ).filter(Role.id == role_id).first()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="역할을 찾을 수 없습니다."
        )
    
    role.description = request.description
    role.is_active = request.is_active
    
    db.commit()
    db.refresh(role)
    
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description or "",
        is_active=role.is_active,
        permissions=[PermissionResponse.from_orm(p) for p in role.permissions],
                    features=[create_feature_response(f) for f in role.features],
        users_count=len(role.users)
    )

@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """역할 삭제"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="역할을 찾을 수 없습니다."
        )
    
    # admin, manager, user 역할은 삭제 불가
    if role.name in ["admin", "manager", "user"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="기본 역할은 삭제할 수 없습니다."
        )
    
    db.delete(role)
    db.commit()
    
    return {"message": "역할이 삭제되었습니다."}

@router.post("/roles/permissions")
async def update_role_permissions(
    request: RolePermissionRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """역할 권한 업데이트"""
    role = db.query(Role).filter(Role.id == request.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="역할을 찾을 수 없습니다."
        )
    
    permissions = db.query(Permission).filter(Permission.id.in_(request.permission_ids)).all()
    role.permissions = permissions
    
    db.commit()
    
    return {"message": "역할 권한이 업데이트되었습니다."}

@router.post("/roles/features")
async def update_role_features(
    request: RoleFeatureRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """역할 기능 업데이트"""
    role = db.query(Role).filter(Role.id == request.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="역할을 찾을 수 없습니다."
        )
    
    features = db.query(Feature).filter(Feature.id.in_(request.feature_ids)).all()
    role.features = features
    
    db.commit()
    
    return {"message": "역할 기능이 업데이트되었습니다."}

# 그룹 관리 API
@router.get("/groups", response_model=List[GroupDetailResponse])
async def get_groups(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """그룹 목록 조회"""
    groups = db.query(Group).options(
        joinedload(Group.members),
        joinedload(Group.permissions),
        joinedload(Group.features).joinedload(Feature.feature_category),
        joinedload(Group.creator)
    ).all()
    
    result = []
    for group in groups:
        # Feature 정보를 수동으로 구성
        feature_responses = []
        for feature in group.features:
            feature_responses.append(FeatureResponse(
                id=feature.id,
                name=feature.name,
                display_name=feature.display_name,
                description=feature.description,
                category_id=feature.category_id,
                icon=feature.icon,
                url_path=feature.url_path,
                is_external=feature.is_external,
                open_in_new_tab=feature.open_in_new_tab,
                is_active=feature.is_active,
                requires_approval=feature.requires_approval,
                sort_order=feature.sort_order or 0,
                category_name=feature.feature_category.name if feature.feature_category else None,
                category_display_name=feature.feature_category.display_name if feature.feature_category else None
            ))
        
        result.append(GroupDetailResponse(
            id=group.id,
            name=group.name,
            description=group.description or "",
            created_by=group.creator.real_name if group.creator else "알 수 없음",
            created_at=group.created_at,
            users_count=len(group.members),
            users=[],  # 목록에서는 사용자 정보는 제외
            permissions=[PermissionResponse.from_orm(p) for p in group.permissions],
            features=feature_responses
        ))
    
    return result

@router.get("/groups/{group_id}", response_model=GroupDetailResponse)
async def get_group_detail(
    group_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """그룹 상세 정보 조회"""
    group = db.query(Group).options(
        joinedload(Group.members).joinedload(User.role),
        joinedload(Group.permissions),
        joinedload(Group.features).joinedload(Feature.feature_category),
        joinedload(Group.creator)
    ).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="그룹을 찾을 수 없습니다."
        )
    
    return GroupDetailResponse(
        id=group.id,
        name=group.name,
        description=group.description or "",
        created_by=group.creator.real_name if group.creator else "알 수 없음",
        created_at=group.created_at,
        users_count=len(group.members),
        users=[GroupUserResponse(
            id=str(user.id),
            real_name=user.real_name,
            display_name=user.display_name,
            email=user.email,
            phone_number=user.phone_number,
            department=user.department,
            position=user.position,
            is_active=user.is_active,
            is_admin=user.is_admin,
            is_verified=user.is_verified,
            approval_status=user.approval_status,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            login_count=user.login_count,
            role_name=user.role.name if user.role else None
        ) for user in group.members],
        permissions=[PermissionResponse.from_orm(p) for p in group.permissions],
        features=[create_feature_response(f) for f in group.features]
    )

@router.post("/groups", response_model=GroupDetailResponse)
async def create_group(
    request: GroupCreateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """새로운 그룹 생성"""
    # 중복 체크
    existing = db.query(Group).filter(Group.name == request.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 그룹명입니다."
        )
    
    group = Group(
        name=request.name,
        description=request.description,
        created_by=current_admin.id
    )
    
    db.add(group)
    db.commit()
    db.refresh(group)
    
    return GroupDetailResponse(
        id=group.id,
        name=group.name,
        description=group.description or "",
        created_by=current_admin.real_name,
        created_at=group.created_at,
        users_count=0,
        permissions=[],
        features=[]
    )

@router.put("/groups/{group_id}", response_model=GroupDetailResponse)
async def update_group(
    group_id: int,
    request: GroupUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """그룹 정보 업데이트"""
    group = db.query(Group).options(
        joinedload(Group.members).joinedload(User.role),
        joinedload(Group.permissions),
        joinedload(Group.features).joinedload(Feature.feature_category),
        joinedload(Group.creator)
    ).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="그룹을 찾을 수 없습니다."
        )
    
    # 이름 중복 체크
    existing = db.query(Group).filter(Group.name == request.name, Group.id != group_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 그룹명입니다."
        )
    
    group.name = request.name
    group.description = request.description
    
    db.commit()
    db.refresh(group)
    
    return GroupDetailResponse(
        id=group.id,
        name=group.name,
        description=group.description or "",
        created_by=group.creator.real_name if group.creator else "알 수 없음",
        created_at=group.created_at,
        users_count=len(group.members),
        users=[GroupUserResponse(
            id=str(user.id),
            real_name=user.real_name,
            display_name=user.display_name,
            email=user.email,
            phone_number=user.phone_number,
            department=user.department,
            position=user.position,
            is_active=user.is_active,
            is_admin=user.is_admin,
            is_verified=user.is_verified,
            approval_status=user.approval_status,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            login_count=user.login_count,
            role_name=user.role.name if user.role else None
        ) for user in group.members],
        permissions=[PermissionResponse.from_orm(p) for p in group.permissions],
        features=[create_feature_response(f) for f in group.features]
    )

@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """그룹 삭제"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="그룹을 찾을 수 없습니다."
        )
    
    db.delete(group)
    db.commit()
    
    return {"message": "그룹이 삭제되었습니다."}

@router.post("/groups/permissions")
async def update_group_permissions(
    request: GroupPermissionRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """그룹 권한 업데이트"""
    group = db.query(Group).filter(Group.id == request.group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="그룹을 찾을 수 없습니다."
        )
    
    permissions = db.query(Permission).filter(Permission.id.in_(request.permission_ids)).all()
    group.permissions = permissions
    
    db.commit()
    
    return {"message": "그룹 권한이 업데이트되었습니다."}

@router.post("/groups/features")
async def update_group_features(
    request: GroupFeatureRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """그룹 기능 업데이트"""
    group = db.query(Group).filter(Group.id == request.group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="그룹을 찾을 수 없습니다."
        )
    
    features = db.query(Feature).filter(Feature.id.in_(request.feature_ids)).all()
    group.features = features
    
    db.commit()
    
    return {"message": "그룹 기능이 업데이트되었습니다."}

# Feature Categories 관리 API
@router.get("/feature-categories")
async def get_feature_categories(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """기능 카테고리 목록 조회"""
    from ..models.permission import FeatureCategory
    categories = db.query(FeatureCategory).filter(FeatureCategory.is_active == True).order_by(FeatureCategory.sort_order).all()
    
    return [
        {
            "id": category.id,
            "name": category.name,
            "display_name": category.display_name,
            "description": category.description,
            "icon": category.icon,
            "color": category.color,
            "sort_order": category.sort_order,
            "is_active": category.is_active
        }
        for category in categories
    ]

# 사용자 그룹 할당
@router.post("/users/group")
async def update_user_group(
    request: UserGroupRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """사용자 그룹 할당/해제"""
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    if request.group_id:
        # 그룹 할당
        group = db.query(Group).filter(Group.id == request.group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="그룹을 찾을 수 없습니다."
            )
        user.group_id = request.group_id
        message = f"사용자가 '{group.name}' 그룹에 할당되었습니다."
    else:
        # 그룹 해제
        user.group_id = None
        message = "사용자의 그룹 할당이 해제되었습니다."
    
    db.commit()
    
    return {"message": message} 
