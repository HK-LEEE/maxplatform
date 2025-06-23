from pydantic_settings import BaseSettings
from pydantic import ConfigDict
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="allow")
    
    # 데이터베이스 타입 및 연결 설정
    database_type: str = os.getenv("DATABASE_TYPE", "postgresql")  # postgresql, mysql, mssql
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:2300@localhost:5432/platform_integration")
    
    # Legacy 호환성 - 기존 설정들은 유지
    mysql_database_url: str = os.getenv("MYSQL_DATABASE_URL", "mysql+pymysql://test:test@localhost:3306/jupyter_platform")
    mssql_database_url: str = os.getenv("MSSQL_DATABASE_URL", "mssql+pyodbc://sa:password@localhost:1433/jupyter_platform?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes")
    
    # Security & JWT Configuration
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
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