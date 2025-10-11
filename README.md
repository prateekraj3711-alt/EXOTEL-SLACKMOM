# 🚀 Exotel to Slack MOM System - FINAL DEPLOYMENT

## 📦 Complete Render Deployment Package

This folder contains all the files needed to deploy the **Exotel to Slack MOM System** on Render.

---

## 📋 Files Included

| File | Purpose |
|------|---------|
| `app.py` | Main FastAPI application with all features |
| `requirements.txt` | Python dependencies |
| `agent_mapping.json` | Clean database with ONLY 12 CUSTOMER SUPPORT agents |
| `env.example` | Environment variables template |
| `CUSTOMER_SUPPORT_TEAM_CONFIGURED.md` | Documentation of configured agents |
| `README.md` | This deployment guide |

---

## ✨ Features Included

✅ **Transcription**: OpenAI Whisper API  
✅ **MOM Generation**: GPT-3.5-turbo with tone & issue type  
✅ **Smart Agent Detection**: Matches phone numbers to agents  
✅ **Department Filtering**: Only CUSTOMER SUPPORT agents  
✅ **Slack Integration**: Posts with agent tagging  
✅ **Transcript in Message**: Full transcript below recording link  
✅ **Duplicate Prevention**: SQLite database tracking  
✅ **Rate Limiting**: Built-in delays and semaphores  
✅ **IST Timezone**: All timestamps in Indian Standard Time  

---

## 🚀 Render Deployment Steps

### **Step 1: Create New Web Service**

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Select the repository with these files

### **Step 2: Configure Service**

**Name:** `exotel-slackmom-final` (or your choice)  
**Region:** Choose closest to your users  
**Branch:** `main` (or your deployment branch)  
**Root Directory:** `SLACKMOM FINAL` (if in subfolder)  
**Runtime:** `Python 3`  
**Build Command:** `pip install -r requirements.txt`  
**Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`  

### **Step 3: Add Environment Variables**

Go to **Environment** tab and add these variables:

```bash
# Slack Configuration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_BOT_TOKEN=xoxb-your-bot-token-here

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here

# Exotel Configuration
EXOTEL_API_KEY=your_exotel_api_key
EXOTEL_API_TOKEN=your_exotel_api_token
EXOTEL_SID=your_exotel_account_sid

# Support Number (legacy, not critical)
SUPPORT_NUMBER=09631084471

# Database
DATABASE_PATH=processed_calls.db

# Rate Limiting
PROCESSING_DELAY=5
MAX_CONCURRENT_CALLS=3

# Department Filter (IMPORTANT!)
ALLOWED_DEPARTMENTS=CUSTOMER SUPPORT

# Port (Render sets this automatically)
PORT=10000
```

### **Step 4: Deploy**

1. Click **"Create Web Service"**
2. Render will automatically:
   - Clone your repo
   - Install dependencies
   - Start the service
3. Wait for deployment to complete (2-3 minutes)

### **Step 5: Get Your Service URL**

Once deployed, your service URL will be:
```
https://exotel-slackmom-final.onrender.com
```

**Important:** Copy this URL - you'll need it for Zapier!

---

## 🔗 Zapier Integration Setup

### **Step 1: Create New Zap**

1. **Trigger:** Schedule by Zapier
   - Frequency: **Every Hour**
   - Minute: `00` (runs at top of each hour)

### **Step 2: Fetch Exotel Calls**

2. **Action:** Webhooks by Zapier → GET Request
   - URL: `https://api.exotel.com/v1/Accounts/YOUR_SID/Calls.json`
   - Method: **GET**
   - Basic Auth:
     - Username: `YOUR_EXOTEL_API_KEY`
     - Password: `YOUR_EXOTEL_API_TOKEN`
   - Query Params:
     - `From`: (leave empty - fetch all)
     - `PageSize`: `100`
     - `StartTime`: Set to 1 hour ago

### **Step 3: Loop Through Calls**

3. **Action:** Looping by Zapier
   - Loop On: `Calls`
   - Create Loop from Line-Items: Yes

### **Step 4: Send to Your Service**

4. **Action:** Webhooks by Zapier → POST Request
   - URL: `https://exotel-slackmom-final.onrender.com/webhook/exotel`
   - Method: **POST**
   - Data (JSON):
     ```json
     {
       "call_id": "{{Sid}}",
       "from_number": "{{From}}",
       "to_number": "{{To}}",
       "duration": "{{Duration}}",
       "recording_url": "{{RecordingUrl}}",
       "status": "{{Status}}"
     }
     ```

### **Step 5: Test & Enable**

1. Test the Zap with a sample call
2. Enable the Zap
3. It will run every hour automatically

---

## 👥 Configured Agents (12 CUSTOMER SUPPORT)

The system is configured to process calls from these 12 agents:

1. Divya Karlapudi - 7799309499
2. Vaibhav Agarwal - 9311633945
3. Supriya Chettri - 8918062860
4. Mohan - 7569954922
5. Md Armaan - 9852338574
6. Ragul A S - 9663175704
7. Ruchi Mishra - 8582962326
8. Mrinalini Krishnan - 9902352404
9. Susmita Deb - 9330818130
10. Syed Wali - 8126033006
11. Uttkarsh Tripathi - 9721439156
12. Arsh Ahmed Chauhan - 8219834257

**Only calls involving these 12 agents will be processed and posted to Slack.**

---

## 🔍 Testing Your Deployment

### **Test the Service is Running:**

Visit in your browser:
```
https://exotel-slackmom-final.onrender.com/
```

You should see:
```json
{
  "status": "active",
  "message": "Exotel-Slack Complete System Running",
  "endpoints": {
    "webhook": "/webhook/exotel",
    "health": "/health"
  }
}
```

### **Test with a Sample Call:**

Use curl or Postman:
```bash
curl -X POST https://exotel-slackmom-final.onrender.com/webhook/exotel \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "test123",
    "from_number": "7799309499",
    "to_number": "9876543210",
    "duration": "120",
    "recording_url": "https://example.com/recording.mp3",
    "status": "completed"
  }'
```

---

## 📊 Monitoring

### **Check Render Logs:**

1. Go to Render Dashboard
2. Click your service
3. Click **"Logs"** tab
4. You'll see:
   ```
   📞 Processing call from 7799309499
   ✅ Agent found: Divya Karlapudi - Department: CUSTOMER SUPPORT
   🎤 Transcribing audio...
   📝 Generating MOM...
   📤 Posting to Slack...
   ✅ Successfully completed
   ```

### **Check Slack:**

Look for messages in your configured Slack channel with:
- Customer details
- Agent name with email tag
- Date and time (IST)
- MOM with tone & issue type
- Full transcript below recording link

---

## 🛠️ Troubleshooting

### **Service not starting:**
- Check Render logs for errors
- Verify all environment variables are set
- Ensure `requirements.txt` is in the root directory

### **No Slack posts:**
- Verify `SLACK_WEBHOOK_URL` is correct
- Check if calls are from CUSTOMER SUPPORT agents
- Look at Render logs for "Skipping call" messages

### **Transcription errors:**
- Verify `OPENAI_API_KEY` is valid
- Check OpenAI account has credits
- Ensure recording URL is accessible

### **Wrong agent detection:**
- Verify phone numbers in `agent_mapping.json`
- Check phone number normalization (removes 0, country codes)
- Review Render logs for "Agent found" messages

---

## 📝 Adding New Agents

To add a new CUSTOMER SUPPORT agent:

1. Edit `agent_mapping.json`:
   ```json
   "9876543210": {
     "name": "New Agent Name",
     "email": "agent@springverify.in",
     "department": "CUSTOMER SUPPORT",
     "team": "Support"
   }
   ```

2. Commit and push to Git:
   ```bash
   git add agent_mapping.json
   git commit -m "Add new agent"
   git push
   ```

3. Render will auto-deploy the update

---

## 💰 Cost Estimates

### **Free Tier (For Testing):**
- ✅ Render: Free (with sleep after 15 min inactivity)
- ✅ Zapier: Free (100 tasks/month)
- ❌ OpenAI: Pay-per-use (no free tier)

### **Production (Recommended):**
- 💵 Render Starter: $7/month (always on, no sleep)
- 💵 Zapier Professional: $20/month (2000 tasks)
- 💵 OpenAI Tier 1: ~$5-10/month (depends on usage)

**Total: ~$32-37/month for reliable production service**

---

## 🎯 What's Next?

### **Optional Enhancements:**

1. **Google Sheets Integration:**
   - Fetch customer names from Google Sheets
   - Replace "Customer 9876543210" with actual names

2. **Multi-Department Support:**
   - Change `ALLOWED_DEPARTMENTS=CUSTOMER SUPPORT,SUPPORT CAND,EMP`
   - Process calls from multiple departments

3. **Custom Slack Channels:**
   - Route different departments to different channels
   - Add channel routing logic in app.py

4. **Analytics Dashboard:**
   - Track call volume, tone distribution
   - Generate weekly reports

---

## ✅ You're All Set!

This deployment package has everything you need. Just:

1. ✅ Push files to Git
2. ✅ Deploy on Render
3. ✅ Configure Zapier
4. ✅ Watch calls flow into Slack!

**Questions?** Check `CUSTOMER_SUPPORT_TEAM_CONFIGURED.md` for agent details.

---

## 📞 Support

For issues or questions about this deployment:
- Check Render logs first
- Verify environment variables
- Test with sample calls
- Review agent_mapping.json for correct phone numbers

**Happy deploying! 🚀**

