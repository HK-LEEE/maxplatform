from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging
from contextlib import asynccontextmanager

# Initialize centralized logging configuration
from .utils.logging_config import setup_logging
from .config import settings

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
from .routers import auth, workspace, jupyter, files, llm, service, admin, chroma, llm_chat, oauth_admin, users, groups, batch_logout
# from .llmops import router as llmops_router  # 임시 비활성화 (chromadb 의존성)
# Flow Studio 라우터 추가
from .routers import flow_studio
# OAuth 2.0 라우터 추가
from .api import oauth_simple, oauth_compatibility, llm_models, security_events
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

# Import background tasks
from .tasks.key_rotation import init_key_rotation_task
from .tasks.nonce_cleanup import init_nonce_cleanup_task

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    main_logger.info("Initializing background tasks...")
    
    # Initialize OIDC background tasks
    init_key_rotation_task()
    init_nonce_cleanup_task()
    
    main_logger.info("Background tasks initialized")
    
    yield
    
    # Shutdown
    main_logger.info("Shutting down background tasks...")

# FastAPI 앱 생성
app = FastAPI(
    title="MAX API",
    description="Manufacturing Artificial Intelligence & DX Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

main_logger.info("MAX Platform backend API starting up")

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # MAX Platform 서비스 URL들
        settings.max_platform_frontend_url,
        settings.max_flowstudio_url,
        settings.max_teamsync_url,
        settings.max_lab_url,
        settings.max_workspace_url,
        settings.max_queryhub_url,
        settings.max_llm_url,
        settings.max_apa_url,
        settings.max_mlops_url,
        # 127.0.0.1 variants for development
        settings.max_platform_frontend_url.replace("localhost", "127.0.0.1"),
        settings.max_flowstudio_url.replace("localhost", "127.0.0.1"),
        settings.max_teamsync_url.replace("localhost", "127.0.0.1"),
        settings.max_lab_url.replace("localhost", "127.0.0.1"),
        settings.max_workspace_url.replace("localhost", "127.0.0.1"),
        settings.max_queryhub_url.replace("localhost", "127.0.0.1"),
        settings.max_llm_url.replace("localhost", "127.0.0.1"),
        settings.max_apa_url.replace("localhost", "127.0.0.1"),
        settings.max_mlops_url.replace("localhost", "127.0.0.1"),
        "http://192.168.15.220",
        "https://maxlab.dwchem.co.kr"
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
app.include_router(oauth_simple.router, prefix="/api/oauth", tags=["OAuth 2.0"])
# OAuth compatibility router (for different logout URL patterns)
app.include_router(oauth_compatibility.router, tags=["OAuth Compatibility"])
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
# 일괄 로그아웃 라우터 추가
app.include_router(batch_logout.router, tags=["Batch Logout"])
app.include_router(batch_logout.user_session_router, tags=["User Sessions"])

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
    #base_url = f"http://localhost:8000"
    base_url = settings.MAX_PLATFORM_API_URL
    
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


@app.get("/.well-known/openid-configuration")
def openid_configuration_root():
    """
    OpenID Connect Discovery Endpoint (Root level)
    Returns OIDC provider configuration
    """

    #base_url = settings.oidc_issuer or settings.max_platform_api_url
    base_url = settings.MAX_PLATFORM_API_URL
    
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/api/oauth/authorize",
        "token_endpoint": f"{base_url}/api/oauth/token",
        "userinfo_endpoint": f"{base_url}/api/oauth/userinfo",
        "jwks_uri": f"{base_url}/api/oauth/jwks",
        "scopes_supported": [
            # OIDC standard scopes
            "openid", "profile", "email", "address", "phone", "offline_access",
            # MAX Platform custom scopes
            "read:profile", "read:features", "read:groups",
            "manage:workflows", "manage:teams", "manage:experiments",
            "manage:workspaces", "manage:apis", "manage:models",
            "groups", "roles",  # Custom OIDC scopes
            # Admin scopes
            "admin:oauth", "admin:users", "admin:system"
        ],
        "response_types_supported": [
            "code",
            "id_token",
            "token id_token",
            "code id_token",
            "code token",
            "code token id_token"
        ],
        "response_modes_supported": ["query", "fragment", "form_post"],
        "grant_types_supported": [
            "authorization_code",
            "implicit",
            "refresh_token",
            "client_credentials"
        ],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256", "HS256"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic",
            "client_secret_jwt",
            "private_key_jwt"
        ],
        "claims_supported": settings.oidc_supported_claims,
        "code_challenge_methods_supported": ["plain", "S256"],
        "introspection_endpoint": f"{base_url}/api/oauth/introspect",
        "revocation_endpoint": f"{base_url}/api/oauth/revoke",
        "claim_types_supported": ["normal"],
        "claims_parameter_supported": False,
        "request_parameter_supported": False,
        "request_uri_parameter_supported": False,
        "require_request_uri_registration": False,
        "check_session_iframe": f"{base_url}/api/oauth/check_session",
        "end_session_endpoint": f"{base_url}/api/oauth/logout",
        "acr_values_supported": ["0", "1"],
        "display_values_supported": ["page", "popup"],
        "prompt_values_supported": ["none", "login", "consent", "select_account"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 