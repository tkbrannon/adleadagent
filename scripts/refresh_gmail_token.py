"""Refresh Gmail OAuth token"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from app.config import get_settings

settings = get_settings()

def refresh_token():
    """Refresh the Gmail OAuth token"""
    try:
        credentials = Credentials(
            token=settings.gmail_access_token,
            refresh_token=settings.gmail_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.gmail_client_id,
            client_secret=settings.gmail_client_secret,
            scopes=["https://mail.google.com/"]
        )
        
        print("Refreshing OAuth token...")
        credentials.refresh(Request())
        
        print("\n✅ Token refreshed successfully!")
        print("\nUpdate your .env file with these new values:")
        print(f"\nGMAIL_ACCESS_TOKEN={credentials.token}")
        print(f"GMAIL_REFRESH_TOKEN={credentials.refresh_token}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Failed to refresh token: {e}")
        print("\nYour refresh token may be invalid or expired.")
        print("You'll need to re-authorize the app.")
        return False

if __name__ == "__main__":
    refresh_token()
