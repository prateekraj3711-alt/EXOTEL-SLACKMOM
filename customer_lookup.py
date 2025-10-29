"""
Customer Lookup Module - Fetches customer details from Google Sheets
"""

import logging
import gspread
from google.oauth2.service_account import Credentials
from typing import Dict, Optional
import os
import json

logger = logging.getLogger(__name__)

class CustomerLookup:
    """Lookup customer details from Google Sheets."""
    
    def __init__(self):
        self.spreadsheet_url = "https://docs.google.com/spreadsheets/d/1to5o5DEvH8PWyuo89Dht-g__VNJw4NGAEP15jvgkWgo/edit?gid=498627995#gid=498627995"
        self.spreadsheet_id = "1to5o5DEvH8PWyuo89Dht-g__VNJw4NGAEP15jvgkWgo"
        self.worksheet_name = "Customer POC"
        self.client = None
        self.cache = {}  # Cache customer data to reduce API calls
        self.cache_loaded = False
        self._init_client()
    
    def _init_client(self):
        """Initialize Google Sheets client."""
        try:
            # Try to get credentials from environment variable
            google_creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
            
            if not google_creds_json:
                logger.warning("Google Sheets credentials not found in environment - customer lookup disabled")
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
                return False
            
            # Open the spreadsheet
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            
            # Get the worksheet
            worksheet = spreadsheet.worksheet(self.worksheet_name)
            
            # Get all records
            records = worksheet.get_all_records()
            
            # Build cache with normalized phone numbers as keys
            self.cache = {}
            for record in records:
                ca_mobile = str(record.get('CA Mobile', '')).strip()
                if ca_mobile:
                    # CA Mobile can have multiple numbers separated by commas
                    phone_numbers = [p.strip() for p in ca_mobile.split(',')]
                    
                    customer_details = {
                        'company_id': str(record.get('Company ID', '')),
                        'company_name': str(record.get('Company Name', '')),
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
            
            self.cache_loaded = True
            logger.info(f"✅ Loaded {len(self.cache)} phone number mappings from Google Sheets")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading customer cache: {e}")
            return False
    
    def lookup_customer(self, phone_number: str) -> Optional[Dict[str, str]]:
        """
        Lookup customer details by phone number.
        
        Args:
            phone_number: Customer phone number to lookup
            
        Returns:
            Dictionary with customer details or None if not found
        """
        try:
            if not self.client:
                logger.debug("Google Sheets client not initialized - skipping customer lookup")
                return None
            
            # Load cache if not already loaded
            if not self.cache_loaded:
                if not self.load_customer_cache():
                    return None
            
            # Clean phone number
            clean_number = self.normalize_phone(phone_number)
            
            # Try exact match first
            if clean_number in self.cache:
                customer_details = self.cache[clean_number]
                logger.info(f"✅ Found customer details for {phone_number}: {customer_details['company_name']}")
                return customer_details
            
            # Try partial match (last 10 digits)
            if len(clean_number) >= 10:
                last_10 = clean_number[-10:]
                for cached_number, details in self.cache.items():
                    if cached_number.endswith(last_10) or last_10 in cached_number:
                        logger.info(f"✅ Found customer (partial match) for {phone_number}: {details['company_name']}")
                        return details
            
            # No match found
            logger.debug(f"ℹ️ No customer details found for {phone_number}")
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
            return f"Customer {fallback_number}"
        
        company_name = customer_details.get('company_name', 'Unknown Company')
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
                'company_name': 'Unknown',
                'ca_name': 'Unknown',
                'ca_email': 'N/A',
                'ca_mobile': 'N/A'
            }
        
        return {
            'company_name': customer_details.get('company_name', 'Unknown'),
            'ca_name': customer_details.get('ca_name', 'Unknown'),
            'ca_email': customer_details.get('ca_email', 'N/A'),
            'ca_mobile': customer_details.get('ca_mobile', 'N/A')
        }


