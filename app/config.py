"""Application configuration"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Gmail
    gmail_address: str
    
    # OAuth2 tokens (preferred)
    gmail_access_token: str = ""
    gmail_refresh_token: str = ""
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    
    # App Password (fallback)
    gmail_app_password: str = ""
    
    # Twilio
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str
    twilio_voice: str = "Polly.Matthew-Neural"  # More natural neural voice
    
    # Airtable
    airtable_api_key: str
    airtable_base_id: str
    airtable_table_name: str = "Leads"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # FastAPI
    fastapi_host: str = "0.0.0.0"
    fastapi_port: int = 8000
    public_webhook_url: str
    
    # Calendly
    calendly_link: str
    
    # Polling
    polling_interval_seconds: int = 30
    
    # Environment
    environment: str = "production"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production-use-openssl-rand-hex-32"
    
    # CMO Agent Integration
    cmo_api_key: str = "cmo-agent-key-change-in-production"
    
    # Database
    database_url: str = "sqlite:///./agent_data.db"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"  # Allow extra fields from .env


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
