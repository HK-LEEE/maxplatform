"""
Jupyter Platform - 메인 FastAPI 애플리케이션
UUID 기반 사용자 관리 시스템
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 라우터 import
from app.routers import auth, workspace, jupyter, files, llm, service, admin
from app.database import get_db
from app.models import User

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="MAX",
    description="종합 AI 및 데이터분석 플랫폼",
    version="2.0.0"
)

# CORS 설정 - 개발 및 배포 환경 모두 지원
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(workspace.router, prefix="/api", tags=["workspaces"])
app.include_router(jupyter.router, prefix="/api", tags=["jupyter"])
app.include_router(files.router, prefix="/api", tags=["files"])
app.include_router(llm.router, prefix="/api", tags=["llm"])
app.include_router(service.router)
app.include_router(admin.router)

# 기본 라우트
@app.get("/")
async def root():
    return {
        "message": "Jupyter Data Platform API v2.0",
        "docs": "/docs",
        "features": [
            "UUID 기반 사용자 관리",
            "JWT 토큰 인증",
            "역할 기반 접근 제어",
            "워크스페이스 관리",
            "Jupyter Lab/Notebook 통합",
            "파일 업로드/다운로드",
            "단계별 실행 결과 저장"
        ]
    }

# 헬스 체크
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}

# API 정보
@app.get("/api/info")
async def api_info():
    return {
        "api_name": "Jupyter Platform API",
        "version": "2.0.0",
        "user_system": "UUID-based",
        "auth_method": "JWT",
        "database": "MySQL/SQLite",
        "features": {
            "jupyter_integration": True,
            "workspace_management": True,
            "file_management": True,
            "user_authentication": True
        }
    }

if __name__ == "__main__":
    # 환경변수에서 설정값 가져오기
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    ) 