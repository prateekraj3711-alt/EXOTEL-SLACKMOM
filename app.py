"""
Exotel to Slack Complete System
Automated call recording transcription and Slack posting with Zapier integration
"""

import os
import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import requests
import sqlite3
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Exotel-Slack Complete System",
    description="Automated call transcription and Slack posting with duplicate prevention",
    version="1.0.0"
)

# Configuration from environment
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')
DEEPGRAM_API_KEY = os.environ.get('DEEPGRAM_API_KEY')  # Deepgram for transcription
EXOTEL_API_KEY = os.environ.get('EXOTEL_API_KEY')
EXOTEL_API_TOKEN = os.environ.get('EXOTEL_API_TOKEN')
EXOTEL_SID = os.environ.get('EXOTEL_SID')
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'processed_calls.db')

# Support agent phone number for direction detection
SUPPORT_NUMBER = os.environ.get('SUPPORT_NUMBER', '09631084471')

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
                # Filter out comment keys
                AGENT_MAPPING = {k: v for k, v in data.items() if not k.startswith('_')}
            logger.info(f"Loaded {len(AGENT_MAPPING)} agent mappings")
        else:
            logger.warning("agent_mapping.json not found - using default mappings")
    except Exception as e:
        logger.error(f"Failed to load agent mapping: {e}")

# Load agent mapping on startup
load_agent_mapping()

# Pydantic Models
class ZapierWebhookPayload(BaseModel):
    """Payload from Zapier webhook"""
    call_id: str = Field(..., description="Exotel Call ID (Sid)")
    from_number: str = Field(..., description="Caller number")
    to_number: str = Field(..., description="Called number")
    duration: int = Field(..., description="Call duration in seconds")
    recording_url: Optional[str] = Field(None, description="Recording URL from Exotel")
    timestamp: Optional[str] = Field(None, description="Call timestamp")
    status: str = Field(default="completed", description="Call status")
    agent_phone: Optional[str] = Field(None, description="Agent phone number")
    agent_name: Optional[str] = Field(None, description="Agent name")
    agent_slack_handle: Optional[str] = Field(None, description="Agent Slack handle")
    department: str = Field(default="Customer Success", description="Department")
    customer_segment: str = Field(default="General", description="Customer segment")


class WebhookResponse(BaseModel):
    """Response to Zapier webhook"""
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
        """Check if call has been processed"""
        with self._get_connection() as conn:
            result = conn.execute(
                "SELECT call_id FROM processed_calls WHERE call_id = ?",
                (call_id,)
            ).fetchone()
            return result is not None
    
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


