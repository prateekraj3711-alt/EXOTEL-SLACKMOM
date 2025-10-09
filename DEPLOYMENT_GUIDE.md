# Deployment Guide

Complete guide for deploying the Exotel-Slack Complete System to production.

## 🎯 Deployment Options Overview

| Platform | Difficulty | Cost | Best For |
|----------|-----------|------|----------|
| **Render** | ⭐ Easy | Free tier available | Quick start, hobby projects |
| **Railway** | ⭐⭐ Easy | $5+/month | Small teams |
| **Heroku** | ⭐⭐ Medium | $7+/month | Enterprise features |
| **AWS ECS** | ⭐⭐⭐ Advanced | Variable | High scale, custom control |
| **Docker** | ⭐⭐ Medium | Infrastructure cost | Self-hosted, on-premise |
| **VPS** | ⭐⭐⭐ Advanced | $5+/month | Full control, custom setup |

## 🚀 Option 1: Deploy to Render (Recommended)

Render offers free tier with persistent storage - perfect for this application.

### Prerequisites

- GitHub account
- Render account (free): [render.com](https://render.com)
- Git installed locally

### Step 1: Push Code to GitHub

```bash
# Navigate to project directory
cd exotel-slack-complete-system

# Initialize git repository
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Exotel-Slack Complete System"

# Create repository on GitHub (via web interface)
# Then add remote and push
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

### Step 2: Create Web Service on Render

1. **Go to Render Dashboard**: [dashboard.render.com](https://dashboard.render.com)

2. **Click "New +"** → **"Web Service"**

3. **Connect Repository**:
   - Select "Connect a repository"
   - Authorize GitHub access
   - Choose your repository

4. **Configure Service**:
   - **Name**: `exotel-slack-complete` (or your choice)
   - **Region**: Choose closest to your users (Singapore for Asia)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Select "Free" (or paid plan for production)

5. **Advanced Settings**:
   - **Health Check Path**: `/health`
   - **Auto-Deploy**: Yes (deploy on git push)

6. Click **"Create Web Service"**

### Step 3: Configure Environment Variables

In Render dashboard, go to your service → **Environment** tab:

Add these variables:

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here
EXOTEL_API_KEY=your_exotel_api_key
EXOTEL_API_TOKEN=your_exotel_api_token
EXOTEL_SID=your_exotel_account_sid
SUPPORT_NUMBER=09631084471
DATABASE_PATH=/opt/render/project/src/processed_calls.db
```

**Important**: Click **"Save Changes"** after adding all variables.

### Step 4: Enable Persistent Disk (Important!)

For duplicate prevention to work across restarts:

1. Go to **"Disks"** tab in Render dashboard
2. Click **"Add Disk"**
3. Configure:
   - **Name**: `database-disk`
   - **Mount Path**: `/opt/render/project/src`
   - **Size**: 1 GB (free tier)
4. Click **"Save"**

**Note**: Free tier includes 1GB persistent disk at no extra cost.

### Step 5: Deploy

Render will automatically deploy your service. Monitor progress:

1. Go to **"Logs"** tab
2. Watch build and deployment logs
3. Wait for "Deploy live" message (takes 2-5 minutes)

### Step 6: Get Your URL

After deployment:

```
https://exotel-slack-complete.onrender.com
```

Test it:
```bash
curl https://your-app-name.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-09T18:00:00Z",
  "database": "connected",
  ...
}
```

### Step 7: Configure Zapier

Use your Render URL in Zapier webhook:
```
https://your-app-name.onrender.com/webhook/zapier
```

See [ZAPIER_INTEGRATION_GUIDE.md](ZAPIER_INTEGRATION_GUIDE.md) for complete setup.

---

## 🚂 Option 2: Deploy to Railway

Railway offers simple deployment with automatic SSL.

### Step 1: Install Railway CLI

```bash
npm install -g @railway/cli
```

### Step 2: Login

```bash
railway login
```

### Step 3: Initialize Project

```bash
cd exotel-slack-complete-system
railway init
```

Select: **"Create new project"**

### Step 4: Add Environment Variables

```bash
# Add variables one by one
railway variables set SLACK_WEBHOOK_URL="your_webhook_url"
railway variables set ASSEMBLYAI_API_KEY="your_api_key"
railway variables set EXOTEL_API_KEY="your_key"
railway variables set EXOTEL_API_TOKEN="your_token"
railway variables set EXOTEL_SID="your_sid"
railway variables set SUPPORT_NUMBER="09631084471"
railway variables set DATABASE_PATH="/app/processed_calls.db"
```

Or use Railway dashboard to add variables via web interface.

### Step 5: Deploy

```bash
railway up
```

Railway will:
- Build Docker image
- Deploy service
- Provide public URL

### Step 6: Add Persistent Volume

1. Go to Railway dashboard
2. Select your project
3. Go to **"Volumes"** tab
4. Click **"New Volume"**
5. Configure:
   - **Mount Path**: `/app`
   - Click **"Add"**

### Step 7: Get URL

```bash
railway domain
```

Or check Railway dashboard for your URL.

---

## 🐳 Option 3: Deploy with Docker (Self-Hosted)

Deploy on any VPS (DigitalOcean, Linode, AWS EC2, etc.)

### Step 1: Prepare VPS

SSH into your server:
```bash
ssh user@your-server-ip
```

Install Docker:
```bash
# Update packages
sudo apt update
sudo apt install -y docker.io docker-compose

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (optional)
sudo usermod -aG docker $USER
```

### Step 2: Upload Code

```bash
# On your local machine
scp -r exotel-slack-complete-system user@your-server-ip:/home/user/
```

Or clone from GitHub:
```bash
# On server
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

### Step 3: Create Environment File

```bash
# On server
cp env.example .env
nano .env
```

Fill in your credentials, then save (Ctrl+X, Y, Enter).

### Step 4: Run with Docker Compose

```bash
# Build and start
docker-compose up -d

# Check logs
docker-compose logs -f

# Check status
docker-compose ps
```

### Step 5: Setup Nginx Reverse Proxy (Optional)

For SSL and custom domain:

```bash
# Install Nginx
sudo apt install -y nginx certbot python3-certbot-nginx

# Create Nginx config
sudo nano /etc/nginx/sites-available/exotel-slack
```

Add configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/exotel-slack /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

Get SSL certificate:
```bash
sudo certbot --nginx -d your-domain.com
```

### Step 6: Setup Auto-Restart

Create systemd service:
```bash
sudo nano /etc/systemd/system/exotel-slack.service
```

Add:
```ini
[Unit]
Description=Exotel-Slack Complete System
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/user/exotel-slack-complete-system
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable exotel-slack.service
sudo systemctl start exotel-slack.service
```

---

## ☁️ Option 4: Deploy to AWS (Advanced)

### Using AWS ECS with Fargate

#### Step 1: Push Image to ECR

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

# Create repository
aws ecr create-repository --repository-name exotel-slack-complete

# Build and tag image
docker build -t exotel-slack-complete .
docker tag exotel-slack-complete:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/exotel-slack-complete:latest

# Push image
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/exotel-slack-complete:latest
```

#### Step 2: Create ECS Task Definition

Create `task-definition.json`:
```json
{
  "family": "exotel-slack-complete",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "exotel-slack-app",
      "image": "YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/exotel-slack-complete:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "SUPPORT_NUMBER", "value": "09631084471"},
        {"name": "DATABASE_PATH", "value": "/app/processed_calls.db"}
      ],
      "secrets": [
        {"name": "SLACK_WEBHOOK_URL", "valueFrom": "arn:aws:secretsmanager:..."},
        {"name": "ASSEMBLYAI_API_KEY", "valueFrom": "arn:aws:secretsmanager:..."}
      ],
      "mountPoints": [
        {
          "sourceVolume": "database",
          "containerPath": "/app"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/exotel-slack",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "volumes": [
    {
      "name": "database",
      "efsVolumeConfiguration": {
        "fileSystemId": "fs-xxxxxxxx",
        "transitEncryption": "ENABLED"
      }
    }
  ]
}
```

Register task:
```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

#### Step 3: Create ECS Service

```bash
aws ecs create-service \
  --cluster default \
  --service-name exotel-slack-complete \
  --task-definition exotel-slack-complete \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=exotel-slack-app,containerPort=8000"
```

---

## 📊 Post-Deployment Checklist

After deploying to any platform:

### 1. Test Health Endpoint

```bash
curl https://your-deployed-url/health
```

Expected: `200 OK` with JSON response

### 2. Test Webhook Endpoint

```bash
curl -X POST https://your-deployed-url/webhook/zapier \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "TEST123",
    "from_number": "+919876543210",
    "to_number": "09631084471",
    "duration": 60,
    "recording_url": "https://example.com/test.mp3",
    "agent_name": "Test Agent",
    "agent_slack_handle": "@test",
    "department": "Customer Success",
    "customer_segment": "General"
  }'
