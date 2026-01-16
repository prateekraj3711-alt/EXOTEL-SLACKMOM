"""
Exotel to Slack Complete System
Automated call recording transcription and Slack posting with Zapier integration
SMART AGENT DETECTION: Matches from_number OR to_number against agent database
"""

import os
import json
import logging
import asyncio
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import requests
import sqlite3
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Import customer lookup module
from customer_lookup import CustomerLookup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Exotel-Slack Complete System",
    description="Automated call transcription and Slack posting with smart agent detection",
    version="2.0.0"
)

# Configuration from environment
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')
SLACK_MISSED_CALL_WEBHOOK_URL = os.environ.get('SLACK_MISSED_CALL_WEBHOOK_URL')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
EXOTEL_API_KEY = os.environ.get('EXOTEL_API_KEY')
EXOTEL_API_TOKEN = os.environ.get('EXOTEL_API_TOKEN')
EXOTEL_SID = os.environ.get('EXOTEL_SID')
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'processed_calls.db')

# Support agent phone number for direction detection
SUPPORT_NUMBER = os.environ.get('SUPPORT_NUMBER', '09631084471')

# Rate limiting configuration
PROCESSING_DELAY = int(os.environ.get('PROCESSING_DELAY', '5'))
MAX_CONCURRENT_CALLS = int(os.environ.get('MAX_CONCURRENT_CALLS', '3'))

# Department filtering configuration
ALLOWED_DEPARTMENTS = os.environ.get('ALLOWED_DEPARTMENTS', 'CUSTOMER SUPPORT')
ALLOWED_DEPT_LIST = [d.strip() for d in ALLOWED_DEPARTMENTS.split(',')] if ALLOWED_DEPARTMENTS.upper() != 'ALL' else []

# Processing semaphore (use threading.Semaphore for cross-thread compatibility)
processing_semaphore = threading.Semaphore(MAX_CONCURRENT_CALLS)

# Agent mapping - load from file
AGENT_MAPPING = {}
def load_agent_mapping():
    """Load agent mapping from JSON file"""
    global AGENT_MAPPING
    try:
        agent_file = Path('agent_mapping.json')
        if agent_file.exists():
            with open(agent_file, 'r') as f:
                data = json.load(f)
                AGENT_MAPPING = {k: v for k, v in data.items() if not k.startswith('_')}
            logger.info(f"✅ Loaded {len(AGENT_MAPPING)} agent mappings from database")
        else:
            logger.warning("agent_mapping.json not found - using default mappings")
    except Exception as e:
        logger.error(f"Failed to load agent mapping: {e}")

load_agent_mapping()

# Pydantic Models
class ExotelWebhookPayload(BaseModel):
    """Payload from Exotel webhook"""
    call_id: str = Field(..., alias="Sid", description="Exotel Call ID (Sid)")
    from_number: str = Field(..., alias="From", description="Caller number")
    
    # Capture both 'To' and 'PhoneNumber' separately
    # 'To' is often the destination (Customer in outbound, VN/Agent in inbound)
    exotel_to: Optional[str] = Field(None, alias="To", description="Exotel 'To' field")
    
    # 'PhoneNumber' is usually the Virtual Number, but we treat it as just another source to check.
    to_number: str = Field(..., alias="PhoneNumber", description="Called number (PhoneNumber field)")
    
    # User requested to check PhoneNumberSid as well (sometimes contains number)
    phone_number_sid: Optional[str] = Field(None, alias="PhoneNumberSid", description="Phone Number SID")

    duration: int = Field(0, alias="Duration", description="Call duration in seconds")
    price: Optional[float] = Field(None, alias="Price", description="Call price")
    direction: str = Field(..., alias="Direction", description="Call direction (inbound/outbound)")
    recording_url: Optional[str] = Field(None, alias="RecordingUrl", description="Recording URL from Exotel")
    timestamp: Optional[str] = Field(None, alias="StartTime", description="Call timestamp")
    status: str = Field(default="completed", alias="Status", description="Call status")
    
    # Optional fields that might be present
    agent_phone: Optional[str] = Field(None, description="Agent phone number")
    agent_name: Optional[str] = Field(None, description="Agent name")
    agent_slack_handle: Optional[str] = Field(None, description="Agent Slack handle")
    department: str = Field(default="Customer Success", description="Department")
    customer_segment: str = Field(default="General", description="Customer segment")

    class Config:
        allow_population_by_field_name = True


class WebhookResponse(BaseModel):
    """Response to webhook"""
    success: bool
    message: str
    call_id: str
    timestamp: str


