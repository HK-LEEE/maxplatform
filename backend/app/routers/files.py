import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from ..database import get_db
from ..services.workspace_service import WorkspaceService
from .auth import get_current_user

router = APIRouter(prefix="/files", tags=["Files"])

@router.get("/{workspace_id}/list")
async def list_files(
    workspace_id: int,
    path: str = "",
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """워크스페이스 내 파일 목록 조회"""
    print(f"=== 파일 목록 요청 ===")
    print(f"워크스페이스 ID: {workspace_id}")
    print(f"경로: '{path}'")
    print(f"사용자 ID: {current_user.id}")
    
    workspace_service = WorkspaceService(db)
    workspace = workspace_service.get_workspace_by_id(workspace_id, current_user.id)
    
    if not workspace:
        print(f"워크스페이스를 찾을 수 없음: {workspace_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    print(f"워크스페이스 찾음: {workspace.name}, path: {workspace.path}")
    
    # 워크스페이스 경로가 None이면 디렉토리 생성
    if not workspace.path:
        print("워크스페이스 경로가 None임. 디렉토리 생성 중...")
        from ..utils.workspace import create_workspace_directory
        workspace_path = create_workspace_directory(current_user.id, workspace.id)
        print(f"워크스페이스 디렉토리 생성됨: {workspace_path}")
        # 데이터베이스 업데이트
        workspace.path = workspace_path
        db.commit()
        db.refresh(workspace)
    
    target_path = os.path.join(workspace.path, path) if path else workspace.path
    print(f"대상 경로: {target_path}")
    
    # 경로가 존재하지 않으면 생성
    if not os.path.exists(target_path):
        print(f"경로가 존재하지 않음. 생성 중: {target_path}")
        try:
            os.makedirs(target_path, exist_ok=True)
            print(f"경로 생성 성공: {target_path}")
        except Exception as e:
            print(f"경로 생성 실패: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create directory: {str(e)}"
            )
    else:
        print(f"경로가 이미 존재함: {target_path}")
    
    files = []
    try:
        for item in os.listdir(target_path):
            item_path = os.path.join(target_path, item)
            is_dir = os.path.isdir(item_path)
            size = os.path.getsize(item_path) if not is_dir else 0
            
            files.append({
                "name": item,
                "is_directory": is_dir,
                "size": size,
                "path": os.path.join(path, item) if path else item
            })
        
        print(f"파일 목록 반환: {len(files)}개 항목")
        return {"files": files, "current_path": path}
    except Exception as e:
        print(f"파일 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list directory: {str(e)}"
        )

@router.post("/{workspace_id}/upload")
async def upload_file(
    workspace_id: int,
    path: str = "",
    files: List[UploadFile] = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """파일 업로드"""
    workspace_service = WorkspaceService(db)
    workspace = workspace_service.get_workspace_by_id(workspace_id, current_user.id)
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # 워크스페이스 경로가 None이면 디렉토리 생성
    if not workspace.path:
        from ..utils.workspace import create_workspace_directory
        workspace_path = create_workspace_directory(current_user.id, workspace.id)
        # 데이터베이스 업데이트
        workspace.path = workspace_path
        db.commit()
        db.refresh(workspace)
    
    upload_path = os.path.join(workspace.path, path) if path else workspace.path
    
    # 경로가 존재하지 않으면 생성
    if not os.path.exists(upload_path):
        try:
            os.makedirs(upload_path, exist_ok=True)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create upload directory: {str(e)}"
            )
    
    uploaded_files = []
    
    for file in files:
        file_path = os.path.join(upload_path, file.filename)
        
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            uploaded_files.append({
                "filename": file.filename,
                "size": len(content),
                "path": os.path.join(path, file.filename) if path else file.filename
            })
        
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload {file.filename}: {str(e)}"
            )
    
    return {"message": "Files uploaded successfully", "files": uploaded_files}

@router.get("/{workspace_id}/download")
async def download_file(
    workspace_id: int,
    file_path: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """파일 다운로드"""
    workspace_service = WorkspaceService(db)
    workspace = workspace_service.get_workspace_by_id(workspace_id, current_user.id)
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # 워크스페이스 경로가 None이면 디렉토리 생성
    if not workspace.path:
        from ..utils.workspace import create_workspace_directory
        workspace_path = create_workspace_directory(current_user.id, workspace.id)
        workspace.path = workspace_path
        db.commit()
        db.refresh(workspace)
    
    full_path = os.path.join(workspace.path, file_path)
    
    if not os.path.exists(full_path) or os.path.isdir(full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    filename = os.path.basename(full_path)
    return FileResponse(
        path=full_path,
        filename=filename,
        media_type='application/octet-stream'
    )

@router.delete("/{workspace_id}/delete")
async def delete_file(
    workspace_id: int,
    file_path: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """파일/폴더 삭제"""
    workspace_service = WorkspaceService(db)
    workspace = workspace_service.get_workspace_by_id(workspace_id, current_user.id)
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # 워크스페이스 경로가 None이면 디렉토리 생성
    if not workspace.path:
        from ..utils.workspace import create_workspace_directory
        workspace_path = create_workspace_directory(current_user.id, workspace.id)
        workspace.path = workspace_path
        db.commit()
        db.refresh(workspace)
    
    full_path = os.path.join(workspace.path, file_path)
    
    if not os.path.exists(full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File or directory not found"
        )
    
    try:
        if os.path.isdir(full_path):
            import shutil
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        
        return {"message": "File deleted successfully"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )

@router.post("/{workspace_id}/create-folder")
async def create_folder(
    workspace_id: int,
    folder_name: str,
    path: str = "",
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """폴더 생성"""
    workspace_service = WorkspaceService(db)
    workspace = workspace_service.get_workspace_by_id(workspace_id, current_user.id)
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # 워크스페이스 경로가 None이면 디렉토리 생성
    if not workspace.path:
        from ..utils.workspace import create_workspace_directory
        workspace_path = create_workspace_directory(current_user.id, workspace.id)
        workspace.path = workspace_path
        db.commit()
        db.refresh(workspace)
    
    parent_path = os.path.join(workspace.path, path) if path else workspace.path
    
    # 부모 경로가 존재하지 않으면 생성
    if not os.path.exists(parent_path):
        try:
            os.makedirs(parent_path, exist_ok=True)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create parent directory: {str(e)}"
            )
    
    folder_path = os.path.join(parent_path, folder_name)
    
    if os.path.exists(folder_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Folder already exists"
        )
    
    try:
        os.makedirs(folder_path)
        return {"message": "Folder created successfully", "path": os.path.join(path, folder_name) if path else folder_name}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create folder: {str(e)}"
        ) 