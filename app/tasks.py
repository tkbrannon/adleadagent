"""Celery tasks for async lead processing"""
from datetime import datetime
from typing import Dict, Any
from loguru import logger
import uuid

from app.celery_app import celery_app
from app.models import LeadRecord, LeadQualification
from app.services import (
    twilio_service,
    airtable_service,
    redis_client
)
from app.config import get_settings
from app.database import SessionLocal, AgentActivity

settings = get_settings()


@celery_app.task(name="process_lead")
def process_lead(lead_data: Dict[str, Any]) -> str:
    """
    Process a new lead: initiate call and store in Airtable
    
    Args:
        lead_data: Dictionary containing lead information
    
    Returns:
        Call SID or error message
    """
    try:
        logger.info(f"Processing lead: {lead_data['fname']} - {lead_data['phone']}")
        
        # Record call initiation time
        call_initiated_at = datetime.utcnow()
        
        # Store timestamp in Redis for speed-to-lead calculation
        email_received_at = datetime.fromisoformat(lead_data['email_received_at'])
        redis_client.store_lead_timestamp(lead_data['phone'], email_received_at)
        
        # Initiate Twilio call
        call_sid = twilio_service.initiate_call(
            to_number=lead_data['phone'],
            lead_name=lead_data['fname']
        )
        
        if not call_sid:
            logger.error(f"Failed to initiate call for {lead_data['fname']}")
            
            # Still create Airtable record with failure status
            lead_record = LeadRecord(
                name=lead_data['fname'],
                email=lead_data['email'],
                phone=lead_data['phone'],
                office_space_interest=lead_data.get('what_kind_of_office_space_are_you_interested_in', 'Other'),
                message=lead_data.get('message'),
                campaign_id=lead_data.get('campaignid'),
                qualification_status=LeadQualification.CALL_FAILED,
                qualification_reason="Failed to initiate call",
                email_received_at=email_received_at,
                call_initiated_at=call_initiated_at,
                speed_to_lead_seconds=(call_initiated_at - email_received_at).total_seconds(),
                page_name=lead_data.get('page_name', 'Mesh Cowork - Private Offices'),
                page_url=lead_data.get('page_url', 'http://tour.meshcowork.com/private-offices/')
            )
            
            airtable_service.create_lead_record(lead_record)
            return "CALL_FAILED"
        
        # Calculate speed to lead
        speed_to_lead = (call_initiated_at - email_received_at).total_seconds()
        
        # Log activity to database
        db = SessionLocal()
        try:
            activity = AgentActivity(
                id=str(uuid.uuid4()),
                activity_type="call_made",
                lead_name=lead_data['fname'],
                lead_phone=lead_data['phone'],
                status="initiated",
                details=f"Call initiated: {call_sid}",
                timestamp=call_initiated_at
            )
            db.add(activity)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
        finally:
            db.close()
        
        # Store call data in Redis for webhook access
        redis_client.store_call_data(call_sid, {
            "name": lead_data['fname'],
            "email": lead_data['email'],
            "phone": lead_data['phone'],
            "office_space_interest": lead_data.get('what_kind_of_office_space_are_you_interested_in', 'Other'),
            "message": lead_data.get('message', ''),
            "campaign_id": lead_data.get('campaignid', ''),
            "email_received_at": email_received_at.isoformat(),
            "call_initiated_at": call_initiated_at.isoformat(),
            "speed_to_lead_seconds": speed_to_lead,
            "page_name": lead_data.get('page_name', 'Mesh Cowork - Private Offices'),
            "page_url": lead_data.get('page_url', 'http://tour.meshcowork.com/private-offices/')
        })
        
        logger.info(f"Call initiated: {call_sid} | Speed to lead: {speed_to_lead:.2f}s")
        return call_sid
    
    except Exception as e:
        logger.error(f"Error processing lead: {e}")
        return f"ERROR: {str(e)}"


@celery_app.task(name="send_followup_sms")
def send_followup_sms(phone: str, name: str, qualified: bool = True) -> bool:
    """
    Send SMS follow-up with Calendly link
    
    Args:
        phone: Lead's phone number
        name: Lead's name
        qualified: Whether lead is qualified
    
    Returns:
        Success status
    """
    try:
        if qualified:
            message = (
                f"Hi {name}! Thanks for speaking with us. "
                f"Book your tour at Mesh Cowork here: {settings.calendly_link} "
                f"We look forward to meeting you!"
            )
        else:
            message = (
                f"Hi {name}! Thanks for your interest in Mesh Cowork. "
                f"While we may not be the perfect fit right now, feel free to reach out "
                f"if your needs change. You can always book a tour: {settings.calendly_link}"
            )
        
        success = twilio_service.send_sms(phone, message)
        
        # Log activity to database
        db = SessionLocal()
        try:
            activity = AgentActivity(
                id=str(uuid.uuid4()),
                activity_type="sms_sent",
                lead_name=name,
                lead_phone=phone,
                status="success" if success else "failed",
                details=f"Follow-up SMS {'sent' if success else 'failed'}",
                timestamp=datetime.utcnow()
            )
            db.add(activity)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log SMS activity: {e}")
        finally:
            db.close()
        
        if success:
            logger.info(f"SMS sent to {phone}")
        else:
            logger.error(f"Failed to send SMS to {phone}")
        
        return success
    
    except Exception as e:
        logger.error(f"Error sending SMS: {e}")
        return False


