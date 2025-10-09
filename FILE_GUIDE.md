# File Guide

Quick reference for all files in this project.

## 📄 Core Application Files

### `app.py`
**The main application file - the heart of the system**

- FastAPI web server
- Database management (SQLite)
- Transcription service (AssemblyAI)
- Slack formatting and posting
- API endpoints

**Lines of Code**: ~700  
**Key Classes**:
- `DatabaseManager` - Handles duplicate prevention
- `TranscriptionService` - Downloads and transcribes recordings
- `SlackFormatter` - Formats messages for Slack

**API Endpoints**:
- `GET /` - Service info
- `GET /health` - Health check
- `POST /webhook/zapier` - Main webhook
- `GET /stats` - Statistics
- `GET /call/{call_id}` - Call details

---

## 🔧 Configuration Files

### `requirements.txt`
**Python dependencies**

Lists all required Python packages:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation
- `requests` - HTTP client

**Install**: `pip install -r requirements.txt`

### `env.example`
**Environment variables template**

Copy this to `.env` and fill in your credentials:
- Slack webhook URL
- AssemblyAI API key
- Exotel credentials
- Support phone number

**Usage**: `cp env.example .env` then edit `.env`

### `.gitignore`
**Git ignore rules**

Prevents committing sensitive files:
- `.env` (contains secrets)
- `*.db` (database files)
- `downloads/` (audio files)
- Python cache files

---

## 🐳 Deployment Files

### `Dockerfile`
**Docker container configuration**

Builds a Docker image with:
- Python 3.11
- Application code
- Dependencies
- Non-root user
- Health checks

**Build**: `docker build -t exotel-slack .`  
**Run**: `docker run -p 8000:8000 --env-file .env exotel-slack`

### `docker-compose.yml`
**Docker Compose configuration**

Runs the complete system with:
- Application container
- Volume mounts for persistence
- Environment variables
- Auto-restart

**Usage**: `docker-compose up -d`

### `render.yaml`
**Render.com deployment config**

Automatic deployment configuration:
- Python 3 environment
- Build and start commands
- Environment variables
- Health check path

**Usage**: Render auto-detects this file when deploying

---

## 📚 Documentation Files

### `README.md`
**Complete system documentation**

**What's inside**:
- Feature overview
- Architecture diagram
- Installation instructions
- Configuration guide
- API documentation
- Troubleshooting

**Length**: ~500 lines  
**Read this**: For complete understanding of the system

### `QUICKSTART.md`
**10-minute setup guide**

**What's inside**:
- Quick deployment to Render (5 min)
- Zapier integration (3 min)
- Testing (2 min)

**Length**: ~200 lines  
**Read this**: To get started ASAP

### `ZAPIER_INTEGRATION_GUIDE.md`
**Complete Zapier setup guide**

**What's inside**:
- Step-by-step Zapier configuration
- Field mapping examples
- Advanced configurations
- Agent mapping
- Troubleshooting Zapier issues

**Length**: ~400 lines  
**Read this**: When setting up Zapier integration

### `DEPLOYMENT_GUIDE.md`
**Deployment to various platforms**

**What's inside**:
- Render deployment (detailed)
- Railway deployment
- Docker deployment
- AWS ECS deployment
- VPS deployment
- Security best practices

**Length**: ~500 lines  
**Read this**: For production deployment

### `TESTING_GUIDE.md`
**Comprehensive testing procedures**

**What's inside**:
- 20+ test procedures
- Unit tests
- Integration tests
- Load testing
- Database testing
- Test templates

**Length**: ~600 lines  
**Read this**: To verify your setup works

### `PROJECT_SUMMARY.md`
**High-level project overview**

**What's inside**:
- Architecture explanation
- Component descriptions
- Workflow examples
- Success metrics
- Technical specifications

**Length**: ~400 lines  
**Read this**: To understand the big picture

### `FILE_GUIDE.md`
**This file - explains all files**

**What's inside**:
- Quick reference for each file
- What each file does
- When to use it

**Length**: Short and sweet  
**Read this**: To understand the project structure

---

## 🧪 Testing & Utility Files

### `test_system.py`
**Automated test script**

Tests all major functionality:
- Health endpoint
- Webhook endpoint
- Duplicate detection
- Call direction logic
- Stats endpoint
- Validation

**Usage**:
```bash
python test_system.py https://your-app.onrender.com
```

**Output**: Color-coded pass/fail results

### `start.sh` (Linux/Mac)
**Quick start script for local development**

Automates:
- Virtual environment creation
- Dependency installation
- Directory creation
- Application startup

**Usage**:
```bash
./start.sh
```

### `start.bat` (Windows)
**Quick start script for Windows**

Same as `start.sh` but for Windows:
- Creates virtual environment
- Installs dependencies
- Starts application

**Usage**:
```batch
start.bat
```

---

## 🗂️ Generated Files (Not in Repo)

These files are created when the application runs:

### `processed_calls.db`
**SQLite database**

Stores:
- All processed call IDs
- Call metadata
- Transcriptions
- Processing status

**Location**: Root directory or `DATABASE_PATH` from `.env`  
**Size**: Grows over time (clean periodically)

### `downloads/`
**Downloaded audio files**

