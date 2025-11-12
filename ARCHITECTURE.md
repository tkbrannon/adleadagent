# Lead Qualification Agent - Architecture

## Overview

This is a **production-ready Account Executive agent** that operates under the CMO department. It automates lead qualification through voice calls and integrates with a parent CMO agent for orchestration.

## Agent Identity

```yaml
Agent ID: lead-qualification-agent-001
Agent Name: Mesh Cowork Lead Qualifier
Agent Type: lead_qualification
Role: account_executive
Department: cmo
Version: 1.0.0
```

## Multi-Agent Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CMO Parent Agent                     │
│              (Orchestrates all CMO agents)              │
│                                                         │
│  • Marketing Agent                                      │
│  • Lead Qualification Agent (THIS)                     │
│  • Content Agent                                        │
│  • Analytics Agent                                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ API Key Authentication
                     │ REST API Communication
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│          Lead Qualification Agent (Account Exec)        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Admin UI  │  │  CMO Agent   │  │   Twilio     │  │
│  │  (Vue.js)   │  │     API      │  │  Webhooks    │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                │                  │           │
│         └────────────────┼──────────────────┘           │
│                          ▼                              │
│                  ┌───────────────┐                      │
│                  │   FastAPI     │                      │
│                  │   Backend     │                      │
│                  └───────┬───────┘                      │
│                          │                              │
│         ┌────────────────┼────────────────┐             │
│         │                │                │             │
│         ▼                ▼                ▼             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│  │  Gmail   │    │  Celery  │    │  Redis   │         │
│  │  Poller  │    │  Worker  │    │  Cache   │         │
│  └────┬─────┘    └────┬─────┘    └──────────┘         │
│       │               │                                 │
│       └───────────────┘                                 │
│                       │                                 │
│                       ▼                                 │
│           ┌───────────────────────┐                     │
│           │  External Services    │                     │
│           ├───────────────────────┤                     │
│           │  • Gmail (IMAP)       │                     │
│           │  • Twilio (Voice/SMS) │                     │
│           │  • Airtable (CRM)     │                     │
│           │  • Calendly           │                     │
│           └───────────────────────┘                     │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Admin UI (`frontend/index.html`)
**Technology**: Vue.js 3 + Tailwind CSS
**Purpose**: Web interface for agent management

**Features**:
- 🔐 JWT authentication
- 📊 Real-time dashboard
- 📧 Email testing interface
- 🔑 Encrypted credentials management
- 📝 Activity logging

**Endpoints Used**:
- `POST /api/auth/login` - User authentication
- `GET /api/admin/stats` - Dashboard metrics
- `POST /api/admin/test-email` - Test email processing
- `GET /api/admin/credentials` - List credentials
- `POST /api/admin/credentials` - Save credentials
- `GET /api/admin/activity` - Activity log

### 2. FastAPI Backend (`app/main.py`)
**Technology**: FastAPI + Uvicorn
**Purpose**: API server and webhook handler

**Responsibilities**:
- Handle Twilio webhooks (call events)
- Serve admin UI
- Provide CMO agent API
- Manage authentication
- Route requests to services

**Key Routes**:
- `/` - Serve UI or API info
- `/api/auth/*` - Authentication
- `/api/admin/*` - Admin operations
- `/api/cmo/*` - CMO agent integration
- `/webhooks/twilio/*` - Twilio callbacks

### 3. Gmail Poller (`poller.py`)
**Technology**: Python + IMAP
**Purpose**: Monitor Gmail for Unbounce leads

**Process**:
1. Connect to Gmail via IMAP
2. Search for unread Unbounce emails
3. Parse lead data from email body
4. Check Redis for duplicates
5. Queue lead for processing
6. Mark email as read

**Polling Interval**: 30 seconds (configurable)

### 4. Celery Worker (`app/tasks.py`)
**Technology**: Celery + Redis
**Purpose**: Async task processing

**Tasks**:
- `process_lead` - Initiate call, track metrics
- `send_followup_sms` - Send Calendly link
- `finalize_lead_record` - Save to Airtable

**Concurrency**: 2 workers (configurable)

### 5. Redis Cache (`app/services/redis_client.py`)
**Technology**: Redis 7
**Purpose**: State management and caching

**Data Stored**:
- Processed email IDs (prevent duplicates)
- Lead timestamps (speed-to-lead calculation)
- Call data (temporary storage during call)
- Call answers (speech recognition results)

**TTL**: 7 days for emails, 24 hours for call data

### 6. Database (`app/database.py`)
**Technology**: SQLAlchemy + SQLite (PostgreSQL in production)
**Purpose**: Persistent storage

