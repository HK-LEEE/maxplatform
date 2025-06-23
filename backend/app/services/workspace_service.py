from sqlalchemy.orm import Session
from typing import List
from ..models.workspace import Workspace
from ..models.user import User
from ..schemas.workspace import WorkspaceCreate
from ..utils.workspace import create_workspace_directory

class WorkspaceService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_workspace(self, workspace_data: WorkspaceCreate, user: User):
        """새 워크스페이스 생성"""
        # 먼저 데이터베이스에 워크스페이스 정보 저장 (경로는 나중에 설정)
        db_workspace = Workspace(
            name=workspace_data.name,
            description=workspace_data.description,
            path=None,  # 임시로 None - 나중에 업데이트
            owner_id=user.id  # UUID 그대로 사용
        )
        self.db.add(db_workspace)
        self.db.commit()
        self.db.refresh(db_workspace)
        
        # 생성된 워크스페이스 ID를 사용하여 디렉토리 생성
        workspace_path = create_workspace_directory(user.id, db_workspace.id)
        
        # 경로 업데이트
        db_workspace.path = workspace_path
        self.db.commit()
        self.db.refresh(db_workspace)
        
        return db_workspace
    
    def get_user_workspaces(self, user_id) -> List[Workspace]:
        """사용자의 워크스페이스 목록 조회"""
        return self.db.query(Workspace).filter(
            Workspace.owner_id == user_id,
            Workspace.is_active == True
        ).all()
    
    def get_workspace_by_id(self, workspace_id: int, user_id):
        """워크스페이스 ID로 조회 (사용자 소유 확인)"""
        return self.db.query(Workspace).filter(
            Workspace.id == workspace_id,
            Workspace.owner_id == user_id,
            Workspace.is_active == True
        ).first()
    
    def delete_workspace(self, workspace_id: int, user_id) -> bool:
        """워크스페이스 삭제 (소프트 삭제)"""
        workspace = self.get_workspace_by_id(workspace_id, user_id)
        if not workspace:
            return False
        
        workspace.is_active = False
        self.db.commit()
        return True
    
    def update_jupyter_info(self, workspace_id: int, port: int, token: str):
        """Jupyter 인스턴스 정보 업데이트"""
        workspace = self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if workspace:
            workspace.jupyter_port = port
            workspace.jupyter_token = token
            self.db.commit()
            return workspace
        return None 