Contains:
- MP3 recordings from Exotel
- Temporary files during processing
- Auto-cleaned after transcription

**Location**: `./downloads/`  
**Gitignored**: Yes

### `.env`
**Environment variables**

Contains:
- API keys
- Secrets
- Configuration

**Created from**: `env.example`  
**Gitignored**: Yes (never commit!)

---

## 📋 File Usage Matrix

| File | Required | When to Use | Edit? |
|------|----------|-------------|-------|
| `app.py` | ✅ Yes | Always | Only for customization |
| `requirements.txt` | ✅ Yes | Always | Only to add dependencies |
| `env.example` | ✅ Yes | Setup | No, copy to `.env` |
| `.env` | ✅ Yes | Runtime | Yes, add your credentials |
| `Dockerfile` | 🔶 Optional | Docker deployment | Rarely |
| `docker-compose.yml` | 🔶 Optional | Docker deployment | Rarely |
| `render.yaml` | 🔶 Optional | Render deployment | Rarely |
| `README.md` | 📖 Docs | Understanding system | No |
| `QUICKSTART.md` | 📖 Docs | Quick setup | No |
| `ZAPIER_INTEGRATION_GUIDE.md` | 📖 Docs | Zapier setup | No |
| `DEPLOYMENT_GUIDE.md` | 📖 Docs | Deploying | No |
| `TESTING_GUIDE.md` | 📖 Docs | Testing | No |
| `PROJECT_SUMMARY.md` | 📖 Docs | Overview | No |
| `FILE_GUIDE.md` | 📖 Docs | File reference | No |
| `test_system.py` | 🧪 Test | Verification | No |
| `start.sh` | 🚀 Helper | Local dev (Unix) | No |
| `start.bat` | 🚀 Helper | Local dev (Windows) | No |

---

## 🎯 Quick Reference by Task

### "I want to deploy quickly"
1. Read: `QUICKSTART.md`
2. Use: `env.example` → `.env`
3. Deploy: Push to Render with `render.yaml`

### "I want to understand the system"
1. Read: `README.md`
2. Read: `PROJECT_SUMMARY.md`
3. Review: `app.py`

### "I want to run locally"
1. Copy: `env.example` to `.env`
2. Edit: `.env` with credentials
3. Run: `./start.sh` (or `start.bat` on Windows)
4. Test: `python test_system.py http://localhost:8000`

### "I want to deploy to production"
1. Read: `DEPLOYMENT_GUIDE.md`
2. Choose platform
3. Follow deployment steps
4. Read: `TESTING_GUIDE.md` to verify

### "I want to set up Zapier"
1. Deploy app first
2. Read: `ZAPIER_INTEGRATION_GUIDE.md`
3. Follow step-by-step instructions
4. Test with sample call

### "I want to customize"
1. Review: `app.py` (SlackFormatter class)
2. Modify message format
3. Test locally
4. Redeploy

### "I want to test"
1. Run: `python test_system.py [URL]`
2. Or follow: `TESTING_GUIDE.md` for manual tests

---

## 📦 What Each File Provides

### Core Functionality
- `app.py` - 100% of application logic

### Dependencies
- `requirements.txt` - All Python packages

### Configuration
- `env.example` - Template
- `.env` - Your actual config (you create this)

### Deployment
- `Dockerfile` - Container build
- `docker-compose.yml` - Complete stack
- `render.yaml` - Cloud deployment

### Documentation (7 files)
- `README.md` - Main docs
- `QUICKSTART.md` - Fast setup
- `ZAPIER_INTEGRATION_GUIDE.md` - Zapier setup
- `DEPLOYMENT_GUIDE.md` - Deploy guide
- `TESTING_GUIDE.md` - Test procedures
- `PROJECT_SUMMARY.md` - Overview
- `FILE_GUIDE.md` - This file

### Testing & Utilities
- `test_system.py` - Automated tests
- `start.sh` - Unix start script
- `start.bat` - Windows start script

---

## 🔢 File Statistics

- **Total Files**: 18
- **Documentation Files**: 7 (~2,500 lines)
- **Code Files**: 4 (~800 lines)
- **Config Files**: 4
- **Utility Scripts**: 3

---

## 💡 Pro Tips

1. **Start with QUICKSTART.md** - fastest way to get running
2. **Keep .env secure** - never commit to git
3. **Read README.md** - comprehensive reference
4. **Use test_system.py** - quick verification
5. **Check DEPLOYMENT_GUIDE.md** - before deploying
6. **Customize app.py** - modify as needed
7. **Monitor processed_calls.db** - clean periodically

---

## 🆘 Need Help?

1. **Quick setup**: See `QUICKSTART.md`
2. **Deployment issues**: See `DEPLOYMENT_GUIDE.md` troubleshooting
3. **Zapier problems**: See `ZAPIER_INTEGRATION_GUIDE.md` troubleshooting
4. **Testing**: See `TESTING_GUIDE.md`
5. **Understanding system**: See `PROJECT_SUMMARY.md`
6. **API reference**: See `README.md` API section

---

**Summary**: This project includes everything you need - application code, deployment configs, comprehensive documentation, and testing tools. Start with QUICKSTART.md and you'll be running in 10 minutes!

