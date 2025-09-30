"""
애플리케이션 설정 관리
"""
import os
from typing import Set
from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # API 설정
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "super-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # OpenRouter 설정
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "openai/gpt-5-mini"
    OPENROUTER_SITE_URL: str = "http://localhost:3000"
    OPENROUTER_APP_NAME: str = "parsing-graph"
    ALLOWED_MODELS: Set[str] = {
        "openai/gpt-5",      # 고급 기능용 (플래너 등)
        "openai/gpt-5-mini"  # 기본 파싱용
    }
    
    # MCP 서버 설정
    MCP_BASE: str = "http://localhost:8001"
    MCP_TIMEOUT: int = 120
    
    # 데이터베이스 설정
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/parsing_graph"
    REDIS_URL: str = "redis://localhost:6379"
    
    # 파일 저장 설정
    UPLOAD_DIR: str = "uploads"
    OUTPUT_DIR: str = "outputs"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 개발 모드
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # CORS 설정
    ALLOWED_HOSTS: list = ["*"]
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3000",
    ]
    
    # LangGraph 설정
    WINDOW_SIZE: int = 5  # 목차 탐지 윈도우 크기
    MAX_RETRIES: int = 3  # 재시도 횟수
    
    # 모델 validation 제거 - 사용자가 원하는 gpt-5, gpt-5-mini 직접 사용
    # @validator("OPENROUTER_MODEL")
    # def validate_openrouter_model(cls, v, values):
    #     """허용된 OpenRouter 모델만 사용"""
    #     return v
    
    @validator("UPLOAD_DIR", "OUTPUT_DIR")
    def create_directories(cls, v):
        """디렉토리 자동 생성"""
        os.makedirs(v, exist_ok=True)
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 전역 설정 인스턴스
settings = Settings()