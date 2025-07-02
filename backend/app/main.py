from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

# 먼저 모든 모델을 import하여 테이블 생성 시 인식되도록 함
from .models.user import User, Group, Role
from .models.workspace import Workspace
from .models.service import Service, ServiceCategory, UserServicePermission
from .models.permission import Permission, Feature
from .models.refresh_token import RefreshToken
from .llmops.models import RAGDataSource, Flow, FlowExecution, FlowExecutionLog, Secret
# Flow Studio 모델 추가
from .models.flow_studio import (
    Project, FlowStudioFlow, ComponentTemplate, 
    FlowComponent, FlowConnection, FlowStudioExecution
)
# LLM Chat 모델 추가
from .models.llm_chat import (
    MAXLLM_Persona, MAXLLM_Prompt_Template, MAXLLM_Chat, MAXLLM_Message, 
    MAXLLM_Message_Feedback, MAXLLM_Shared_Chat, MAXLLM_Flow_Publish_Access
)

# 모델 import 후에 database 모듈 import
from .database import create_tables
from .routers import auth, workspace, jupyter, files, llm, service, admin, chroma, llm_chat, oauth_admin
# from .llmops import router as llmops_router  # 임시 비활성화 (chromadb 의존성)
# Flow Studio 라우터 추가
from .routers import flow_studio
# OAuth 2.0 라우터 추가
from .api import oauth_simple

# FastAPI 앱 생성
app = FastAPI(
    title="MAX API",
    description="Manufacturing Artificial Intelligence & DX Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", 
    "http://localhost:3001", 
    "http://127.0.0.1:3000", 
    "http://127.0.0.1:3001", 
    "http://localhost:3005", 
    "http://127.0.0.1:3005",
    "http://localhost:3006",
    "http://127.0.0.1:3006"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모든 모델 import 후 데이터베이스 테이블 생성
create_tables()

# 라우터 추가
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(admin.router, tags=["Admin"])
app.include_router(workspace.router, prefix="/api", tags=["Workspaces"])
app.include_router(jupyter.router, prefix="/api", tags=["Jupyter"])
app.include_router(files.router, prefix="/api", tags=["Files"])
app.include_router(llm.router, prefix="/api/llm", tags=["LLM"])
# app.include_router(llmops_router, tags=["LLMOps"])  # 임시 비활성화 (chromadb 의존성)
app.include_router(service.router)
# Flow Studio 라우터 추가
app.include_router(flow_studio.router, tags=["Flow Studio"])
# ChromaDB 라우터 추가
app.include_router(chroma.router, tags=["ChromaDB"])
# LLM Chat 라우터 추가
app.include_router(llm_chat.router, tags=["LLM Chat"])
# OAuth 2.0 라우터 추가
app.include_router(oauth_simple.router, tags=["OAuth 2.0"])
# OAuth 2.0 관리 라우터 추가
app.include_router(oauth_admin.router, tags=["OAuth Admin"])

# 정적 파일 서빙 (업로드된 파일용)
if not os.path.exists("data"):
    os.makedirs("data")
    
app.mount("/static", StaticFiles(directory="data"), name="static")

@app.get("/")
async def root():
    return {
        "message": "Jupyter Data Platform API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "API가 정상적으로 작동 중입니다."
    }

@app.get("/api/health") 
async def api_health_check():
    return {
        "status": "healthy",
        "message": "API가 정상적으로 작동 중입니다."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 