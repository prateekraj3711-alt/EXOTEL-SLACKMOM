# Testing Guide

Comprehensive testing guide for the Exotel-Slack Complete System.

## 📋 Testing Checklist

- [ ] Local development setup
- [ ] Health endpoint test
- [ ] Webhook endpoint test
- [ ] Database duplicate prevention
- [ ] Transcription service
- [ ] Slack posting
- [ ] Call direction logic
- [ ] End-to-end Zapier integration
- [ ] Load testing (optional)

## 🏠 Local Testing

### Setup

1. **Install dependencies**:
   ```bash
   cd exotel-slack-complete-system
   pip install -r requirements.txt
   ```

2. **Create `.env` file**:
   ```bash
   cp env.example .env
   ```

3. **Edit `.env` with test credentials**:
   ```env
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/TEST/WEBHOOK
   ASSEMBLYAI_API_KEY=test_key_here
   EXOTEL_API_KEY=test_key
   EXOTEL_API_TOKEN=test_token
   EXOTEL_SID=test_sid
   SUPPORT_NUMBER=09631084471
   DATABASE_PATH=test_processed_calls.db
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

   Server should start at: `http://localhost:8000`

## 🧪 Unit Tests

### Test 1: Health Endpoint

**Purpose**: Verify service is running and responsive

```bash
curl http://localhost:8000/health
```

**Expected Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2025-10-09T18:00:00Z",
  "database": "connected",
  "stats": {
    "total_processed": 0,
    "successfully_posted": 0,
    "failed": 0
  },
  "services": {
    "transcription": "enabled",
    "slack": "enabled"
  }
}
```

**✅ Pass Criteria**:
- Returns 200 status code
- Response is valid JSON
- `status` field is "healthy"
- `database` field is "connected"

---

### Test 2: Root Endpoint

**Purpose**: Verify API documentation endpoint

```bash
curl http://localhost:8000/
```

**Expected Response** (200 OK):
```json
{
  "service": "Exotel-Slack Complete System",
  "version": "1.0.0",
  "status": "running",
  "endpoints": { ... }
}
```

**✅ Pass Criteria**:
- Returns 200 status code
- Shows service information
- Lists available endpoints

---

### Test 3: Webhook Endpoint - Valid Payload

**Purpose**: Test webhook with valid call data

```bash
curl -X POST http://localhost:8000/webhook/zapier \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "TEST_CALL_001",
    "from_number": "+919876543210",
    "to_number": "09631084471",
    "duration": 120,
    "recording_url": null,
    "timestamp": "2025-10-09T17:58:27Z",
    "status": "completed",
    "agent_name": "Test Agent",
    "agent_slack_handle": "@testagent",
    "department": "Customer Success",
    "customer_segment": "General"
  }'
```

**Expected Response** (200 OK):
```json
{
  "success": true,
  "message": "Call queued for processing",
  "call_id": "TEST_CALL_001",
  "timestamp": "..."
}
```

**✅ Pass Criteria**:
- Returns 200 status code
- `success` field is `true`
- Returns correct `call_id`

---

### Test 4: Duplicate Detection

**Purpose**: Verify duplicate prevention works

```bash
# First request
curl -X POST http://localhost:8000/webhook/zapier \
  -H "Content-Type: application/json" \
  -d '{"call_id": "DUPLICATE_TEST_001", "from_number": "+919876543210", "to_number": "09631084471", "duration": 60, "agent_name": "Test", "agent_slack_handle": "@test", "department": "CS", "customer_segment": "General"}'

# Wait 2 seconds
sleep 2

# Second request with same call_id
curl -X POST http://localhost:8000/webhook/zapier \
  -H "Content-Type: application/json" \
  -d '{"call_id": "DUPLICATE_TEST_001", "from_number": "+919876543210", "to_number": "09631084471", "duration": 60, "agent_name": "Test", "agent_slack_handle": "@test", "department": "CS", "customer_segment": "General"}'
```

**Expected Response** (second request):
```json
{
  "success": true,
  "message": "Duplicate call - already processed",
  "call_id": "DUPLICATE_TEST_001",
  "timestamp": "..."
}
```

**✅ Pass Criteria**:
- Second request returns success but with duplicate message
- Database contains only one entry for this call_id
- No duplicate processing occurs

---

### Test 5: Call Direction Logic - Incoming

**Purpose**: Test incoming call detection

```bash
curl -X POST http://localhost:8000/webhook/zapier \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "INCOMING_TEST_001",
    "from_number": "+919876543210",
    "to_number": "09631084471",
    "duration": 60,
    "recording_url": null,
    "agent_name": "Test",
    "agent_slack_handle": "@test",
    "department": "CS",
    "customer_segment": "General"
  }'
