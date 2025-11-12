# Quick Setup Guide

## Step-by-Step Setup (15 minutes)

### 1. Gmail App Password (2 min)
```
1. Go to: https://myaccount.google.com/security
2. Enable 2-Step Verification (if not already)
3. Click "App passwords"
4. Select "Mail" and "Other (Custom name)"
5. Name it "Lead Agent"
6. Copy the 16-character password
```

### 2. Twilio Account (5 min)
```
1. Sign up: https://www.twilio.com/try-twilio
2. Verify your phone number
3. Get a phone number:
   - Console → Phone Numbers → Buy a number
   - Select one with Voice + SMS capabilities
   - Cost: ~$1.15/month
4. Copy from dashboard:
   - Account SID
   - Auth Token
   - Phone Number
```

### 3. Airtable Base (5 min)
```
1. Sign up: https://airtable.com/signup
2. Create new base: "Mesh Leads"
3. Rename table to: "Leads"
4. Add fields (copy/paste from README.md Airtable section)
5. Get credentials:
   - Account → API → Generate API key
   - Base ID from URL (starts with "app")
```

### 4. Local Environment (3 min)
```bash
cd /Users/tabaribrannon/Documents/mesh_agents/cmo/adleadagent

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

### 5. Test Locally
```bash
# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Or use Docker Compose for everything
docker-compose up
```

### 6. Deploy to Digital Ocean

**Option A: App Platform (Easiest)**
```bash
# Push to GitHub first
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/adleadagent.git
git push -u origin main

# Install DO CLI
brew install doctl

# Login
doctl auth init

# Update .do/app.yaml with your GitHub repo
# Then deploy
doctl apps create --spec .do/app.yaml
```

**Option B: Droplet**
```bash
# Create droplet via DO dashboard
# SSH into it
ssh root@YOUR_DROPLET_IP

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
apt install docker-compose

# Clone and run
git clone https://github.com/YOUR_USERNAME/adleadagent.git
cd adleadagent
nano .env  # Add your credentials
docker-compose up -d
```

### 7. Configure Twilio Webhooks

After deployment, get your public URL and configure:

```
Twilio Console → Phone Numbers → Your Number → Configure

Voice & Fax:
  A CALL COMES IN → Webhook
  URL: https://your-app-url/webhooks/twilio/call-start
  HTTP POST

Status Callback URL:
  URL: https://your-app-url/webhooks/twilio/call-status
  HTTP POST
```

### 8. Test End-to-End

1. Send a test email to contact@meshcowork.com with Unbounce format
2. Watch logs: `docker-compose logs -f`
3. Should see:
   - Gmail poller detects email
   - Celery worker initiates call
   - Call placed to lead
   - Answers recorded
   - SMS sent
   - Airtable record created

## Environment Variables Checklist

Copy these to your `.env` file:

```bash
# Gmail
GMAIL_ADDRESS=contact@meshcowork.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx  # 16 chars from Google

# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_VOICE=Polly.Joanna

# Airtable
AIRTABLE_API_KEY=keyXXXXXXXXXXXXXX
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX
AIRTABLE_TABLE_NAME=Leads

# Redis (local)
REDIS_URL=redis://localhost:6379/0

# App Config
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
PUBLIC_WEBHOOK_URL=https://your-app.ondigitalocean.app

# Calendly
CALENDLY_LINK=https://calendly.com/meshcowork/book-a-tour-at-2020

# Polling
POLLING_INTERVAL_SECONDS=30

# Environment
ENVIRONMENT=production
```

## Verification Commands

```bash
# Check Redis
redis-cli ping
# Should return: PONG

# Check FastAPI
curl http://localhost:8000/health
# Should return: {"status":"healthy",...}

# Check Celery
celery -A app.celery_app inspect active
# Should show active workers

# Check logs
tail -f logs/app.log
tail -f logs/poller.log
```

## Common Issues

### "Authentication failed" (Gmail)
- Make sure 2FA is enabled
- Use App Password, not regular password
- Remove spaces from App Password

### "Unable to create record" (Twilio)
- Verify Account SID and Auth Token
- Check phone number format: +1234567890
- Verify phone number has Voice capability

### "404 Not Found" (Webhooks)
- Verify PUBLIC_WEBHOOK_URL is correct
- Make sure FastAPI is running
- Check ngrok/DO URL is accessible

### "No emails found"
- Check Gmail inbox for Unbounce emails
- Verify email subject contains "new lead has been captured"
- Check Gmail credentials

## Next Steps

1. ✅ Monitor first few leads closely
2. ✅ Adjust qualification logic if needed
3. ✅ Customize SMS messages
4. ✅ Set up monitoring/alerts
5. ✅ Review Airtable data regularly

## Support Resources

- Twilio Docs: https://www.twilio.com/docs
- FastAPI Docs: https://fastapi.tiangolo.com
- Celery Docs: https://docs.celeryq.dev
- Digital Ocean Docs: https://docs.digitalocean.com
