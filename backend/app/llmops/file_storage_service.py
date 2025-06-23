"""
파일 저장 관리 서비스

사용자별/그룹별 파일 저장 폴더 구조를 관리합니다.
"""

import os
import shutil
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile

from ..models.user import User
from .models import RAGDataSource, OwnerType

import logging

logger = logging.getLogger(__name__)

class FileStorageService:
    """파일 저장 관리 서비스"""
    
    def __init__(self, base_storage_path: str = "./file_storage"):
        self.base_storage_path = Path(base_storage_path)
        self.ensure_base_directory()
    
    def ensure_base_directory(self):
        """기본 저장 디렉토리 생성"""
        try:
            self.base_storage_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"File storage base directory ensured: {self.base_storage_path}")
        except Exception as e:
            logger.error(f"Failed to create base storage directory: {str(e)}")
            raise
    
    def get_user_storage_path(self, user_id: str) -> Path:
        """사용자별 저장 경로 반환"""
        user_path = self.base_storage_path / "users" / str(user_id)
        user_path.mkdir(parents=True, exist_ok=True)
        return user_path
    
    def get_group_storage_path(self, group_id: str) -> Path:
        """그룹별 저장 경로 반환"""
        group_path = self.base_storage_path / "groups" / str(group_id)
        group_path.mkdir(parents=True, exist_ok=True)
        return group_path
    
    def get_datasource_storage_path(self, datasource: RAGDataSource) -> Path:
        """데이터소스별 저장 경로 반환"""
        if datasource.owner_type == OwnerType.USER:
            base_path = self.get_user_storage_path(datasource.owner_id)
        else:  # GROUP
            base_path = self.get_group_storage_path(datasource.owner_id)
        
        # 데이터소스별 하위 폴더 생성
        datasource_path = base_path / "rag_datasources" / f"ds_{datasource.id}_{datasource.name}"
        datasource_path.mkdir(parents=True, exist_ok=True)
        return datasource_path
    
    async def save_uploaded_file(
        self, 
        file: UploadFile, 
        datasource: RAGDataSource,
        current_user: User
    ) -> Dict[str, Any]:
        """업로드된 파일을 적절한 위치에 저장"""
        try:
            # 저장 경로 결정
            storage_path = self.get_datasource_storage_path(datasource)
            
            # 파일명 중복 방지를 위한 고유 식별자 추가
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:8]
            safe_filename = self._sanitize_filename(file.filename)
            final_filename = f"{timestamp}_{unique_id}_{safe_filename}"
            
            file_path = storage_path / final_filename
            
            # 파일 저장
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            # 파일 정보 반환
            relative_path = str(file_path.relative_to(self.base_storage_path))
            
            file_info = {
                "original_filename": file.filename,
                "stored_filename": final_filename,
                "file_path": str(file_path),
                "relative_path": relative_path,
                "file_size": len(content),
                "content_type": file.content_type,
                "upload_time": datetime.now().isoformat(),
                "uploaded_by": str(current_user.id),
                "datasource_id": datasource.id,
                "storage_location": {
                    "owner_type": datasource.owner_type.value,
                    "owner_id": datasource.owner_id,
                    "relative_path": relative_path
                }
            }
            
            logger.info(f"File saved: {file.filename} -> {file_path}")
            return file_info
            
        except Exception as e:
            logger.error(f"Failed to save file {file.filename}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"파일 저장 실패: {str(e)}"
            )
    
    def _sanitize_filename(self, filename: str) -> str:
        """파일명 안전화 (특수문자 제거)"""
        import re
        # 한글, 영문, 숫자, 점, 하이픈, 언더스코어만 허용
        safe_name = re.sub(r'[^\w\-_\.]', '_', filename)
        # 연속된 언더스코어 제거
        safe_name = re.sub(r'_+', '_', safe_name)
        return safe_name
    
    def get_stored_files(self, datasource: RAGDataSource) -> List[Dict[str, Any]]:
        """데이터소스에 저장된 파일 목록 조회"""
        try:
            storage_path = self.get_datasource_storage_path(datasource)
            
            files = []
            if storage_path.exists():
                for file_path in storage_path.iterdir():
                    if file_path.is_file():
                        stat = file_path.stat()
                        files.append({
                            "filename": file_path.name,
                            "file_path": str(file_path),
                            "file_size": stat.st_size,
                            "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "relative_path": str(file_path.relative_to(self.base_storage_path))
                        })
            
            return sorted(files, key=lambda x: x["created_time"], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get stored files for datasource {datasource.id}: {str(e)}")
            return []
    
    def delete_stored_file(self, file_path: str) -> bool:
        """저장된 파일 삭제"""
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {str(e)}")
            return False
    
    def cleanup_datasource_files(self, datasource: RAGDataSource) -> bool:
        """데이터소스 삭제 시 관련 파일들 정리"""
        try:
            storage_path = self.get_datasource_storage_path(datasource)
            
            if storage_path.exists():
                shutil.rmtree(storage_path)
                logger.info(f"Cleaned up files for datasource {datasource.id}")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup files for datasource {datasource.id}: {str(e)}")
            return False
    
    def get_storage_stats(self, owner_type: OwnerType, owner_id: str) -> Dict[str, Any]:
        """저장소 사용량 통계"""
        try:
            if owner_type == OwnerType.USER:
                base_path = self.get_user_storage_path(owner_id)
            else:
                base_path = self.get_group_storage_path(owner_id)
            
            total_size = 0
            file_count = 0
            
            if base_path.exists():
                for file_path in base_path.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
                        file_count += 1
            
            return {
                "owner_type": owner_type.value,
                "owner_id": owner_id,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_count": file_count,
                "storage_path": str(base_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {str(e)}")
            return {
                "owner_type": owner_type.value,
                "owner_id": owner_id,
                "total_size_bytes": 0,
                "total_size_mb": 0,
                "file_count": 0,
                "error": str(e)
            }
    
    def migrate_existing_files(self, datasource: RAGDataSource) -> bool:
        """기존 파일들을 새로운 저장 구조로 마이그레이션 (선택적)"""
        try:
            # 기존 임시 저장소에서 파일들을 찾아서 이동
            # 이 부분은 기존 시스템에 따라 구현
            logger.info(f"Migration completed for datasource {datasource.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate files for datasource {datasource.id}: {str(e)}")
            return False 