```

**Expected Behavior**:
- System detects this as incoming (from_number is NOT support number)
- Support Number = to_number (09631084471)
- Customer Number = from_number (+919876543210)

**✅ Pass Criteria**:
- Call queued successfully
- Direction logic correctly identifies incoming call

---

### Test 6: Call Direction Logic - Outgoing

**Purpose**: Test outgoing call detection

```bash
curl -X POST http://localhost:8000/webhook/zapier \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "OUTGOING_TEST_001",
    "from_number": "09631084471",
    "to_number": "+919876543210",
    "duration": 60,
    "recording_url": null,
    "agent_name": "Test",
    "agent_slack_handle": "@test",
    "department": "CS",
    "customer_segment": "General"
  }'
```

**Expected Behavior**:
- System detects this as outgoing (from_number IS support number)
- Support Number = from_number (09631084471)
- Customer Number = to_number (+919876543210)

**✅ Pass Criteria**:
- Call queued successfully
- Direction logic correctly identifies outgoing call

---

### Test 7: Missing Required Fields

**Purpose**: Test validation for missing required fields

```bash
curl -X POST http://localhost:8000/webhook/zapier \
  -H "Content-Type: application/json" \
  -d '{
    "from_number": "+919876543210",
    "to_number": "09631084471"
  }'
```

**Expected Response** (422 Unprocessable Entity):
```json
{
  "detail": [
    {
      "loc": ["body", "call_id"],
      "msg": "field required",
      "type": "value_error.missing"
    },
    ...
  ]
}
```

**✅ Pass Criteria**:
- Returns 422 status code
- Shows validation errors for missing fields

---

### Test 8: Stats Endpoint

**Purpose**: Verify statistics tracking

```bash
# After running previous tests
curl http://localhost:8000/stats
```

**Expected Response** (200 OK):
```json
{
  "stats": {
    "total_processed": 4,
    "successfully_posted": 0,
    "failed": 4
  },
  "timestamp": "..."
}
```

**✅ Pass Criteria**:
- Returns 200 status code
- Shows accurate count of processed calls
- Stats match number of test calls made

---

### Test 9: Call Details Endpoint

**Purpose**: Retrieve specific call details

```bash
curl http://localhost:8000/call/TEST_CALL_001
```

**Expected Response** (200 OK):
```json
{
  "call_id": "TEST_CALL_001",
  "from_number": "+919876543210",
  "to_number": "09631084471",
  "duration": 120,
  "timestamp": "...",
  "processed_at": "...",
  "transcription_text": "...",
  "slack_posted": false,
  "status": "failed"
}
```

**✅ Pass Criteria**:
- Returns 200 status code
- Shows complete call details
- Data matches original webhook payload

---

## 🎙️ Transcription Testing

### Test 10: Transcription with Real Audio

**Purpose**: Test full transcription pipeline

**Requirements**:
- Valid `ASSEMBLYAI_API_KEY`
- Publicly accessible audio file URL

```bash
curl -X POST http://localhost:8000/webhook/zapier \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "TRANSCRIPTION_TEST_001",
    "from_number": "+919876543210",
    "to_number": "09631084471",
    "duration": 30,
    "recording_url": "https://example.com/sample-call.mp3",
    "agent_name": "Test Agent",
    "agent_slack_handle": "@test",
    "department": "Customer Success",
    "customer_segment": "General"
  }'
```

**Expected Behavior**:
1. Webhook returns success immediately
2. Background task downloads recording
3. Recording sent to AssemblyAI
4. Transcription completes (1-3 minutes)
5. Message posted to Slack

**Monitor logs**:
```bash
# Watch application logs for transcription progress
# You'll see:
# - "Downloading recording for call..."
# - "Transcribing call..."
# - "Transcription completed: X characters"
# - "Posting to Slack"
# - "Successfully completed processing..."
```

**✅ Pass Criteria**:
- Webhook returns success instantly (< 1 second)
- Recording downloads successfully
- AssemblyAI transcription completes
- Transcription has content
- Slack message posted with transcription

---

## 💬 Slack Integration Testing

### Test 11: Slack Webhook

**Purpose**: Verify Slack webhook is working

```bash
curl -X POST YOUR_SLACK_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{
    "text": "🧪 Test message from Exotel-Slack System - If you see this, Slack integration is working!"
  }'