```

Expected: `200 OK` with success message

### 3. Check Logs

- **Render**: Dashboard → Logs tab
- **Railway**: Dashboard → Deployments → Logs
- **Docker**: `docker-compose logs -f`
- **AWS**: CloudWatch Logs

### 4. Verify Database Persistence

```bash
# Make a test request
curl -X POST https://your-url/webhook/zapier -d '...'

# Restart service
# (method depends on platform)

# Make same request again
curl -X POST https://your-url/webhook/zapier -d '...'

# Check response - should say "Duplicate call"
```

### 5. Test Full Flow

1. Make a real Exotel call
2. Wait for Zapier to trigger (1-15 min)
3. Check your deployed app logs
4. Verify transcription completes
5. Check Slack for formatted message

### 6. Monitor Performance

Check stats endpoint:
```bash
curl https://your-deployed-url/stats
```

### 7. Setup Monitoring (Optional)

- **Uptime Robot**: [uptimerobot.com](https://uptimerobot.com) - Free uptime monitoring
- **Better Uptime**: [betteruptime.com](https://betteruptime.com) - Advanced monitoring
- **Sentry**: Error tracking and performance monitoring

---

## 🔒 Security Best Practices

### 1. Secure Environment Variables

- Never commit `.env` file to git
- Use secrets management (AWS Secrets Manager, Render Secrets, etc.)
- Rotate API keys regularly

### 2. Enable HTTPS

All major platforms (Render, Railway, Heroku) provide automatic HTTPS.

For self-hosted: Use Let's Encrypt (Certbot)

### 3. Add API Authentication (Optional)

Add authentication to webhook endpoint:

```python
# In app.py
from fastapi import Header, HTTPException

WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET')

@app.post("/webhook/zapier")
async def zapier_webhook(
    payload: ZapierWebhookPayload,
    x_webhook_secret: Optional[str] = Header(None)
):
    if x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # ... rest of code
```

### 4. Rate Limiting (Optional)

Add rate limiting for high-traffic scenarios:

```bash
pip install slowapi
```

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/webhook/zapier")
@limiter.limit("10/minute")
async def zapier_webhook(request: Request, payload: ZapierWebhookPayload):
    # ... code
```

---

## 🔄 Updating Your Deployment

### Render/Railway (Git-based)

```bash
# Make changes locally
git add .
git commit -m "Update: ..."
git push

# Auto-deploys on push
```

### Docker (Self-hosted)

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

### AWS ECS

```bash
# Build new image
docker build -t exotel-slack-complete .
docker tag exotel-slack-complete:latest YOUR_ECR_URL:latest
docker push YOUR_ECR_URL:latest

# Update service
aws ecs update-service --cluster default --service exotel-slack-complete --force-new-deployment
```

---

## 🆘 Troubleshooting Deployment

### Issue: Build fails

**Check**:
- `requirements.txt` is complete
- Python version compatibility
- Build logs for specific error

**Solution**:
- Verify all dependencies
- Check Python version (3.11+ required)
- Review build command

### Issue: Service crashes on startup

**Check**:
- Environment variables are set correctly
- Database path is writable
- Logs for startup errors

**Solution**:
- Verify all required env vars
- Check persistent disk is mounted
- Review startup logs

### Issue: Database doesn't persist

**Check**:
- Persistent disk/volume is configured
- `DATABASE_PATH` points to mounted volume
- Permissions on database file

**Solution**:
- Enable persistent disk (Render)
- Add volume (Railway/Docker)
- Check mount path matches `DATABASE_PATH`

### Issue: 502 Bad Gateway

**Check**:
- Service is running
- Health check is passing
- Port configuration is correct

**Solution**:
- Check logs for errors
- Verify app binds to `0.0.0.0:$PORT`
- Test health endpoint

---

## ✅ Deployment Complete!

Your Exotel-Slack Complete System is now deployed and ready to handle production traffic.

**Next Steps**:
1. ✅ Configure Zapier integration
2. ✅ Test with real Exotel calls
3. ✅ Monitor logs and performance
4. ✅ Set up uptime monitoring

**Your deployed URL**:
```
https://your-app-name.onrender.com
```

Use this URL in your Zapier webhook configuration!

