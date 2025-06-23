from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# FeatureCategory 스키마
class FeatureCategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True

class FeatureCategoryCreate(FeatureCategoryBase):
    pass

class FeatureCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class FeatureCategory(FeatureCategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Permission 스키마
class PermissionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    category: Optional[str] = None
    is_active: bool = True

class PermissionCreate(PermissionBase):
    pass

class PermissionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None

class Permission(PermissionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Feature 스키마
class FeatureBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = None
    icon: Optional[str] = None
    url_path: Optional[str] = None
    auto_grant: bool = False
    is_active: bool = True
    requires_approval: bool = False
    is_external: bool = False
    open_in_new_tab: bool = False
    sort_order: int = 0

class FeatureCreate(FeatureBase):
    pass

class FeatureUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = None
    icon: Optional[str] = None
    url_path: Optional[str] = None
    auto_grant: Optional[bool] = None
    is_active: Optional[bool] = None
    requires_approval: Optional[bool] = None
    is_external: Optional[bool] = None
    open_in_new_tab: Optional[bool] = None
    sort_order: Optional[int] = None

class Feature(FeatureBase):
    id: int
    created_at: datetime
    updated_at: datetime
    feature_category: Optional[FeatureCategory] = None
    
    class Config:
        from_attributes = True

# 카테고리 포함 Feature 응답 스키마
class FeatureWithCategory(Feature):
    feature_category: Optional[FeatureCategory] = None

# 카테고리별 Feature 리스트 스키마
class CategoryWithFeatures(FeatureCategory):
    features: List[Feature] = [] 