# Quick Start - Admin UI

## 5-Minute Setup

### 1. Install Dependencies
```bash
cd /Users/tabaribrannon/Documents/mesh_agents/cmo/adleadagent
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Create `.env` File
```bash
cp .env.example .env
nano .env
```

Add these new lines to your `.env`:
```bash
# Security
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# CMO Agent Integration
CMO_API_KEY=cmo-mesh-agent-2024-secure-key

# Database
DATABASE_URL=sqlite:///./agent_data.db
```

### 3. Create Admin User
```bash
python scripts/create_admin.py
```

Output:
```
✅ Admin user created successfully!
   Username: admin
   Email: admin@meshcowork.com
   Password: admin123

⚠️  IMPORTANT: Change the password after first login!
```

### 4. Start Everything
```bash
# Option A: Docker (Recommended)
docker-compose up

# Option B: Manual (3 terminals)
# Terminal 1: Redis
redis-server

# Terminal 2: FastAPI + UI
python app/main.py

# Terminal 3: Celery Worker
celery -A app.celery_app worker --loglevel=info

# Terminal 4: Gmail Poller
python poller.py
```

### 5. Access UI
Open browser: **http://localhost:8000**

Login:
- Username: `admin`
- Password: `admin123`

## What You Can Do

### ✅ Dashboard
- View real-time metrics (leads, calls, SMS)
- Monitor agent health
- Check speed-to-lead performance

### ✅ Test Email
Paste this sample email to test:

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
John Doe

email
john@example.com

phone
5551234567

what_kind_of_office_space_are_you_interested_in
Private Office

message
Looking for office space

campaignid
12345
```

Click "Process Test Email" → System will:
1. Parse the email
2. Initiate a call to the phone number
3. Ask 5 qualification questions
4. Send SMS with Calendly link
5. Log to Airtable

### ✅ Manage Credentials
Add your API credentials securely:

**Gmail:**
- Service: `gmail`
- Key: `app_password`
- Value: Your 16-char app password

**Twilio:**
- Service: `twilio`
- Key: `account_sid`
- Value: Your Twilio Account SID

- Service: `twilio`
- Key: `auth_token`
- Value: Your Twilio Auth Token

**Airtable:**
- Service: `airtable`
- Key: `api_key`
- Value: Your Airtable API key

### ✅ View Activity
See real-time log of:
- Leads processed
- Calls made
- SMS sent
- Qualification results

## CMO Agent Integration

Your CMO parent agent can manage this agent via API:

### Get Agent Status
```bash
curl -X GET http://localhost:8000/api/cmo/status \
  -H "X-API-Key: cmo-mesh-agent-2024-secure-key"
```

### Send Command
```bash
curl -X POST http://localhost:8000/api/cmo/command \
  -H "X-API-Key: cmo-mesh-agent-2024-secure-key" \
  -H "Content-Type: application/json" \
  -d '{"command": "get_status"}'
```

### Trigger Lead Processing
```bash
curl -X POST http://localhost:8000/api/cmo/trigger-lead \
  -H "X-API-Key: cmo-mesh-agent-2024-secure-key" \
  -H "Content-Type: application/json" \
  -d '{
    "fname": "Jane",
    "email": "jane@example.com",
    "phone": "+15551234567",
    "what_kind_of_office_space_are_you_interested_in": "Coworking"
  }'
```

### Get Performance Report
```bash
curl -X GET http://localhost:8000/api/cmo/report/today \
  -H "X-API-Key: cmo-mesh-agent-2024-secure-key"
```

## Agent Identity

This agent identifies itself as:
- **Agent ID**: `lead-qualification-agent-001`
- **Agent Type**: `lead_qualification`
- **Role**: `account_executive`
- **Department**: `cmo`
- **Capabilities**: email_monitoring, outbound_calling, speech_recognition, lead_qualification, sms_followup, crm_integration

## Architecture

```
┌──────────────────────────────────────┐
│         CMO Parent Agent             │
│   (Orchestrates multiple agents)     │
└──────────────┬───────────────────────┘
               │ API Key Auth
               ▼
┌──────────────────────────────────────┐
│   Lead Qualification Agent (This)    │
│   Role: Account Executive            │
├──────────────────────────────────────┤
│  • Monitors Gmail for leads          │
│  • Calls leads via Twilio            │
│  • Qualifies with 5 questions        │
│  • Sends SMS follow-up               │
│  • Logs to Airtable                  │
│  • Reports to CMO agent              │
└──────────────────────────────────────┘
```

## Next Steps

1. ✅ Change admin password (after first login)
2. ✅ Add your real API credentials
3. ✅ Test with a real email
4. ✅ Configure CMO agent to manage this agent
5. ✅ Deploy to Digital Ocean
6. ✅ Set up monitoring

## Troubleshooting

**UI won't load?**
```bash
# Check if FastAPI is running
curl http://localhost:8000/health

# Check logs
tail -f logs/app.log
```

**Can't login?**
```bash
# Recreate admin user
python scripts/create_admin.py
```

**Credentials not saving?**
```bash
# Check if ENCRYPTION_KEY is set
grep ENCRYPTION_KEY .env

# Generate new key if missing
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**CMO API returns 403?**
```bash
# Verify API key matches
grep CMO_API_KEY .env

# Test with curl
curl -X GET http://localhost:8000/api/cmo/capabilities \
  -H "X-API-Key: your-key-here"
```

## API Documentation

Full interactive API docs: **http://localhost:8000/docs**

This includes:
- All endpoints
- Request/response schemas
- Try-it-out functionality
- Authentication examples
