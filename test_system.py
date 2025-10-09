#!/usr/bin/env python3
"""
Test script for Exotel-Slack Complete System
Run this to verify your setup is working correctly
"""

import requests
import json
import time
import sys
from datetime import datetime

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_test(test_name):
    print(f"{Colors.YELLOW}Testing: {test_name}...{Colors.ENDC}")

def print_pass(message):
    print(f"{Colors.GREEN}✅ PASS: {message}{Colors.ENDC}")

def print_fail(message):
    print(f"{Colors.RED}❌ FAIL: {message}{Colors.ENDC}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.ENDC}")

def test_health_endpoint(base_url):
    """Test 1: Health endpoint"""
    print_test("Health Endpoint")
    
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy':
                print_pass("Health endpoint responding")
                print_info(f"Database: {data.get('database')}")
                print_info(f"Stats: {data.get('stats')}")
                return True
            else:
                print_fail(f"Status is not healthy: {data.get('status')}")
                return False
        else:
            print_fail(f"Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False

def test_root_endpoint(base_url):
    """Test 2: Root endpoint"""
    print_test("Root Endpoint")
    
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'service' in data and 'version' in data:
                print_pass("Root endpoint responding")
                print_info(f"Service: {data.get('service')}")
                print_info(f"Version: {data.get('version')}")
                return True
            else:
                print_fail("Invalid response format")
                return False
        else:
            print_fail(f"Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False

def test_webhook_valid(base_url):
    """Test 3: Webhook with valid payload"""
    print_test("Webhook - Valid Payload")
    
    payload = {
        "call_id": f"TEST_{int(time.time())}",
        "from_number": "+919876543210",
        "to_number": "09631084471",
        "duration": 120,
        "recording_url": None,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "completed",
        "agent_name": "Test Agent",
        "agent_slack_handle": "@test",
        "department": "Customer Success",
        "customer_segment": "General"
    }
    
    try:
        response = requests.post(
            f"{base_url}/webhook/zapier",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print_pass("Webhook accepted valid payload")
                print_info(f"Message: {data.get('message')}")
                print_info(f"Call ID: {data.get('call_id')}")
                return True, payload['call_id']
            else:
                print_fail(f"Success is False: {data.get('message')}")
                return False, None
        else:
            print_fail(f"Status code: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False, None
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False, None

def test_duplicate_detection(base_url, call_id):
    """Test 4: Duplicate detection"""
    print_test("Duplicate Detection")
    
    if not call_id:
        print_fail("No call_id from previous test")
        return False
    
    payload = {
        "call_id": call_id,  # Same call_id as previous test
        "from_number": "+919876543210",
        "to_number": "09631084471",
        "duration": 120,
        "agent_name": "Test Agent",
        "agent_slack_handle": "@test",
        "department": "Customer Success",
        "customer_segment": "General"
    }
    
    try:
        response = requests.post(
            f"{base_url}/webhook/zapier",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'duplicate' in data.get('message', '').lower():
                print_pass("Duplicate detection working")
                print_info(f"Message: {data.get('message')}")
                return True
            else:
                print_fail(f"Did not detect duplicate: {data.get('message')}")
                return False
        else:
            print_fail(f"Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False

def test_call_direction_incoming(base_url):
    """Test 5: Call direction - incoming"""
    print_test("Call Direction - Incoming")
    
    payload = {
        "call_id": f"INCOMING_TEST_{int(time.time())}",
        "from_number": "+919876543210",  # Customer
        "to_number": "09631084471",      # Support
        "duration": 60,
        "agent_name": "Test Agent",
        "agent_slack_handle": "@test",
        "department": "Customer Success",
        "customer_segment": "General"
    }
    
    try:
        response = requests.post(
            f"{base_url}/webhook/zapier",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print_pass("Incoming call accepted")
                print_info("System should identify this as incoming call")
                print_info(f"Support: {payload['to_number']}, Customer: {payload['from_number']}")
                return True
            else:
                print_fail(f"Failed: {data.get('message')}")
                return False
        else:
            print_fail(f"Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False

def test_call_direction_outgoing(base_url):
    """Test 6: Call direction - outgoing"""
    print_test("Call Direction - Outgoing")
    
    payload = {
        "call_id": f"OUTGOING_TEST_{int(time.time())}",
        "from_number": "09631084471",    # Support
        "to_number": "+919876543210",    # Customer
        "duration": 60,
        "agent_name": "Test Agent",
        "agent_slack_handle": "@test",
        "department": "Customer Success",
        "customer_segment": "General"
    }
    
    try:
        response = requests.post(
            f"{base_url}/webhook/zapier",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print_pass("Outgoing call accepted")
                print_info("System should identify this as outgoing call")
                print_info(f"Support: {payload['from_number']}, Customer: {payload['to_number']}")
                return True
            else:
                print_fail(f"Failed: {data.get('message')}")
                return False
        else:
            print_fail(f"Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False

def test_stats_endpoint(base_url):
    """Test 7: Stats endpoint"""
    print_test("Stats Endpoint")
    
    try:
        response = requests.get(f"{base_url}/stats", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'stats' in data:
                stats = data['stats']
                print_pass("Stats endpoint responding")
                print_info(f"Total Processed: {stats.get('total_processed')}")
                print_info(f"Successfully Posted: {stats.get('successfully_posted')}")
                print_info(f"Failed: {stats.get('failed')}")
                return True
            else:
                print_fail("Invalid response format")
                return False
        else:
            print_fail(f"Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False

def test_missing_fields(base_url):
    """Test 8: Missing required fields"""
    print_test("Validation - Missing Fields")
    
    payload = {
        "from_number": "+919876543210",
        "to_number": "09631084471"
        # Missing call_id and other required fields
    }
    
    try:
        response = requests.post(
            f"{base_url}/webhook/zapier",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 422:  # Unprocessable Entity
            print_pass("Validation working - rejected invalid payload")
            return True
        else:
            print_fail(f"Expected 422, got {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False

def main():
    """Main test runner"""
    
    print_header("Exotel-Slack Complete System - Test Suite")
    
    # Get base URL from user or use default
    if len(sys.argv) > 1:
        base_url = sys.argv[1].rstrip('/')
    else:
        print("Enter your deployment URL (or press Enter for localhost:8000):")
        base_url = input("> ").strip().rstrip('/') or "http://localhost:8000"
    
    print_info(f"Testing: {base_url}")
    
    # Track results
    results = []
    
    # Run tests
    results.append(("Health Endpoint", test_health_endpoint(base_url)))
    results.append(("Root Endpoint", test_root_endpoint(base_url)))
    
    success, call_id = test_webhook_valid(base_url)
    results.append(("Webhook Valid Payload", success))
    
    time.sleep(1)  # Small delay before duplicate test
    results.append(("Duplicate Detection", test_duplicate_detection(base_url, call_id)))
    
    results.append(("Incoming Call Direction", test_call_direction_incoming(base_url)))
    results.append(("Outgoing Call Direction", test_call_direction_outgoing(base_url)))
    results.append(("Stats Endpoint", test_stats_endpoint(base_url)))
    results.append(("Missing Fields Validation", test_missing_fields(base_url)))
    
    # Print summary
    print_header("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.ENDC}" if result else f"{Colors.RED}❌ FAIL{Colors.ENDC}"
        print(f"{test_name:<30} {status}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.ENDC}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 All tests passed! Your system is working correctly!{Colors.ENDC}")
        return 0
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  Some tests failed. Check the output above for details.{Colors.ENDC}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

