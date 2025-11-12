"""Database configuration and models for user/credential management"""
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Use SQLite for simplicity (can switch to PostgreSQL for production)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agent_data.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, default="admin")  # admin, cmo_agent, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


class AgentCredentials(Base):
    """Encrypted credentials storage"""
    __tablename__ = "agent_credentials"
    
    id = Column(String, primary_key=True, index=True)
    service_name = Column(String, nullable=False)  # gmail, twilio, airtable
    credential_key = Column(String, nullable=False)  # e.g., "api_key", "account_sid"
    encrypted_value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String, nullable=True)


class AgentActivity(Base):
    """Activity log for agent operations"""
    __tablename__ = "agent_activity"
    
    id = Column(String, primary_key=True, index=True)
    activity_type = Column(String, nullable=False)  # lead_processed, call_made, sms_sent
    lead_phone = Column(String, nullable=True)
    lead_name = Column(String, nullable=True)
    status = Column(String, nullable=False)  # success, failed, pending
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class TestEmail(Base):
    """Test email submissions"""
    __tablename__ = "test_emails"
    
    id = Column(String, primary_key=True, index=True)
    submitted_by = Column(String, nullable=False)
    email_content = Column(Text, nullable=False)
    parsed_data = Column(Text, nullable=True)
    processing_status = Column(String, default="pending")
    call_sid = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