# Database Manager
class DatabaseManager:
    """Manage SQLite database for duplicate prevention"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_calls (
                    call_id TEXT PRIMARY KEY,
                    from_number TEXT,
                    to_number TEXT,
                    duration INTEGER,
                    timestamp TEXT,
                    processed_at TEXT,
                    transcription_text TEXT,
                    slack_posted BOOLEAN,
                    status TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON processed_calls(timestamp)
            """)
            conn.commit()
        logger.info(f"Database initialized at {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def is_call_processed(self, call_id: str) -> bool:
        """Check if call has been successfully processed and posted to Slack"""
        with self._get_connection() as conn:
            # Check if call was ever successfully posted to Slack (regardless of time)
            result = conn.execute(
                "SELECT call_id, slack_posted, processed_at FROM processed_calls WHERE call_id = ? AND slack_posted = 1",
                (call_id,)
            ).fetchone()
            if result:
                processed_at = result[2] if result[2] else 'unknown'
                logger.info(f"✅ Call {call_id} already successfully posted to Slack at {processed_at}")
                return True
            return False
    
    def mark_call_processing(self, call_id: str, call_data: Dict[str, Any]) -> bool:
        """Mark call as being processed (prevents race condition)
        Returns True if successfully marked, False if already exists
        BULLETPROOF: No call will ever be processed twice
        """
        with self._get_connection() as conn:
            # Check if call already exists (any status, any time)
            existing = conn.execute(
                "SELECT call_id, slack_posted, status, processed_at FROM processed_calls WHERE call_id = ?",
                (call_id,)
            ).fetchone()
            
            if existing:
                call_status = existing[2] if existing[2] else 'unknown'
                slack_posted = existing[1] if existing[1] else False
                processed_at = existing[3] if existing[3] else 'unknown'
                
                # Block if call was already posted to Slack (PERMANENT BLOCK)
                if slack_posted:
                    logger.warning(f"🚫 PERMANENT DUPLICATE BLOCK: {call_id}")
                    logger.warning(f"   Status: {call_status}")
                    logger.warning(f"   Slack Posted: {slack_posted}")
                    logger.warning(f"   Processed At: {processed_at}")
                    logger.warning(f"   BLOCKING: Call already posted to Slack (Zapier polling detected)")
                    return False
                
                # Block if call is currently being processed (RACE CONDITION PREVENTION)
                if call_status == 'processing':
                    logger.warning(f"🚫 PROCESSING DUPLICATE BLOCK: {call_id}")
                    logger.warning(f"   Status: {call_status}")
                    logger.warning(f"   Processed At: {processed_at}")
                    logger.warning(f"   BLOCKING: Call currently being processed")
                    return False
                
                # Call exists but failed - allow retry only if it's been more than 1 hour
                one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
                if processed_at < one_hour_ago:
                    logger.info(f"🔄 RETRYING FAILED CALL: {call_id}")
                    logger.info(f"   Previous Status: {call_status}")
                    logger.info(f"   Previous Slack Posted: {slack_posted}")
                    logger.info(f"   Previous Processed At: {processed_at}")
                    # Update the existing record to processing
                    conn.execute("""
                        UPDATE processed_calls 
                        SET status = 'processing', processed_at = ?, transcription_text = 'Processing...'
                        WHERE call_id = ?
                    """, (datetime.utcnow().isoformat(), call_id))
                    conn.commit()
                    logger.info(f"🔄 RETRY LOCK: Marked call {call_id} as processing (retry)")
                    return True
                else:
                    # Call failed recently - block retry
                    logger.warning(f"🚫 RECENT FAILURE BLOCK: {call_id}")
                    logger.warning(f"   Previous Status: {call_status}")
                    logger.warning(f"   Processed At: {processed_at}")
                    logger.warning(f"   BLOCKING: Call failed recently, wait 1 hour before retry")
                    return False
            
            # Insert new call as processing with BULLETPROOF locking
            conn.execute("""
                INSERT INTO processed_calls 
                (call_id, from_number, to_number, duration, timestamp, processed_at, 
                 transcription_text, slack_posted, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                call_id,
                call_data['from_number'],
                call_data['to_number'],
                call_data['duration'],
                call_data.get('timestamp', datetime.utcnow().isoformat()),
                datetime.utcnow().isoformat(),
                'Processing...',
                False,
                'processing'
            ))
            conn.commit()
        logger.info(f"🔒 BULLETPROOF LOCK: Marked call {call_id} as processing")
        return True
    
    def mark_call_processed(self, call_data: Dict[str, Any], transcription: str, success: bool):
        """Mark call as processed"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO processed_calls 
                (call_id, from_number, to_number, duration, timestamp, processed_at, 
                 transcription_text, slack_posted, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                call_data['call_id'],
                call_data['from_number'],
                call_data['to_number'],
                call_data['duration'],
                call_data.get('timestamp', datetime.utcnow().isoformat()),
                datetime.utcnow().isoformat(),
                transcription,
                success,
                'completed' if success else 'failed'
            ))
            conn.commit()
        logger.info(f"Marked call {call_data['call_id']} as processed")
    
    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics"""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM processed_calls").fetchone()[0]
            posted = conn.execute(
                "SELECT COUNT(*) FROM processed_calls WHERE slack_posted = 1"
            ).fetchone()[0]
            failed = conn.execute(
                "SELECT COUNT(*) FROM processed_calls WHERE status = 'failed'"
            ).fetchone()[0]
            
            return {
                'total_processed': total,
                'successfully_posted': posted,
                'failed': failed
            }


# Initialize database
db_manager = DatabaseManager(DATABASE_PATH)


# Transcription Service using OpenAI Whisper
class TranscriptionService:
    """Handle audio transcription using OpenAI Whisper"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/audio/transcriptions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def download_recording(self, recording_url: str, call_id: str) -> str:
        """Download recording from Exotel"""
        try:
            downloads_dir = Path("downloads")
            downloads_dir.mkdir(exist_ok=True)
            
            file_path = downloads_dir / f"{call_id}.mp3"
            
            auth = (EXOTEL_API_KEY, EXOTEL_API_TOKEN) if EXOTEL_API_KEY else None
            
            response = requests.get(recording_url, auth=auth, timeout=60)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded recording to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to download recording: {e}")
            raise
    
    def transcribe_audio(self, audio_file_path: str) -> str:
        """Transcribe audio file using OpenAI Whisper"""
        try:
            logger.info("Transcribing audio with OpenAI Whisper...")
            
            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'file': (os.path.basename(audio_file_path), audio_file, 'audio/mpeg')
                }
                data = {
                    'model': 'whisper-1',
                    'language': 'en',
                    'response_format': 'json'
                }
                
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    files=files,
                    data=data,
                    timeout=120
                )
            
            response.raise_for_status()
            result = response.json()
            
            transcription = result.get('text', '')
            
            if transcription:
                logger.info(f"✅ Transcription completed: {len(transcription)} characters")
                return transcription
            
            raise Exception("No transcription text returned from OpenAI Whisper")
            
        except Exception as e:
            logger.error(f"❌ OpenAI Whisper transcription error: {e}")
            raise
        finally:
            try:
                if os.path.exists(audio_file_path):
                    os.remove(audio_file_path)
                    logger.info(f"Cleaned up audio file: {audio_file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup audio file: {e}")


# MOM Generator Service
class MOMGenerator:
    """Generate Meeting Minutes from transcription using OpenAI"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_mom(self, transcription: str, customer_name: str = "Customer", agent_name: str = "Agent") -> str:
        """Generate structured Meeting Minutes from transcription with retry logic
        
        Args:
            transcription: The call transcript text
            customer_name: Name of the customer (from Google Sheets or phone number)
            agent_name: Name of the agent (from agent database)
        """
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** attempt)
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} after {delay}s delay...")
                    time.sleep(delay)
                
                logger.info(f"Generating MOM from transcription (attempt {attempt + 1}/{max_retries})...")
                logger.info(f"   Customer: {customer_name}")
                logger.info(f"   Agent: {agent_name}")
                
                prompt = f"""You are an expert at creating concise Meeting Minutes (MOM) for customer support calls.

CRITICAL SPEAKER INFORMATION:
- Customer Name: {customer_name}
- Agent Name: {agent_name}

Analyze this call transcription and create a structured MOM with these sections:

