"""
LLMOps 권한 관리

멀티테넌트 환경에서 RAG 데이터소스와 플로우에 대한 접근 권한을 관리합니다.
"""

from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from ..database import get_db
from ..models.user import User
from ..models.workspace import Workspace
from .models import RAGDataSource, Flow, OwnerType

import logging

logger = logging.getLogger(__name__)

class LLMOpsAuthService:
    """LLMOps 권한 관리 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_accessible_rag_datasources(self, current_user: User) -> List[RAGDataSource]:
        """
        현재 사용자가 접근 가능한 모든 RAG 데이터소스 목록을 반환합니다.
        
        권한 규칙:
        - Admin: 모든 데이터소스 접근 가능
        - 일반 사용자: 자신이 소유한 개인 데이터소스 + 자신이 속한 그룹의 데이터소스
        
        Args:
            current_user: 현재 로그인된 사용자
            
        Returns:
            접근 가능한 RAG 데이터소스 목록
        """
        try:
            # Admin인 경우 모든 데이터소스 반환
            if current_user.is_admin:
                logger.info(f"Admin user {current_user.id} accessing all RAG datasources")
                return self.db.query(RAGDataSource).filter(RAGDataSource.is_active == True).all()
            
            # 일반 사용자의 경우
            conditions = []
            
            # 1. 개인 소유 데이터소스
            conditions.append(
                and_(
                    RAGDataSource.owner_type == OwnerType.USER,
                    RAGDataSource.owner_id == str(current_user.id)
                )
            )
            
            # 2. 사용자가 속한 그룹 소유 데이터소스
            if current_user.group_id:  # 그룹에 속한 경우
                conditions.append(
                    and_(
                        RAGDataSource.owner_type == OwnerType.GROUP,
                        RAGDataSource.owner_id == str(current_user.group_id)
                    )
                )
                logger.info(f"User {current_user.id} has group access to group {current_user.group_id}")
            else:
                logger.info(f"User {current_user.id} has no group membership")
            
            # 조건이 없으면 개인 데이터소스만 반환
            if not conditions:
                logger.warning(f"User {current_user.id} has no accessible datasources")
                return []
            
            # 쿼리 실행
            datasources = self.db.query(RAGDataSource).filter(
                and_(
                    RAGDataSource.is_active == True,
                    or_(*conditions)
                )
            ).all()
            
            logger.info(f"User {current_user.id} can access {len(datasources)} RAG datasources")
            return datasources
            
        except Exception as e:
            logger.error(f"Error getting accessible RAG datasources for user {current_user.id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="데이터소스 목록 조회 중 오류가 발생했습니다."
            )
    
    def get_rag_datasource_with_permission(self, source_id: int, current_user: User) -> RAGDataSource:
        """
        특정 RAG 데이터소스에 대한 접근 권한을 확인하고 반환합니다.
        
        Args:
            source_id: 데이터소스 ID
            current_user: 현재 로그인된 사용자
            
        Returns:
            접근 권한이 있는 경우 RAGDataSource 객체
            
        Raises:
            HTTPException: 권한이 없거나 데이터소스가 존재하지 않는 경우
        """
        try:
            # 데이터소스 조회
            datasource = self.db.query(RAGDataSource).filter(
                RAGDataSource.id == source_id,
                RAGDataSource.is_active == True
            ).first()
            
            if not datasource:
                # 더 자세한 디버깅 정보 추가
                all_datasources = self.db.query(RAGDataSource).all()
                active_datasources = self.db.query(RAGDataSource).filter(RAGDataSource.is_active == True).all()
                logger.warning(f"RAG datasource {source_id} not found or inactive. "
                             f"Total datasources: {len(all_datasources)}, "
                             f"Active datasources: {len(active_datasources)}, "
                             f"Active IDs: {[ds.id for ds in active_datasources]}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="데이터소스를 찾을 수 없습니다."
                )
            
            # Admin인 경우 모든 데이터소스 접근 가능
            if current_user.is_admin:
                logger.info(f"Admin user {current_user.id} accessing RAG datasource {source_id}")
                return datasource
            
            # 권한 확인
            has_permission = False
            
            # 개인 소유 데이터소스 확인
            if (datasource.owner_type == OwnerType.USER and 
                datasource.owner_id == str(current_user.id)):
                has_permission = True
                logger.info(f"User {current_user.id} accessing own RAG datasource {source_id}")
            
            # 그룹 소유 데이터소스 확인
            elif (datasource.owner_type == OwnerType.GROUP and 
                  current_user.group_id and 
                  datasource.owner_id == str(current_user.group_id)):
                has_permission = True
                logger.info(f"User {current_user.id} accessing group RAG datasource {source_id} (group: {current_user.group_id})")
            
            if not has_permission:
                logger.warning(f"User {current_user.id} denied access to RAG datasource {source_id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="이 데이터소스에 접근할 권한이 없습니다."
                )
            
            return datasource
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking permission for RAG datasource {source_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="권한 확인 중 오류가 발생했습니다."
            )
    
    def can_access_rag_datasource(self, current_user: User, datasource: RAGDataSource) -> bool:
        """
        사용자가 특정 RAG 데이터소스에 접근할 수 있는지 확인합니다.
        
        Args:
            current_user: 현재 로그인된 사용자
            datasource: 확인할 RAG 데이터소스
            
        Returns:
            접근 가능 여부
        """
        try:
            # Admin인 경우 모든 데이터소스 접근 가능
            if current_user.is_admin:
                logger.info(f"Admin user {current_user.id} accessing RAG datasource {datasource.id}")
                return True
            
            # 개인 소유 데이터소스 확인
            if (datasource.owner_type == OwnerType.USER and 
                datasource.owner_id == str(current_user.id)):
                logger.info(f"User {current_user.id} accessing own RAG datasource {datasource.id}")
                return True
            
            # 그룹 소유 데이터소스 확인
            if (datasource.owner_type == OwnerType.GROUP and 
                current_user.group_id and 
                datasource.owner_id == str(current_user.group_id)):
                logger.info(f"User {current_user.id} accessing group RAG datasource {datasource.id} (group: {current_user.group_id})")
                return True
            
            logger.warning(f"User {current_user.id} denied access to RAG datasource {datasource.id}")
            return False
            
        except Exception as e:
            logger.error(f"Error checking access permission for RAG datasource {datasource.id}: {str(e)}")
            return False
    
    def can_modify_rag_datasource(self, current_user: User, datasource: RAGDataSource) -> bool:
        """
        사용자가 특정 RAG 데이터소스를 수정할 수 있는지 확인합니다.
        
        Args:
            current_user: 현재 로그인된 사용자
            datasource: 확인할 RAG 데이터소스
            
        Returns:
            수정 가능 여부
        """
        try:
            # Admin인 경우 모든 데이터소스 수정 가능
            if current_user.is_admin:
                logger.info(f"Admin user {current_user.id} can modify RAG datasource {datasource.id}")
                return True
            
            # 개인 소유 데이터소스 확인
            if (datasource.owner_type == OwnerType.USER and 
                datasource.owner_id == str(current_user.id)):
                logger.info(f"User {current_user.id} can modify own RAG datasource {datasource.id}")
                return True
            
            # 그룹 소유 데이터소스 확인 (그룹 멤버는 수정 가능)
            if (datasource.owner_type == OwnerType.GROUP and 
                current_user.group_id and 
                datasource.owner_id == str(current_user.group_id)):
                logger.info(f"User {current_user.id} can modify group RAG datasource {datasource.id} (group: {current_user.group_id})")
                return True
            
            logger.warning(f"User {current_user.id} denied modify access to RAG datasource {datasource.id}")
            return False
            
        except Exception as e:
            logger.error(f"Error checking modify permission for RAG datasource {datasource.id}: {str(e)}")
            return False
    
    def can_create_rag_datasource(self, current_user: User, owner_type: OwnerType, owner_id: Optional[str] = None) -> bool:
        """
        사용자가 특정 타입의 RAG 데이터소스를 생성할 수 있는지 확인합니다.
        
        Args:
            current_user: 현재 로그인된 사용자
            owner_type: 생성하려는 데이터소스의 소유자 타입
            owner_id: 소유자 ID (WORKSPACE 타입인 경우 필수)
            
        Returns:
            생성 가능 여부
        """
        try:
            # Admin은 모든 타입 생성 가능
            if current_user.is_admin:
                return True
            
            # 개인 데이터소스 생성
            if owner_type == OwnerType.USER:
                return True  # 모든 사용자가 개인 데이터소스 생성 가능
            
            # 그룹 데이터소스 생성
            if owner_type == OwnerType.GROUP:
                if not owner_id:
                    return False
                
                # 사용자가 해당 그룹의 멤버인지 확인
                if current_user.group_id and str(current_user.group_id) == owner_id:
                    return True
                
                # 사용자가 해당 그룹의 소유자인지 확인
                group = self.db.query(Workspace).filter(
                    Workspace.id == int(owner_id),
                    Workspace.owner_id == current_user.id
                ).first()
                
                return group is not None
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking create permission: {str(e)}")
            return False
    
    def can_access_collection(self, collection_name: str, current_user: User) -> bool:
        """
        컬렉션 이름을 기반으로 사용자의 접근 권한을 확인합니다.
        
        컬렉션 이름 형식:
        - 개인: user_{user_id}_{unique_id}_{safe_name}
        - 그룹: group_{group_id}_{unique_id}_{safe_name}
        
        Args:
            collection_name: ChromaDB 컬렉션 이름
            current_user: 현재 로그인된 사용자
            
        Returns:
            접근 가능 여부
        """
        try:
            # Admin은 모든 컬렉션 접근 가능
            if current_user.is_admin:
                return True
            
            # 컬렉션 이름 파싱
            parts = collection_name.split('_')
            if len(parts) < 3:
                logger.warning(f"Invalid collection name format: {collection_name}")
                return False
            
            owner_type = parts[0]  # 'user' or 'group'
            owner_id = parts[1]    # user_id or group_id
            
            # 개인 컬렉션 접근 확인
            if owner_type == "user":
                return owner_id == str(current_user.id)
            
            # 그룹 컬렉션 접근 확인
            elif owner_type == "group":
                # 사용자가 해당 그룹의 멤버인지 확인
                if current_user.group_id and str(current_user.group_id) == owner_id:
                    return True
                
                # 사용자가 해당 그룹의 소유자인지 확인
                try:
                    group = self.db.query(Workspace).filter(
                        Workspace.id == int(owner_id),
                        Workspace.owner_id == current_user.id
                    ).first()
                    return group is not None
                except ValueError:
                    logger.warning(f"Invalid group ID in collection name: {owner_id}")
                    return False
            
            logger.warning(f"Unknown owner type in collection name: {owner_type}")
            return False
            
        except Exception as e:
            logger.error(f"Error checking collection access for {collection_name}: {str(e)}")
            return False
    
    def get_user_collections_pattern(self, current_user: User) -> List[str]:
        """
        사용자가 접근 가능한 컬렉션 이름 패턴을 반환합니다.
        
        Args:
            current_user: 현재 로그인된 사용자
            
        Returns:
            접근 가능한 컬렉션 이름 패턴 목록
        """
        try:
            patterns = []
            
            # Admin은 모든 패턴
            if current_user.is_admin:
                patterns.extend(["user_*", "group_*"])
                return patterns
            
            # 개인 컬렉션 패턴
            patterns.append(f"user_{current_user.id}_*")
            
            # 그룹 컬렉션 패턴
            if current_user.group_id:
                patterns.append(f"group_{current_user.group_id}_*")
            
            # 사용자가 소유한 그룹들의 컬렉션 패턴
            owned_groups = self.db.query(Workspace).filter(
                Workspace.owner_id == current_user.id
            ).all()
            
            for group in owned_groups:
                patterns.append(f"group_{group.id}_*")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error getting collection patterns for user {current_user.id}: {str(e)}")
            return [f"user_{current_user.id}_*"]  # 최소한 개인 컬렉션은 접근 가능
    
    def get_accessible_flows(self, current_user: User, workspace_id: Optional[int] = None) -> List[Flow]:
        """
        현재 사용자가 접근 가능한 플로우 목록을 반환합니다.
        
        Args:
            current_user: 현재 로그인된 사용자
            workspace_id: 특정 그룹의 플로우만 조회할 경우
            
        Returns:
            접근 가능한 플로우 목록
        """
        try:
            # Admin인 경우 모든 플로우 반환
            if current_user.is_admin:
                query = self.db.query(Flow)
                if workspace_id:
                    query = query.filter(Flow.workspace_id == workspace_id)
                return query.all()
            
            # 일반 사용자의 경우 - 자신이 속한 그룹의 플로우만 접근 가능
            conditions = []
            
            if workspace_id:
                # 특정 그룹의 플로우 요청
                if current_user.group_id == workspace_id:
                    conditions.append(Flow.workspace_id == workspace_id)
            else:
                # 모든 접근 가능한 플로우 요청
                if current_user.group_id:
                    conditions.append(Flow.workspace_id == current_user.group_id)
            
            if not conditions:
                return []
            
            flows = self.db.query(Flow).filter(or_(*conditions)).all()
            logger.info(f"User {current_user.id} can access {len(flows)} flows")
            return flows
            
        except Exception as e:
            logger.error(f"Error getting accessible flows for user {current_user.id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="플로우 목록 조회 중 오류가 발생했습니다."
            )

# 의존성 주입용 함수들
def get_llmops_auth_service(db: Session = Depends(get_db)) -> LLMOpsAuthService:
    """LLMOps 권한 서비스 의존성 주입"""
    return LLMOpsAuthService(db)

async def get_rag_datasource_with_permission(
    source_id: int,
    current_user: User = Depends(lambda: None),  # 실제 의존성은 라우터에서 처리
    db: Session = Depends(get_db)
) -> RAGDataSource:
    """
    FastAPI 의존성 주입을 위한 RAG 데이터소스 권한 확인 함수
    """
    auth_service = LLMOpsAuthService(db)
    return auth_service.get_rag_datasource_with_permission(source_id, current_user) 