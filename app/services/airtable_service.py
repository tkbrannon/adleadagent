"""Airtable service for storing lead data"""
from pyairtable import Api
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger
from app.config import get_settings
from app.models import LeadRecord

settings = get_settings()


class AirtableService:
    """Airtable client for lead storage"""
    
    def __init__(self):
        self.api = Api(settings.airtable_api_key)
        self.table = self.api.table(
            settings.airtable_base_id,
            settings.airtable_table_name
        )
    
    def create_lead_record(self, lead: LeadRecord) -> Optional[str]:
        """Create a new lead record in Airtable"""
        try:
            # Prepare record data
            record_data = {
                "Name": lead.name,
                "Email": lead.email,
                "Phone": lead.phone,
                "Office Space Interest": lead.office_space_interest,
                "Message": lead.message or "",
                "Campaign ID": lead.campaign_id or "",
                
                # Call data
                "Call SID": lead.call_sid or "",
                "Call Status": lead.call_status or "",
                "Call Duration (seconds)": lead.call_duration or 0,
                
                # Qualification
                "Qualification Status": lead.qualification_status.value,
                "Qualification Reason": lead.qualification_reason or "",
                
                # Timing
                "Email Received At": lead.email_received_at.isoformat(),
                "Call Initiated At": lead.call_initiated_at.isoformat() if lead.call_initiated_at else "",
                "Call Completed At": lead.call_completed_at.isoformat() if lead.call_completed_at else "",
                "SMS Sent At": lead.sms_sent_at.isoformat() if lead.sms_sent_at else "",
                "Speed to Lead (seconds)": lead.speed_to_lead_seconds or 0,
                
                # Metadata
                "Page Name": lead.page_name,
                "Page URL": lead.page_url,
                "Created At": lead.created_at.isoformat(),
            }
            
            # Add call answers if available
            if lead.call_answers:
                record_data["Years in Business"] = lead.call_answers.get("q1", "")
                record_data["Number of Employees"] = lead.call_answers.get("q2", "")
                record_data["Has Clients"] = lead.call_answers.get("q3", "")
                record_data["Budget"] = lead.call_answers.get("q4", "")
                record_data["Office Preference"] = lead.call_answers.get("q5", "")
            
            # Create record
            record = self.table.create(record_data)
            
            logger.info(f"Created Airtable record: {record['id']} for {lead.name}")
            return record['id']
        
        except Exception as e:
            logger.error(f"Failed to create Airtable record for {lead.name}: {e}")
            return None
    
    def update_lead_record(self, record_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing lead record"""
        try:
            self.table.update(record_id, updates)
            logger.info(f"Updated Airtable record: {record_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update Airtable record {record_id}: {e}")
            return False
    
    def get_schema_info(self) -> str:
        """Return information about required Airtable schema"""
        return """
        Required Airtable Fields:
        
        Text Fields:
        - Name (Single line text)
        - Email (Email)
        - Phone (Phone number)
        - Office Space Interest (Single line text)
        - Message (Long text)
        - Campaign ID (Single line text)
        - Call SID (Single line text)
        - Call Status (Single line text)
        - Qualification Status (Single select: qualified, unqualified, no_answer, call_failed, pending)
        - Qualification Reason (Long text)
        - Page Name (Single line text)
        - Page URL (URL)
        - Years in Business (Single line text)
        - Number of Employees (Single line text)
        - Has Clients (Single line text)
        - Budget (Single line text)
        - Office Preference (Single line text)
        
        Number Fields:
        - Call Duration (seconds) (Number)
        - Speed to Lead (seconds) (Number)
        
        Date Fields:
        - Email Received At (Date)
        - Call Initiated At (Date)
        - Call Completed At (Date)
        - SMS Sent At (Date)
        - Created At (Date)
        """


# Singleton instance
airtable_service = AirtableService()