**Tone:** [REQUIRED - Choose ONE: "Normal" or "Escalation"]
Determine if the call is an escalation (customer is frustrated/angry/upset/demanding manager) or normal (regular inquiry/polite conversation).

**Mood Analysis:** [REQUIRED - Choose ONE: "Satisfied", "Neutral", "Frustrated", "Angry", "Confused", "Relieved"]
Analyze the customer's emotional state throughout the call and overall satisfaction level.

**Concern Type:** [REQUIRED - Choose ONE or MORE from: Case Status Update, Insufficiency, Recharge, Product, Miscellaneous, Employment Verification, Document Issue, Payment Issue, Technical Problem]
Categorize the main concern or issue type discussed. Can be multiple types separated by commas.

**Issue Type:** [REQUIRED - Choose ONE or MORE from: Case Status Update, Insufficiency, Recharge, Product, Miscellaneous]
Categorize the main topics discussed. Can be multiple types separated by commas.

**Customer Issue:**
[Summarize the main problem/concern the customer is reporting - minimum 1 line]

**Key Discussion Points:**
[CRITICAL: Extract 5-8 key discussion points in natural narrative format]
[MANDATORY FORMAT: Write naturally without explicit speaker labels - identify speaker within the sentence]
[Use natural flow like "Agent confirmed..." or "Customer asked..." - no "Customer:" or "Agent (Name):" prefixes]
[PARAPHRASE the conversation while RETAINING the ACTUAL CONTEXT and meaning]
[Make it look professional and polished - clean up filler words, hesitations, and casual speech]
[Keep all important details, numbers, names, deadlines, and specific information]
[CORRECT FORMAT EXAMPLES (Paraphrased - Professional Narrative):]
[- Agent confirmed verification for Maksud Ariba Allay and identified a minor discrepancy.]
[- Customer asked for confirmation on when the report will be ready.]
[- Agent committed to completing it by end of day.]
[- Customer requested a BVG report for multiple candidates and needs it promptly.]
[- Agent offered to send the report immediately and asked if the customer wants reports for all completed candidates.]
[WRONG FORMAT: "Customer: Requested..." or "Agent (Name): Offered..." - DO NOT use explicit speaker labels]
[WRONG FORMAT: "The agent mentioned..." - Use "Agent mentioned..." instead]
[Paraphrase naturally while preserving all critical context, timelines, commitments, and specific details]

**Action Items:**
[List specific actions needed to resolve this issue - each action on a new line]

**Resolution Status:**
[State if issue was resolved or pending]

CRITICAL REQUIREMENTS: 
- The MOM must have AT LEAST 3 substantial lines of content
- For "Key Discussion Points" - Use NATURAL NARRATIVE FORMAT without explicit speaker labels (e.g., "Agent confirmed..." or "Customer asked...")
- PARAPHRASE the conversation professionally while RETAINING all context and meaning
- Clean up filler words, hesitations, and casual speech to make it look polished
- Keep all important details: numbers, names, deadlines, commitments, and specific information
- Each section should be detailed and informative
- Include specific details from the transcription
- MUST include Tone, Mood Analysis, and Concern Type at the beginning
- Mood Analysis is MANDATORY for customer satisfaction tracking

FORMAT:
**Tone:** [Normal/Escalation]
**Mood Analysis:** [Satisfied/Neutral/Frustrated/Angry/Confused/Relieved]
**Concern Type:** [Case Status Update/Insufficiency/Recharge/Product/Miscellaneous/Employment Verification/Document Issue/Payment Issue/Technical Problem]
**Issue Type:** [One or more categories]

**Customer Issue:**
[Summary]

**Key Discussion Points:**
[Narrative format discussion points - natural flow without explicit speaker labels, professional and polished]

**Action Items:**
[Actions]

**Resolution Status:**
[Status]

Transcription:
{transcription}

Create the MOM in a clear, professional format with actual conversation content."""

                payload = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"You are a professional customer support analyst who creates detailed meeting minutes. CRITICAL: In Key Discussion Points, write in natural narrative format WITHOUT explicit speaker labels. Identify the speaker naturally within each sentence (e.g., 'Agent confirmed...' or 'Customer asked...'). Paraphrase professionally while retaining all context. Clean up filler words and casual speech to make it polished. Example: '- Agent confirmed verification for Maksud Ariba Allay and identified a minor discrepancy.' or '- Customer asked for confirmation on when the report will be ready.'. DO NOT use 'Customer:' or 'Agent (Name):' prefixes. DO NOT use quote marks. ALWAYS include Tone, Mood Analysis, and Concern Type fields."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 800
                }
                
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                
                response.raise_for_status()
                result = response.json()
                
                if 'choices' in result and len(result['choices']) > 0:
                    mom = result['choices'][0]['message']['content'].strip()
                    logger.info(f"✅ MOM generated successfully: {len(mom)} characters")
                    return mom
                
                raise Exception("No MOM generated from OpenAI")
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.warning(f"⚠️ OpenAI rate limit hit (429) - attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        logger.error("❌ Max retries reached for OpenAI rate limit")
                elif e.response.status_code == 401:
                    logger.error("❌ OpenAI API authentication failed - check API key")
                    break
                else:
                    logger.error(f"❌ OpenAI API HTTP error: {e.response.status_code}")
                    if attempt < max_retries - 1:
                        continue
                    break
            except Exception as e:
                logger.error(f"❌ MOM generation error: {e}")
                if attempt < max_retries - 1:
                    continue
                break
        
        logger.error("OpenAI API unavailable after all retries. Using structured fallback.")
        logger.warning("Falling back to structured transcription with 3+ lines")
        
        fallback_mom = f"""**Tone:** Normal
**Mood Analysis:** Neutral
**Concern Type:** Miscellaneous
**Issue Type:** Miscellaneous

**Call Summary:**
The call was regarding a customer support inquiry. The conversation lasted {len(transcription)} characters.

**Transcription:**
{transcription[:400] if len(transcription) > 400 else transcription}

**Note:** Automated MOM generation temporarily unavailable (OpenAI rate limit). This is a direct transcription of the call.

