# Mesh Cowork Lead Qualification Agent

Automated lead qualification system that:
- 📧 Monitors Gmail for Unbounce lead notifications
- 📞 Places outbound voice calls via Twilio
- 🎤 Qualifies leads with 5 spoken questions (speech recognition)
- 💬 Sends SMS follow-up with Calendly link
- 📊 Logs all data + speed-to-lead metrics to Airtable

## Architecture

```
Gmail → Python Poller (30s) → Redis Queue → Celery Worker
                                              ↓
                                         Twilio Call
                                              ↓
                                    FastAPI Webhooks ← TwiML
                                              ↓
                                         Airtable
```

## Tech Stack

- **FastAPI**: Webhook server for Twilio callbacks
- **Celery + Redis**: Async task queue for lead processing
- **Twilio**: Voice calls and SMS
- **Gmail API**: Email monitoring via IMAP
- **Airtable**: Lead database and analytics
- **Digital Ocean**: App Platform deployment

## Prerequisites

### 1. Gmail Setup
1. Enable 2FA on your Gmail account
2. Generate an App Password:
   - Go to Google Account → Security → 2-Step Verification → App passwords
   - Create password for "Mail" app
   - Save this password for `.env` file

### 2. Twilio Setup
1. Sign up at [twilio.com](https://www.twilio.com)
2. Get a phone number with Voice capabilities
3. Copy Account SID and Auth Token from dashboard
4. Configure webhook URLs (after deployment):
   - Voice: `https://your-app.ondigitalocean.app/webhooks/twilio/call-start`
   - Status Callback: `https://your-app.ondigitalocean.app/webhooks/twilio/call-status`

### 3. Airtable Setup
1. Create a new base at [airtable.com](https://airtable.com)
2. Create a table named "Leads" with these fields:

**Text Fields:**
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

**Number Fields:**
- Call Duration (seconds) (Number)
- Speed to Lead (seconds) (Number)

**Date Fields:**
- Email Received At (Date)
- Call Initiated At (Date)
- Call Completed At (Date)
- SMS Sent At (Date)
- Created At (Date)

3. Get API key: Account → API → Generate API key
4. Get Base ID: From URL when viewing base (starts with `app...`)

## Local Development

### 1. Clone and Install

```bash
cd /Users/tabaribrannon/Documents/mesh_agents/cmo/adleadagent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Start Services

**Option A: Docker Compose (Recommended)**
```bash
docker-compose up
```

**Option B: Manual**
```bash
# Terminal 1: Redis
redis-server

# Terminal 2: FastAPI
python app/main.py

# Terminal 3: Celery Worker
celery -A app.celery_app worker --loglevel=info

# Terminal 4: Gmail Poller
python poller.py
```

### 4. Test Webhooks Locally

Use [ngrok](https://ngrok.com) to expose local server:
```bash
ngrok http 8000
```

Update `.env`:
```
PUBLIC_WEBHOOK_URL=https://your-ngrok-url.ngrok.io
```

Configure Twilio webhook URLs with your ngrok URL.

## Digital Ocean Deployment

### Method 1: App Platform (Recommended)

1. **Push to GitHub**
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/adleadagent.git
git push -u origin main
```

2. **Create App on Digital Ocean**
```bash
# Install doctl CLI
brew install doctl

# Authenticate
doctl auth init

# Deploy
doctl apps create --spec .do/app.yaml
```

3. **Configure Secrets in DO Dashboard**
   - Go to App → Settings → Environment Variables
   - Add all secrets from `.env.example`

4. **Update Twilio Webhooks**
   - Get your app URL from DO dashboard
   - Update Twilio webhook URLs with production URL

### Method 2: Droplet with Docker

1. **Create Droplet**
   - Ubuntu 22.04
   - Basic plan ($12/month)
   - Add SSH key

2. **SSH and Setup**
```bash
ssh root@your-droplet-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose

# Clone repo
git clone https://github.com/your-username/adleadagent.git
cd adleadagent

# Create .env file
nano .env
# Paste your environment variables

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f
```

3. **Setup Nginx (Optional)**
```bash
apt install nginx certbot python3-certbot-nginx

# Configure reverse proxy
nano /etc/nginx/sites-available/leadagent

# Add SSL
certbot --nginx -d your-domain.com
```

## Monitoring

### View Logs
```bash
# Docker Compose
docker-compose logs -f

# Individual services
docker-compose logs -f fastapi
docker-compose logs -f celery-worker
docker-compose logs -f gmail-poller

# Local files
tail -f logs/app.log
tail -f logs/poller.log
```

### Health Checks
```bash
# API health
curl http://localhost:8000/health

# Redis
redis-cli ping
```

## Call Flow

1. **Lead submits Unbounce form** → Email sent to contact@meshcowork.com
2. **Gmail Poller** detects email (every 30s)
3. **Celery Worker** initiates Twilio call
4. **Twilio calls lead** → Greeting + 5 questions:
   - Q1: How many years have you been in business?
   - Q2: How many employees do you have?
   - Q3: Do you currently have clients?
   - Q4: What is your monthly budget for office space?
   - Q5: Do you want a private office or are you interested in coworking?
5. **Speech recognition** captures answers
6. **Qualification logic** determines if lead is qualified
7. **SMS sent** with Calendly link
8. **Airtable record** created with all data + metrics

## Qualification Logic

**Unqualified if 3+ of these are true:**
- Less than 1 year in business
- Solo entrepreneur (no team)
- No current clients
- No clear budget

**Otherwise:** Qualified (with notes if 1-2 flags)

## Customization

### Change Questions
Edit `app/services/twilio_service.py`:
```python
QUESTIONS = {
    "q1": "Your custom question 1?",
    "q2": "Your custom question 2?",
    # ...
}
```

### Change Qualification Logic
Edit `app/tasks.py` → `_determine_qualification()` function

### Change Voice
Edit `.env`:
```
TWILIO_VOICE=Polly.Matthew  # Male voice
# Or: Polly.Joanna (female), Polly.Amy, etc.
```

### Change SMS Message
Edit `app/tasks.py` → `send_followup_sms()` function

## Troubleshooting

### No calls being made
1. Check Gmail poller logs: `docker-compose logs gmail-poller`
2. Verify Gmail credentials in `.env`
3. Check Redis connection: `redis-cli ping`
4. Verify Celery worker is running: `docker-compose logs celery-worker`

### Calls fail immediately
1. Verify Twilio credentials
2. Check phone number format (E.164: +1234567890)
3. Verify webhook URL is publicly accessible
4. Check Twilio debugger: https://www.twilio.com/console/debugger

### Speech recognition not working
1. Verify `PUBLIC_WEBHOOK_URL` is correct
2. Check webhook logs in FastAPI
3. Test with clear speech (avoid background noise)
4. Increase `timeout` in Gather if needed

### Airtable errors
1. Verify API key and Base ID
2. Check field names match exactly (case-sensitive)
3. Verify field types match schema

## Cost Estimate

### Digital Ocean App Platform
- Web service: $5/month
- 2x Worker services: $10/month
- Redis: $15/month
- **Total: ~$30/month**

### Twilio
- Phone number: $1.15/month
- Voice calls: $0.013/minute
- SMS: $0.0079/message
- **~$50-100/month** (100 leads)

### Other Services
- Gmail: Free
- Airtable: Free (up to 1,200 records/base)

## Support

For issues or questions:
1. Check logs first
2. Review Twilio debugger
3. Test webhooks with ngrok locally
4. Verify all environment variables are set

## License

MIT
