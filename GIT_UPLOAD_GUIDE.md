# Git Upload Guide

## 📤 What Files to Upload to Git

### ✅ Files to UPLOAD (Commit to Git)

#### Core Application Files
- ✅ **`app.py`** - Main application code
- ✅ **`requirements.txt`** - Python dependencies
- ✅ **`agent_mapping.json`** - Agent phone number mappings

#### Configuration Templates
- ✅ **`env.example`** - Environment variables template (NO secrets!)
- ✅ **`.gitignore`** - Git ignore rules

#### Deployment Files
- ✅ **`Dockerfile`** - Docker container configuration
- ✅ **`docker-compose.yml`** - Docker Compose setup
- ✅ **`render.yaml`** - Render deployment config

#### Documentation Files
- ✅ **`README.md`** - Main documentation
- ✅ **`QUICKSTART.md`** - Quick setup guide
- ✅ **`ZAPIER_INTEGRATION_GUIDE.md`** - Zapier setup
- ✅ **`DEPLOYMENT_GUIDE.md`** - Deployment instructions
- ✅ **`TESTING_GUIDE.md`** - Testing procedures
- ✅ **`PROJECT_SUMMARY.md`** - Project overview
- ✅ **`FILE_GUIDE.md`** - File reference
- ✅ **`AGENT_TRACKING_GUIDE.md`** - Agent mapping guide
- ✅ **`GIT_UPLOAD_GUIDE.md`** - This file

#### Utility Scripts
- ✅ **`test_system.py`** - Automated test script
- ✅ **`start.sh`** - Unix/Linux start script
- ✅ **`start.bat`** - Windows start script

---

### ❌ Files to NEVER UPLOAD (Security Risk!)

#### Sensitive Configuration
- ❌ **`.env`** - Contains API keys and secrets ⚠️ NEVER COMMIT!
- ❌ **`*.env.local`** - Local environment files
- ❌ **`*.env.production`** - Production secrets

#### Generated/Runtime Files
- ❌ **`processed_calls.db`** - Database file (contains call data)
- ❌ **`*.db`** - Any database files
- ❌ **`*.db-journal`** - SQLite journal files

#### Downloaded Files
- ❌ **`downloads/`** - Downloaded audio recordings
- ❌ **`downloads/*.mp3`** - Audio files
- ❌ **`downloads/*.wav`** - Audio files

#### Python Cache
- ❌ **`__pycache__/`** - Python cache directory
- ❌ **`*.pyc`** - Compiled Python files
- ❌ **`*.pyo`** - Optimized Python files
- ❌ **`.pytest_cache/`** - Pytest cache

#### Virtual Environment
- ❌ **`venv/`** - Python virtual environment
- ❌ **`env/`** - Alternative venv name
- ❌ **`.venv/`** - Hidden venv

#### IDE Files
- ❌ **`.vscode/`** - VS Code settings (optional - can commit if shared)
- ❌ **`.idea/`** - PyCharm settings
- ❌ **`*.swp`** - Vim swap files

#### Logs
- ❌ **`*.log`** - Log files
- ❌ **`logs/`** - Log directory

#### OS Files
- ❌ **`.DS_Store`** - macOS metadata
- ❌ **`Thumbs.db`** - Windows thumbnails
- ❌ **`desktop.ini`** - Windows folder config

---

## 🚀 Step-by-Step Git Upload

### Step 1: Navigate to Directory

```bash
cd exotel-slack-complete-system
```

### Step 2: Initialize Git (if not already done)

```bash
git init
```

### Step 3: Verify .gitignore

Check that `.gitignore` exists and contains:

```gitignore
# Environment
.env
.env.local
*.env.production

# Database
*.db
*.db-journal
*.sqlite
*.sqlite3

# Downloads
downloads/
downloads/*.mp3
downloads/*.wav

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db
desktop.ini

# Testing
.pytest_cache/
.coverage
htmlcov/
```

### Step 4: Check What Will Be Committed

```bash
git status
```

**Should show** (green = will be committed):
```
app.py
requirements.txt
agent_mapping.json
env.example
.gitignore
Dockerfile
docker-compose.yml
render.yaml
README.md
QUICKSTART.md
... (all documentation files)
test_system.py
start.sh
start.bat
```

**Should NOT show** (these are ignored):
```
.env
processed_calls.db
downloads/
__pycache__/
venv/
```

### Step 5: Add Files