**Action Required:**
• Review call transcription for customer concerns
• Follow up with customer if needed
• Update ticket with call details"""
        
        return fallback_mom


# Google Drive Integration Service
class GoogleDriveService:
    """Upload transcript files to Google Drive for automatic NotebookLM sync"""
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.service = None
        self.folder_id = None
        
    def setup_drive_service(self):
        """Initialize Google Drive API service"""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            import pickle
            import os
            
            SCOPES = ['https://www.googleapis.com/auth/drive.file']
            
            creds = None
            # Check if token.pickle exists
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
            
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if self.client_id and self.client_secret:
                        from google_auth_oauthlib.flow import Flow
                        flow = Flow.from_client_config(
                            {
                                "web": {
                                    "client_id": self.client_id,
                                    "client_secret": self.client_secret,
                                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                                    "token_uri": "https://oauth2.googleapis.com/token",
                                    "redirect_uris": ["http://localhost:8080"]
                                }
                            },
                            SCOPES
                        )
                        # For server deployment, we'll use a different approach
                        logger.warning("Google Drive OAuth requires manual setup - using local file fallback")
                        return False
                    else:
                        logger.warning("Google Drive credentials not found - file upload disabled")
                        return False
                
                # Save credentials for next run
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
            
            self.service = build('drive', 'v3', credentials=creds)
            
            # Create or find the transcripts folder
            self.folder_id = self._create_or_find_folder()
            return True
            
        except ImportError:
            logger.warning("Google Drive libraries not installed - file upload disabled")
            return False
        except Exception as e:
            logger.error(f"Failed to setup Google Drive service: {e}")
            return False
    
    def _create_or_find_folder(self):
        """Create or find the Exotel Transcripts folder in Google Drive"""
        try:
            # Search for existing folder
            results = self.service.files().list(
                q="name='Exotel Transcripts' and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name)"
            ).execute()
            
            folders = results.get('files', [])
            
            if folders:
                # Folder exists, return its ID
                folder_id = folders[0]['id']
                logger.info(f"Found existing 'Exotel Transcripts' folder: {folder_id}")
                return folder_id
            else:
                # Create new folder
                folder_metadata = {
                    'name': 'Exotel Transcripts',
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                
                folder = self.service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()
                
                folder_id = folder.get('id')
                logger.info(f"Created new 'Exotel Transcripts' folder: {folder_id}")
                return folder_id
                
        except Exception as e:
            logger.error(f"Failed to create/find folder: {e}")
            return None
    
    def send_transcript(self, transcript: str, call_data: Dict[str, Any]) -> bool:
        """Upload structured transcript file to Google Drive for automatic NotebookLM sync"""
        try:
            call_id = call_data.get('call_id', 'unknown')
            customer_number = call_data.get('from_number', 'unknown')
            agent_number = call_data.get('to_number', 'unknown')
            timestamp = call_data.get('start_time', 'unknown')
            duration = call_data.get('duration', 'unknown')
            
            # Create structured transcript content for NotebookLM
            structured_transcript = f"""CALL TRANSCRIPT - {call_id}
========================================

CALL METADATA:
- Call ID: {call_id}
- Customer Number: {customer_number}
- Agent Number: {agent_number}
- Date/Time: {timestamp}
- Duration: {duration}
- Source: Exotel Call Recording

TRANSCRIPT CONTENT:
{transcript}

