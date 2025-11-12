"""Gmail service for monitoring lead notifications"""
import imaplib
import email
from email.header import decode_header
from datetime import datetime
from typing import List, Optional
import re
import base64
from loguru import logger
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from app.config import get_settings
from app.models import UnbounceLead

settings = get_settings()


class GmailService:
    """Gmail IMAP service for reading Unbounce notifications"""
    
    def __init__(self):
        self.imap_server = "imap.gmail.com"
        self.email_address = settings.gmail_address
        self.connection: Optional[imaplib.IMAP4_SSL] = None
        self.credentials: Optional[Credentials] = None
        
        # Determine auth method
        self.use_oauth = bool(settings.gmail_access_token and settings.gmail_refresh_token)
        
        if self.use_oauth:
            logger.info("Using OAuth2 authentication for Gmail")
            self._setup_oauth_credentials()
        else:
            logger.info("Using App Password authentication for Gmail")
    
    def _setup_oauth_credentials(self):
        """Setup OAuth2 credentials"""
        try:
            self.credentials = Credentials(
                token=settings.gmail_access_token,
                refresh_token=settings.gmail_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.gmail_client_id,
                client_secret=settings.gmail_client_secret,
                scopes=["https://mail.google.com/"]
            )
            
            # Refresh if expired
            if self.credentials.expired and self.credentials.refresh_token:
                logger.info("Refreshing expired OAuth2 token")
                self.credentials.refresh(Request())
                logger.info("OAuth2 token refreshed successfully")
        
        except Exception as e:
            logger.error(f"Failed to setup OAuth2 credentials: {e}")
            self.use_oauth = False
    
    def _generate_oauth2_string(self) -> str:
        """Generate OAuth2 authentication string for IMAP"""
        auth_string = f"user={self.email_address}\1auth=Bearer {self.credentials.token}\1\1"
        return auth_string
    
    def connect(self) -> bool:
        """Connect to Gmail IMAP server"""
        try:
            self.connection = imaplib.IMAP4_SSL(self.imap_server)
            
            if self.use_oauth and self.credentials:
                # OAuth2 authentication
                auth_string = self._generate_oauth2_string()
                self.connection.authenticate('XOAUTH2', lambda x: auth_string.encode())
                logger.info(f"Connected to Gmail with OAuth2: {self.email_address}")
            else:
                # App Password authentication (fallback)
                self.connection.login(self.email_address, settings.gmail_app_password)
                logger.info(f"Connected to Gmail with App Password: {self.email_address}")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to connect to Gmail: {e}")
            
            # If OAuth fails, try to refresh token and retry
            if self.use_oauth and self.credentials:
                try:
                    logger.info("Attempting to refresh OAuth2 token and retry...")
                    self.credentials.refresh(Request())
                    return self.connect()
                except Exception as refresh_error:
                    logger.error(f"Token refresh failed: {refresh_error}")
            
            return False
    
    def disconnect(self) -> None:
        """Disconnect from Gmail"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except:
                pass
    
    def get_unread_unbounce_emails(self) -> List[tuple]:
        """Get unread emails from Unbounce"""
        if not self.connection:
            self.connect()
        
        try:
            # Select inbox
            self.connection.select("INBOX")
            
            # Search for unread emails from Unbounce
            status, messages = self.connection.search(
                None, 
                '(UNSEEN SUBJECT "new lead has been captured")'
            )
            
            if status != "OK":
                logger.warning("No unread Unbounce emails found")
                return []
            
            email_ids = messages[0].split()
            logger.info(f"Found {len(email_ids)} unread Unbounce emails")
            
            return email_ids
        
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
    
    def parse_unbounce_email(self, email_id: bytes) -> Optional[UnbounceLead]:
        """Parse Unbounce lead notification email"""
        try:
            # Fetch email
            status, msg_data = self.connection.fetch(email_id, "(RFC822)")
            
            if status != "OK":
                return None
            
            # Parse email
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # Get email received time
            date_str = email_message.get("Date")
            email_received_at = email.utils.parsedate_to_datetime(date_str)
            
            # Extract body
            body = self._get_email_body(email_message)
            
            if not body:
                logger.warning(f"Empty email body for ID: {email_id}")
                return None
            
            # Parse lead data from body
            lead_data = self._parse_lead_data(body)
            
            if not lead_data:
                logger.warning(f"Could not parse lead data from email: {email_id}")
                return None
            
            # Create lead object
            lead = UnbounceLead(
                fname=lead_data.get("fname", ""),
                email=lead_data.get("email", ""),
                phone=lead_data.get("phone", ""),
                what_kind_of_office_space_are_you_interested_in=lead_data.get(
                    "what_kind_of_office_space_are_you_interested_in", "Other"
                ),
                message=lead_data.get("message"),
                campaignid=lead_data.get("campaignid"),
                email_received_at=email_received_at,
                page_name=lead_data.get("page_name", "Mesh Cowork - Private Offices"),
                page_url=lead_data.get("page_url", "http://tour.meshcowork.com/private-offices/")
            )
            
            logger.info(f"Parsed lead: {lead.fname} - {lead.phone}")
            return lead
        
        except Exception as e:
            logger.error(f"Error parsing email {email_id}: {e}")
            return None
    
    def mark_as_read(self, email_id: bytes) -> None:
        """Mark email as read"""
        try:
            self.connection.store(email_id, "+FLAGS", "\\Seen")
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
    
    def _get_email_body(self, email_message) -> str:
        """Extract email body text"""
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode()
                        break
                    except:
                        pass
        else:
            try:
                body = email_message.get_payload(decode=True).decode()
            except:
                pass
        
        return body
    
    def _parse_lead_data(self, body: str) -> Optional[dict]:
        """Parse lead data from email body"""
        try:
            data = {}
            
            # Extract fields using regex patterns
            patterns = {
                "fname": r"fname\s*\n\s*(.+)",
                "email": r"email\s*\n\s*(.+)",
                "phone": r"phone\s*\n\s*(.+)",
                "what_kind_of_office_space_are_you_interested_in": r"what_kind_of_office_space_are_you_interested_in\s*\n\s*(.+)",
                "message": r"message\s*\n\s*(.+)",
                "campaignid": r"campaignid\s*\n\s*(.+)",
                "page_name": r"Page Name\s*\n\s*(.+)",
                "page_url": r"URL\s*\n\s*(http.+)",
            }
            
            for field, pattern in patterns.items():
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    data[field] = match.group(1).strip()
            
            # Validate required fields
            if not all(k in data for k in ["fname", "email", "phone"]):
                logger.error("Missing required fields in email")
                return None
            
            return data
        
        except Exception as e:
            logger.error(f"Error parsing lead data: {e}")
            return None


# Singleton instance
gmail_service = GmailService()
