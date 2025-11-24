# Exotel → Slack MOM (Automated Call Transcription & MOM Posting)

Automated system to download Exotel call recordings, transcribe them (OpenAI Whisper), generate concise Meeting Minutes (MOM) using OpenAI, upload transcripts to Google Drive (for NotebookLM sync), and post structured MOM messages into Slack with smart agent detection and robust duplicate-prevention.

This repository contains a FastAPI service (app.py) with:
- Smart agent detection (phone → agent mapping + optional Slack user lookup)
- Transcription (OpenAI Whisper)
- MOM generation (OpenAI chat completion)
- Google Drive upload for transcripts (optional)
- Slack posting via incoming webhook
- SQLite database to prevent duplicate Slack posts
- Google Sheets customer lookup for customer names

Files of interest
- app.py — main FastAPI application and processing pipeline
- customer_lookup.py — Google Sheets integration and caching for customer names
- agent_mapping.json — agent phone → name/email/department mappings (used for smart detection)
- requirements.txt — Python dependencies
- Dockerfile, docker-compose.yml, render.yaml — containerization / deployment helpers

Features
- Automatic download of Exotel recordings (via URL received from Zapier webhook)
- OpenAI Whisper transcription (audio → text)
- AI-generated professionally formatted MOM (with tone, mood analysis, action items)
- Upload transcript for NotebookLM via Google Drive
- Slack posting with agent email or Slack mention
- Triple-layer duplicate prevention:
  1. Quick check if call already posted
  2. DB-level processing lock (prevents race conditions)
  3. Final safety check before posting
- Department filtering and rate limiting
- Health and stats endpoints

Quick start — local (dev)
1. Clone repo:
   git clone https://github.com/prateekraj3711-alt/EXOTEL-SLACKMOM.git
   cd EXOTEL-SLACKMOM

2. (Optional) Create a virtualenv:
   python -m venv venv
   source venv/bin/activate

3. Install dependencies:
   pip install -r requirements.txt

4. Set environment variables (examples below) then run:
   export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
   export OPENAI_API_KEY="sk-..."
   export EXOTEL_API_KEY="exotel_api_key"
   export EXOTEL_API_TOKEN="exotel_api_token"
   # (optional)
   export SLACK_BOT_TOKEN="xoxb-..."
   export GOOGLE_CLIENT_ID="..."
   export GOOGLE_CLIENT_SECRET="..."
   # Google Sheets service-account JSON (stringified) if you use customer lookup:
   export GOOGLE_SHEETS_CREDENTIALS='{"type":"service_account", ... }'

   Start server:
   uvicorn app:app --host 0.0.0.0 --port 8000

5. Health:
   GET http://localhost:8000/health

Quick start — Docker
- Build:
  docker build -t exotel-slackmom .
- Run (example):
  docker run -e SLACK_WEBHOOK_URL=... -e OPENAI_API_KEY=... -p 8000:8000 exotel-slackmom

- Docker Compose:
  Edit docker-compose.yml to add environment variables, then:
  docker-compose up --build -d

Important environment variables
(These are read in app.py — supply via your environment, container secrets manager, or deployment platform.)

Required for basic operation:
- SLACK_WEBHOOK_URL — Slack Incoming Webhook URL used to post messages
- OPENAI_API_KEY — OpenAI API key (Whisper transcription + MOM generation)

Optional / recommended:
- SLACK_BOT_TOKEN — If set, the app will query Slack users for phone → Slack user lookup (for tagging)
- EXOTEL_API_KEY, EXOTEL_API_TOKEN — For authenticated downloads of Exotel recordings (if required)
- EXOTEL_SID — (if used in your Exotel setup)
- DATABASE_PATH — SQLite path (default: processed_calls.db)
- GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET — For Google Drive integration (server-side OAuth requires setup)
- GOOGLE_SHEETS_CREDENTIALS — JSON credentials (string) for a Google service account used by customer_lookup.py
- ALLOWED_DEPARTMENTS — Comma-separated list to filter calls by agent department (default: "CUSTOMER SUPPORT")
- PROCESSING_DELAY — Delay in seconds between processing calls (default: 5)
- MAX_CONCURRENT_CALLS — Maximum concurrent call processing (default: 3)
- SUPPORT_NUMBER — Organization support phone number (used for direction detection)

