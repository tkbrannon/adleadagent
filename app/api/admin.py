"""Admin API endpoints for UI"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid
from cryptography.fernet import Fernet
import os

from app.database import get_db, AgentCredentials, AgentActivity, TestEmail
from app.auth import get_current_user, require_role, User
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Encryption key for credentials (store in env in production)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY)


class CredentialUpdate(BaseModel):
    service_name: str
    credential_key: str
    value: str


class CredentialResponse(BaseModel):
    id: str
    service_name: str
    credential_key: str
    masked_value: str
    updated_at: datetime


class ActivityResponse(BaseModel):
    id: str
    activity_type: str
    lead_phone: str | None
    lead_name: str | None
    status: str
    details: str | None
    timestamp: datetime


class TestEmailSubmit(BaseModel):
    email_content: str


class AgentStats(BaseModel):
    total_leads_processed: int
    calls_made_today: int
    sms_sent_today: int
    qualified_leads: int
    average_speed_to_lead: float


@router.get("/stats", response_model=AgentStats)
async def get_agent_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get agent performance statistics"""
    from datetime import date
    
    today = date.today()
    
    # Count activities
    total_leads = db.query(AgentActivity).filter(
        AgentActivity.activity_type == "lead_processed"
    ).count()
    
    calls_today = db.query(AgentActivity).filter(
        AgentActivity.activity_type == "call_made",
        AgentActivity.timestamp >= today
    ).count()
    
    sms_today = db.query(AgentActivity).filter(
        AgentActivity.activity_type == "sms_sent",
        AgentActivity.timestamp >= today
    ).count()
    
    # This would come from Airtable in real implementation
    qualified = db.query(AgentActivity).filter(
        AgentActivity.status == "qualified"
    ).count()
    
    return AgentStats(
        total_leads_processed=total_leads,
        calls_made_today=calls_today,
        sms_sent_today=sms_today,
        qualified_leads=qualified,
        average_speed_to_lead=4.5  # Placeholder
    )


@router.get("/credentials", response_model=List[CredentialResponse])
async def list_credentials(
    current_user: User = Depends(require_role(["admin", "cmo_agent"])),
    db: Session = Depends(get_db)
):
    """List all stored credentials (masked)"""
    credentials = db.query(AgentCredentials).all()
    
    return [
        CredentialResponse(
            id=cred.id,
            service_name=cred.service_name,
            credential_key=cred.credential_key,
            masked_value="*" * 8 + cred.encrypted_value[-4:],
            updated_at=cred.updated_at
        )
        for cred in credentials
    ]


@router.post("/credentials")
async def update_credential(
    credential: CredentialUpdate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Update or create a credential"""
    # Encrypt value
    encrypted_value = cipher_suite.encrypt(credential.value.encode()).decode()
    
    # Check if exists
    existing = db.query(AgentCredentials).filter(
        AgentCredentials.service_name == credential.service_name,
        AgentCredentials.credential_key == credential.credential_key
    ).first()
    
    if existing:
        existing.encrypted_value = encrypted_value
        existing.updated_at = datetime.utcnow()
        existing.updated_by = current_user.username
        db.commit()
        return {"message": "Credential updated", "id": existing.id}
    else:
        new_cred = AgentCredentials(
            id=str(uuid.uuid4()),
            service_name=credential.service_name,
            credential_key=credential.credential_key,
            encrypted_value=encrypted_value,
            updated_by=current_user.username
        )
        db.add(new_cred)
        db.commit()
        return {"message": "Credential created", "id": new_cred.id}


@router.delete("/credentials/{credential_id}")
async def delete_credential(
    credential_id: str,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Delete a credential"""
    credential = db.query(AgentCredentials).filter(
        AgentCredentials.id == credential_id
    ).first()
    
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    db.delete(credential)
    db.commit()
    
    return {"message": "Credential deleted"}


@router.get("/activity", response_model=List[ActivityResponse])
async def get_activity_log(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent agent activity"""
    activities = db.query(AgentActivity).order_by(
        AgentActivity.timestamp.desc()
    ).limit(limit).all()
    
    return activities


@router.post("/test-email")
async def submit_test_email(
    test_data: TestEmailSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit a test email for processing"""
    from app.services.gmail_service import GmailService
    from app.tasks import process_lead
    
    # Parse email
    gmail_service = GmailService()
    lead_data = gmail_service._parse_lead_data(test_data.email_content)
    
    if not lead_data:
        raise HTTPException(
            status_code=400,
            detail="Failed to parse email content. Check format."
        )
    
    # Create test email record
    test_email = TestEmail(
        id=str(uuid.uuid4()),
        submitted_by=current_user.username,
        email_content=test_data.email_content,
        parsed_data=str(lead_data),
        processing_status="queued"
    )
    
    db.add(test_email)
    db.commit()
    
    # Queue for processing
    lead_dict = {
        **lead_data,
        "email_received_at": datetime.utcnow().isoformat()
    }
    
    result = process_lead.delay(lead_dict)
    
    # Log activity
    activity = AgentActivity(
        id=str(uuid.uuid4()),
        activity_type="test_email_submitted",
        lead_phone=lead_data.get("phone"),
        lead_name=lead_data.get("fname"),
        status="queued",
        details=f"Test submitted by {current_user.username}"
    )
    db.add(activity)
    db.commit()
    
    return {
        "message": "Test email queued for processing",
        "test_id": test_email.id,
        "task_id": result.id,
        "parsed_lead": lead_data
    }


@router.get("/health")
async def agent_health():
    """Check agent health status"""
    from app.services import redis_client
    
    redis_ok = redis_client.health_check()
    
    return {
        "status": "healthy" if redis_ok else "degraded",
        "services": {
            "redis": "connected" if redis_ok else "disconnected",
            "fastapi": "running",
            "celery": "unknown"  # Would need to check Celery
        },
        "timestamp": datetime.utcnow().isoformat()
    }