**Tables**:
- `users` - Admin users and authentication
- `agent_credentials` - Encrypted API credentials
- `agent_activity` - Activity audit log
- `test_emails` - Test email submissions

### 7. Authentication (`app/auth.py`)
**Technology**: JWT + bcrypt
**Purpose**: Secure access control

**Features**:
- Password hashing (bcrypt)
- JWT token generation
- Role-based access (admin, cmo_agent, viewer)
- Token expiration (24 hours)

### 8. Services Layer

#### Gmail Service (`app/services/gmail_service.py`)
- IMAP connection management
- Email parsing (Unbounce format)
- Lead data extraction

#### Twilio Service (`app/services/twilio_service.py`)
- Outbound call initiation
- SMS sending
- TwiML generation (call flow)

#### Airtable Service (`app/services/airtable_service.py`)
- Lead record creation
- Data synchronization
- Schema validation

## Data Flow

### Lead Processing Flow

```
1. Unbounce Form Submitted
   ↓
2. Email sent to contact@meshcowork.com
   ↓
3. Gmail Poller detects email (30s interval)
   ↓
4. Parse lead data from email body
   ↓
5. Check Redis: Already processed?
   → Yes: Skip
   → No: Continue
   ↓
6. Mark as processed in Redis
   ↓
7. Queue Celery task: process_lead
   ↓
8. Celery Worker:
   - Record timestamp (speed-to-lead)
   - Initiate Twilio call
   - Store call data in Redis
   ↓
9. Twilio calls lead
   ↓
10. Lead answers → Webhook: /webhooks/twilio/call-start
    ↓
11. TwiML: Greeting + Question 1
    ↓
12. Speech Recognition → Webhook: /webhooks/twilio/answer/q1
    ↓
13. Store answer in Redis
    ↓
14. Repeat for Questions 2-5
    ↓
15. Call completes → Webhook: /webhooks/twilio/call-status
    ↓
16. Celery task: finalize_lead_record
    - Retrieve all answers from Redis
    - Apply qualification logic
    - Create Airtable record
    - Queue SMS task
    ↓
17. Celery task: send_followup_sms
    - Send Calendly link via SMS
    ↓
18. Done ✓
```

### CMO Agent Communication Flow

```
1. CMO Agent needs lead status
   ↓
2. HTTP GET /api/cmo/status
   Headers: X-API-Key: <key>
   ↓
3. Verify API key
   ↓
4. Query database for metrics
   ↓
5. Return JSON response:
   {
     "agent_id": "lead-qualification-agent-001",
     "status": "active",
     "metrics": {...}
   }
   ↓
6. CMO Agent receives status
```

## Security Architecture

### 1. Authentication Layers

```
┌─────────────────────────────────────┐
│         Admin UI Users              │
│    (JWT Token Authentication)       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      FastAPI Middleware             │
│  • Verify JWT signature             │
│  • Check token expiration           │
│  • Extract user info                │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Role-Based Access Control      │
│  • admin: Full access               │
│  • cmo_agent: Read metrics          │
│  • viewer: Read-only                │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│         CMO Parent Agent            │
│    (API Key Authentication)         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      API Key Verification           │
│  • Check X-API-Key header           │
│  • Compare with stored key          │
└─────────────────────────────────────┘
```

### 2. Credential Encryption

```python
# Encryption Flow
Plain Credential → Fernet Encryption → Database
                   (AES-128)

# Decryption Flow (when needed)
Database → Fernet Decryption → Use in API call
```

### 3. Security Best Practices

✅ **Implemented**:
- Password hashing (bcrypt with salt)
- JWT tokens (signed, expiring)
- Encrypted credential storage
- API key authentication
- CORS protection
- SQL injection prevention (SQLAlchemy ORM)
- XSS prevention (Vue.js escaping)

⚠️ **Production TODO**:
- Rate limiting
- HTTPS only
- IP whitelisting for CMO agent
- Audit logging
- Secrets rotation
- Database backups

## API Contracts

### CMO Agent API

#### 1. Get Agent Status
```http
GET /api/cmo/status
Headers:
  X-API-Key: <cmo-api-key>

Response 200:
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
  },
  "last_activity": "2024-01-15T10:30:00",
  "uptime_hours": 24.0
}
```

#### 2. Send Command
```http
POST /api/cmo/command
Headers:
  X-API-Key: <cmo-api-key>
  Content-Type: application/json

Body:
{
  "command": "pause",
  "parameters": {}
}

Commands:
- start: Start agent
- stop: Stop agent
- pause: Pause processing
- resume: Resume processing
- get_status: Get current status
- get_metrics: Get performance metrics

Response 200:
{
  "status": "success",
  "message": "Agent paused",
  "command": "pause"
}
```

