"""Send a test call to verify the system works end-to-end"""
import sys
sys.path.insert(0, '/Users/tabaribrannon/Documents/mesh_agents/cmo/adleadagent')

from app.tasks import process_lead
from datetime import datetime

def send_test_call():
    """Send a test call to your own phone number"""
    
    # IMPORTANT: Change this to YOUR phone number for testing
    YOUR_PHONE = input("Enter your phone number (format: +1234567890): ")
    YOUR_NAME = input("Enter your name: ")
    
    print(f"\nSending test call to {YOUR_PHONE}...")
    print("You should receive a call in a few seconds.\n")
    
    # Create test lead data
    test_lead = {
        "fname": YOUR_NAME,
        "email": "test@meshcowork.com",
        "phone": YOUR_PHONE,
        "what_kind_of_office_space_are_you_interested_in": "Private Office",
        "message": "This is a test call",
        "campaignid": "TEST123",
        "email_received_at": datetime.utcnow().isoformat(),
        "page_name": "Mesh Cowork - Private Offices",
        "page_url": "http://tour.meshcowork.com/private-offices/"
    }
    
    # Process lead (this will initiate the call)
    result = process_lead.delay(test_lead)
    
    print(f"Task queued: {result.id}")
    print("\nWait for the call...")
    print("Answer and respond to the 5 questions.")
    print("You should receive an SMS with the Calendly link afterwards.")
    print("\nCheck Airtable for the record after the call completes.")

if __name__ == "__main__":
    print("=" * 60)
    print("TEST CALL SCRIPT")
    print("=" * 60)
    print("\nThis will:")
    print("1. Call your phone number")
    print("2. Ask you 5 qualification questions")
    print("3. Send you an SMS with Calendly link")
    print("4. Create a record in Airtable")
    print("\nMake sure:")
    print("- Redis is running")
    print("- Celery worker is running")
    print("- FastAPI server is running")
    print("- All environment variables are set")
    print("=" * 60)
    print()
    
    confirm = input("Ready to proceed? (yes/no): ")
    
    if confirm.lower() == "yes":
        send_test_call()
    else:
        print("Test cancelled.")
