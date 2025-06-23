from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

class ServiceBase(BaseModel):
    name: str = Field(..., description="서비스 고유명")
    display_name: str = Field(..., description="화면 표시명")
    description: Optional[str] = Field(None, description="서비스 설명")
    url: str = Field(..., description="서비스 URL")
    icon_url: Optional[str] = Field(None, description="아이콘 URL")
    thumbnail_url: Optional[str] = Field(None, description="썸네일 URL")
    is_active: bool = Field(True, description="활성화 여부")
    is_external: bool = Field(False, description="외부 서비스 여부")
    requires_auth: bool = Field(True, description="인증 필요 여부")
    open_in_new_tab: bool = Field(False, description="새 탭 열기")
    sort_order: int = Field(0, description="정렬 순서")
    category: Optional[str] = Field(None, description="카테고리")

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    icon_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_external: Optional[bool] = None
    requires_auth: Optional[bool] = None
    open_in_new_tab: Optional[bool] = None
    sort_order: Optional[int] = None
    category: Optional[str] = None

class ServiceResponse(ServiceBase):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: str

    class Config:
        from_attributes = True

class UserAccessibleService(BaseModel):
    """사용자가 접근 가능한 서비스 정보"""
    service_id: int
    service_name: str
    service_display_name: str
    description: Optional[str]
    url: str
    icon_url: Optional[str]
    thumbnail_url: Optional[str]
    is_external: bool
    open_in_new_tab: bool
    category: Optional[str]
    sort_order: int

class MotherPageResponse(BaseModel):
    """Mother 페이지 응답 모델"""
    user_info: dict
    services: List[UserAccessibleService]
    categories: List[dict]

class ServiceCategoryBase(BaseModel):
    name: str = Field(..., description="카테고리 고유명")
    display_name: str = Field(..., description="화면 표시명")
    description: Optional[str] = Field(None, description="카테고리 설명")
    sort_order: int = Field(0, description="정렬 순서")
    is_active: bool = Field(True, description="활성화 여부")

class ServiceCategoryCreate(ServiceCategoryBase):
    pass

class ServiceCategoryResponse(ServiceCategoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ServicePermissionBase(BaseModel):
    user_id: str = Field(..., description="사용자 UUID")
    service_id: int = Field(..., description="서비스 ID")
    permission_level: str = Field("read", description="권한 레벨")
    custom_permissions: Optional[str] = Field(None, description="커스텀 권한 JSON")
    expires_at: Optional[datetime] = Field(None, description="만료일")

class ServicePermissionCreate(ServicePermissionBase):
    pass

class ServicePermissionResponse(ServicePermissionBase):
    id: int
    granted_at: datetime
    granted_by: str
    is_active: bool

    class Config:
        from_attributes = True
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        # UUID 객체를 문자열로 변환
        if hasattr(obj, 'user_id') and isinstance(obj.user_id, uuid.UUID):
            obj.user_id = str(obj.user_id)
        return super().model_validate(obj, **kwargs) 