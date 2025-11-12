"""FastAPI application for Twilio webhooks"""
from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from loguru import logger
import sys
import os

from app.config import get_settings
from app.services import twiml_generator, redis_client
from app.tasks import finalize_lead_record
from app.database import init_db
from app.api import admin, cmo_agent
from app.auth import create_user, UserCreate, authenticate_user, create_access_token, Token
from app.database import get_db
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/app.log", rotation="500 MB", level="DEBUG")

settings = get_settings()

app = FastAPI(
    title="Mesh Cowork Lead Agent",
    description="Automated lead qualification system with CMO integration",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Include API routers
app.include_router(admin.router)
app.include_router(cmo_agent.router)

# Serve static files (frontend)
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def root():
    """Serve frontend or API info"""
    if os.path.exists("frontend/index.html"):
        with open("frontend/index.html") as f:
            return HTMLResponse(content=f.read())
    return {
        "status": "healthy",
        "service": "Mesh Cowork Lead Agent",
        "version": "1.0.0",
        "role": "account_executive",
        "department": "cmo"
    }


@app.post("/api/auth/login")
async def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Login endpoint"""
    user = authenticate_user(db, username, password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    
    return Token(access_token=access_token, token_type="bearer")


@app.post("/api/auth/register")
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register new user (first user only, or admin-created)"""
    # Check if any users exist
    from app.database import User
    user_count = db.query(User).count()
    
    if user_count > 0:
        raise HTTPException(status_code=403, detail="Registration disabled. Contact admin.")
    
    user = create_user(db, user_data)
    
    return {"message": "User created successfully", "username": user.username}


@app.get("/health")
async def health_check():
    """Detailed health check"""
    redis_healthy = redis_client.health_check()
    
    return {
        "status": "healthy" if redis_healthy else "degraded",
        "redis": "connected" if redis_healthy else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/webhooks/twilio/call-start", response_class=PlainTextResponse)
async def call_start(request: Request):
    """
    Initial webhook when call is answered
    Returns TwiML to greet lead and start questions
    """
    try:
        form_data = await request.form()
        call_sid = form_data.get("CallSid")
        
        logger.info(f"Call answered: {call_sid}")
        
        # Get lead data from Redis
        call_data = redis_client.get_call_data(call_sid)
        
        if not call_data:
            logger.error(f"No call data found for {call_sid}")
            return twiml_generator.error()
        
        lead_name = call_data.get("name", "there")
        
        # Return greeting TwiML
        return twiml_generator.greeting(lead_name)
    
    except Exception as e:
        logger.error(f"Error in call-start webhook: {e}")
        return twiml_generator.error()


@app.post("/webhooks/twilio/question/{question_id}", response_class=PlainTextResponse)
async def ask_question(question_id: str):
    """
    Ask a specific qualification question
    Returns TwiML with Gather for speech recognition
    """
    try:
        logger.info(f"Asking question: {question_id}")
        return twiml_generator.ask_question(question_id)
    
    except Exception as e:
        logger.error(f"Error asking question {question_id}: {e}")
        return twiml_generator.error()


@app.post("/webhooks/twilio/answer/{question_id}", response_class=PlainTextResponse)
async def process_answer(
    question_id: str,
    CallSid: str = Form(...),
    SpeechResult: str = Form(None),
    Confidence: float = Form(None)
):
    """
    Process answer from speech recognition
    Store answer and move to next question
    """
    try:
        logger.info(f"Answer received for {question_id}: {SpeechResult} (confidence: {Confidence})")
        
        # Store answer in Redis
        if SpeechResult:
            redis_client.update_call_answer(CallSid, question_id, SpeechResult)
        
        # Move to next question
        return twiml_generator.next_question(question_id)
    
    except Exception as e:
        logger.error(f"Error processing answer for {question_id}: {e}")
        return twiml_generator.error()


@app.post("/webhooks/twilio/call-status")
async def call_status(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    CallDuration: str = Form(None)
):
    """
    Receive call status updates from Twilio
    Finalize lead record when call completes
    """
    try:
        logger.info(f"Call status update: {CallSid} - {CallStatus}")
        
        # If call completed, finalize the lead record
        if CallStatus == "completed":
            call_duration = int(CallDuration) if CallDuration else 0
            
            # Trigger async task to finalize record
            finalize_lead_record.delay(CallSid, CallStatus, call_duration)
            
            # Update SMS sent timestamp
            call_data = redis_client.get_call_data(CallSid)
            if call_data:
                redis_client.update_call_answer(CallSid, "sms_sent_at", datetime.utcnow().isoformat())
        
        return {"status": "received"}
    
    except Exception as e:
        logger.error(f"Error processing call status: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/webhooks/twilio/sms-status")
async def sms_status(
    MessageSid: str = Form(...),
    MessageStatus: str = Form(...)
):
    """Receive SMS delivery status updates"""
    logger.info(f"SMS status: {MessageSid} - {MessageStatus}")
    return {"status": "received"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.fastapi_host,
        port=settings.fastapi_port,
        reload=True
    )
