"""Create initial admin user"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, init_db
from app.auth import create_user, UserCreate

def create_admin():
    """Create default admin user"""
    init_db()
    
    db = SessionLocal()
    
    try:
        # Check if admin exists
        from app.database import User
        existing = db.query(User).filter(User.username == "admin").first()
        
        if existing:
            print("❌ Admin user already exists")
            return
        
        # Create admin
        admin_data = UserCreate(
            username="admin",
            email="admin@meshcowork.com",
            password="admin123",  # Change this!
            full_name="System Administrator",
            role="admin"
        )
        
        user = create_user(db, admin_data)
        
        print("✅ Admin user created successfully!")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print("\n⚠️  IMPORTANT: Change the password after first login!")
    
    except Exception as e:
        print(f"❌ Failed to create admin: {e}")
    
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
