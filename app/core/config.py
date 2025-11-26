"""
Application configuration using Pydantic Settings.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = "Tribe"
    app_env: str = "development"
    debug: bool = True
    api_version: str = "v1"
    secret_key: str = "change-this-secret-key-in-production"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database
    database_url: str = "postgresql+asyncpg://tribe_user:tribe_password@localhost:5432/tribe_db"
    db_pool_size: int = 20
    db_max_overflow: int = 10
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_password: Optional[str] = None
    
    # JWT
    jwt_secret_key: str = "change-this-jwt-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    
    # AWS S3
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket: str = "tribe-app-media"
    cloudfront_domain: Optional[str] = None
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    
    # Firebase
    firebase_credentials_path: Optional[str] = None
    
    # Sentry
    sentry_dsn: Optional[str] = None
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 100
    
    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:8080"
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env.lower() == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

