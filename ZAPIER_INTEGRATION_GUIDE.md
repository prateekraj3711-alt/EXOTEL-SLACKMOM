# Zapier Integration Guide

Complete step-by-step guide to integrate Exotel with your Slack system using Zapier.

## 📋 Prerequisites

Before starting, ensure you have:

- [x] Zapier account (Free tier works, Pro+ recommended for high volume)
- [x] Exotel account with API access
- [x] Your deployed system URL (e.g., `https://your-app.onrender.com`)
- [x] System health check passing: `https://your-app.onrender.com/health`

## 🎯 Integration Flow

```
Exotel Call → Zapier Trigger → Transform Data → POST to Your System → Transcribe → Post to Slack
```

## 🚀 Step-by-Step Setup

### Step 1: Create New Zap

1. Log in to [zapier.com](https://zapier.com)
2. Click **"Create Zap"** button (top left or center)
3. Name your Zap: `Exotel to Slack - Call Transcriptions`

### Step 2: Configure Trigger (Exotel)

#### Option A: Exotel App (Recommended if available)

1. **Search for Trigger App**: Type "Exotel" in the search bar
2. **Select Trigger Event**: Choose one of:
   - "New Call" (if available)
   - "Call Completed" (preferred - ensures recording is ready)
   - "New Recording" (if available)
3. **Connect Account**: Click "Sign in to Exotel"
   - Enter your Exotel API Key
   - Enter your Exotel API Token
   - Enter your Exotel SID
4. **Test Trigger**: 
   - Click "Test trigger"
   - Make a test call if needed
   - Zapier should fetch sample data
   - Click "Continue"

#### Option B: Webhook Catch Hook (If no Exotel app)

1. **Select Trigger**: Choose "Webhooks by Zapier"
2. **Select Event**: Choose "Catch Hook"
3. **Copy Webhook URL**: Zapier provides a URL like:
   ```
   https://hooks.zapier.com/hooks/catch/123456/abcdef/
   ```
4. **Configure Exotel**:
   - Go to Exotel Dashboard
   - Navigate to your Flow/Applet settings
   - Add webhook URL in "Call Completed" or "Recording Ready" webhook field
   - Save configuration
5. **Test Webhook**:
   - Make a test call through Exotel
   - Return to Zapier
   - Click "Test trigger"
   - Zapier should catch the webhook data
   - Click "Continue"

#### Option C: API Polling (Advanced)

If neither above options work:

1. **Add Action**: "Webhooks by Zapier" → "GET"
2. **Configure**:
   - URL: `https://api.exotel.com/v1/Accounts/{YOUR_SID}/Calls.json`
   - Method: GET
   - Auth: Basic Auth (Username: API Key, Password: API Token)
   - Query Parameters: `?Status=completed&PageSize=10`
3. **Add Filter**: Only continue if call is new (not processed before)
4. **Schedule**: Use "Schedule by Zapier" to run every 5-15 minutes

### Step 3: Add Filter (Optional but Recommended)

Add a filter to only process completed calls with recordings:

1. Click **"+"** button between trigger and next action
2. Select **"Filter by Zapier"**
3. Add conditions:
   - **Condition 1**: `Status` → `Text Exactly Matches` → `completed`
   - **Condition 2**: `RecordingUrl` → `Text Exists`
4. Click "Continue"

### Step 4: Add Formatter (Data Transformation)

This step ensures data is in the correct format:

1. Click **"+"** to add action
2. Search for **"Formatter by Zapier"**
3. Select **"Text"** action
4. Configure:
   - **Transform**: Text → Replace
   - **Input**: `{{Trigger__Duration}}`
   - **Find**: (leave blank if duration is already in seconds)
   - **Replace**: (leave blank)

### Step 5: Configure POST Action to Your System

This is the main action that sends data to your deployed system.

1. Click **"+"** to add action
2. Search for **"Webhooks by Zapier"**
3. Select **"POST"** action event

#### Configure POST Request

**URL**
```
https://your-app.onrender.com/webhook/zapier
```
Replace `your-app.onrender.com` with your actual deployment URL.

**Payload Type**
```
json
```

**Data (Map these fields)**

Click "Show all options" and add these fields:

| Field Name | Value from Exotel Trigger | Example |
|------------|---------------------------|---------|
| `call_id` | Sid or CallSid | `{{1. Sid}}` |
| `from_number` | From or CallerNumber | `{{1. From}}` |
| `to_number` | To or CalledNumber | `{{1. To}}` |
| `duration` | Duration | `{{1. Duration}}` |
| `recording_url` | RecordingUrl | `{{1. RecordingUrl}}` |
| `timestamp` | DateCreated or StartTime | `{{1. DateCreated}}` |
| `status` | Status | `{{1. Status}}` |
| `agent_name` | AgentName or custom field | `Prateek Raj` or `{{1. AgentName}}` |
| `agent_slack_handle` | Custom field or static | `@prateek.raj` |
| `department` | Department or static | `Customer Success` |
| `customer_segment` | Custom field or static | `General` |

**Example JSON mapping:**

```json
{
  "call_id": "{{1. Exotel Call__Sid}}",
  "from_number": "{{1. Exotel Call__From}}",
  "to_number": "{{1. Exotel Call__To}}",
  "duration": "{{1. Exotel Call__Duration}}",
  "recording_url": "{{1. Exotel Call__RecordingUrl}}",
  "timestamp": "{{1. Exotel Call__DateCreated}}",
  "status": "{{1. Exotel Call__Status}}",
  "agent_name": "Prateek Raj",
  "agent_slack_handle": "@prateek.raj",
  "department": "Customer Success",
  "customer_segment": "General"
}
```

**Headers** (Usually auto-filled, but verify):
```
Content-Type: application/json
```

**Advanced Options:**
- **Unflatten**: No
- **Wrap Request in Array**: No

### Step 6: Handle Agent Mapping (Optional)

If you have multiple agents and want to map them:

#### Option A: Static Mapping with Paths

Add a **"Paths by Zapier"** step before POST:

1. **Path A**: If `{{Agent}}` = "agent1@example.com" → set `agent_slack_handle` to `@agent1`
2. **Path B**: If `{{Agent}}` = "agent2@example.com" → set `agent_slack_handle` to `@agent2`
3. **Default Path**: Set to `@support`

#### Option B: Lookup Table

Add a **"Formatter by Zapier"** → "Lookup Table":

1. **Input**: `{{Trigger__AgentEmail}}`
2. **Lookup Table**:
   ```
   agent1@example.com → @agent1
   agent2@example.com → @agent2
   agent3@example.com → @agent3
   ```
3. **Fallback**: `@support`

#### Option C: Google Sheets Lookup

1. Create Google Sheet with columns: `Agent Email`, `Slack Handle`, `Department`
2. Add "Google Sheets" action → "Lookup Spreadsheet Row"
3. Search for agent by email
4. Use returned Slack handle in POST request

### Step 7: Test the Integration

1. Click **"Test step"** button in Zapier
2. Zapier will send a test POST request to your system
3. **Expected Response**:
   ```json
   {
     "success": true,
     "message": "Call queued for processing",
     "call_id": "...",
     "timestamp": "..."
   }
   ```
4. **Check your Slack channel** (wait 1-3 minutes for transcription)
   - You should see a formatted message with call details
   - Transcription should appear in the "Full Transcription" section

### Step 8: Handle Errors (Add Error Path)

1. Add **"Filter by Zapier"** after POST action
2. **Condition**: Only continue if `{{POST_response__success}}` is `false`
3. Add **"Gmail"** or **"Slack"** action to send error notification
4. Configure error message:
   ```
   Error processing call {{call_id}}:
   Error: {{POST_response__error}}
   ```

### Step 9: Turn On Your Zap

1. Review all steps
2. Give your Zap a meaningful name
3. Click **"Publish"** or toggle switch to **ON**
4. Zap is now live! 🎉

## 🎨 Advanced Configuration

### Handling Call Direction Dynamically

If Exotel doesn't provide direction, add a **Code by Zapier** step:

```javascript
// Determine call direction based on phone numbers
const fromNumber = inputData.from_number.replace(/\D/g, '');
const supportNumber = '09631084471'.replace(/\D/g, '');

let direction = 'incoming';
if (fromNumber.includes(supportNumber)) {
  direction = 'outgoing';
}

output = {
  direction: direction
};
```

### Custom Timestamp Formatting

Add **"Formatter by Zapier"** → "Date/Time" → "Format":

1. **Input**: `{{Trigger__DateCreated}}`
2. **From Format**: Auto-detect or specify Exotel's format
3. **To Format**: `YYYY-MM-DD HH:mm:ss UTC`
4. Use formatted output in POST data

### Batch Processing Multiple Recordings

If you get multiple recordings at once:

1. Use **"Looping by Zapier"** (Premium feature)
2. Loop through each recording
3. POST each one individually to your system

### Customer Segment Detection

Add **"Formatter by Zapier"** → "Text" → "Lookup Table":

1. **Input**: Customer phone number or customer ID
2. **Lookup Table**: Map known customers to segments
3. **Fallback**: "General"

## 🧪 Testing Your Zap

### Test with Sample Data

1. In Zapier editor, use "Test & Review" for each step
2. Click "Retest" if you make changes
3. Verify data mapping is correct

### Test with Real Call

1. Make a test call through Exotel
2. Wait for trigger to fire (1-15 minutes depending on Zapier plan)
3. Check **Zapier Task History**: [zapier.com/app/history](https://zapier.com/app/history)
4. Look for your Zap execution
5. Click on task to see detailed logs
6. Verify:
   - ✅ Trigger fired
   - ✅ Data transformed correctly
   - ✅ POST succeeded
   - ✅ Your system received data (check `/stats` endpoint)
   - ✅ Slack message posted

### Check System Logs

**If deployed on Render:**
```
Go to Render Dashboard → Your Service → Logs
```

**If running locally:**
```
Check terminal output for processing logs
```

**If using Docker:**
```bash
docker-compose logs -f
```

### Verify in Slack

Check your Slack channel for the formatted message. It should include:
- 📞 Support Number
- 📱 Customer Number
- ❗ Concern (brief excerpt)
- 👤 CS Agent
- 🏢 Department
- ⏰ Timestamp
- 📋 Call Metadata
- 📝 Full Transcription
- 🎧 Recording note

## 🐛 Troubleshooting

### Issue: Trigger not firing

**Symptoms:**
- No tasks showing in Zapier history
- Calls not being processed

**Checks:**
- Is Zap turned ON? (Check toggle in "My Zaps")
- Is Exotel webhook configured correctly?
- Check Exotel dashboard for webhook delivery logs
- Verify Exotel account credentials

**Solutions:**
- Re-authenticate Exotel connection in Zapier
- Test trigger manually
- Make a test call and wait 15 minutes (free tier)
- Check Exotel webhook delivery status

### Issue: POST action fails with 404

**Symptoms:**
- Zapier shows "404 Not Found" error
- Task marked as failed

**Checks:**
- Verify deployment URL is correct
- Check if app is running: `curl https://your-app.com/health`
- Look at Render/Railway deployment logs

**Solutions:**
- Correct the URL in Zapier (remove trailing slashes)
- Ensure app is deployed and running
- Check health endpoint manually
- Verify no typos in URL

### Issue: POST action fails with 500

**Symptoms:**
- Zapier shows "500 Internal Server Error"
- Task failed

**Checks:**
- Check your app logs (Render/Docker/Local)
- Verify all environment variables are set
- Check if required fields are missing

**Solutions:**
- Verify `SLACK_WEBHOOK_URL` is set
- Verify `ASSEMBLYAI_API_KEY` is set
- Check field mapping in Zapier
- Ensure all required fields are being sent

### Issue: Duplicate messages in Slack

**Symptoms:**
- Same call appears multiple times in Slack

**Checks:**
- Check if multiple Zaps are enabled
- Verify `call_id` is unique
- Check database for duplicate entries

**Solutions:**
- Disable duplicate Zaps
- System should prevent duplicates automatically
- Check `/stats` endpoint to see if call was processed multiple times
- Query database: Check `processed_calls` table

### Issue: Wrong data in Slack message

**Symptoms:**
- Phone numbers swapped
- Wrong agent name
- Missing fields

**Checks:**
- Review field mappings in Zapier POST data
- Check Exotel trigger data format
- Use "Test & Review" to see actual values

**Solutions:**
- Correct field mappings
- Add Formatter steps to transform data
- Use static values for missing fields
- Map correct Exotel fields

### Issue: Call direction is wrong

**Symptoms:**
- Incoming calls shown as outgoing or vice versa

**Checks:**
- Verify `SUPPORT_NUMBER` environment variable is correct
- Check phone number format (with/without +91)

**Solutions:**
- Update `SUPPORT_NUMBER` in environment variables
- Add Code by Zapier step to normalize phone numbers
- Use explicit direction field if Exotel provides it

### Issue: No Slack message appears

**Symptoms:**
- Zapier POST succeeds
- No error in logs
- But no Slack message

**Checks:**
- Is transcription completing? (Can take 1-3 minutes)
- Check app logs for transcription errors
- Verify Slack webhook URL
- Test Slack webhook manually

**Solutions:**
- Wait 3-5 minutes for transcription to complete
- Check `/call/{call_id}` endpoint to see status
- Test Slack webhook with curl
- Verify AssemblyAI API key is valid

## 📊 Monitoring Your Zap

### Zapier Task History

View all Zap executions:
1. Go to [zapier.com/app/history](https://zapier.com/app/history)
2. Filter by your Zap name
3. See success/failure rate
4. Click any task for detailed logs

### Set Up Zap Alerts

1. Go to Zap settings
2. Enable "Error Notifications"
3. Choose email or Slack notifications
4. Get alerted when Zap fails

### Monitor Your System

Check your system's statistics:
```bash
curl https://your-app.onrender.com/stats
```

Response:
```json
{
  "stats": {
    "total_processed": 150,
    "successfully_posted": 148,
    "failed": 2
  },
  "timestamp": "2025-10-09T18:00:00Z"
}
```

## 📈 Optimization for High Volume

### For 50+ Agents

1. **Upgrade Zapier Plan**:
   - Professional: 1-minute polling, 2,000 tasks/month
   - Team/Company: Instant webhooks, unlimited tasks

2. **Use Webhooks** (not polling):
   - Configure Exotel to push to Zapier webhook
   - Instant triggering instead of polling

3. **Optimize System**:
   - Deploy on paid Render plan (not free tier)
   - Enable persistent disk storage
   - Monitor database size

4. **Add Multiple Zaps** (if needed):
   - Separate Zap for each agent group
   - Load balancing across different endpoints

### Performance Tips

- **Minimize Formatter steps**: Only transform what's necessary
- **Use async operations**: Your system already handles this
- **Enable webhooks**: Faster than polling
- **Monitor limits**: Track Zapier task usage

## ✅ Checklist

Before going live, verify:

- [ ] Zap is published and turned ON
- [ ] Test call successfully processed end-to-end
- [ ] Slack message appears with correct format
- [ ] No duplicates when same call is re-processed
- [ ] All required fields are mapped correctly
- [ ] Call direction logic works correctly
- [ ] Agent names/handles are correct
- [ ] Error notifications are configured
- [ ] Zapier task history is clean (no errors)
- [ ] System health endpoint returns healthy status
- [ ] Database is persisting (not in-memory)

## 📚 Additional Resources

- [Zapier Webhooks Documentation](https://zapier.com/apps/webhook/help)
- [Exotel API Documentation](https://developer.exotel.com/)
- [AssemblyAI API Documentation](https://www.assemblyai.com/docs)
- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)

## 🆘 Need Help?

If you're still having issues:

1. Check system logs (Render/Docker/Local)
2. Check Zapier Task History for errors
3. Test each component individually:
   - Exotel → Zapier trigger
   - Zapier → Your system POST
   - Your system → Transcription
   - Your system → Slack
4. Verify all credentials and API keys
5. Check environment variables are set correctly

---

**You're all set!** 🎉 Your Exotel-to-Slack integration is now fully automated and ready to handle 50+ support agents.