```bash
# Add all files (respects .gitignore)
git add .

# Or add files individually
git add app.py
git add requirements.txt
git add agent_mapping.json
git add *.md
git add Dockerfile docker-compose.yml render.yaml
git add test_system.py start.sh start.bat
git add env.example .gitignore
```

### Step 6: Verify Staging

```bash
git status
```

Should show all files in green (staged for commit).

### Step 7: Commit

```bash
git commit -m "Initial commit: Exotel-Slack Complete System with phone-based agent tracking"
```

### Step 8: Create GitHub Repository

1. Go to [github.com](https://github.com)
2. Click "New repository" (+ icon, top right)
3. Name: `exotel-slack-integration` (or your choice)
4. Description: "Automated Exotel call transcription and Slack posting system"
5. Choose:
   - ✅ **Public** (if open source) OR **Private** (for internal use)
   - ❌ Don't initialize with README (you already have one)
   - ❌ Don't add .gitignore (you already have one)
6. Click "Create repository"

### Step 9: Add Remote

Copy the URL from GitHub, then:

```bash
git remote add origin https://github.com/YOUR_USERNAME/exotel-slack-integration.git
```

Or for SSH:
```bash
git remote add origin git@github.com:YOUR_USERNAME/exotel-slack-integration.git
```

### Step 10: Push to GitHub

```bash
git branch -M main
git push -u origin main
```

### Step 11: Verify on GitHub

Go to your repository URL:
```
https://github.com/YOUR_USERNAME/exotel-slack-integration
```

Should see all files listed ✅

---

## 🔐 Security Checklist

Before pushing to Git, verify:

- [ ] `.env` is NOT in the repository
- [ ] `.env` is listed in `.gitignore`
- [ ] No API keys in any committed files
- [ ] No passwords in any committed files
- [ ] No database files committed
- [ ] `env.example` has placeholder values (not real credentials)
- [ ] `agent_mapping.json` doesn't contain sensitive personal data (or use generic names)

### Check for Sensitive Data

```bash
# Search for potential API keys
grep -r "sk-" .
grep -r "api_key" .
grep -r "token" .
grep -r "secret" .
grep -r "password" .
```

If found in any file except `env.example` (with placeholders), **DO NOT COMMIT!**

---

## 📝 Complete File Checklist

Copy this checklist and verify before pushing:

### Core Files (Required)
- [ ] `app.py`
- [ ] `requirements.txt`
- [ ] `agent_mapping.json`
- [ ] `env.example`
- [ ] `.gitignore`

### Deployment Files
- [ ] `Dockerfile`
- [ ] `docker-compose.yml`
- [ ] `render.yaml`

### Documentation Files
- [ ] `README.md`
- [ ] `QUICKSTART.md`
- [ ] `ZAPIER_INTEGRATION_GUIDE.md`
- [ ] `DEPLOYMENT_GUIDE.md`
- [ ] `TESTING_GUIDE.md`
- [ ] `PROJECT_SUMMARY.md`
- [ ] `FILE_GUIDE.md`
- [ ] `AGENT_TRACKING_GUIDE.md`
- [ ] `GIT_UPLOAD_GUIDE.md`

### Utility Scripts
- [ ] `test_system.py`
- [ ] `start.sh`
- [ ] `start.bat`

### Files to Exclude
- [ ] `.env` is NOT committed ⚠️
- [ ] `*.db` files are NOT committed
- [ ] `downloads/` is NOT committed
- [ ] `__pycache__/` is NOT committed
- [ ] `venv/` is NOT committed

**Total files to upload**: 17 files

---

## 🔄 Updating Your Repository

### After Making Changes

```bash
# Check what changed
git status

# Add specific files
git add app.py
git add agent_mapping.json

# Or add all changed files
git add .

# Commit with descriptive message
git commit -m "Update agent mapping with new agents"

# Push to GitHub
git push
```

### If You Accidentally Committed Secrets

**If you committed `.env` or secrets, IMMEDIATELY**:

```bash
# Remove from Git history
git rm --cached .env
git commit -m "Remove .env from repository"
git push

# Then ROTATE ALL SECRETS immediately:
# - Generate new Slack webhook URL
# - Get new AssemblyAI API key
# - Update all credentials
```

**Note**: Even after removing, secrets may still be in Git history. Consider:
- Rotating all exposed credentials
- Using `git filter-branch` or BFG Repo-Cleaner to remove from history
- Making repository private if it was public

---

## 📊 Repository Size

Your repository will be approximately:

- **Code**: ~50 KB (`app.py`)
- **Documentation**: ~150 KB (all .md files)
- **Config files**: ~5 KB
- **Scripts**: ~10 KB
- **Total**: ~215 KB

Very lightweight! 🎉

---

## 🎯 Best Practices

### 1. Commit Messages

Use descriptive commit messages:

✅ **Good**:
```bash
git commit -m "Add phone-based agent tracking and mapping"
git commit -m "Fix duplicate detection for edge cases"
git commit -m "Update documentation with deployment steps"
```

❌ **Bad**:
```bash
git commit -m "update"
git commit -m "fix"
git commit -m "changes"
```

### 2. Commit Frequently

- Commit after each feature is complete
- Commit before making major changes (easy to revert)
- Don't commit broken code (use branches for WIP)

### 3. Use Branches (Optional)

For experimentation:
```bash
git checkout -b feature/new-feature
# Make changes
git commit -am "Add new feature"
git checkout main
git merge feature/new-feature
```

### 4. Keep Documentation Updated

When you change code, update relevant documentation:
- Update `README.md` if features change
- Update `AGENT_TRACKING_GUIDE.md` if agent logic changes
- Update `env.example` if new env vars are added

---

## 🚀 Deploy After Push

After pushing to GitHub:

1. **Render** will auto-deploy (if connected)
2. **Railway** will auto-deploy (if configured)
3. **Manual deployments**: Pull latest code

### Render Auto-Deploy

If you connected GitHub to Render:
- Every `git push` triggers automatic deployment
- Check Render dashboard for deployment status
- Monitor logs for any errors

### Manual Pull on Server

If self-hosting:
```bash
ssh user@your-server
cd /path/to/app
git pull
docker-compose up -d --build  # or restart however you're running
```

---

## ✅ Quick Verification

After pushing, verify your repository has:

1. ✅ All 17+ files visible on GitHub
2. ✅ README.md displays correctly
3. ✅ No `.env` file visible
4. ✅ No database files visible
5. ✅ No `downloads/` folder visible
6. ✅ `.gitignore` is present
7. ✅ All documentation readable

---

## 🆘 Troubleshooting

### "Permission denied (publickey)"

**Solution**: Set up SSH key or use HTTPS instead

```bash
# Use HTTPS instead of SSH
git remote set-url origin https://github.com/YOUR_USERNAME/REPO.git
```

### "Repository not found"

**Solution**: Check repository URL and access permissions

```bash
# Verify remote
git remote -v

# Update if needed
git remote set-url origin https://github.com/YOUR_USERNAME/CORRECT-REPO.git
```

### "Failed to push some refs"

**Solution**: Pull latest changes first

```bash
git pull origin main
# Resolve any conflicts
git push origin main
```

### ".env file is showing in my commits"

**Solution**: Remove from Git tracking

```bash
git rm --cached .env
git commit -m "Remove .env from tracking"
git push
# Then ROTATE all secrets!
```

---

## 📚 Additional Resources

- [GitHub Documentation](https://docs.github.com/)
- [Git Basics](https://git-scm.com/book/en/v2/Getting-Started-Git-Basics)
- [.gitignore Guide](https://git-scm.com/docs/gitignore)

---

## ✨ Summary

**Upload these 17 files**:
1. app.py
2. requirements.txt
3. agent_mapping.json
4. env.example
5. .gitignore
6. Dockerfile
7. docker-compose.yml
8. render.yaml
9. README.md
10. QUICKSTART.md
11. ZAPIER_INTEGRATION_GUIDE.md
12. DEPLOYMENT_GUIDE.md
13. TESTING_GUIDE.md
14. PROJECT_SUMMARY.md
15. FILE_GUIDE.md
16. AGENT_TRACKING_GUIDE.md
17. GIT_UPLOAD_GUIDE.md
18. test_system.py
19. start.sh
20. start.bat

**NEVER upload**:
- ❌ .env
- ❌ *.db files
- ❌ downloads/
- ❌ __pycache__/
- ❌ venv/

**Quick command**:
```bash
cd exotel-slack-complete-system
git init
git add .
git commit -m "Initial commit"
git remote add origin YOUR_GITHUB_URL
git push -u origin main
```

🎉 **Done! Your code is now on GitHub and ready to deploy!**