Webhook endpoint (Zapier)
- POST /webhook/zapier
- Expected JSON payload (see Pydantic model in app.py ZapierWebhookPayload). Minimal example:
  {
    "call_id": "EXOTEL_SID_123",
    "from_number": "919876543210",
    "to_number": "919631084471",
    "duration": 120,
    "recording_url": "https://exotel-recording-url.mp3",
    "timestamp": "2025-11-24T04:00:00Z",
    "status": "completed"
  }

How agent detection works
- First attempts Slack workspace lookup (if SLACK_BOT_TOKEN provided) to identify agent by phone and tag their Slack user.
- If not found in Slack, looks up agent_mapping.json (phone → metadata). Add any additional agent phone numbers to agent_mapping.json to improve matching.
- If an agent is identified, system determines call direction (incoming/outgoing) and constructs message fields accordingly.

Customer lookup (Google Sheets)
- customer_lookup.py reads a specific Google Spreadsheet (sheet and ID are set inside the module).
- Set GOOGLE_SHEETS_CREDENTIALS to the service-account JSON to enable this feature.
- The service caches sheet data and refreshes every 30 minutes.

Transcription & MOM
- Transcription performed using OpenAI Whisper endpoint.
- MOM generation uses OpenAI chat completion (gpt-3.5-turbo in the current code).
- If OpenAI calls fail (rate-limited/unavailable), a structured fallback MOM is used.

Storage and duplicate prevention
- SQLite DB (processed_calls table) stores calls and status to avoid duplicate Slack posts.
- Emergency cleanup on startup deletes stale non-posted records older than 2 hours.

Logging & monitoring
- Logs are printed to stdout (configured via Python logging). Check container logs or systemd logs depending on deployment.
- /health and /stats endpoints provide quick operational info.

Example cURL (test)
curl -X POST http://localhost:8000/webhook/zapier \
 -H "Content-Type: application/json" \
 -d '{
   "call_id":"test-123",
   "from_number":"919876543210",
   "to_number":"919631084471",
   "duration":30,
   "recording_url":"https://example.com/test.mp3",
   "timestamp":"2025-11-24T04:00:00Z",
   "status":"completed"
 }'

Troubleshooting tips
- "Slack webhook not configured": set SLACK_WEBHOOK_URL.
- OpenAI auth errors: ensure OPENAI_API_KEY is valid and has entitlement for audio/transcription and model usage.
- Exotel recording download issues: ensure EXOTEL_API_KEY / EXOTEL_API_TOKEN are set if recordings require auth.
- Google Sheets errors: ensure GOOGLE_SHEETS_CREDENTIALS is a valid service account JSON with access to the spreadsheet.
- If duplicates appear: check processed_calls.db entries and startup logs; the app runs 3-layer duplicate prevention but stale failures can be inspected/cleaned.
- Check downloads/ and transcripts/ directories created by the app (app creates downloads on startup).

Extending / Customization ideas
- Replace GPT model or tune temperature/prompt for different MOM style.
- Add re-try/backoff persistence for OpenAI failures.
- Integrate with ticketing systems (Zendesk/Jira) to auto-create or update tickets from MOM/action items.
- Add RBAC or verify incoming Zapier requests with a shared secret to ensure authenticity.

Security notes
- Do not commit secrets to the repo. Use environment variables or your deployment platform's secret store.
- Google Sheets service account JSON should be stored securely and not exposed.



Maintainer / Contact
- Repository: https://github.com/prateekraj3711-alt/EXOTEL-SLACKMOM
- For issues: open an issue in the GitHub repo

Acknowledgements
- Built with FastAPI, OpenAI Whisper, Slack, Google Drive & Google Sheets APIs.


- Or produce a short CONTRIBUTING.md or LICENSE file.