#### 3. Trigger Lead Processing
```http
POST /api/cmo/trigger-lead
Headers:
  X-API-Key: <cmo-api-key>
  Content-Type: application/json

Body:
{
  "fname": "John",
  "email": "john@example.com",
  "phone": "+15551234567",
  "what_kind_of_office_space_are_you_interested_in": "Private Office",
  "message": "Optional message",
  "campaignid": "12345"
}

Response 200:
{
  "status": "success",
  "message": "Lead queued for processing",
  "task_id": "abc-123",
  "lead": {
    "name": "John",
    "phone": "+15551234567"
  }
}
```

#### 4. Get Performance Report
```http
GET /api/cmo/report/{period}
Headers:
  X-API-Key: <cmo-api-key>

Periods: today, week, month

Response 200:
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

#### 5. Get Agent Capabilities
```http
GET /api/cmo/capabilities
Headers:
  X-API-Key: <cmo-api-key>

Response 200:
{
  "agent_id": "lead-qualification-agent-001",
  "agent_name": "Mesh Cowork Lead Qualifier",
  "agent_type": "lead_qualification",
  "role": "account_executive",
  "department": "cmo",
  "version": "1.0.0",
  "capabilities": [
    "email_monitoring",
    "outbound_calling",
    "speech_recognition",
    "lead_qualification",
    "sms_followup",
    "crm_integration"
  ],
  "integrations": [
    "gmail",
    "twilio",
    "airtable",
    "calendly"
  ],
  "commands": [
    "start",
    "stop",
    "pause",
    "resume",
    "get_status",
    "get_metrics"
  ]
}
```

## Deployment Architecture

### Development
```
Local Machine
├── Redis (Docker)
├── FastAPI (localhost:8000)
├── Celery Worker
├── Gmail Poller
└── SQLite Database
```

### Production (Digital Ocean App Platform)
```
Digital Ocean
├── Web Service (FastAPI + UI)
│   └── Instances: 1-3 (auto-scaling)
├── Worker Service (Celery)
│   └── Instances: 2
├── Worker Service (Gmail Poller)
│   └── Instances: 1
└── Managed Redis
    └── 256MB RAM
```

## Performance Metrics

### Target SLAs
- **Speed-to-Lead**: < 5 seconds (email received → call initiated)
- **Call Connection**: < 10 seconds
- **SMS Delivery**: < 30 seconds
- **Airtable Sync**: < 5 seconds
- **API Response**: < 100ms

### Monitoring Points
- Email polling frequency
- Call success rate
- Speech recognition accuracy
- SMS delivery rate
- Qualification conversion rate
- System uptime

## Scalability

### Current Capacity
- **Leads/hour**: ~120 (30s polling)
- **Concurrent calls**: Limited by Twilio account
- **Database**: SQLite (suitable for < 10k records)

### Scaling Strategy
1. **Horizontal**: Add more Celery workers
2. **Vertical**: Increase worker concurrency
3. **Database**: Migrate to PostgreSQL
4. **Caching**: Add Redis cluster
5. **Load Balancing**: Multiple FastAPI instances

## Error Handling

### Failure Scenarios

1. **Gmail Connection Fails**
   - Retry with exponential backoff
   - Alert admin after 3 failures
   - Continue with cached credentials

2. **Twilio Call Fails**
   - Log failure to Airtable
   - Mark lead as "call_failed"
   - Send SMS anyway

3. **Speech Recognition Fails**
   - Repeat question once
   - If still fails, skip to next
   - Mark answer as "not_captured"

4. **Airtable Sync Fails**
   - Retry 3 times
   - Store in local DB as backup
   - Alert admin

5. **Redis Connection Lost**
   - Degrade gracefully
   - Use in-memory fallback
   - Alert admin

## Future Enhancements

### Phase 2
- [ ] Multi-language support
- [ ] Custom qualification rules (UI)
- [ ] A/B testing for call scripts
- [ ] Voice analytics (sentiment)
- [ ] Integration with more CRMs

### Phase 3
- [ ] AI-powered qualification
- [ ] Predictive lead scoring
- [ ] Automated follow-up sequences
- [ ] Video call support
- [ ] Mobile app for admins

## Maintenance

### Regular Tasks
- **Daily**: Check logs, monitor metrics
- **Weekly**: Review qualification accuracy
- **Monthly**: Update dependencies, backup database
- **Quarterly**: Security audit, performance review

### Backup Strategy
- Database: Daily automated backups
- Credentials: Encrypted backup to secure storage
- Logs: 30-day retention
- Configuration: Version controlled (Git)
