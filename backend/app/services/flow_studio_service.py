import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.flow_studio import (
    Project, FlowStudioFlow, ComponentTemplate, FlowComponent, 
    FlowConnection, FlowStudioExecution, FlowStudioPublish, PublishStatus
)
from ..schemas.flow_studio import (
    ProjectCreate, ProjectUpdate, FlowCreate, FlowUpdate,
    ComponentTemplateCreate, FlowComponentCreate, FlowComponentUpdate,
    FlowConnectionCreate, FlowExecutionCreate, FlowSaveRequest,
    FlowPublishRequest, FlowPublishResponse, ProjectResponse, FlowResponse
)

logger = logging.getLogger(__name__)

class FlowStudioService:
    """Flow Studio 서비스 클래스 - 권한 기반 접근 제어 포함"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _get_user_access_filter(self, user_info: dict):
        """사용자 접근 권한에 따른 필터 조건 생성"""
        user_id = user_info["user_id"]
        group_id = user_info.get("group_id")
        
        # 개인 프로젝트 조건
        personal_condition = and_(
            Project.owner_type == "user",
            Project.user_id == user_id
        )
        
        # 그룹 프로젝트 조건 (사용자가 그룹에 속한 경우만)
        if group_id:
            group_condition = and_(
                Project.owner_type == "group",
                Project.group_id == group_id
            )
            return or_(personal_condition, group_condition)
        else:
            return personal_condition
    
    # ==================== Project 관련 메서드 ====================
    
    async def get_projects(self, user_info: dict, skip: int = 0, limit: int = 100) -> List[ProjectResponse]:
        """사용자의 프로젝트 목록 조회 (권한 기반)"""
        try:
            access_filter = self._get_user_access_filter(user_info)
            
            projects = self.db.query(Project)\
                .filter(access_filter)\
                .offset(skip).limit(limit)\
                .all()
            
            # ORM 객체를 Pydantic 스키마로 명시적 변환
            project_responses = []
            for project in projects:
                project_response = ProjectResponse.model_validate(project)
                project_responses.append(project_response)
            
            logger.info(f"프로젝트 {len(projects)}개 조회 완료 - 사용자: {user_info['user_id']}")
            return project_responses
        except Exception as e:
            logger.error(f"프로젝트 목록 조회 실패: {e}")
            raise
    
    async def get_project_by_id(self, project_id: str, user_info: dict) -> Optional[ProjectResponse]:
        """프로젝트 단일 조회 (권한 확인)"""
        try:
            access_filter = self._get_user_access_filter(user_info)
            
            project = self.db.query(Project)\
                .filter(and_(Project.id == project_id, access_filter))\
                .first()
            
            if project:
                logger.info(f"프로젝트 조회 완료: {project_id}")
                return ProjectResponse.model_validate(project)
            else:
                logger.warning(f"프로젝트 접근 권한 없음 또는 존재하지 않음: {project_id}")
                return None
        except Exception as e:
            logger.error(f"프로젝트 조회 실패: {e}")
            raise
    
    async def create_project(self, user_info: dict, project_data: ProjectCreate) -> ProjectResponse:
        """프로젝트 생성 (그룹 정보 포함)"""
        try:
            user_id = user_info["user_id"]
            
            # 기본 프로젝트인 경우 기존 기본 프로젝트 해제
            if project_data.is_default:
                await self._unset_default_projects(user_info)
            
            # 프로젝트 데이터 준비
            project_dict = project_data.model_dump()
            
            # 소유자 정보 설정
            if hasattr(project_data, 'owner_type') and project_data.owner_type == "group":
                # 그룹 소유 프로젝트
                if not user_info.get("group_id"):
                    raise ValueError("그룹 프로젝트를 생성하려면 사용자가 그룹에 속해야 합니다.")
                project_dict.update({
                    "user_id": user_id,
                    "group_id": user_info["group_id"],
                    "owner_type": "group"
                })
                logger.info(f"그룹 프로젝트 생성 - 그룹: {user_info['group_name']} ({user_info['group_id']})")
            else:
                # 개인 소유 프로젝트
                project_dict.update({
                    "user_id": user_id,
                    "group_id": None,
                    "owner_type": "user"
                })
                logger.info(f"개인 프로젝트 생성 - 사용자: {user_id}")
            
            project = Project(**project_dict)
            self.db.add(project)
            self.db.commit()
            self.db.refresh(project)
            
            logger.info(f"프로젝트 생성 완료: {project.id} - {project.name} (소유자: {project.owner_type})")
            return ProjectResponse.model_validate(project)
        except Exception as e:
            self.db.rollback()
            logger.error(f"프로젝트 생성 실패: {e}")
            raise
    
    async def update_project(self, project_id: str, user_info: dict, 
                           project_data: ProjectUpdate) -> Optional[ProjectResponse]:
        """프로젝트 수정 (권한 확인)"""
        try:
            project_response = await self.get_project_by_id(project_id, user_info)
            if not project_response:
                return None
            
            # ORM 객체 다시 조회 (수정을 위해)
            access_filter = self._get_user_access_filter(user_info)
            project = self.db.query(Project)\
                .filter(and_(Project.id == project_id, access_filter))\
                .first()
            
            if not project:
                return None
            
            # 기본 프로젝트 설정 시 기존 기본 프로젝트 해제
            if project_data.is_default:
                await self._unset_default_projects(user_info)
            
            update_data = project_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(project, field, value)
            
            project.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(project)
            
            logger.info(f"프로젝트 수정 완료: {project_id}")
            return ProjectResponse.model_validate(project)
        except Exception as e:
            self.db.rollback()
            logger.error(f"프로젝트 수정 실패: {e}")
            raise
    
    async def delete_project(self, project_id: str, user_info: dict) -> bool:
        """프로젝트 삭제 (권한 확인)"""
        try:
            project = await self.get_project_by_id(project_id, user_info)
            if not project:
                return False
            
            self.db.delete(project)
            self.db.commit()
            
            logger.info(f"프로젝트 삭제 완료: {project_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"프로젝트 삭제 실패: {e}")
            raise
    
    async def _unset_default_projects(self, user_info: dict):
        """사용자의 기본 프로젝트 해제 (권한 기반)"""
        access_filter = self._get_user_access_filter(user_info)
        
        self.db.query(Project)\
            .filter(and_(access_filter, Project.is_default == True))\
            .update({Project.is_default: False})
    
    # ==================== Flow 관련 메서드 ====================
    
    async def get_flows(self, project_id: str, user_info: dict, 
                       skip: int = 0, limit: int = 100) -> List[FlowResponse]:
        """프로젝트의 플로우 목록 조회 (권한 확인)"""
        try:
            # 프로젝트 소유권 확인
            project = await self.get_project_by_id(project_id, user_info)
            if not project:
                logger.warning(f"프로젝트 접근 권한 없음: {project_id}")
                return []
            
            flows = self.db.query(FlowStudioFlow)\
                .filter(FlowStudioFlow.project_id == project_id)\
                .offset(skip).limit(limit)\
                .all()
            
            # ORM 객체를 Pydantic 스키마로 명시적 변환
            flow_responses = []
            for flow in flows:
                flow_response = FlowResponse.model_validate(flow)
                flow_responses.append(flow_response)
            
            logger.info(f"플로우 {len(flows)}개 조회 완료 - 프로젝트: {project_id}")
            return flow_responses
        except Exception as e:
            logger.error(f"플로우 목록 조회 실패: {e}")
            raise
    
    async def get_flow_by_id(self, flow_id: str, user_info: dict) -> Optional[FlowStudioFlow]:
        """플로우 단일 조회 (소유권 확인)"""
        try:
            access_filter = self._get_user_access_filter(user_info)
            
            flow = self.db.query(FlowStudioFlow)\
                .join(Project)\
                .filter(and_(FlowStudioFlow.id == flow_id, access_filter))\
                .first()
            
            if flow:
                logger.info(f"플로우 조회 완료: {flow_id}")
            else:
                logger.warning(f"플로우 접근 권한 없음 또는 존재하지 않음: {flow_id}")
            return flow
        except Exception as e:
            logger.error(f"플로우 조회 실패: {e}")
            raise
    
    async def create_flow(self, user_info: dict, flow_data: FlowCreate) -> Optional[FlowStudioFlow]:
        """플로우 생성 (권한 확인)"""
        try:
            # 프로젝트 소유권 확인
            project = await self.get_project_by_id(flow_data.project_id, user_info)
            if not project:
                logger.warning(f"프로젝트 접근 권한 없음: {flow_data.project_id}")
                return None
            
            # 플로우 데이터 준비
            flow_dict = flow_data.model_dump()
            user_id = user_info["user_id"]
            
            # 권한 정보 설정
            if hasattr(flow_data, 'owner_type') and flow_data.owner_type == "group":
                # 그룹 소유 플로우
                if not user_info.get("group_id"):
                    raise ValueError("그룹 플로우를 생성하려면 사용자가 그룹에 속해야 합니다.")
                flow_dict.update({
                    "user_id": user_id,
                    "group_id": user_info["group_id"],
                    "owner_type": "group"
                })
                logger.info(f"그룹 플로우 생성 - 그룹: {user_info['group_name']} ({user_info['group_id']})")
            else:
                # 개인 소유 플로우
                flow_dict.update({
                    "user_id": user_id,
                    "group_id": None,
                    "owner_type": "user"
                })
                logger.info(f"개인 플로우 생성 - 사용자: {user_id}")
            
            flow = FlowStudioFlow(**flow_dict)
            self.db.add(flow)
            self.db.commit()
            self.db.refresh(flow)
            
            logger.info(f"플로우 생성 완료: {flow.id} - {flow.name} (프로젝트: {project.name}, 소유자: {flow.owner_type})")
            return flow
        except Exception as e:
            self.db.rollback()
            logger.error(f"플로우 생성 실패: {e}")
            raise
    
    async def update_flow(self, flow_id: str, user_info: dict, 
                         flow_data: FlowUpdate) -> Optional[FlowStudioFlow]:
        """플로우 수정 (권한 확인)"""
        try:
            flow = await self.get_flow_by_id(flow_id, user_info)
            if not flow:
                return None
            
            update_data = flow_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(flow, field, value)
            
            flow.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(flow)
            
            logger.info(f"플로우 수정 완료: {flow_id}")
            return flow
        except Exception as e:
            self.db.rollback()
            logger.error(f"플로우 수정 실패: {e}")
            raise
    
    async def delete_flow(self, flow_id: str, user_info: dict) -> bool:
        """플로우 삭제 (권한 확인)"""
        try:
            flow = await self.get_flow_by_id(flow_id, user_info)
            if not flow:
                return False
            
            self.db.delete(flow)
            self.db.commit()
            
            logger.info(f"플로우 삭제 완료: {flow_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"플로우 삭제 실패: {e}")
            raise
    
    # ==================== Component Template 관련 메서드 ====================
    
    async def get_component_templates(self, category: Optional[str] = None,
                                    skip: int = 0, limit: int = 100) -> List[ComponentTemplate]:
        """컴포넌트 템플릿 목록 조회 (공용 리소스)"""
        try:
            query = self.db.query(ComponentTemplate)
            if category:
                query = query.filter(ComponentTemplate.category == category)
            
            templates = query.offset(skip).limit(limit).all()
            logger.info(f"컴포넌트 템플릿 {len(templates)}개 조회 완료")
            return templates
        except Exception as e:
            logger.error(f"컴포넌트 템플릿 목록 조회 실패: {e}")
            raise
    
    async def create_component_template(self, template_data: ComponentTemplateCreate) -> ComponentTemplate:
        """컴포넌트 템플릿 생성"""
        try:
            template = ComponentTemplate(**template_data.model_dump())
            self.db.add(template)
            self.db.commit()
            self.db.refresh(template)
            
            logger.info(f"컴포넌트 템플릿 생성 완료: {template.id} - {template.name}")
            return template
        except Exception as e:
            self.db.rollback()
            logger.error(f"컴포넌트 템플릿 생성 실패: {e}")
            raise
    
    # ==================== 통계 관련 메서드 ====================
    
    async def get_flow_studio_stats(self, user_info: dict) -> Dict[str, int]:
        """Flow Studio 통계 조회 (권한 기반)"""
        try:
            access_filter = self._get_user_access_filter(user_info)
            
            # 접근 가능한 프로젝트 수
            total_projects = self.db.query(Project).filter(access_filter).count()
            
            # 접근 가능한 활성 플로우 수
            active_flows = self.db.query(FlowStudioFlow)\
                .join(Project)\
                .filter(and_(access_filter, FlowStudioFlow.is_active == True))\
                .count()
            
            # 총 실행 수 (사용자 기준)
            total_executions = self.db.query(FlowStudioExecution)\
                .filter(FlowStudioExecution.user_id == user_info["user_id"])\
                .count()
            
            stats = {
                "total_projects": total_projects,
                "active_flows": active_flows,
                "total_executions": total_executions
            }
            
            logger.info(f"Flow Studio 통계 조회 완료 - 사용자: {user_info['user_id']}")
            return stats
        except Exception as e:
            logger.error(f"Flow Studio 통계 조회 실패: {e}")
            raise
    
    # ==================== RAG 데이터소스 권한 관련 메서드 ====================
    
    async def get_accessible_rag_datasources(self, user_info: dict) -> List[Dict[str, Any]]:
        """사용자가 접근 가능한 RAG 데이터소스 목록 조회"""
        try:
            from ..llmops.models import RAGDataSource, OwnerType
            
            user_id = user_info["user_id"]
            group_id = user_info.get("group_id")
            
            # 개인 데이터소스 조건
            personal_condition = and_(
                RAGDataSource.owner_type == OwnerType.USER,
                RAGDataSource.owner_id == user_id
            )
            
            # 그룹 데이터소스 조건 (사용자가 그룹에 속한 경우만)
            if group_id:
                group_condition = and_(
                    RAGDataSource.owner_type == OwnerType.GROUP,
                    RAGDataSource.owner_id == group_id
                )
                access_filter = or_(personal_condition, group_condition)
            else:
                access_filter = personal_condition
            
            datasources = self.db.query(RAGDataSource)\
                .filter(and_(access_filter, RAGDataSource.is_active == True))\
                .all()
            
            # 응답 형식으로 변환
            result = []
            for ds in datasources:
                result.append({
                    "id": ds.id,
                    "name": ds.name,
                    "description": ds.description,
                    "owner_type": ds.owner_type.value,
                    "document_count": ds.document_count,
                    "created_at": ds.created_at
                })
            
            logger.info(f"접근 가능한 RAG 데이터소스 {len(result)}개 조회 완료 - 사용자: {user_id}")
            return result
        except Exception as e:
            logger.error(f"RAG 데이터소스 목록 조회 실패: {e}")
            raise
    
    async def save_flow_with_project(self, user_info: dict, save_request: FlowSaveRequest) -> Dict[str, Any]:
        """플로우 저장 (프로젝트 자동 생성 포함)"""
        try:
            from ..schemas.flow_studio import FlowSaveRequest, ProjectCreate, FlowCreate
            
            user_id = user_info["user_id"]
            project = None
            
            # 기존 프로젝트 사용 또는 새 프로젝트 생성
            if save_request.project_id:
                # 기존 프로젝트 사용
                project = await self.get_project_by_id(save_request.project_id, user_info)
                if not project:
                    raise ValueError("프로젝트를 찾을 수 없거나 접근 권한이 없습니다.")
            else:
                # 새 프로젝트 생성
                project_name = f"{save_request.name} Project"
                project_data = ProjectCreate(
                    name=project_name,
                    description=f"{save_request.name} 플로우를 위한 프로젝트",
                    owner_type=save_request.owner_type,
                    is_default=False
                )
                project = await self.create_project(user_info, project_data)
                if not project:
                    raise ValueError("프로젝트 생성에 실패했습니다.")
            
            # 플로우 생성
            flow_data = FlowCreate(
                project_id=project.id,
                name=save_request.name,
                description=save_request.description,
                flow_data=save_request.flow_data,
                owner_type=save_request.owner_type,
                is_active=True
            )
            
            flow = await self.create_flow(user_info, flow_data)
            if not flow:
                raise ValueError("플로우 생성에 실패했습니다.")
            
            logger.info(f"플로우 저장 완료: {flow.name} (프로젝트: {project.name})")
            
            return {
                "success": True,
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "owner_type": project.owner_type
                },
                "flow": {
                    "id": flow.id,
                    "name": flow.name,
                    "owner_type": flow.owner_type,
                    "created_at": flow.created_at
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"플로우 저장 실패: {e}")
            raise
    
    # ==================== Publish 관련 메서드 ====================
    
    async def publish_flow(self, flow_id: str, user_info: dict, 
                          publish_request: FlowPublishRequest) -> Optional[FlowPublishResponse]:
        """플로우 배포"""
        try:
            # 플로우 권한 확인
            flow = await self.get_flow_by_id(flow_id, user_info)
            if not flow:
                logger.warning(f"플로우 접근 권한 없음 또는 존재하지 않음: {flow_id}")
                return None
            
            # 버전 처리
            if publish_request.version:
                new_version = publish_request.version
            else:
                # 자동 버전 증가 (마지막 배포 버전 기준)
                last_publish = self.db.query(FlowStudioPublish)\
                    .filter(FlowStudioPublish.flow_id == flow_id)\
                    .order_by(FlowStudioPublish.published_at.desc())\
                    .first()
                
                if last_publish:
                    # 기존 버전에서 마이너 버전 증가
                    try:
                        major, minor, patch = last_publish.version.split('.')
                        new_version = f"{major}.{int(minor) + 1}.0"
                    except:
                        new_version = "1.1.0"
                else:
                    new_version = "1.0.0"
            
            # 기존 최신 배포 버전 해제
            self.db.query(FlowStudioFlow)\
                .filter(and_(
                    FlowStudioFlow.project_id == flow.project_id,
                    FlowStudioFlow.is_latest_published == True
                ))\
                .update({FlowStudioFlow.is_latest_published: False})
            
            # 플로우 상태 업데이트
            flow.publish_status = PublishStatus.PUBLISHED
            flow.version = new_version
            flow.is_latest_published = True
            flow.updated_at = datetime.utcnow()
            
            # 배포 이력 생성
            publish_record = FlowStudioPublish(
                flow_id=flow_id,
                version=new_version,
                publish_status=PublishStatus.PUBLISHED,
                published_by=user_info["user_id"],
                publish_message=publish_request.publish_message,
                flow_data_snapshot=flow.flow_data,
                target_environment=publish_request.target_environment,
                deployment_config=publish_request.deployment_config,
                webhook_url=None,  # 추후 설정
                webhook_called=False
            )
            
            self.db.add(publish_record)
            self.db.commit()
            self.db.refresh(publish_record)
            
            # LLMOps 시스템에 웹훅 호출
            webhook_response = await self._call_llmops_webhook(flow, publish_record, user_info)
            
            # 웹훅 응답 업데이트
            if webhook_response:
                publish_record.webhook_called = True
                publish_record.webhook_response = webhook_response
                self.db.commit()
            
            logger.info(f"플로우 배포 완료: {flow_id} v{new_version}")
            
            return FlowPublishResponse(
                id=publish_record.id,
                flow_id=flow_id,
                version=new_version,
                publish_status=PublishStatus.PUBLISHED,
                published_by=user_info["user_id"],
                publish_message=publish_request.publish_message,
                target_environment=publish_request.target_environment,
                webhook_called=publish_record.webhook_called,
                webhook_response=webhook_response,
                published_at=publish_record.published_at
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"플로우 배포 실패: {e}")
            raise
    
    async def unpublish_flow(self, flow_id: str, user_info: dict) -> bool:
        """플로우 배포 해제 (DEPRECATED 상태로 변경)"""
        try:
            flow = await self.get_flow_by_id(flow_id, user_info)
            if not flow:
                return False
            
            if flow.publish_status != PublishStatus.PUBLISHED:
                logger.warning(f"배포되지 않은 플로우입니다: {flow_id}")
                return False
            
            # 플로우 상태 업데이트
            flow.publish_status = PublishStatus.DEPRECATED
            flow.is_latest_published = False
            flow.updated_at = datetime.utcnow()
            
            # 배포 이력에 사용 중단 시간 기록
            latest_publish = self.db.query(FlowStudioPublish)\
                .filter(and_(
                    FlowStudioPublish.flow_id == flow_id,
                    FlowStudioPublish.publish_status == PublishStatus.PUBLISHED
                ))\
                .order_by(FlowStudioPublish.published_at.desc())\
                .first()
            
            if latest_publish:
                latest_publish.publish_status = PublishStatus.DEPRECATED
                latest_publish.deprecated_at = datetime.utcnow()
            
            self.db.commit()
            
            # LLMOps 시스템에 배포 해제 웹훅 호출
            await self._call_llmops_unpublish_webhook(flow, user_info)
            
            logger.info(f"플로우 배포 해제 완료: {flow_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"플로우 배포 해제 실패: {e}")
            raise
    
    async def get_publish_history(self, flow_id: str, user_info: dict, 
                                 skip: int = 0, limit: int = 20) -> List[FlowStudioPublish]:
        """플로우 배포 이력 조회"""
        try:
            # 플로우 권한 확인
            flow = await self.get_flow_by_id(flow_id, user_info)
            if not flow:
                return []
            
            publish_history = self.db.query(FlowStudioPublish)\
                .filter(FlowStudioPublish.flow_id == flow_id)\
                .order_by(FlowStudioPublish.published_at.desc())\
                .offset(skip).limit(limit)\
                .all()
            
            logger.info(f"플로우 배포 이력 {len(publish_history)}개 조회 완료: {flow_id}")
            return publish_history
            
        except Exception as e:
            logger.error(f"플로우 배포 이력 조회 실패: {e}")
            raise
    
    async def _call_llmops_webhook(self, flow: FlowStudioFlow, publish_record: FlowStudioPublish, 
                                  user_info: dict) -> Optional[Dict[str, Any]]:
        """LLMOps 시스템에 배포 웹훅 호출"""
        try:
            import httpx
            import os
            
            # 웹훅 URL 구성
            llmops_base_url = os.getenv('LLMOPS_API_BASE_URL', 'http://localhost:8000')
            webhook_url = f"{llmops_base_url}/api/llmops/admin/reload-flow/{flow.project_id}/{flow.id}"
            
            # 웹훅 데이터
            webhook_data = {
                "reason": f"Flow published: v{publish_record.version}",
                "force": False,
                "flow_data": publish_record.flow_data_snapshot,
                "version": publish_record.version,
                "published_by": user_info.get("username", user_info["user_id"]),
                "environment": publish_record.target_environment
            }
            
            # 관리자 API 키
            admin_api_key = os.getenv('LLMOPS_ADMIN_API_KEY', 'admin-super-secret-key-2024')
            
            headers = {
                "X-Admin-API-Key": admin_api_key,
                "Content-Type": "application/json"
            }
            
            # 웹훅 호출
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=webhook_data,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"LLMOps 웹훅 호출 성공: {webhook_url}")
                    return result
                else:
                    logger.error(f"LLMOps 웹훅 호출 실패: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"LLMOps 웹훅 호출 중 오류: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _call_llmops_unpublish_webhook(self, flow: FlowStudioFlow, user_info: dict):
        """LLMOps 시스템에 배포 해제 웹훅 호출"""
        try:
            import httpx
            import os
            
            # 웹훅 URL 구성 (배포 해제는 동일한 엔드포인트 사용)
            llmops_base_url = os.getenv('LLMOPS_API_BASE_URL', 'http://localhost:8000')
            webhook_url = f"{llmops_base_url}/api/llmops/admin/reload-flow/{flow.project_id}/{flow.id}"
            
            webhook_data = {
                "reason": "Flow unpublished (deprecated)",
                "force": True  # 강제로 워커 종료
            }
            
            admin_api_key = os.getenv('LLMOPS_ADMIN_API_KEY', 'admin-super-secret-key-2024')
            headers = {
                "X-Admin-API-Key": admin_api_key,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=webhook_data,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    logger.info(f"LLMOps 배포 해제 웹훅 호출 성공: {webhook_url}")
                else:
                    logger.warning(f"LLMOps 배포 해제 웹훅 호출 실패: {response.status_code}")
                    
        except Exception as e:
            logger.warning(f"LLMOps 배포 해제 웹훅 호출 중 오류 (무시됨): {e}") 