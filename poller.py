"""Gmail polling service - monitors for new Unbounce leads"""
import time
import sys
from loguru import logger
from datetime import datetime

from app.config import get_settings
from app.services import gmail_service, redis_client
from app.tasks import process_lead

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/poller.log", rotation="500 MB", level="DEBUG")

settings = get_settings()


def poll_gmail():
    """Poll Gmail for new Unbounce lead notifications"""
    logger.info("Starting Gmail poller...")
    
    # Connect to Gmail
    if not gmail_service.connect():
        logger.error("Failed to connect to Gmail. Exiting.")
        return
    
    logger.info(f"Polling every {settings.polling_interval_seconds} seconds")
    
    try:
        while True:
            try:
                # Get unread Unbounce emails
                email_ids = gmail_service.get_unread_unbounce_emails()
                
                if email_ids:
                    logger.info(f"Processing {len(email_ids)} new leads")
                
                for email_id in email_ids:
                    try:
                        # Check if already processed (prevent duplicates)
                        email_id_str = email_id.decode() if isinstance(email_id, bytes) else str(email_id)
                        
                        if redis_client.is_email_processed(email_id_str):
                            logger.info(f"Email {email_id_str} already processed, skipping")
                            gmail_service.mark_as_read(email_id)
                            continue
                        
                        # Parse lead data
                        lead = gmail_service.parse_unbounce_email(email_id)
                        
                        if not lead:
                            logger.warning(f"Failed to parse email {email_id_str}")
                            gmail_service.mark_as_read(email_id)
                            continue
                        
                        # Mark as processed in Redis
                        redis_client.mark_email_processed(email_id_str)
                        
                        # Mark email as read
                        gmail_service.mark_as_read(email_id)
                        
                        # Queue lead for processing (async via Celery)
                        lead_dict = lead.model_dump()
                        # Convert datetime to ISO string for JSON serialization
                        lead_dict['email_received_at'] = lead.email_received_at.isoformat()
                        
                        process_lead.delay(lead_dict)
                        
                        logger.info(f"✓ Lead queued: {lead.fname} ({lead.phone})")
                    
                    except Exception as e:
                        logger.error(f"Error processing email {email_id}: {e}")
                        continue
                
                # Sleep before next poll
                time.sleep(settings.polling_interval_seconds)
            
            except KeyboardInterrupt:
                logger.info("Polling interrupted by user")
                break
            
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                time.sleep(settings.polling_interval_seconds)
    
    finally:
        gmail_service.disconnect()
        logger.info("Gmail poller stopped")


if __name__ == "__main__":
    poll_gmail()
