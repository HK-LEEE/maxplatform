"""
Flow Provider for FlowRunner Pro

데이터베이스에서 Flow 데이터를 가져오고 실행 권한을 검사하는 모듈
Flow Studio의 flows와 publishes 테이블에서 데이터를 조회하고 권한을 확인
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select, and_, desc
    from sqlalchemy.orm import selectinload
except ImportError:
    logging.warning("SQLAlchemy를 가져올 수 없습니다. 모의 구현을 사용합니다.")
    
    class AsyncSession:
        def __init__(self, *args, **kwargs):
            pass
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, *args):
            pass
    
    def select(*args, **kwargs):
        return None
    
    def and_(*args):
        return None
    
    def desc(*args):
        return None
    
    def selectinload(*args):
        return None

from ..database import get_async_session
from ..models import FlowStudioFlow, FlowStudioPublish

logger = logging.getLogger(__name__)


class FlowProvider:
    """
    Flow Provider 클래스
    
    데이터베이스에서 Flow 데이터를 가져오고 실행 권한을 검사하는 역할
    flow_studio_flows와 flow_studio_publishes 테이블을 조회하여 권한 확인
    """
    
    def __init__(self):
        """FlowProvider 초기화"""
        logger.info("FlowProvider 초기화 완료")
    
    async def get_published_flow(
        self, 
        flow_id: str, 
        user_id: str, 
        user_groups: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        게시된 Flow 데이터를 가져오고 실행 권한을 검사합니다.
        
        Args:
            flow_id: 플로우 ID
            user_id: 요청 사용자 ID
            user_groups: 사용자 소속 그룹 ID 리스트
            
        Returns:
            권한이 있는 경우 flow_data_snapshot JSON 데이터, 없으면 None
        """
        try:
            async with get_async_session() as session:
                # 가장 최신 PUBLISHED 상태의 플로우 조회
                publish_query = (
                    select(FlowStudioPublish)
                    .where(
                        and_(
                            FlowStudioPublish.flow_id == flow_id,
                            FlowStudioPublish.status == 'PUBLISHED'
                        )
                    )
                    .order_by(desc(FlowStudioPublish.created_at))
                    .limit(1)
                )
                
                publish_result = await session.execute(publish_query)
                publish_record = publish_result.scalar_one_or_none()
                
                if not publish_record:
                    logger.warning(f"게시된 플로우를 찾을 수 없음: {flow_id}")
                    return None
                
                # 플로우 기본 정보 및 권한 정보 조회
                flow_query = (
                    select(FlowStudioFlow)
                    .where(FlowStudioFlow.id == flow_id)
                )
                
                flow_result = await session.execute(flow_query)
                flow_record = flow_result.scalar_one_or_none()
                
                if not flow_record:
                    logger.warning(f"플로우 기본 정보를 찾을 수 없음: {flow_id}")
                    return None
                
                # 권한 검사
                if not self._check_access_permission(flow_record, user_id, user_groups):
                    logger.warning(f"플로우 실행 권한 없음: {flow_id}, 사용자: {user_id}")
                    return None
                
                # flow_data_snapshot JSON 파싱
                try:
                    if isinstance(publish_record.flow_data_snapshot, str):
                        flow_data = json.loads(publish_record.flow_data_snapshot)
                    else:
                        flow_data = publish_record.flow_data_snapshot
                    
                    logger.info(f"플로우 데이터 조회 성공: {flow_id}")
                    return flow_data
                    
                except json.JSONDecodeError as e:
                    logger.error(f"플로우 데이터 JSON 파싱 실패: {flow_id} - {e}")
                    return None
                
        except Exception as e:
            logger.error(f"플로우 데이터 조회 실패: {flow_id} - {e}")
            return None
    
    def _check_access_permission(
        self, 
        flow_record: Any, 
        user_id: str, 
        user_groups: List[str]
    ) -> bool:
        """
        플로우 실행 권한을 검사합니다.
        
        Args:
            flow_record: FlowStudioFlow 레코드
            user_id: 요청 사용자 ID
            user_groups: 사용자 소속 그룹 ID 리스트
            
        Returns:
            권한이 있으면 True, 없으면 False
        """
        try:
            owner_type = getattr(flow_record, 'owner_type', 'public')
            
            # 공개 플로우인 경우 항상 허용
            if owner_type == 'public':
                logger.debug(f"공개 플로우 접근 허용: {flow_record.id}")
                return True
            
            # 사용자 소유 플로우인 경우
            elif owner_type == 'user':
                flow_user_id = getattr(flow_record, 'user_id', None)
                if flow_user_id == user_id:
                    logger.debug(f"소유자 접근 허용: {flow_record.id}, 사용자: {user_id}")
                    return True
                else:
                    logger.debug(f"소유자 불일치: {flow_record.id}, 플로우 소유자: {flow_user_id}, 요청자: {user_id}")
                    return False
            
            # 그룹 소유 플로우인 경우
            elif owner_type == 'group':
                flow_group_id = getattr(flow_record, 'group_id', None)
                if flow_group_id and str(flow_group_id) in [str(g) for g in user_groups]:
                    logger.debug(f"그룹 접근 허용: {flow_record.id}, 그룹: {flow_group_id}")
                    return True
                else:
                    logger.debug(f"그룹 권한 없음: {flow_record.id}, 플로우 그룹: {flow_group_id}, 사용자 그룹: {user_groups}")
                    return False
            
            # 알 수 없는 owner_type인 경우 기본적으로 거부
            else:
                logger.warning(f"알 수 없는 owner_type: {owner_type}")
                return False
                
        except Exception as e:
            logger.error(f"권한 검사 실패: {e}")
            return False
    
    async def get_flow_metadata(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """
        플로우 메타데이터를 조회합니다.
        
        Args:
            flow_id: 플로우 ID
            
        Returns:
            플로우 메타데이터 딕셔너리 또는 None
        """
        try:
            async with get_async_session() as session:
                # 플로우 기본 정보 조회
                flow_query = select(FlowStudioFlow).where(FlowStudioFlow.id == flow_id)
                flow_result = await session.execute(flow_query)
                flow_record = flow_result.scalar_one_or_none()
                
                if not flow_record:
                    return None
                
                # 최신 게시 정보 조회
                publish_query = (
                    select(FlowStudioPublish)
                    .where(FlowStudioPublish.flow_id == flow_id)
                    .order_by(desc(FlowStudioPublish.created_at))
                    .limit(1)
                )
                
                publish_result = await session.execute(publish_query)
                publish_record = publish_result.scalar_one_or_none()
                
                metadata = {
                    "flow_id": flow_record.id,
                    "name": getattr(flow_record, 'name', ''),
                    "description": getattr(flow_record, 'description', ''),
                    "owner_type": getattr(flow_record, 'owner_type', 'public'),
                    "user_id": getattr(flow_record, 'user_id', None),
                    "group_id": getattr(flow_record, 'group_id', None),
                    "created_at": getattr(flow_record, 'created_at', None),
                    "updated_at": getattr(flow_record, 'updated_at', None),
                    "published": publish_record is not None,
                    "published_at": getattr(publish_record, 'created_at', None) if publish_record else None,
                    "publish_status": getattr(publish_record, 'status', None) if publish_record else None
                }
                
                return metadata
                
        except Exception as e:
            logger.error(f"플로우 메타데이터 조회 실패: {flow_id} - {e}")
            return None
    
    async def list_accessible_flows(
        self, 
        user_id: str, 
        user_groups: List[str], 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        사용자가 접근 가능한 플로우 목록을 조회합니다.
        
        Args:
            user_id: 사용자 ID
            user_groups: 사용자 소속 그룹 ID 리스트
            limit: 반환할 최대 플로우 수
            
        Returns:
            접근 가능한 플로우 목록
        """
        try:
            async with get_async_session() as session:
                # 게시된 플로우 중에서 권한이 있는 것들만 조회
                query = (
                    select(FlowStudioFlow)
                    .join(FlowStudioPublish, FlowStudioFlow.id == FlowStudioPublish.flow_id)
                    .where(FlowStudioPublish.status == 'PUBLISHED')
                    .order_by(desc(FlowStudioFlow.updated_at))
                    .limit(limit)
                )
                
                result = await session.execute(query)
                flows = result.scalars().all()
                
                accessible_flows = []
                for flow in flows:
                    if self._check_access_permission(flow, user_id, user_groups):
                        flow_info = {
                            "flow_id": flow.id,
                            "name": getattr(flow, 'name', ''),
                            "description": getattr(flow, 'description', ''),
                            "owner_type": getattr(flow, 'owner_type', 'public'),
                            "updated_at": getattr(flow, 'updated_at', None)
                        }
                        accessible_flows.append(flow_info)
                
                logger.info(f"접근 가능한 플로우 조회 완료: {len(accessible_flows)}개")
                return accessible_flows
                
        except Exception as e:
            logger.error(f"접근 가능한 플로우 목록 조회 실패: {e}")
            return []


# 싱글턴 인스턴스 생성
flow_provider = FlowProvider() 