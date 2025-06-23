from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing import Optional, Any
from uuid import UUID

class WorkspaceBase(BaseModel):
    name: str
    description: Optional[str] = None

class WorkspaceCreate(WorkspaceBase):
    pass

class WorkspaceResponse(WorkspaceBase):
    id: int
    path: Optional[str] = None  # path가 None일 수 있도록 수정
    is_active: bool
    jupyter_port: Optional[int] = None
    jupyter_token: Optional[str] = None
    owner_id: str  # UUID 문자열
    created_at: datetime
    
    @model_validator(mode='before')
    @classmethod
    def convert_uuid_to_string(cls, data: Any) -> Any:
        """UUID를 문자열로 변환"""
        if isinstance(data, dict):
            if 'owner_id' in data and isinstance(data['owner_id'], UUID):
                data['owner_id'] = str(data['owner_id'])
        elif hasattr(data, 'owner_id') and isinstance(data.owner_id, UUID):
            data.owner_id = str(data.owner_id)
        return data
    
    class Config:
        from_attributes = True 