========================================
END OF TRANSCRIPT - {call_id}
"""
            
            # Setup Google Drive service if not already done
            if not self.service:
                if not self.setup_drive_service():
                    logger.warning("Google Drive service not available - saving to local file instead")
                    return self._save_local_file(structured_transcript, call_id, timestamp)
            
            # Upload to Google Drive
            filename = f"transcript_{call_id}_{timestamp.replace(':', '-').replace(' ', '_')}.txt"
            
            # Create file metadata
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id] if self.folder_id else []
            }
            
            # Create media upload
            from googleapiclient.http import MediaIoBaseUpload
            import io
            
            media = MediaIoBaseUpload(
                io.BytesIO(structured_transcript.encode('utf-8')),
                mimetype='text/plain',
                resumable=True
            )
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"📚 Transcript uploaded to Google Drive: {filename}")
            logger.info(f"📄 Transcript length: {len(transcript)} characters")
            logger.info(f"🔗 Google Drive file ID: {file_id}")
            logger.info(f"📁 File will automatically appear in NotebookLM when Google Drive is connected")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upload transcript to Google Drive: {e}")
            # Fallback to local file
            logger.info("Falling back to local file storage...")
            return self._save_local_file(structured_transcript, call_id, timestamp)
    
    def _save_local_file(self, structured_transcript: str, call_id: str, timestamp: str) -> bool:
        """Fallback method to save transcript locally"""
        try:
            import os
            filename = f"transcript_{call_id}_{timestamp.replace(':', '-').replace(' ', '_')}.txt"
            filepath = f"transcripts/{filename}"
            
            # Create transcripts directory if it doesn't exist
            os.makedirs("transcripts", exist_ok=True)
            
            # Write transcript to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(structured_transcript)
            
            logger.info(f"📚 Transcript saved to local file: {filepath}")
            logger.info(f"📁 File ready for manual upload to NotebookLM: {filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save local transcript file: {e}")
            return False


# Slack User Lookup Service
class SlackUserLookup:
    """Query Slack workspace to find user info by phone number"""
    
    def __init__(self, bot_token: Optional[str]):
        self.bot_token = bot_token
        self.users_cache = {}
        self.cache_loaded = False
    
    def normalize_phone(self, phone: str) -> str:
        """Normalize phone number for comparison"""
        normalized = ''.join(filter(str.isdigit, phone))
        # Remove country code +91
        if normalized.startswith('91') and len(normalized) == 12:
            normalized = normalized[2:]
        # Remove leading 0
        if normalized.startswith('0') and len(normalized) == 11:
            normalized = normalized[1:]
        return normalized
    
    def load_users(self) -> bool:
        """Load all users from Slack workspace"""
        if not self.bot_token:
            logger.warning("Slack bot token not configured - cannot lookup users")
            return False
        
        try:
            logger.info("Loading users from Slack workspace...")
            
            response = requests.get(
                "https://slack.com/api/users.list",
                headers={"Authorization": f"Bearer {self.bot_token}"},
                timeout=10
            )
            
            response.raise_for_status()
            data = response.json()
            
            if not data.get('ok'):
                logger.error(f"Slack API error: {data.get('error')}")
                return False
            
            for member in data.get('members', []):
                if member.get('deleted') or member.get('is_bot'):
                    continue
                
                profile = member.get('profile', {})
                phone = profile.get('phone', '')
                
                if phone:
                    normalized_phone = self.normalize_phone(phone)
                    self.users_cache[normalized_phone] = {
                        'name': profile.get('real_name', profile.get('display_name', 'Unknown')),
                        'slack_handle': member.get('name', 'unknown'),
                        'user_id': member.get('id', ''),  # SLACK USER ID FOR TAGGING
                        'email': profile.get('email', ''),
                        'title': profile.get('title', ''),
                        'department': profile.get('fields', {}).get('department', 'Customer Success')
                    }
            
            self.cache_loaded = True
            logger.info(f"✅ Loaded {len(self.users_cache)} users from Slack workspace")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load Slack users: {e}")
            return False
    
    def get_user_by_phone(self, phone: str) -> Optional[Dict[str, str]]:
        """Look up user in Slack by phone number"""
        if not self.cache_loaded:
            self.load_users()
        
        normalized = self.normalize_phone(phone)
        user = self.users_cache.get(normalized)
        
        if user:
            logger.info(f"📧 Found Slack user: {user['name']} ({user['email']}) - Will tag as <@{user['user_id']}>")
        
        return user


slack_user_lookup = SlackUserLookup(SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None


# Slack Formatter
class SlackFormatter:
    """Format call data for Slack posting with smart agent detection"""
    
    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize phone number for comparison"""
        normalized = phone.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
        # Remove country code +91
        if normalized.startswith('91') and len(normalized) == 12:
            normalized = normalized[2:]
        # Remove leading 0
        if normalized.startswith('0') and len(normalized) == 11:
            normalized = normalized[1:]
        return normalized
    
    @staticmethod
    def find_agent_from_call(from_number: str, to_number: str, extra_number: str = None, phone_number_sid: str = None) -> Optional[Dict[str, str]]:
        """
        SMART AGENT DETECTION:
        Check from_number, to_number, extra_number, and phone_number_sid against authorized agent database.
        Returns agent info if found, None otherwise.
        """
        candidates = [
            (from_number, "outgoing"),  # If from matches, agent is caller (outgoing)
            (to_number, "incoming"),    # If to matches, agent is receiver (incoming)
        ]
        if extra_number:
            candidates.append((extra_number, "incoming")) 
        if phone_number_sid:
            candidates.append((phone_number_sid, "incoming"))

        logger.debug(f"🔍 Checking for agent match in: {candidates}")
        
        # Check agent_mapping.json database
        for mapped_phone, agent_data in AGENT_MAPPING.items():
            mapped_clean = SlackFormatter.normalize_phone(mapped_phone)
            
            for candidate_phone, direction in candidates:
                if not candidate_phone:
                    continue
                    
                candidate_clean = SlackFormatter.normalize_phone(candidate_phone)
                
                if mapped_clean == candidate_clean:
                    email = agent_data.get('email', '')
                    name = agent_data.get('name', 'Support Agent')
                    
                    # Try to enrich with Slack info if available
                    slack_mention = f"📧 {email}" if email else "@support"
                    user_id = ""
                    if slack_user_lookup:
                        # try looking up by the matched phone
                        slack_user = slack_user_lookup.get_user_by_phone(mapped_phone)
                        if slack_user:
                            user_id = slack_user.get('user_id', '')
                            slack_mention = f"<@{user_id}>" if user_id else slack_mention

                    logger.info(f"✅ Found authorized agent ({candidate_phone}): {name}")
                    return {
                        "phone": candidate_phone,
                        "name": name,
                        "slack_mention": slack_mention,
                        "email": email,
                        "user_id": user_id,
                        "department": agent_data.get('department', 'CUSTOMER SUPPORT'),
                        "team": agent_data.get('team', 'Support'),
                        "direction": direction
                    }
        
        return None
    
    @staticmethod
    def format_message(call_data: Dict[str, Any], mom: str, transcript: str = "") -> Dict[str, Any]:
        """Format Slack message with smart agent detection and email tagging
        Returns dict with 'message', 'customer_number', 'agent_name', 'timestamp'
        """
        
        # SMART DETECTION: Find which number belongs to support agent
        agent_info = SlackFormatter.find_agent_from_call(
            call_data['from_number'],
            call_data['to_number'],
            call_data.get('exotel_to'),
            call_data.get('phone_number_sid')
        )
        
        if agent_info:
            # Agent found in database
            agent_phone = agent_info['phone']
            agent_name = agent_info['name']
            agent_mention = agent_info['slack_mention']
            agent_email = agent_info.get('email', '')
            department = agent_info['department']
            direction = agent_info['direction']
            
            # Determine support vs customer number based on which one is the agent
            if direction == "outgoing":
                support_number = call_data['from_number']
                customer_number = call_data['to_number']
            else:
                support_number = call_data['to_number']
                customer_number = call_data['from_number']
            
            logger.info(f"📊 Call Summary: Agent={agent_name}, Direction={direction}")
        else:
            # No agent found - use fallback
            logger.warning(f"⚠️ No agent found in database for call {call_data['call_id']}")
            logger.warning(f"   From: {call_data['from_number']}")
            logger.warning(f"   To: {call_data['to_number']}")
            
            # Assume incoming call (customer called support) as default
            support_number = call_data.get('to_number', 'Unknown')
            customer_number = call_data.get('from_number', 'Unknown')
            agent_name = call_data.get('agent_name', 'Unknown Agent')
            agent_mention = '@support'
            agent_email = call_data.get('agent_email', '')
            department = call_data.get('department', 'Customer Success')
            direction = "incoming"  # Default assumption
        
        # Format timestamp - CONVERT TO IST
        timestamp = call_data.get('timestamp', datetime.utcnow().isoformat())
        
        # Default to UTC now
        dt_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        
        try:
            if 'T' in timestamp:
                # ISO Format (UTC): "2026-01-06T13:02:33.989386Z"
                # Parse as UTC, then convert to IST
                dt_utc = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                dt_ist = dt_utc + timedelta(hours=5, minutes=30)
            elif ' ' in timestamp:
                # Exotel/Zapier Format (Likely ALREADY IST): "2025-11-07 11:31:02"
                # Assuming this is local time (IST), so keep as is
                dt_ist = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            else:
                # Fallback
                dt_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        except Exception as e:
            logger.warning(f"⚠️ Timestamp parsing error: {e}. Using current IST time.")
            
        timestamp_formatted = dt_ist.strftime('%Y-%m-%d %H:%M:%S IST')
        date_only = dt_ist.strftime('%Y-%m-%d')
        
        duration_sec = call_data.get('duration', 0)
        duration_formatted = f"{duration_sec}s ({int(duration_sec // 60)}m {duration_sec % 60}s)"
        
        # Lookup customer name from Google Sheets
        customer_details = customer_lookup.lookup_customer(customer_number)
        if customer_details:
            company_name = customer_details.get('company_name', 'Name not found')
            ca_name = customer_details.get('ca_name', '')
            if ca_name:
                customer_legal_name = f"{company_name} ({ca_name})"
            else:
                customer_legal_name = company_name
        else:
            customer_legal_name = "Name not found"
        
        # Determine call type and emoji
        call_type = call_data.get('call_type', 'Normal')
        if call_type == "Missed Call":
            title_emoji = "📵"
            title_text = "Missed Call Alert"
            content_section = f"⚠️ *Call was missed.* No recording available."
        elif call_type == "Voicemail Call":
            title_emoji = "📠"
            title_text = "Voicemail Received"
            
            # If transcription is available (MOM variable holds transcription for voicemails)
            if mom and len(mom) > 10:
                short_transcription = mom[:1500] + "..." if len(mom) > 1500 else mom
                content_section = f"📝 *Voicemail Transcription:*\n\n{short_transcription}"
            else:
                content_section = f"📝 *Voicemail recorded.* Check recording link below (Transcription unavailable or too short)."
        else:
            title_emoji = "📞"
            title_text = "Customer Support Call Summary"
            content_section = f"📝 *Meeting Minutes (MOM):*\n\n{mom}"

        # Build Exotel recording link
        exotel_link = call_data.get('recording_url', 'N/A')
        recording_display = f"<{exotel_link}|Listen on Exotel>" if exotel_link != 'N/A' else 'None'
        
        # Main message body - clean and focused
        # Main message body - Professional & Clean
        message = f"""{title_emoji} *{title_text}*

*Customer Details*
• Name: {customer_legal_name}
• Number: `{customer_number}`

*Agent Details*
• Agent: {agent_name} {agent_mention}
• Number: `{support_number}`
• Department: {department}

*Call Duration & Time*
• Time: {timestamp_formatted}
• Duration: {duration_formatted}

*Summary*
{content_section}

*Resources*
• Recording: {recording_display}
• Call ID: `{call_data['call_id']}`"""
        
        return {
            'message': message,
            'customer_number': customer_number,
            'customer_legal_name': customer_legal_name,
            'agent_name': agent_name,
            'timestamp': timestamp_formatted,
            'call_id': call_data['call_id'],
            'exotel_link': exotel_link,
            'mom': mom  # Store MOM separately for potential future use
        }
    
    @staticmethod
    def post_to_slack(message_data: Dict[str, Any], webhook_url: str) -> bool:
        """Post formatted message to Slack
        
        Args:
            message_data: Dict containing 'message' and other metadata
            webhook_url: Slack webhook URL
        """
        try:
            main_message = message_data['message']
            
            # Post message via webhook
            payload = {
                "text": main_message,
                "mrkdwn": True,
                "unfurl_links": False,
                "unfurl_media": False
            }
            
            response = requests.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
            
            logger.info("✅ Successfully posted message to Slack")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to post to Slack: {e}")
            return False


