"""API endpoints for CMO Agent to manage this sub-agent"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel
import uuid

from app.database import get_db, AgentActivity
from app.config import get_settings

router = APIRouter(prefix="/api/cmo", tags=["cmo-agent"])

settings = get_settings()

# CMO Agent API Key (set in environment)
CMO_API_KEY = settings.cmo_api_key if hasattr(settings, 'cmo_api_key') else "cmo-agent-key-change-me"


def verify_cmo_agent(x_api_key: str = Header(...)):
    """Verify CMO agent API key"""
    if x_api_key != CMO_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True


class AgentCommand(BaseModel):
    """Command from CMO agent"""
    command: str  # start, stop, pause, resume, get_status
    parameters: Optional[dict] = None


class AgentStatusResponse(BaseModel):
    """Agent status for CMO"""
    agent_id: str
    agent_name: str
    agent_type: str
    status: str  # active, paused, stopped, error
    role: str  # account_executive
    department: str  # cmo
    metrics: dict
    last_activity: Optional[datetime]
    uptime_hours: float


class LeadReport(BaseModel):
    """Lead processing report"""
    period: str  # today, week, month
    total_leads: int
    qualified_leads: int
    calls_made: int
    sms_sent: int
    average_speed_to_lead: float
    conversion_rate: float


@router.get("/status", response_model=AgentStatusResponse)
async def get_agent_status(
    _: bool = Depends(verify_cmo_agent),
    db: Session = Depends(get_db)
):
    """Get current agent status for CMO dashboard"""
    from app.services import redis_client
    
    # Get recent activity
    last_activity = db.query(AgentActivity).order_by(
        AgentActivity.timestamp.desc()
    ).first()
    
    # Calculate metrics
    today = datetime.utcnow().date()
    today_activities = db.query(AgentActivity).filter(
        AgentActivity.timestamp >= today
    ).all()
    
    calls_today = sum(1 for a in today_activities if a.activity_type == "call_made")
    sms_today = sum(1 for a in today_activities if a.activity_type == "sms_sent")
    leads_today = sum(1 for a in today_activities if a.activity_type == "lead_processed")
    
    # Check service health
    redis_ok = redis_client.health_check()
    status = "active" if redis_ok else "error"
    
    return AgentStatusResponse(
        agent_id="lead-qualification-agent-001",
        agent_name="Mesh Cowork Lead Qualifier",
        agent_type="lead_qualification",
        status=status,
        role="account_executive",
        department="cmo",
        metrics={
            "calls_today": calls_today,
            "sms_today": sms_today,
            "leads_today": leads_today,
            "redis_connected": redis_ok
        },
        last_activity=last_activity.timestamp if last_activity else None,
        uptime_hours=24.0  # Placeholder
    )


@router.post("/command")
async def send_command(
    command: AgentCommand,
    _: bool = Depends(verify_cmo_agent),
    db: Session = Depends(get_db)
):
    """Send command to agent from CMO"""
    
    # Log command
    activity = AgentActivity(
        id=str(uuid.uuid4()),
        activity_type="cmo_command",
        status="received",
        details=f"Command: {command.command}, Params: {command.parameters}"
    )
    db.add(activity)
    db.commit()
    
    # Handle commands
    if command.command == "get_status":
        return await get_agent_status(_=True, db=db)
    
    elif command.command == "pause":
        # In production, this would pause the poller
        return {
            "status": "success",
            "message": "Agent paused",
            "command": command.command
        }
    
    elif command.command == "resume":
        return {
            "status": "success",
            "message": "Agent resumed",
            "command": command.command
        }
    
    elif command.command == "get_metrics":
        return await get_lead_report(period="today", _=True, db=db)
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown command: {command.command}"
        )


@router.get("/report/{period}", response_model=LeadReport)
async def get_lead_report(
    period: str = "today",
    _: bool = Depends(verify_cmo_agent),
    db: Session = Depends(get_db)
):
    """Get lead processing report for CMO"""
    
    # Calculate date range
    now = datetime.utcnow()
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:
        raise HTTPException(status_code=400, detail="Invalid period")
    
    # Query activities
    activities = db.query(AgentActivity).filter(
        AgentActivity.timestamp >= start_date
    ).all()
    
    total_leads = sum(1 for a in activities if a.activity_type == "lead_processed")
    calls_made = sum(1 for a in activities if a.activity_type == "call_made")
    sms_sent = sum(1 for a in activities if a.activity_type == "sms_sent")
    qualified = sum(1 for a in activities if a.status == "qualified")
    
    conversion_rate = (qualified / total_leads * 100) if total_leads > 0 else 0
    
    return LeadReport(
        period=period,
        total_leads=total_leads,
        qualified_leads=qualified,
        calls_made=calls_made,
        sms_sent=sms_sent,
        average_speed_to_lead=4.5,  # Would calculate from actual data
        conversion_rate=conversion_rate
    )


@router.post("/trigger-lead")
async def trigger_lead_processing(
    lead_data: dict,
    _: bool = Depends(verify_cmo_agent),
    db: Session = Depends(get_db)
):
    """Allow CMO agent to trigger lead processing directly"""
    from app.tasks import process_lead
    
    # Validate required fields
    required = ["fname", "email", "phone"]
    if not all(k in lead_data for k in required):
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {required}"
        )
    
    # Add timestamp if not present
    if "email_received_at" not in lead_data:
        lead_data["email_received_at"] = datetime.utcnow().isoformat()
    
    # Queue for processing
    result = process_lead.delay(lead_data)
    
    # Log activity
    activity = AgentActivity(
        id=str(uuid.uuid4()),
        activity_type="cmo_triggered_lead",
        lead_phone=lead_data.get("phone"),
        lead_name=lead_data.get("fname"),
        status="queued",
        details=f"Triggered by CMO agent"
    )
    db.add(activity)
    db.commit()
    
    return {
        "status": "success",
        "message": "Lead queued for processing",
        "task_id": result.id,
        "lead": {
            "name": lead_data.get("fname"),
            "phone": lead_data.get("phone")
        }
    }


@router.get("/capabilities")
async def get_agent_capabilities(_: bool = Depends(verify_cmo_agent)):
    """Return agent capabilities for CMO discovery"""
    return {
        "agent_id": "lead-qualification-agent-001",
        "agent_name": "Mesh Cowork Lead Qualifier",
        "agent_type": "lead_qualification",
        "role": "account_executive",
        "department": "cmo",
        "version": "1.0.0",
        "capabilities": [
            "email_monitoring",
            "outbound_calling",
            "speech_recognition",
            "lead_qualification",
            "sms_followup",
            "crm_integration"
        ],
        "integrations": [
            "gmail",
            "twilio",
            "airtable",
            "calendly"
        ],
        "commands": [
            "start",
            "stop",
            "pause",
            "resume",
            "get_status",
            "get_metrics"
        ],
        "metrics_available": [
            "leads_processed",
            "calls_made",
            "sms_sent",
            "qualification_rate",
            "speed_to_lead"
        ]
    }
