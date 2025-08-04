from pydantic_settings import BaseSettings
from pydantic import ConfigDict
import os
from dotenv import load_dotenv

load_dotenv()

##DB Config 수정점.

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="allow")
    
    # 데이터베이스 타입 및 연결 설정
    database_type: str = os.getenv("DATABASE_TYPE", "postgresql")  # postgresql, mysql, mssql
    #database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:2300@localhost:5432/platform_integration")
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:2300@172.28.32.1:5432/platform_integration")

    # Legacy 호환성 - 기존 설정들은 유지
    mysql_database_url: str = os.getenv("MYSQL_DATABASE_URL", "mysql+pymysql://test:test@localhost:3306/jupyter_platform")
    mssql_database_url: str = os.getenv("MSSQL_DATABASE_URL", "mssql+pyodbc://sa:password@localhost:1433/jupyter_platform?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes")
    
    # Security & JWT Configuration
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # Service Token Configuration
    service_token: str = os.getenv("SERVICE_TOKEN", "")
    service_client_id: str = os.getenv("SERVICE_CLIENT_ID", "maxplatform-service")
    service_client_secret: str = os.getenv("SERVICE_CLIENT_SECRET", "service_maxplatform_2025_dev_secret")
    service_token_expire_hours: int = int(os.getenv("SERVICE_TOKEN_EXPIRE_HOURS", "24"))
    
    # =================
    # MAX Platform URL 설정 (Production 배포용)
    # =================
    # 환경 구분
    max_platform_environment: str = os.getenv("MAX_PLATFORM_ENVIRONMENT", "development")
    
    # 현재 서버 정보
    max_platform_host: str = os.getenv("MAX_PLATFORM_HOST", "0.0.0.0")
    max_platform_port: int = int(os.getenv("MAX_PLATFORM_PORT", "8000"))
    max_platform_api_url: str = os.getenv("MAX_PLATFORM_API_URL", "http://localhost:8000")
    
    # Frontend URL (OAuth 리다이렉트용)
    max_platform_frontend_url: str = os.getenv("MAX_PLATFORM_FRONTEND_URL", "http://localhost:3000")
    
    # MAX Platform 서비스 URL
    max_flowstudio_url: str = os.getenv("MAX_FLOWSTUDIO_URL", "http://localhost:3005")
    max_flowstudio_callback_url: str = os.getenv("MAX_FLOWSTUDIO_CALLBACK_URL", "http://localhost:3005/oauth/callback")
    
    max_teamsync_url: str = os.getenv("MAX_TEAMSYNC_URL", "http://localhost:3015")
    max_teamsync_callback_url: str = os.getenv("MAX_TEAMSYNC_CALLBACK_URL", "http://localhost:3015/oauth/callback")
    
    max_lab_url: str = os.getenv("MAX_LAB_URL", "http://localhost:3010")
    max_lab_callback_url: str = os.getenv("MAX_LAB_CALLBACK_URL", "http://localhost:3010/oauth/callback")
    
    max_workspace_url: str = os.getenv("MAX_WORKSPACE_URL", "http://localhost:3020")
    max_workspace_callback_url: str = os.getenv("MAX_WORKSPACE_CALLBACK_URL", "http://localhost:3020/oauth/callback")
    
    max_apa_url: str = os.getenv("MAX_APA_URL", "http://localhost:3035")
    max_apa_callback_url: str = os.getenv("MAX_APA_CALLBACK_URL", "http://localhost:3035/oauth/callback")
    
    max_mlops_url: str = os.getenv("MAX_MLOPS_URL", "http://localhost:3040")
    max_mlops_callback_url: str = os.getenv("MAX_MLOPS_CALLBACK_URL", "http://localhost:3040/oauth/callback")
    
    max_queryhub_url: str = os.getenv("MAX_QUERYHUB_URL", "http://localhost:3025")
    max_queryhub_callback_url: str = os.getenv("MAX_QUERYHUB_CALLBACK_URL", "http://localhost:3025/oauth/callback")
    
    max_llm_url: str = os.getenv("MAX_LLM_URL", "http://localhost:3030")
    max_llm_callback_url: str = os.getenv("MAX_LLM_CALLBACK_URL", "http://localhost:3030/oauth/callback")

    # Jupyter
    jupyter_base_url: str = os.getenv("JUPYTER_BASE_URL", "http://localhost")
    jupyter_port_start: int = 8888
    jupyter_port_end: int = 9100  # 포트 범위 확장 (8888-9100, 총 212개 포트)
    
    # 워크스페이스 설정
    data_dir: str = os.path.abspath(os.getenv("DATA_DIR", "./data"))
    users_dir: str = os.path.join(data_dir, "users")
    
    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8000
    
    # LLM 설정들
    # Azure OpenAI 설정
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    azure_openai_deployment_name: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    
    # Ollama 설정
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_default_model: str = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2")
    
    # LLM 일반 설정
    default_llm_provider: str = os.getenv("DEFAULT_LLM_PROVIDER", "ollama")  # "azure" 또는 "ollama"
    max_tokens: int = int(os.getenv("MAX_TOKENS", "4000"))
    temperature: float = float(os.getenv("TEMPERATURE", "0.1"))
    
    # Jupyter AI 설정
    ai_default_provider: str = os.getenv("AI_DEFAULT_PROVIDER", "gpt4all")
    ai_default_model: str = os.getenv("AI_DEFAULT_MODEL", "gpt4all:orca-mini-3b-gguf2-q4_0")
    
    # AI API 키들
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    
    # AI 모델 목록 (쉼표로 구분)
    ai_openai_models: str = os.getenv("AI_OPENAI_MODELS", "gpt-3.5-turbo,gpt-4")
    ai_anthropic_models: str = os.getenv("AI_ANTHROPIC_MODELS", "claude-3-sonnet,claude-3-haiku")
    ai_google_models: str = os.getenv("AI_GOOGLE_MODELS", "gemini-pro")
    
    # AI 사용 제한
    ai_max_tokens: int = int(os.getenv("AI_MAX_TOKENS", "1000"))
    ai_temperature: float = float(os.getenv("AI_TEMPERATURE", "0.7"))
    ai_max_chat_history: int = int(os.getenv("AI_MAX_CHAT_HISTORY", "10"))
    ai_enabled_features: str = os.getenv("AI_ENABLED_FEATURES", "chat,completion,learn")
    
    # =================
    # OIDC (OpenID Connect) 설정
    # =================
    # OIDC 발급자 (Issuer)
    oidc_issuer: str = os.getenv("OIDC_ISSUER", max_platform_api_url)
    
    # ID Token 서명 알고리즘
    oidc_signing_algorithm: str = os.getenv("OIDC_SIGNING_ALG", "RS256")
    
    # 키 로테이션 주기 (일)
    oidc_key_rotation_days: int = int(os.getenv("OIDC_KEY_ROTATION_DAYS", "90"))
    
    # ID Token 만료 시간 (분)
    oidc_id_token_expire_minutes: int = int(os.getenv("OIDC_ID_TOKEN_EXPIRE_MINUTES", "60"))
    
    # OIDC 마이그레이션 설정
    oidc_migration_enabled: bool = os.getenv("OIDC_MIGRATION_ENABLED", "true").lower() == "true"
    oidc_dual_mode: bool = os.getenv("OIDC_DUAL_MODE", "true").lower() == "true"  # OAuth 2.0과 OIDC 동시 지원
    oidc_legacy_hs256_support: bool = os.getenv("OIDC_LEGACY_HS256", "true").lower() == "true"  # 전환 기간 동안 HS256 지원
    oidc_migration_grace_period_days: int = int(os.getenv("OIDC_GRACE_PERIOD_DAYS", "90"))
    
    # 지원되는 OIDC Claims
    oidc_supported_claims: list = [
        "sub", "name", "given_name", "family_name", "middle_name", "nickname",
        "preferred_username", "profile", "picture", "website", "gender",
        "birthdate", "zoneinfo", "locale", "updated_at",
        "email", "email_verified", 
        "phone_number", "phone_number_verified",
        "address",
        "groups", "group_id", "group_name",  # MAX Platform custom claims
        "role", "role_id", "role_name", "permissions",  # MAX Platform custom claims
        "is_admin"  # MAX Platform custom claim
    ]
    
    def get_workspace_path(self, user_id, workspace_id: int = None) -> str:
        """워크스페이스 경로 생성 - data/users/{user_id}/{workspace_id} 형태"""
        # UUID 객체를 문자열로 변환
        user_id_str = str(user_id)
        
        if workspace_id is not None:
            return os.path.join(self.users_dir, user_id_str, str(workspace_id))
        else:
            # 호환성을 위해 workspace_id가 없으면 기본 사용자 폴더 반환
            return os.path.join(self.users_dir, user_id_str)

settings = Settings() 