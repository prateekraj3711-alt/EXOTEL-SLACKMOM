"""
Customer Lookup Module - Fetches customer details from Google Sheets
"""

import logging
import gspread
from google.oauth2.service_account import Credentials
from typing import Dict, Optional
import os
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CustomerLookup:
    """Lookup customer details from Google Sheets with auto-refresh."""
    
    def __init__(self):
        self.spreadsheet_url = "https://docs.google.com/spreadsheets/d/1to5o5DEvH8PWyuo89Dht-g__VNJw4NGAEP15jvgkWgo/edit?gid=498627995#gid=498627995"
        self.spreadsheet_id = "1to5o5DEvH8PWyuo89Dht-g__VNJw4NGAEP15jvgkWgo"
        self.worksheet_name = "Customer POC"  # EXACT SHEET NAME WITH SPACE
        self.client = None
        self.cache = {}  # Cache customer data to reduce API calls
        self.cache_loaded = False
        self.last_cache_refresh = None  # Track when cache was last refreshed
        self.cache_refresh_interval = timedelta(minutes=30)  # Refresh every 30 minutes
        self._init_client()
    
    def _init_client(self):
        """Initialize Google Sheets client."""
        try:
            # Try to get credentials from environment variable
            google_creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
            
            if not google_creds_json:
                logger.warning("⚠️ Google Sheets credentials not found in environment - customer lookup disabled")
                return
            
            # Parse credentials JSON
            creds_dict = json.loads(google_creds_json)
            
            # Define the scope
            scope = [
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
            
            # Create credentials
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            
            # Authorize the client
            self.client = gspread.authorize(creds)
            
            logger.info("✅ Google Sheets client initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Error initializing Google Sheets client: {e}")
            self.client = None
    
    def normalize_phone(self, phone_number: str) -> str:
        """Normalize phone number for comparison (remove +, spaces, hyphens)."""
        return phone_number.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    def load_customer_cache(self):
        """Load all customer data into cache for fast lookup."""
        try:
            if not self.client:
                logger.warning("⚠️ Google Sheets client not initialized - cannot load customer data")
                return False
            
            logger.info(f"📊 Opening spreadsheet: {self.spreadsheet_id}")
            
            # Open the spreadsheet
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            
            logger.info("📋 Available worksheets:")
            for sheet in spreadsheet.worksheets():
                logger.info(f"   - '{sheet.title}' (ID: {sheet.id})")
            
            # Try to get worksheet by name first
            try:
                logger.info(f"📄 Trying to open worksheet by name: '{self.worksheet_name}'")
                worksheet = spreadsheet.worksheet(self.worksheet_name)
                logger.info(f"✅ Found worksheet by name: '{self.worksheet_name}'")
            except Exception as e:
                logger.warning(f"⚠️ Could not find worksheet by name: {e}")
                # Try by GID (498627995)
                logger.info("📄 Trying to open worksheet by GID: 498627995")
                worksheet = spreadsheet.get_worksheet_by_id(498627995)
                logger.info(f"✅ Found worksheet by GID: '{worksheet.title}'")
            
            # Get all records
            records = worksheet.get_all_records()
            
            logger.info(f"📋 Retrieved {len(records)} records from sheet")
            
            # Build cache with normalized phone numbers as keys
            self.cache = {}
            phone_count = 0
            
            for record in records:
                ca_mobile = str(record.get('CA Mobile', '')).strip()
                company_name = str(record.get('Company Name', '')).strip()
                
                if ca_mobile and company_name:
                    # CA Mobile can have multiple numbers separated by commas
                    phone_numbers = [p.strip() for p in ca_mobile.split(',')]
                    
                    customer_details = {
                        'company_id': str(record.get('Company ID', '')),
                        'company_name': company_name,
                        'company_status': str(record.get('Company Status', '')),
                        'ca_name': str(record.get('CA Name', '')),
                        'ca_email': str(record.get('CA Email', '')),
                        'ca_mobile': ca_mobile,
                        'original_phone': ca_mobile
                    }
                    
                    # Add each phone number to cache
                    for phone in phone_numbers:
                        if phone:  # Skip empty strings
                            clean_number = self.normalize_phone(phone)
                            self.cache[clean_number] = customer_details
                            phone_count += 1
                            logger.debug(f"  📞 Cached: {phone} → {company_name}")
            
            self.cache_loaded = True
            self.last_cache_refresh = datetime.utcnow()  # Record refresh time
            logger.info(f"✅ Loaded {phone_count} phone number mappings from {len(records)} companies in Google Sheets")
            logger.info(f"🕐 Cache refresh timestamp: {self.last_cache_refresh.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading customer cache: {e}")
            logger.error(f"   Spreadsheet ID: {self.spreadsheet_id}")
            logger.error(f"   Worksheet Name: '{self.worksheet_name}'")
            return False
    
    def lookup_customer(self, phone_number: str) -> Optional[Dict[str, str]]:
        """
        Lookup customer details by phone number with auto-refresh every 30 minutes.
        
        Args:
            phone_number: Customer phone number to lookup
            
        Returns:
            Dictionary with customer details or None if not found
        """
        try:
            if not self.client:
                logger.debug("⚠️ Google Sheets client not initialized - skipping customer lookup")
                return None
            
            # Check if cache needs refresh (older than 30 minutes)
            cache_expired = False
            if self.last_cache_refresh:
                time_since_refresh = datetime.utcnow() - self.last_cache_refresh
                cache_expired = time_since_refresh > self.cache_refresh_interval
                
                if cache_expired:
                    minutes_old = int(time_since_refresh.total_seconds() / 60)
                    logger.info(f"🔄 Cache is {minutes_old} minutes old - refreshing from Google Sheets...")
            
            # Load cache if not loaded OR if expired
            if not self.cache_loaded or cache_expired:
                if not self.cache_loaded:
                    logger.info("📥 Loading customer data from Google Sheets (first time)...")
                if not self.load_customer_cache():
                    return None
            
            # Clean phone number
            clean_number = self.normalize_phone(phone_number)
            
            # Remove leading 0 if present (e.g., 06001813067 -> 6001813067)
            if clean_number.startswith('0') and len(clean_number) > 10:
                clean_number = clean_number[1:]
            
            logger.info(f"🔍 Looking up customer for: {phone_number} (normalized: {clean_number})")
            
            # Try exact match first
            if clean_number in self.cache:
                customer_details = self.cache[clean_number]
                logger.info(f"✅ Found customer (exact match) for {phone_number}: {customer_details['company_name']}")
                return customer_details
            
            # Try with 91 prefix (India country code)
            if not clean_number.startswith('91') and len(clean_number) == 10:
                clean_number_with_91 = '91' + clean_number
                if clean_number_with_91 in self.cache:
                    customer_details = self.cache[clean_number_with_91]
                    logger.info(f"✅ Found customer (with +91) for {phone_number}: {customer_details['company_name']}")
                    return customer_details
            
            # Try partial match (last 10 digits)
            last_10 = clean_number[-10:] if len(clean_number) >= 10 else clean_number
            for cached_number, details in self.cache.items():
                # Match if last 10 digits are the same
                if len(cached_number) >= 10 and cached_number[-10:] == last_10:
                    logger.info(f"✅ Found customer (last 10 digits match) for {phone_number}: {details['company_name']}")
                    return details
            
            # No match found
            logger.warning(f"❌ No customer details found for {phone_number}")
            logger.warning(f"   Tried: {clean_number}, 91{clean_number[-10:] if len(clean_number) >= 10 else clean_number}, last 10: {last_10}")
            logger.warning(f"   Total cached numbers: {len(self.cache)}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error looking up customer: {e}")
            return None
    
    def format_customer_display(self, customer_details: Optional[Dict[str, str]], fallback_number: str) -> str:
        """
        Format customer details for display.
        
        Args:
            customer_details: Dictionary with customer details
            fallback_number: Phone number to use if no customer details found
            
        Returns:
            Formatted string for display
        """
        if not customer_details:
            return "Name not found"
        
        company_name = customer_details.get('company_name', 'Name not found')
        ca_name = customer_details.get('ca_name', '')
        
        if ca_name:
            return f"{company_name} ({ca_name})"
        else:
            return company_name
    
    def get_customer_contact_info(self, customer_details: Optional[Dict[str, str]]) -> Dict[str, str]:
        """
        Get customer contact information.
        
        Args:
            customer_details: Dictionary with customer details
            
        Returns:
            Dictionary with contact info
        """
        if not customer_details:
            return {
                'company_name': 'Name not found',
                'ca_name': '',
                'ca_email': '',
                'ca_mobile': ''
            }
        
        return {
            'company_name': customer_details.get('company_name', 'Name not found'),
            'ca_name': customer_details.get('ca_name', ''),
            'ca_email': customer_details.get('ca_email', ''),
            'ca_mobile': customer_details.get('ca_mobile', '')
        }