```

**Expected Result**:
- Message appears in your Slack channel
- Message formatting is correct

**✅ Pass Criteria**:
- Returns 200 status code
- Message visible in Slack channel

---

### Test 12: Full Slack Message Format

**Purpose**: Verify complete Slack message formatting

After running Test 10 (transcription test), check your Slack channel for message with this format:

```
📞 Support Number:
09631084471

📱 Candidate/Customer Number:
+919876543210

❗ Concern:
[First 200 chars of transcription]

👤 CS Agent:
@test <+919876543210>

🏢 Department:
Customer Success

⏰ Timestamp:
2025-10-09 17:58:27 UTC

📋 Call Metadata:
• Call ID: `TRANSCRIPTION_TEST_001`
• Duration: 30s
• Status: completed
• Agent: Test Agent
• Customer Segment: General

📝 Full Transcription:
```
[Complete transcription]
```

🎧 Recording/Voice Note:
Recording processed and transcribed above
```

**✅ Pass Criteria**:
- All sections present
- Phone numbers correctly assigned based on direction
- Transcription appears in both "Concern" and "Full Transcription"
- Formatting matches image exactly

---

## 🔗 Zapier Integration Testing

### Test 13: Zapier Test Request

**Purpose**: Test Zapier webhook integration

**Setup**:
1. Configure Zap as per ZAPIER_INTEGRATION_GUIDE.md
2. Use "Test step" in Zapier

**Expected Result**:
- Zapier shows success response
- Your system logs show incoming request
- Stats endpoint shows one more processed call

**✅ Pass Criteria**:
- Zapier test succeeds
- Application receives and processes request
- Response returned to Zapier in < 1 second

---

### Test 14: End-to-End with Real Exotel Call

**Purpose**: Test complete flow from Exotel to Slack

**Steps**:
1. Make a real call through Exotel
2. Wait for call to complete and recording to be ready
3. Zapier triggers (1-15 minutes depending on plan)
4. Zapier sends webhook to your system
5. System downloads recording
6. System transcribes audio
7. System posts to Slack

**Monitor**:
- Zapier Task History: [zapier.com/app/history](https://zapier.com/app/history)
- Your application logs (Render/Docker/Local)
- Slack channel for message

**✅ Pass Criteria**:
- Call appears in Zapier history
- Webhook successfully sent to your system
- Recording downloaded and transcribed
- Message posted to Slack with correct format
- No errors in logs

---

## 📊 Database Testing

### Test 15: Database Persistence

**Purpose**: Verify database survives restart

```bash
# Check current stats
curl http://localhost:8000/stats

# Restart application
# - Docker: docker-compose restart
# - Local: Ctrl+C then python app.py again
# - Render: Trigger manual deploy

# Check stats again
curl http://localhost:8000/stats
```

**Expected Result**:
- Stats are the same before and after restart
- Database file exists and is not empty

**✅ Pass Criteria**:
- Total processed count remains same after restart
- Database file persists
- No data loss

---

### Test 16: Database Query

**Purpose**: Manually inspect database

```bash
# Open database
sqlite3 processed_calls.db

# Query all calls
SELECT * FROM processed_calls;

# Count total
SELECT COUNT(*) FROM processed_calls;

# Check for duplicates
SELECT call_id, COUNT(*) as count 
FROM processed_calls 
GROUP BY call_id 
HAVING count > 1;

# Exit
.quit
```

**✅ Pass Criteria**:
- Database opens successfully
- Records match API stats
- No duplicate call_ids
- All fields populated correctly

---

## ⚡ Load Testing (Optional)

### Test 17: Concurrent Requests

**Purpose**: Test system handles multiple simultaneous calls

```bash
# Install Apache Bench (if not installed)
# Ubuntu: sudo apt install apache2-utils
# Mac: comes pre-installed

# Run load test - 100 requests, 10 concurrent
ab -n 100 -c 10 -p payload.json -T application/json http://localhost:8000/webhook/zapier
```

Create `payload.json`:
```json
{
  "call_id": "LOAD_TEST_${RANDOM}",
  "from_number": "+919876543210",
  "to_number": "09631084471",
  "duration": 60,
  "agent_name": "Test",
  "agent_slack_handle": "@test",
  "department": "CS",
  "customer_segment": "General"
}
```

**Expected Results**:
- All requests return 200 OK
- Average response time < 100ms
- No errors or crashes

**✅ Pass Criteria**:
- 100% success rate
- Fast response times
- System stable under load

---

## 🐛 Error Testing

### Test 18: Invalid JSON

```bash
curl -X POST http://localhost:8000/webhook/zapier \
  -H "Content-Type: application/json" \
  -d 'invalid json{'