# Initialize services
transcription_service = TranscriptionService(OPENAI_API_KEY) if OPENAI_API_KEY else None
mom_generator = MOMGenerator(OPENAI_API_KEY) if OPENAI_API_KEY else None
google_drive_service = GoogleDriveService(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET) if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET else None
customer_lookup = CustomerLookup()  # Initialize customer lookup service

def emergency_cleanup_old_records():
    """Emergency cleanup of old records that might cause duplicate posts"""
    try:
        with db_manager._get_connection() as conn:
            # Delete all records older than 2 hours that were never posted to Slack
            two_hours_ago = (datetime.utcnow() - timedelta(hours=2)).isoformat()
            
            cursor = conn.execute("""
                DELETE FROM processed_calls 
                WHERE processed_at < ? AND slack_posted = 0
            """, (two_hours_ago,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                logger.warning(f"🧹 EMERGENCY CLEANUP: Deleted {deleted_count} old failed records")
            else:
                logger.info("🧹 EMERGENCY CLEANUP: No old records to clean")
                
    except Exception as e:
        logger.error(f"❌ Emergency cleanup failed: {e}")


async def process_call_with_rate_limit(call_data: Dict[str, Any]):
    """Process call with rate limiting to prevent server overload"""
    call_id = call_data['call_id']
    
    # Acquire semaphore (wait if max concurrent calls reached)
    processing_semaphore.acquire()
    try:
        logger.info(f"[Queue] Starting processing for call {call_id}")
        call_type = call_data.get('call_type', 'Normal')
        
        transcription = ""
        mom = ""
        
        # Determine if we should transcribe
        should_transcribe = False
        duration = call_data.get('duration', 0)

        if call_type == "Normal":
            should_transcribe = True
        elif call_type == "Voicemail Call":
            # Only transcribe voicemail if duration > 10 seconds
            if duration > 10:
                should_transcribe = True
                logger.info(f"📼 Voicemail duration {duration}s > 10s. Proceeding with transcription.")
            else:
                transcription = f"Voicemail too short to transcribe ({duration}s)"
                logger.info(f"⏭️ Voicemail duration {duration}s <= 10s. Skipping transcription.")
        
        # Perform transcription if criteria met
        if should_transcribe:
            # Check if recording URL is provided
            recording_url = call_data.get('recording_url')
            if recording_url:
                # Download and transcribe
                try:
                    logger.info(f"Downloading recording for call {call_id}")
                    audio_file = transcription_service.download_recording(recording_url, call_id)
                    
                    logger.info(f"Transcribing call {call_id}")
                    transcription = transcription_service.transcribe_audio(audio_file)
                    
                    if not transcription:
                        transcription = "No transcription possible."
                except Exception as e:
                    logger.error(f"Error in transcription: {e}")
                    transcription = f"Error in transcription: {str(e)}"
            else:
                transcription = "No recording available."
            
            # Generate MOM only for Normal calls (Voicemails get transcript only)
            if call_type == "Normal" and transcription and "Error" not in transcription:
                # Get agent and customer information for MOM generation
                agent_info = SlackFormatter.find_agent_from_call(
                    call_data['from_number'],
                    call_data['to_number'],
                    call_data.get('exotel_to'),
                    call_data.get('phone_number_sid')
                )
                
                # Determine customer number based on agent detection
                if agent_info:
                    if agent_info['direction'] == "outgoing":
                        customer_number = call_data['to_number']
                    else:
                        customer_number = call_data['from_number']
                    agent_name = agent_info['name']
                else:
                    # Fallback
                    customer_number = call_data['from_number']
                    agent_name = "Agent"
                
                # For MOM generation, use simple labels
                customer_name_for_mom = "Customer"
                agent_name_for_mom = agent_name
                
                if mom_generator and transcription:
                    logger.info(f"Generating MOM for call {call_id}")
                    mom = mom_generator.generate_mom(transcription, customer_name=customer_name_for_mom, agent_name=agent_name_for_mom)
                else:
                    mom = transcription
        else:
            transcription = "Voicemail (Check Link)"
            mom = "N/A"

        # Upload transcript to Google Drive for automatic NotebookLM sync (only if transcription exists and it's a normal call)
        if google_drive_service and call_type == "Normal" and transcription and "N/A" not in transcription and "Error" not in transcription:
            logger.info(f"Uploading transcript to Google Drive for call {call_id}")
            google_drive_service.send_transcript(transcription, call_data)
        
        # BULLETPROOF DUPLICATE PREVENTION - Layer 3: Final safety check before Slack post
        if db_manager.is_call_processed(call_id):
            logger.warning(f"🚫 FINAL SAFETY CHECK: Call {call_id} already posted to Slack - SKIPPING DUPLICATE POST")
            return
        
        # Format and post to Slack
        logger.info(f"Formatting message for Slack ({call_type})")
        slack_message_data = SlackFormatter.format_message(call_data, mom, transcription)
        
        # Determine Webhook URL based on Call Type
        target_webhook_url = SLACK_WEBHOOK_URL
        
        # Route all calls to main channel per user request
        # if call_type == "Voicemail Call" and SLACK_MISSED_CALL_WEBHOOK_URL:
        #      target_webhook_url = SLACK_MISSED_CALL_WEBHOOK_URL
        #      logger.info("🔀 Routing to Missed Call Channel (Voicemail)")
        
        logger.info(f"Posting to Slack")
        success = SlackFormatter.post_to_slack(
            message_data=slack_message_data,
            webhook_url=target_webhook_url
        )
        
        # Mark as processed
        db_manager.mark_call_processed(call_data, transcription, success)
        
        if success:
            logger.info(f"✅ Successfully completed processing for call {call_id}")
        else:
            logger.error(f"❌ Failed to post to Slack for call {call_id}")
            
        # Add delay before next call
        if PROCESSING_DELAY > 0:
            await asyncio.sleep(PROCESSING_DELAY)
            
    except Exception as e:
        logger.error(f"❌ Error processing call {call_id}: {e}")
        db_manager.mark_call_processed(call_data, f"Error: {str(e)}", False)
    finally:
        processing_semaphore.release()


def process_call_background(call_data: Dict[str, Any]):
    """Wrapper to run async processing in background"""
    try:
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(process_call_with_rate_limit(call_data))
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Error in background processing wrapper: {e}")


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Exotel-Slack Complete System",
        "version": "2.0.0",
        "status": "running",
        "features": [
            "Smart Agent Detection (97 agents)",
            "OpenAI Whisper Transcription",
            "AI MOM Generation",
            "Slack User Tagging by Phone & Email",
            "Duplicate Prevention",
            "IST Timezone Support"
        ],
        "agents_loaded": len(AGENT_MAPPING),
        "endpoints": {
            "health": "/health",
            "zapier_webhook": "/webhook/zapier",
            "stats": "/stats"
        },
        "documentation": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    stats = db_manager.get_stats()
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "database": "connected",
        "agents_loaded": len(AGENT_MAPPING),
        "stats": stats,
        "services": {
            "transcription": "enabled (OpenAI Whisper)" if transcription_service else "disabled",
            "mom_generator": "enabled" if mom_generator else "disabled",
            "google_drive": "enabled" if google_drive_service else "disabled (set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)",
            "slack": "enabled" if SLACK_WEBHOOK_URL else "disabled",
            "slack_user_lookup": "enabled" if slack_user_lookup else "disabled (set SLACK_BOT_TOKEN)",
            "agent_database": f"{len(AGENT_MAPPING)} agents loaded"
        }
    }


@app.post("/webhook/exotel", response_model=WebhookResponse)
@app.post("/webhook/zapier", response_model=WebhookResponse)
async def exotel_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Main webhook endpoint for Exotel integration (formerly Zapier)"""
    try:
        # Parse JSON body
        body_json = await request.json()
        logger.info(f"📥 Webhook body: {json.dumps(body_json, indent=2)}")
        
        # Validate payload
        payload = ExotelWebhookPayload(**body_json)
        
        call_id = payload.call_id
        logger.info(f"📞 Received webhook for call {call_id}")
        logger.info(f"   From: {payload.from_number}")
        logger.info(f"   To: {payload.to_number}")
        logger.info(f"   Direction: {payload.direction}")
        logger.info(f"   Price: {payload.price}")
        
        # Identify Call Type
        call_type = "Normal"
        if payload.direction == "inbound":
            # STRICT FILTER: All inbound calls MUST have a recording AND be > 10 seconds
            if not payload.recording_url or payload.duration <= 10:
                logger.info(f"⏭️ Skipping Inbound Call {call_id} - Duration {payload.duration}s <= 10s or No Recording")
                return WebhookResponse(
                    success=True,
                    message="Skipped - Short/No Recording Inbound Call",
                    call_id=call_id,
                    timestamp=datetime.utcnow().isoformat() + "Z"
                )
            
            # If it passed the filter, it has a recording -> Treat as Voicemail Call (per user request)
            # "Voicemail Call just strictly recording presence, ignoring price."
            call_type = "Voicemail Call"
        
        logger.info(f"   Detection Debug: Direction={payload.direction}, RecURL={'Present' if payload.recording_url else 'None'}, Price={payload.price}")
        logger.info(f"   Detected Call Type: {call_type}")

        # BULLETPROOF DUPLICATE PREVENTION - Layer 1: Quick existence check
        if db_manager.is_call_processed(call_id):
            logger.warning(f"🚫 PERMANENT DUPLICATE CALL DETECTED (Layer 1): {call_id}")
            return WebhookResponse(
                success=True,
                message="Duplicate call - already posted to Slack (layer 1)",
                call_id=call_id,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        
        # TIME VALIDATION: Only process calls from last 1 hour
        try:
            call_date_str = payload.timestamp
            if call_date_str:
                if 'T' in call_date_str or '+' in call_date_str or call_date_str.count(':') == 3:
                    call_date = datetime.fromisoformat(call_date_str.replace('Z', '+00:00'))
                    call_time = call_date.replace(tzinfo=None)
                elif ' ' in call_date_str:
                    # Handle Exotel format: 2026-01-02 19:08:36
                    call_time = datetime.strptime(call_date_str, '%Y-%m-%d %H:%M:%S')
                else:
                    call_time = datetime.fromisoformat(call_date_str)
                
                current_time = datetime.utcnow()
                time_difference = current_time - call_time
                time_difference_abs = abs(time_difference.total_seconds())
                hours_diff = time_difference_abs / 3600
                
                # Relaxed Check: 365 Days (8760 hours)
                if hours_diff > 8760: 
                    logger.warning(f"🚫 OLD/FUTURE CALL REJECTED: {call_id} (Diff: {hours_diff:.2f}h)")
                    return WebhookResponse(
                        success=True,
                        message=f"Call rejected - time window error ({hours_diff:.2f} hours)",
                        call_id=call_id,
                        timestamp=datetime.utcnow().isoformat() + "Z"
                    )
        except Exception as e:
            logger.warning(f"⚠️ Could not validate call timestamp: {e}")
        
        if not SLACK_WEBHOOK_URL:
            raise HTTPException(status_code=500, detail="Slack webhook not configured")
        
        logger.info(f"   To (Field): {payload.exotel_to}")
        
        # STRICT AGENT FILTER: Only process if at least one number matches an authorized agent
        # We check: From (Caller), PhoneNumber (Virtual Number), To (Exotel Dialed), PhoneNumberSid
        agent_info = SlackFormatter.find_agent_from_call(
            payload.from_number, 
            payload.to_number,
            payload.exotel_to,
            payload.phone_number_sid
        )
        
        if not agent_info:
            logger.info(f"🚫 Skipping call {call_id} - Unauthorized numbers: From={payload.from_number}, To={payload.to_number}, PNSid={payload.phone_number_sid}")
            return WebhookResponse(
                success=True,
                message="Call skipped - Unauthorized agent numbers",
                call_id=call_id,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        
        agent_name = agent_info.get('name', 'Unknown')
        agent_team = agent_info.get('team', 'Support')
        logger.info(f"✅ Authorized agent detected: {agent_name} ({agent_team})")

        # CONDITIONAL PROCESSING FOR SUPPORT-CAND TEAM
        # For Support-CAND agents, we ONLY process Missed Calls and Voicemail Calls.
        # Normal calls are skipped to save costs/noise.
        if agent_team == "Support-CAND" and call_type == "Normal":
            logger.info(f"⏭️ Skipping Normal call for Support-CAND agent: {agent_name}")
            return WebhookResponse(
                success=True,
                message=f"Normal call skipped for Support-CAND agent",
                call_id=call_id,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )

        # DEPARTMENT FILTER (Legacy support, but primarily using the list provided)
        if ALLOWED_DEPT_LIST:
            agent_dept = agent_info.get('department', 'Unknown')
            if agent_dept not in ALLOWED_DEPT_LIST:
                logger.info(f"🚫 Skipping call {call_id} - Department '{agent_dept}' not allowed")
                return WebhookResponse(
                    success=True,
                    message=f"Call skipped - Dept filter",
                    call_id=call_id,
                    timestamp=datetime.utcnow().isoformat() + "Z"
                )
        
        call_data = {
            'call_id': call_id,
            'from_number': payload.from_number,
            'to_number': payload.to_number,
            'duration': payload.duration,
            'recording_url': payload.recording_url,
            'timestamp': payload.timestamp or datetime.utcnow().isoformat(),
            'status': payload.status,
            'direction': payload.direction,
            'price': payload.price,
            'call_type': call_type,
            'agent_phone': payload.agent_phone,
            'agent_name': payload.agent_name,
            'agent_slack_handle': payload.agent_slack_handle,
            'department': payload.department,
            'customer_segment': payload.customer_segment
        }
        
        # BULLETPROOF DUPLICATE PREVENTION - Layer 2: Database lock check
        if not db_manager.mark_call_processing(call_id, call_data):
            return WebhookResponse(
                success=True,
                message="Duplicate call - already processing (layer 2)",
                call_id=call_id,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        
        background_tasks.add_task(process_call_background, call_data)
        logger.info(f"✅ Queued {call_type} for processing: {call_id}")
        
        return WebhookResponse(
            success=True,
            message=f"{call_type} queued for processing",
            call_id=call_id,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in webhook handler: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in webhook handler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get processing statistics"""
    stats = db_manager.get_stats()
    return {
        "stats": stats,
        "agents_loaded": len(AGENT_MAPPING),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/call/{call_id}")
async def get_call_details(call_id: str):
    """Get details of a processed call"""
    with db_manager._get_connection() as conn:
        result = conn.execute(
            "SELECT * FROM processed_calls WHERE call_id = ?",
            (call_id,)
        ).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Call not found")
        
        return dict(result)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "details": str(exc),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("=" * 60)
    logger.info("Starting Exotel-Slack Complete System v2.0")
    logger.info("=" * 60)
    
    # Emergency cleanup of old records
    emergency_cleanup_old_records()
    logger.info(f"Database: {DATABASE_PATH}")
    logger.info(f"Agent Database: {len(AGENT_MAPPING)} agents loaded")
    logger.info(f"Transcription: {'Enabled (OpenAI Whisper)' if transcription_service else 'Disabled'}")
    logger.info(f"MOM Generator: {'Enabled' if mom_generator else 'Disabled'}")
    logger.info(f"Google Drive: {'Enabled' if google_drive_service else 'Disabled (set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)'}")
    logger.info(f"Slack: {'Enabled' if SLACK_WEBHOOK_URL else 'Disabled'}")
    logger.info(f"Slack User Lookup: {'Enabled' if slack_user_lookup else 'Disabled (set SLACK_BOT_TOKEN)'}")
    logger.info(f"Support Number: {SUPPORT_NUMBER}")
    logger.info(f"Rate Limiting: {PROCESSING_DELAY}s delay, {MAX_CONCURRENT_CALLS} concurrent calls")
    logger.info(f"Smart Agent Detection: Enabled ✅")
    if ALLOWED_DEPT_LIST:
        logger.info(f"🔍 Department Filter: ENABLED - Only processing: {', '.join(ALLOWED_DEPT_LIST)}")
    else:
        logger.info(f"🔍 Department Filter: DISABLED - Processing all departments")
    logger.info("=" * 60)
    
    Path("downloads").mkdir(exist_ok=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )
