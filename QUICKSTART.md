# Quick Start Guide

Get up and running in 10 minutes! ⚡

## 🎯 Goal

Have your Exotel-to-Slack system deployed and processing calls automatically.

## 📋 What You Need

Before starting, get these ready:

1. **Slack Webhook URL**
   - Go to: https://api.slack.com/messaging/webhooks
   - Create incoming webhook
   - Copy webhook URL

2. **AssemblyAI API Key**
   - Sign up: https://www.assemblyai.com
   - Get free API key (100 hours/month free)
   - Copy API key

3. **Exotel Credentials**
   - Exotel API Key
   - Exotel API Token
   - Exotel Account SID

4. **Your Support Phone Number**
   - Example: `09631084471`

## 🚀 5-Minute Setup

### Step 1: Deploy to Render (2 minutes)

1. **Fork or Push to GitHub**:
   ```bash
   cd exotel-slack-complete-system
   git init
   git add .
   git commit -m "Initial commit"
   # Create repo on GitHub, then:
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Deploy on Render**:
   - Go to: https://dashboard.render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Click "Connect"
   - Render auto-detects settings from `render.yaml`
   - Click "Create Web Service"

### Step 2: Add Environment Variables (1 minute)

In Render dashboard, add these:

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
ASSEMBLYAI_API_KEY=your_assemblyai_api_key
EXOTEL_API_KEY=your_exotel_api_key
EXOTEL_API_TOKEN=your_exotel_api_token
EXOTEL_SID=your_exotel_sid
SUPPORT_NUMBER=09631084471
```

Click **"Save Changes"**

### Step 3: Enable Persistent Disk (30 seconds)

1. Go to "Disks" tab in Render
2. Click "Add Disk"
3. Mount Path: `/opt/render/project/src`
4. Size: 1 GB
5. Click "Save"

### Step 4: Wait for Deployment (2 minutes)

Watch the "Logs" tab. When you see "Deploy live", you're ready!

Get your URL: `https://your-app-name.onrender.com`

### Step 5: Test It (30 seconds)

```bash
curl https://your-app-name.onrender.com/health
```

Should return: `{"status": "healthy", ...}`

✅ **Your system is now live!**

---

## 🔗 Connect Zapier (3 minutes)

### Quick Zapier Setup

1. **Create Zap**: Go to https://zapier.com/app/zaps
2. **Trigger**: 
   - Search "Exotel"
   - Choose "New Call" or "Call Completed"
   - Connect your Exotel account
3. **Action**:
   - Search "Webhooks"
   - Choose "POST"
   - URL: `https://your-app-name.onrender.com/webhook/zapier`
   - Payload Type: `json`
   - Data:
     ```json
     {
       "call_id": "{{Sid}}",
       "from_number": "{{From}}",
       "to_number": "{{To}}",
       "duration": "{{Duration}}",
       "recording_url": "{{RecordingUrl}}",
       "timestamp": "{{DateCreated}}",
       "status": "{{Status}}",
       "agent_name": "Prateek Raj",
       "agent_slack_handle": "@prateek.raj",
       "department": "Customer Success",
       "customer_segment": "General"
     }
     ```
4. **Test**: Click "Test step"
5. **Turn On**: Toggle Zap to ON

✅ **Zapier connected!**

---

## 🎉 You're Done!

Your system is now:
- ✅ Automatically fetching Exotel call recordings
- ✅ Transcribing them with AssemblyAI
- ✅ Posting formatted messages to Slack
- ✅ Preventing duplicates
- ✅ Handling 50+ agents

## 🧪 Test End-to-End

1. Make a test call through Exotel
2. Wait 1-15 minutes (depending on Zapier plan)
3. Check Slack for formatted message

## 📊 Monitor

- **Health**: `https://your-app-name.onrender.com/health`
- **Stats**: `https://your-app-name.onrender.com/stats`
- **Logs**: Render Dashboard → Logs tab
- **Zapier**: https://zapier.com/app/history

## 🆘 Troubleshooting

**No Slack messages?**
- Check Render logs for errors
- Verify Slack webhook URL is correct
- Test webhook manually: 
  ```bash
  curl -X POST YOUR_SLACK_WEBHOOK_URL \
    -H 'Content-Type: application/json' \
    -d '{"text":"Test"}'
  ```

**Zapier not triggering?**
- Check Zap is turned ON
- Verify Exotel webhook is configured
- Check Zapier Task History

**Duplicates appearing?**
- Verify persistent disk is enabled in Render
- Check `DATABASE_PATH` points to mounted disk

## 📚 Next Steps

- Read [README.md](README.md) for detailed documentation
- See [ZAPIER_INTEGRATION_GUIDE.md](ZAPIER_INTEGRATION_GUIDE.md) for advanced Zapier setup
- Review [TESTING_GUIDE.md](TESTING_GUIDE.md) for testing procedures
- Check [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for other deployment options

---

## 💡 Pro Tips

1. **Free Tier Limits**:
   - Render: 750 hours/month (always on)
   - AssemblyAI: 100 hours transcription/month
   - Zapier Free: 100 tasks/month

2. **For High Volume**:
   - Upgrade Zapier to Pro ($20/month) for faster polling
   - Upgrade Render to paid plan ($7/month) for better performance
   - Consider AssemblyAI paid plan for more hours

3. **Multiple Agents**:
   - Map agent emails to Slack handles in Zapier
   - Use Lookup Table or Code step
   - See advanced examples in Zapier guide

4. **Custom Fields**:
   - Modify `app.py` to add custom fields
   - Update Slack message format as needed
   - Redeploy with `git push`

---

**Congratulations! Your Exotel-Slack integration is live!** 🎉

Need help? Check the troubleshooting guides or review the logs.

