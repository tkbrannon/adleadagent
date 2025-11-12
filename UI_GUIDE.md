# Admin UI Guide

## Overview

The Lead Qualification Agent now includes a production-ready web UI for:
- ✅ Secure authentication (JWT-based)
- ✅ Credentials management (encrypted storage)
- ✅ Email testing interface
- ✅ Real-time dashboard
- ✅ Activity logging
- ✅ CMO Agent API integration

## Architecture

```
┌─────────────────┐
│   CMO Agent     │ ← Parent agent (orchestrates multiple sub-agents)
└────────┬────────┘
         │ API calls (with API key)
         ▼
┌─────────────────────────────────────┐
│  Lead Qualification Agent (This)   │
│  Role: Account Executive            │
│  Department: CMO                    │
├─────────────────────────────────────┤
│  • Admin UI (Vue.js)                │
│  • FastAPI Backend                  │
│  • JWT Authentication               │
│  • Encrypted Credentials Storage    │
│  • CMO Agent API Endpoints          │
└─────────────────────────────────────┘
```

## Quick Start

### 1. Install Additional Dependencies

```bash
cd /Users/tabaribrannon/Documents/mesh_agents/cmo/adleadagent
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Update Environment Variables

Add to your `.env` file:

```bash
# Security (IMPORTANT: Change these in production!)
SECRET_KEY=your-secret-key-use-openssl-rand-hex-32
ENCRYPTION_KEY=generate-with-python-fernet-generate-key

# CMO Agent Integration
CMO_API_KEY=your-cmo-agent-api-key-here

# Database
DATABASE_URL=sqlite:///./agent_data.db
```

### 3. Create Admin User

```bash
python scripts/create_admin.py
```

Default credentials:
- Username: `admin`
- Password: `admin123`

**⚠️ Change this immediately after first login!**

### 4. Start the Application

```bash
# Option A: Docker Compose (includes UI)
docker-compose up

# Option B: Manual
python app/main.py
```

### 5. Access the UI

Open browser: `http://localhost:8000`

## UI Features

### 1. Dashboard Tab
- **Real-time metrics**: Total leads, calls today, SMS sent, qualified leads
- **Agent status**: Health checks, Redis connection, speed-to-lead
- **Performance monitoring**: Average response times

### 2. Test Email Tab
- **Email testing**: Paste Unbounce email content
- **Instant validation**: See parsed lead data
- **Live processing**: Triggers actual call flow
- **Results display**: Success/failure with details

### 3. Credentials Tab
- **Secure storage**: Encrypted credentials in database
- **Service management**: Gmail, Twilio, Airtable
- **Easy updates**: Add/edit/delete credentials via UI
- **Masked display**: Only shows last 4 characters

### 4. Activity Log Tab
- **Real-time feed**: All agent activities
- **Detailed tracking**: Lead processing, calls, SMS
- **Status indicators**: Success, failed, pending
- **Timestamps**: Full audit trail

## CMO Agent Integration

The agent exposes API endpoints for the parent CMO agent to manage it.

### Authentication

CMO Agent uses API key authentication:

```bash
X-API-Key: your-cmo-agent-api-key
```

### Available Endpoints

#### 1. Get Agent Status
```bash
GET /api/cmo/status
Headers: X-API-Key: your-key

Response:
{
  "agent_id": "lead-qualification-agent-001",
  "agent_name": "Mesh Cowork Lead Qualifier",
  "agent_type": "lead_qualification",
  "status": "active",
  "role": "account_executive",
  "department": "cmo",
  "metrics": {
    "calls_today": 5,
    "sms_today": 5,
    "leads_today": 5
  }
}
```

#### 2. Send Command
```bash
POST /api/cmo/command
Headers: X-API-Key: your-key
Body:
{
  "command": "pause",
  "parameters": {}
}

Commands: start, stop, pause, resume, get_status, get_metrics
```

#### 3. Get Performance Report
```bash
GET /api/cmo/report/today
Headers: X-API-Key: your-key

Response:
{
  "period": "today",
  "total_leads": 10,
  "qualified_leads": 7,
  "calls_made": 10,
  "sms_sent": 10,
  "average_speed_to_lead": 4.5,
  "conversion_rate": 70.0
}
```

#### 4. Trigger Lead Processing
```bash
POST /api/cmo/trigger-lead
Headers: X-API-Key: your-key
Body:
{
  "fname": "John",
  "email": "john@example.com",
  "phone": "+15551234567",
  "what_kind_of_office_space_are_you_interested_in": "Private Office"
}
```

