"""
Application configuration using Pydantic Settings
"""
import os
from typing import Any, Dict, List, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # App
    APP_NAME: str = "Universal Bot OS"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "*",  # Allow all in development
        "https://web.telegram.org",
        "https://webk.telegram.org",
        "https://webz.telegram.org",
    ]
    
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES") # Modified
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY") # Modified
    
    # Railway Environment
    RAILWAY_ENVIRONMENT: str = Field(default="production", env="RAILWAY_ENVIRONMENT") # Added
    
    # Admin User
    ADMIN_USERNAME: str = Field(default="admin", env="ADMIN_USERNAME") # Added
    ADMIN_PASSWORD: str = Field(default="admin", env="ADMIN_PASSWORD") # Added
    
    # Railway
    PORT: int = Field(default=8000, env="PORT")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

