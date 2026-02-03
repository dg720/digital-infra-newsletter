"""Configuration module - loads settings from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    tavily_api_key: str = Field(..., alias="TAVILY_API_KEY")
    
    # Model Configuration
    model_manager: str = Field(default="gpt-4o", alias="MODEL_MANAGER")
    model_research: str = Field(default="gpt-4o", alias="MODEL_RESEARCH")
    model_review: str = Field(default="gpt-4o", alias="MODEL_REVIEW")
    model_edit: str = Field(default="gpt-4o", alias="MODEL_EDIT")
    model_web_search: str = Field(default="gpt-4o-mini", alias="MODEL_WEB_SEARCH")
    
    # Agent Configuration
    max_tool_calls_per_agent: int = Field(default=12, alias="MAX_TOOL_CALLS_PER_AGENT")
    
    # Storage Configuration
    issues_dir: str = Field(default="./issues", alias="ISSUES_DIR")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
