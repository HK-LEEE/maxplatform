from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging

# Initialize centralized logging configuration
from .utils.logging_config import setup_logging

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
    MAXLLM_Message_Feedback, MAXLLM_Shared_Chat, MAXLLM_Flow_Publish_Access,
    MAXLLM_Model, MAXLLM_Model_Permission
)
# Security Event 모델 추가
from .models.security_event import (
    SecurityEvent, SecurityThreatRule, SecurityAlert, 
    SecurityBlockedIP, SecurityStatistics
)

# 모델 import 후에 database 모듈 import
from .database import create_tables
from .routers import auth, workspace, jupyter, files, llm, service, admin, chroma, llm_chat, oauth_admin, users, groups
# from .llmops import router as llmops_router  # 임시 비활성화 (chromadb 의존성)
# Flow Studio 라우터 추가
from .routers import flow_studio
# OAuth 2.0 라우터 추가
from .api import oauth_simple, llm_models, security_events
# Group Tree 라우터 추가
from .routers import group_tree

# Setup logging configuration with daily rotation
setup_logging(
    log_file="./logs/backend",  # Will be expanded to backend_YYYY_MM_DD.log
    backup_count=10,  # Keep 10 days of logs
    use_daily_rotation=True  # Use daily rotation instead of size-based
)

# Get the main application logger
main_logger = logging.getLogger("app.main")

# FastAPI 앱 생성
app = FastAPI(
    title="MAX API",
    description="Manufacturing Artificial Intelligence & DX Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

main_logger.info("MAX Platform backend API starting up")

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # 기본 프론트엔드
        "http://localhost:3000", 
        "http://localhost:3001", 
        "http://127.0.0.1:3000", 
        "http://127.0.0.1:3001", 
        "http://localhost:3005", 
        "http://127.0.0.1:3005",
        "http://localhost:3006",
        "http://127.0.0.1:3006",
        # OAuth 클라이언트 포트들
        "http://localhost:3010",  # maxlab
        "http://localhost:3015",  # maxteamsync
        "http://localhost:3020",  # maxworkspace
        "http://localhost:3025",  # maxqueryhub
        "http://localhost:3030",  # maxllm
        "http://localhost:3035",  # maxapa
        "http://localhost:3040",  # maxmlops
        "http://127.0.0.1:3010",  # maxlab
        "http://127.0.0.1:3015",  # maxteamsync
        "http://127.0.0.1:3020",  # maxworkspace
        "http://127.0.0.1:3025",  # maxqueryhub
        "http://127.0.0.1:3030",  # maxllm
        "http://127.0.0.1:3035",  # maxapa
        "http://127.0.0.1:3040",  # maxmlops
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모든 모델 import 후 데이터베이스 테이블 생성
main_logger.info("Creating database tables")
create_tables()
main_logger.info("Database tables created successfully")

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
# LLM 모델 관리 라우터 추가
app.include_router(llm_models.router, tags=["LLM Models"])
# 보안 이벤트 라우터 추가
app.include_router(security_events.router, tags=["Security Events"])
# 그룹 트리 라우터 추가
app.include_router(group_tree.router, tags=["Group Tree"])
# 사용자 및 그룹 API 라우터 추가 (OAuth 표준 준수)
app.include_router(users.router)
app.include_router(groups.router)

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

@app.get("/.well-known/oauth-authorization-server")
def oauth_metadata_root():
    """
    OAuth 2.0 Authorization Server Metadata (Root level)
    RFC 8414 compliant metadata endpoint
    """
    base_url = f"http://localhost:8000"
    
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/api/oauth/authorize",
        "token_endpoint": f"{base_url}/api/oauth/token",
        "userinfo_endpoint": f"{base_url}/api/oauth/userinfo",
        "revocation_endpoint": f"{base_url}/api/oauth/revoke",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
        "revocation_endpoint_auth_methods_supported": ["client_secret_post"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "scopes_supported": [
            "read:profile",
            "read:features", 
            "read:groups",
            "manage:workflows",
            "manage:teams",
            "manage:experiments",
            "manage:workspaces",
            "manage:apis",
            "manage:models"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 