"""Data models for lead processing"""
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class OfficeSpaceType(str, Enum):
    """Office space interest types"""
    PRIVATE_OFFICE = "Private Office"
    COWORKING = "Coworking"
    OTHER = "Other"


class LeadQualification(str, Enum):
    """Lead qualification status"""
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    NO_ANSWER = "no_answer"
    CALL_FAILED = "call_failed"
    PENDING = "pending"


class UnbounceLead(BaseModel):
    """Lead data parsed from Unbounce email"""
    fname: str
    email: EmailStr
    phone: str
    what_kind_of_office_space_are_you_interested_in: str
    message: Optional[str] = None
    campaignid: Optional[str] = None
    
    # Metadata
    email_received_at: datetime
    page_name: str = "Mesh Cowork - Private Offices"
    page_url: str = "http://tour.meshcowork.com/private-offices/"


class CallAnswers(BaseModel):
    """Answers collected during qualification call"""
    years_in_business: Optional[str] = None
    num_employees: Optional[str] = None
    has_clients: Optional[str] = None
    budget: Optional[str] = None
    office_preference: Optional[str] = None


class LeadRecord(BaseModel):
    """Complete lead record for Airtable"""
    # Original lead data
    name: str
    email: str
    phone: str
    office_space_interest: str
    message: Optional[str] = None
    campaign_id: Optional[str] = None
    
    # Call data
    call_sid: Optional[str] = None
    call_status: Optional[str] = None
    call_duration: Optional[int] = None
    call_answers: Optional[Dict[str, Any]] = None
    
    # Qualification
    qualification_status: LeadQualification = LeadQualification.PENDING
    qualification_reason: Optional[str] = None
    
    # Timing metrics
    email_received_at: datetime
    call_initiated_at: Optional[datetime] = None
    call_completed_at: Optional[datetime] = None
    sms_sent_at: Optional[datetime] = None
    speed_to_lead_seconds: Optional[float] = None
    
    # Metadata
    page_name: str
    page_url: str
    created_at: datetime = datetime.utcnow()


class TwilioCallStatus(BaseModel):
    """Twilio call status webhook payload"""
    CallSid: str
    CallStatus: str
    From: Optional[str] = None
    To: Optional[str] = None
    CallDuration: Optional[str] = None


class TwilioGatherResult(BaseModel):
    """Twilio speech recognition result"""
    CallSid: str
    SpeechResult: Optional[str] = None
    Confidence: Optional[float] = None
    question_id: str  # Which question was answered