```

**Expected**: 400 Bad Request or 422 Unprocessable Entity

---

### Test 19: Missing SLACK_WEBHOOK_URL

```bash
# Temporarily unset environment variable
unset SLACK_WEBHOOK_URL

# Restart app and try webhook
curl -X POST http://localhost:8000/webhook/zapier -d '...'
```

**Expected**: 500 Internal Server Error with message about Slack webhook not configured

---

### Test 20: Missing ASSEMBLYAI_API_KEY

```bash
# Temporarily unset environment variable
unset ASSEMBLYAI_API_KEY

# Restart app and try webhook
curl -X POST http://localhost:8000/webhook/zapier -d '...'
```

**Expected**: 500 Internal Server Error with message about transcription service not configured

---

## 📝 Test Results Template

Use this template to track test results:

```markdown
## Test Results - [Date]

### Environment
- Platform: [Local/Render/Docker]
- Python Version: [3.11.x]
- Branch: [main]

### Unit Tests
- [ ] Test 1: Health Endpoint - ✅ PASS / ❌ FAIL
- [ ] Test 2: Root Endpoint - ✅ PASS / ❌ FAIL
- [ ] Test 3: Valid Webhook - ✅ PASS / ❌ FAIL
- [ ] Test 4: Duplicate Detection - ✅ PASS / ❌ FAIL
- [ ] Test 5: Incoming Call Direction - ✅ PASS / ❌ FAIL
- [ ] Test 6: Outgoing Call Direction - ✅ PASS / ❌ FAIL
- [ ] Test 7: Missing Fields - ✅ PASS / ❌ FAIL
- [ ] Test 8: Stats Endpoint - ✅ PASS / ❌ FAIL
- [ ] Test 9: Call Details - ✅ PASS / ❌ FAIL

### Integration Tests
- [ ] Test 10: Transcription - ✅ PASS / ❌ FAIL
- [ ] Test 11: Slack Webhook - ✅ PASS / ❌ FAIL
- [ ] Test 12: Slack Message Format - ✅ PASS / ❌ FAIL
- [ ] Test 13: Zapier Test - ✅ PASS / ❌ FAIL
- [ ] Test 14: End-to-End - ✅ PASS / ❌ FAIL

### Database Tests
- [ ] Test 15: Database Persistence - ✅ PASS / ❌ FAIL
- [ ] Test 16: Database Query - ✅ PASS / ❌ FAIL

### Performance Tests
- [ ] Test 17: Load Testing - ✅ PASS / ❌ FAIL

### Error Tests
- [ ] Test 18: Invalid JSON - ✅ PASS / ❌ FAIL
- [ ] Test 19: Missing Slack Config - ✅ PASS / ❌ FAIL
- [ ] Test 20: Missing Transcription Config - ✅ PASS / ❌ FAIL

### Notes
[Add any observations, issues found, or improvements needed]
```

---

## ✅ Pre-Production Checklist

Before deploying to production:

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Database persistence verified
- [ ] Duplicate prevention works
- [ ] Call direction logic correct
- [ ] Slack messages formatted correctly
- [ ] Zapier integration tested
- [ ] End-to-end test with real call succeeds
- [ ] Error handling tested
- [ ] Environment variables configured
- [ ] Logs are clean (no critical errors)
- [ ] Health endpoint returns healthy
- [ ] Documentation reviewed
- [ ] Monitoring setup (uptime checks)

---

## 🆘 Troubleshooting Tests

### If tests fail:

1. **Check logs**: Look for error messages
2. **Verify environment**: All env vars set correctly?
3. **Check services**: Are external services (Slack, AssemblyAI) working?
4. **Database**: Is it writable? Does it have data?
5. **Network**: Can app reach external APIs?
6. **Credentials**: Are API keys valid?

### Common Issues:

**"Database locked"**:
- SQLite is single-writer
- If running tests too fast, add delays
- Or use concurrent-safe database (PostgreSQL)

**"Transcription fails"**:
- Check AssemblyAI API key
- Verify recording URL is accessible
- Check audio file format (should be MP3/WAV)

**"Slack message not posted"**:
- Verify webhook URL
- Test webhook manually with curl
- Check Slack app/webhook status

---

## 📚 Additional Testing Resources

- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest Documentation](https://docs.pytest.org/)
- [AssemblyAI API Docs](https://www.assemblyai.com/docs)
- [Slack API Testing](https://api.slack.com/messaging/webhooks#test)

---

**Happy Testing!** 🧪