# Transcription Service
class TranscriptionService:
    """Handle audio transcription using Deepgram"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.deepgram.com/v1/listen"
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/mpeg"
        }
    
    def download_recording(self, recording_url: str, call_id: str) -> str:
        """Download recording from Exotel"""
        try:
            # Create downloads directory
            downloads_dir = Path("downloads")
            downloads_dir.mkdir(exist_ok=True)
            
            file_path = downloads_dir / f"{call_id}.mp3"
            
            # Download with authentication
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
        """Transcribe audio file using Deepgram (Basic/Free Tier)"""
        try:
            logger.info("Transcribing audio with Deepgram (basic model)...")
            
            # Use basic Deepgram parameters compatible with free tier
            params = {
                "punctuate": "true",
                "language": "en"
            }
            # Removed: model, smart_format, diarize, tier - use defaults for free tier
            
            # Send audio file directly
            with open(audio_file_path, 'rb') as audio_file:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    params=params,
                    data=audio_file,
                    timeout=120
                )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract transcription
            if 'results' in result and 'channels' in result['results']:
                channel = result['results']['channels'][0]
                
                if 'alternatives' in channel and len(channel['alternatives']) > 0:
                    alternative = channel['alternatives'][0]
                    transcription = alternative.get('transcript', '')
                    
                    if transcription:
                        logger.info(f"Transcription completed: {len(transcription)} characters")
                        return transcription
            
            raise Exception("No transcription results from Deepgram")
            
        except Exception as e:
            logger.error(f"Deepgram transcription error: {e}")
            raise
        finally:
            # Cleanup downloaded file
            try:
                if os.path.exists(audio_file_path):
                    os.remove(audio_file_path)
                    logger.info(f"Cleaned up audio file: {audio_file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup audio file: {e}")


# Slack Formatter
class SlackFormatter:
    """Format call data for Slack posting in exact format from image"""
    
    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize phone number for comparison"""
        return phone.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
    
    @staticmethod
    def get_agent_info(phone_number: str) -> Dict[str, str]:
        """Get agent information from phone number"""
        normalized = SlackFormatter.normalize_phone(phone_number)
        
        # Check agent mapping
        for mapped_phone, agent_data in AGENT_MAPPING.items():
            if SlackFormatter.normalize_phone(mapped_phone) == normalized:
                return agent_data
        
        # Default if not found
        return {
            "name": "Support Agent",
            "slack_handle": "@support",
            "department": "Customer Success",
            "team": "Support"
        }
    
    @staticmethod
    def determine_direction(from_number: str, to_number: str, support_number: str) -> str:
        """Determine call direction based on phone numbers"""
        from_clean = SlackFormatter.normalize_phone(from_number)
        to_clean = SlackFormatter.normalize_phone(to_number)
        support_clean = SlackFormatter.normalize_phone(support_number)
        
        # Check if from_number matches any agent in mapping
        for mapped_phone in AGENT_MAPPING.keys():
            if SlackFormatter.normalize_phone(mapped_phone) == from_clean:
                return "outgoing"
        
        # Fallback to support number check
        if support_clean in from_clean:
            return "outgoing"
        else:
            return "incoming"
    
    @staticmethod
    def format_message(call_data: Dict[str, Any], transcription: str) -> str:
        """
        Format Slack message in exact format from the image
        
        Format:
        📞 Support Number: ...
        📱 Candidate/Customer Number: ...
        ❗ Concern: [First 100 chars of transcription]
        👤 CS Agent: @handle
        🏢 Department: ...
        ⏰ Timestamp: ...
        
        📋 Call Metadata:
        • Call ID: ...
        • Duration: ...
        • Status: ...
        • Agent: ...
        • Customer Segment: ...
        
        📝 Full Transcription:
        [Complete transcription]
        
        🎧 Recording/Voice Note:
        [Recording available but not displayed per requirements]
        """
        
        # Determine call direction
        direction = SlackFormatter.determine_direction(
            call_data['from_number'],
            call_data['to_number'],
            SUPPORT_NUMBER
        )
        
        # Set support and customer numbers based on direction
        if direction == "outgoing":
            support_number = call_data['from_number']
            customer_number = call_data['to_number']
        else:  # incoming
            support_number = call_data['to_number']
            customer_number = call_data['from_number']
        
        # Get concern (first 100 characters of transcription or first sentence)
        concern = transcription[:200] + "..." if len(transcription) > 200 else transcription
        if '\n' in concern:
            concern = concern.split('\n')[0]
        
        # Get agent info from phone number or use provided data
        agent_phone = call_data.get('agent_phone')
        if agent_phone:
            agent_info = SlackFormatter.get_agent_info(agent_phone)
            agent_name = agent_info['name']
            agent_handle = agent_info['slack_handle']
            department = agent_info['department']
        else:
            # Use provided data or defaults
            agent_name = call_data.get('agent_name', 'Support Agent')
            agent_handle = call_data.get('agent_slack_handle', '@support')
            department = call_data.get('department', 'Customer Success')
        
        # Ensure agent handle has @
        if not agent_handle.startswith('@'):
            agent_handle = f"@{agent_handle}"
        
        # Format timestamp
        timestamp = call_data.get('timestamp', datetime.utcnow().isoformat())
        if 'T' in timestamp:
            # Parse ISO format
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            timestamp_formatted = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        else:
            timestamp_formatted = timestamp
        
        # Format duration
        duration_sec = call_data.get('duration', 0)
        duration_formatted = f"{duration_sec}s"
        
        # Build message
        message = f"""📞 *Support Number:*
{support_number}

📱 *Candidate/Customer Number:*
{customer_number}

❗ *Concern:*
{concern}

👤 *CS Agent:*
{agent_handle} <{support_number}>

🏢 *Department:*
{department}

⏰ *Timestamp:*
{timestamp_formatted}

📋 *Call Metadata:*
• Call ID: `{call_data['call_id']}`
• Duration: {duration_formatted}
• Status: {call_data.get('status', 'Completed')}
• Agent: {agent_name}
• Customer Segment: {call_data.get('customer_segment', 'General')}

📝 *Full Transcription:*