#### 5. Get Agent Capabilities
```bash
GET /api/cmo/capabilities
Headers: X-API-Key: your-key

Response:
{
  "agent_id": "lead-qualification-agent-001",
  "agent_type": "lead_qualification",
  "role": "account_executive",
  "department": "cmo",
  "capabilities": [
    "email_monitoring",
    "outbound_calling",
    "speech_recognition",
    "lead_qualification",
    "sms_followup",
    "crm_integration"
  ],
  "commands": ["start", "stop", "pause", "resume", "get_status"]
}
```

## Security Features

### 1. Authentication
- **JWT tokens**: Secure, stateless authentication
- **Password hashing**: bcrypt with salt
- **Token expiration**: 24-hour validity
- **Role-based access**: admin, cmo_agent, viewer

### 2. Credentials Storage
- **Encryption**: Fernet symmetric encryption
- **Masked display**: Never shows full credentials
- **Audit trail**: Tracks who updated what
- **Secure deletion**: Permanent removal

### 3. API Security
- **API key authentication**: For CMO agent
- **CORS protection**: Configurable origins
- **Rate limiting**: (Add in production)
- **HTTPS only**: (Configure in production)

## Database Schema

### Users Table
- `id`: Unique identifier
- `username`: Login username
- `email`: User email
- `hashed_password`: bcrypt hash
- `role`: admin, cmo_agent, viewer
- `is_active`: Account status
- `last_login`: Last login timestamp

### Agent Credentials Table
- `id`: Unique identifier
- `service_name`: gmail, twilio, airtable
- `credential_key`: api_key, account_sid, etc.
- `encrypted_value`: Fernet encrypted
- `updated_by`: User who updated

### Agent Activity Table
- `id`: Unique identifier
- `activity_type`: lead_processed, call_made, etc.
- `lead_phone`: Lead phone number
- `status`: success, failed, pending
- `details`: Additional information
- `timestamp`: Activity time

## Production Deployment

### 1. Update Security Settings

```bash
# Generate secure keys
python -c "import secrets; print(secrets.token_hex(32))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add to `.env`:
```bash
SECRET_KEY=<generated-key>
ENCRYPTION_KEY=<generated-key>
CMO_API_KEY=<strong-random-key>
```

### 2. Use PostgreSQL (Production)

Update `.env`:
```bash
DATABASE_URL=postgresql://user:password@localhost/leadagent
```

### 3. Enable HTTPS

Update CORS in `app/main.py`:
```python
allow_origins=["https://yourdomain.com"]
```

### 4. Set Up Reverse Proxy

Nginx config:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Testing the UI

### 1. Test Login
```bash
# Default credentials
Username: admin
Password: admin123
```

### 2. Test Email Processing
Paste this sample email in the Test Email tab:

```
A new lead has been captured from your Unbounce page!

Landing Page Details

Page Name
Mesh Cowork - Private Offices

URL
http://tour.meshcowork.com/private-offices/

Variant
A

Submitted Form Data

fname
Test User

email
test@example.com

phone
5551234567

what_kind_of_office_space_are_you_interested_in
Private Office

message
Test message

campaignid
12345
```

### 3. Test Credentials
Add a test credential:
- Service: `gmail`
- Key: `app_password`
- Value: `test123`

### 4. Test CMO API
```bash
curl -X GET http://localhost:8000/api/cmo/status \
  -H "X-API-Key: your-cmo-agent-api-key"
```

## Troubleshooting

### UI Not Loading
1. Check if FastAPI is running: `curl http://localhost:8000/health`
2. Check browser console for errors
3. Verify `frontend/index.html` exists

### Login Fails
1. Check if admin user exists: `python scripts/create_admin.py`
2. Verify database file exists: `ls agent_data.db`
3. Check logs: `tail -f logs/app.log`

### Credentials Not Saving
1. Verify `ENCRYPTION_KEY` is set in `.env`
2. Check database permissions
3. Verify user has admin role

### CMO API Returns 403
1. Verify `CMO_API_KEY` matches in both systems
2. Check header format: `X-API-Key` (case-sensitive)
3. Check logs for authentication errors

## Next Steps

1. ✅ Change default admin password
2. ✅ Set secure `SECRET_KEY` and `ENCRYPTION_KEY`
3. ✅ Configure CMO agent API key
4. ✅ Test email processing end-to-end
5. ✅ Set up monitoring/alerts
6. ✅ Deploy to production (Digital Ocean)
7. ✅ Configure HTTPS and domain
8. ✅ Integrate with CMO parent agent

## Support

For issues:
1. Check logs: `logs/app.log`
2. Verify environment variables
3. Test each component individually
4. Review API documentation: `http://localhost:8000/docs`