@celery_app.task(name="finalize_lead_record")
def finalize_lead_record(call_sid: str, call_status: str, call_duration: int = 0) -> bool:
    """
    Finalize lead record in Airtable after call completes
    
    Args:
        call_sid: Twilio call SID
        call_status: Final call status
        call_duration: Call duration in seconds
    
    Returns:
        Success status
    """
    try:
        # Get call data from Redis
        call_data = redis_client.get_call_data(call_sid)
        
        if not call_data:
            logger.error(f"No call data found for {call_sid}")
            return False
        
        # Get all answers
        call_answers = {
            "q1": call_data.get("answer_q1", ""),
            "q2": call_data.get("answer_q2", ""),
            "q3": call_data.get("answer_q3", ""),
            "q4": call_data.get("answer_q4", ""),
            "q5": call_data.get("answer_q5", ""),
        }
        
        # Determine qualification status
        qualification_status, qualification_reason = _determine_qualification(call_answers, call_status)
        
        # Create lead record
        call_completed_at = datetime.utcnow()
        
        lead_record = LeadRecord(
            name=call_data.get("name", ""),
            email=call_data.get("email", ""),
            phone=call_data.get("phone", ""),
            office_space_interest=call_data.get("office_space_interest", "Other"),
            message=call_data.get("message"),
            campaign_id=call_data.get("campaign_id"),
            call_sid=call_sid,
            call_status=call_status,
            call_duration=call_duration,
            call_answers=call_answers,
            qualification_status=qualification_status,
            qualification_reason=qualification_reason,
            email_received_at=datetime.fromisoformat(call_data.get("email_received_at")),
            call_initiated_at=datetime.fromisoformat(call_data.get("call_initiated_at")),
            call_completed_at=call_completed_at,
            speed_to_lead_seconds=float(call_data.get("speed_to_lead_seconds", 0)),
            page_name=call_data.get("page_name", "Mesh Cowork - Private Offices"),
            page_url=call_data.get("page_url", "http://tour.meshcowork.com/private-offices/")
        )
        
        # Save to Airtable (but don't fail if it doesn't work)
        record_id = airtable_service.create_lead_record(lead_record)
        
        if record_id:
            logger.info(f"Lead record finalized in Airtable: {record_id}")
        else:
            logger.warning(f"Airtable save failed for {call_sid}, but continuing with SMS")
        
        # Send follow-up SMS regardless of Airtable status
        send_followup_sms.delay(
            phone=lead_record.phone,
            name=lead_record.name,
            qualified=(qualification_status == LeadQualification.QUALIFIED)
        )
        
        # Log lead processing completion
        db = SessionLocal()
        try:
            activity = AgentActivity(
                id=str(uuid.uuid4()),
                activity_type="lead_processed",
                lead_name=lead_record.name,
                lead_phone=lead_record.phone,
                status="qualified" if qualification_status == LeadQualification.QUALIFIED else "not_qualified",
                details=f"Lead finalized: {qualification_reason}. Airtable: {'saved' if record_id else 'failed'}",
                timestamp=datetime.utcnow()
            )
            db.add(activity)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log lead processing activity: {e}")
        finally:
            db.close()
        
        logger.info(f"Lead processing completed for {call_sid}")
        return True
    
    except Exception as e:
        logger.error(f"Error finalizing lead record: {e}")
        return False


def _determine_qualification(answers: Dict[str, str], call_status: str) -> tuple:
    """
    Determine if lead is qualified based on answers
    
    Returns:
        (qualification_status, reason)
    """
    if call_status != "completed":
        return LeadQualification.NO_ANSWER, f"Call status: {call_status}"
    
    # Check if we got answers
    if not any(answers.values()):
        return LeadQualification.NO_ANSWER, "No answers recorded"
    
    reasons = []
    
    # Q1: Years in business (looking for established businesses)
    years = answers.get("q1", "").lower()
    if any(word in years for word in ["0", "zero", "new", "just started", "starting"]):
        reasons.append("Less than 1 year in business")
    
    # Q2: Number of employees (looking for teams)
    employees = answers.get("q2", "").lower()
    if any(word in employees for word in ["0", "zero", "none", "just me", "solo"]):
        reasons.append("Solo entrepreneur (no team)")
    
    # Q3: Has clients (looking for active businesses)
    clients = answers.get("q3", "").lower()
    if any(word in clients for word in ["no", "not yet", "none", "don't have"]):
        reasons.append("No current clients")
    
    # Q4: Budget (looking for realistic budget)
    budget = answers.get("q4", "").lower()
    if any(word in budget for word in ["don't know", "not sure", "no budget", "free"]):
        reasons.append("No clear budget")
    
    # Qualification logic: Disqualify if 3+ red flags
    if len(reasons) >= 3:
        return LeadQualification.UNQUALIFIED, "; ".join(reasons)
    elif len(reasons) >= 1:
        return LeadQualification.QUALIFIED, f"Qualified with notes: {'; '.join(reasons)}"
    else:
        return LeadQualification.QUALIFIED, "Strong fit - established business with team and clients"
