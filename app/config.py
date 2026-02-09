# from pydantic_settings import BaseSettings
# from functools import lru_cache


# class Settings(BaseSettings):
#     """Application configuration settings."""
    
#     # Environment
#     environment: str = "development"
    
#     # Groq API
#     groq_api_key: str
#     groq_model: str = "llama-3.3-70b-versatile"
    
#     # Database
#     database_url: str
    
#     # API
#     api_host: str = "0.0.0.0"
#     api_port: int = 8000
#     api_key: str
    
#     # Security
#     secret_key: str
#     algorithm: str = "HS256"
#     access_token_expire_minutes: int = 30
    
#     # RAG Configuration
#     embedding_model: str = "all-MiniLM-L6-v2"
#     chunk_size: int = 1000
#     chunk_overlap: int = 200
#     top_k_results: int = 5
    
#     # Rate Limiting
#     rate_limit_per_minute: int = 60
    
#     class Config:
#         env_file = ".env"
#         case_sensitive = False


# @lru_cache()
# def get_settings() -> Settings:
#     """Get cached settings instance."""
#     return Settings()
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    # Environment
    environment: str = "development"

    # Groq API
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    # Database
    database_url: str

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # RAG Configuration
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k_results: int = 5

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # ✅ Pydantic v2 config
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="allow",  # ← THIS fixes your crash
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
