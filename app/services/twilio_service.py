"""Twilio service for voice calls and SMS"""
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from typing import Optional
from loguru import logger
from app.config import get_settings

settings = get_settings()


class TwilioService:
    """Twilio client for calls and SMS"""
    
    def __init__(self):
        self.client = Client(
            settings.twilio_account_sid,
            settings.twilio_auth_token
        )
        self.from_number = settings.twilio_phone_number
    
    def initiate_call(self, to_number: str, lead_name: str) -> Optional[str]:
        """Initiate outbound call to lead"""
        try:
            # Clean phone number
            to_number = self._format_phone(to_number)
            
            # Create call
            call = self.client.calls.create(
                to=to_number,
                from_=self.from_number,
                url=f"{settings.public_webhook_url}/webhooks/twilio/call-start",
                status_callback=f"{settings.public_webhook_url}/webhooks/twilio/call-status",
                status_callback_event=["initiated", "ringing", "answered", "completed"],
                method="POST",
                record=False  # Set to True if you want call recordings
            )
            
            logger.info(f"Call initiated to {to_number}: {call.sid}")
            return call.sid
        
        except Exception as e:
            logger.error(f"Failed to initiate call to {to_number}: {e}")
            return None
    
    def send_sms(self, to_number: str, message: str) -> bool:
        """Send SMS to lead"""
        try:
            to_number = self._format_phone(to_number)
            
            sms = self.client.messages.create(
                to=to_number,
                from_=self.from_number,
                body=message
            )
            
            logger.info(f"SMS sent to {to_number}: {sms.sid}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_number}: {e}")
            return False
    
    def _format_phone(self, phone: str) -> str:
        """Format phone number to E.164 format"""
        # Remove all non-numeric characters
        digits = ''.join(filter(str.isdigit, phone))
        
        # Add +1 if not present (assuming US numbers)
        if not digits.startswith('1') and len(digits) == 10:
            digits = '1' + digits
        
        return '+' + digits


class TwiMLGenerator:
    """Generate TwiML responses for call flow"""
    
    QUESTIONS = {
        "q1": "How many years have you been in business?",
        "q2": "How many employees do you have?",
        "q3": "Do you currently have clients?",
        "q4": "What is your monthly budget for office space?",
        "q5": "Do you want a private office or are you interested in coworking?"
    }
    
    @staticmethod
    def greeting(lead_name: str) -> str:
        """Initial greeting TwiML"""
        response = VoiceResponse()
        response.say(
            f"Hello {lead_name}, this is Mesh Cowork calling about your inquiry. "
            f"I'd like to ask you a few quick questions to better understand your needs. "
            f"This will only take a minute.",
            voice=settings.twilio_voice
        )
        response.redirect(f"{settings.public_webhook_url}/webhooks/twilio/question/q1")
        return str(response)
    
    @staticmethod
    def ask_question(question_id: str, call_sid: str = None, retry_count: int = 0) -> str:
        """Ask a qualification question with speech recognition"""
        response = VoiceResponse()
        
        question_text = TwiMLGenerator.QUESTIONS.get(question_id)
        
        if not question_text:
            # End call if invalid question
            response.say("Thank you for your time.", voice=settings.twilio_voice)
            response.hangup()
            return str(response)
        
        gather = Gather(
            input="speech",
            action=f"{settings.public_webhook_url}/webhooks/twilio/answer/{question_id}?retry={retry_count}",
            method="POST",
            timeout=5,
            speech_timeout="auto",
            language="en-US"
        )
        
        gather.say(question_text, voice=settings.twilio_voice)
        response.append(gather)
        
        # If no input, retry once then skip
        if retry_count < 1:
            response.say(
                "I didn't catch that. Let me ask again.",
                voice=settings.twilio_voice
            )
            response.redirect(f"{settings.public_webhook_url}/webhooks/twilio/question/{question_id}?retry={retry_count + 1}")
        else:
            # Max retries reached, move to next question
            response.say(
                "I'll skip that question for now.",
                voice=settings.twilio_voice
            )
            response.redirect(f"{settings.public_webhook_url}/webhooks/twilio/answer/{question_id}?skip=true")
        
        return str(response)
    
    @staticmethod
    def next_question(current_question_id: str) -> str:
        """Move to next question"""
        response = VoiceResponse()
        
        # Map to next question
        next_q = {
            "q1": "q2",
            "q2": "q3",
            "q3": "q4",
            "q4": "q5",
            "q5": None  # Last question
        }
        
        next_question_id = next_q.get(current_question_id)
        
        if next_question_id:
            response.redirect(f"{settings.public_webhook_url}/webhooks/twilio/question/{next_question_id}")
        else:
            # End of questions
            response.say(
                "Thank you for answering my questions. "
                "You'll receive a text message shortly with a link to schedule a tour. "
                "We look forward to meeting you!",
                voice=settings.twilio_voice
            )
            response.hangup()
        
        return str(response)
    
    @staticmethod
    def no_answer() -> str:
        """Handle no answer"""
        response = VoiceResponse()
        response.say(
            "We're sorry we missed you. You'll receive a text message with more information.",
            voice=settings.twilio_voice
        )
        response.hangup()
        return str(response)
    
    @staticmethod
    def error() -> str:
        """Handle errors"""
        response = VoiceResponse()
        response.say(
            "We're experiencing technical difficulties. Please call us back at your convenience.",
            voice=settings.twilio_voice
        )
        response.hangup()
        return str(response)


# Singleton instances
twilio_service = TwilioService()
twiml_generator = TwiMLGenerator()
