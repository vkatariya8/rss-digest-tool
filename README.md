# RSS Digest Tool for VC

Daily AI-powered RSS feed digest that filters startup news for early-stage VC investment relevance.

## Setup

### 1. Get API Keys

**Groq API Key (free):**
- Go to https://console.groq.com
- Sign up and create an API key

**Gmail App Password:**
- Go to your Google Account → Security
- Enable 2-Step Verification if not already enabled
- Go to App Passwords → Generate a new password for "Mail"
- Save the 16-character password

### 2. Configure Secrets (for GitHub Actions)

In your GitHub repo, go to Settings → Secrets and variables → Actions → New repository secret:

| Secret Name | Value |
|---|---|
| `GROQ_API_KEY` | Your Groq API key |
| `SMTP_EMAIL` | Your Gmail address |
| `SMTP_PASSWORD` | Your Gmail App Password |
| `RECIPIENT_EMAIL` | Email to receive digest |

### 3. Manage Feeds & AI Config

**Add/remove RSS feeds** — Edit `feeds.txt` (one URL per line, `#` for comments).

**Change AI model or prompt** — Edit `config.json`:
- `model`: Groq model name (e.g. `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `mixtral-8x7b-32768`)
- `temperature`: 0.0 to 1.0 (lower = more deterministic)
- `prompt`: The system prompt sent to the model

### 4. Test Locally

```bash
cp .env.example .env
# Edit .env with your credentials
pip install -r requirements.txt
python -m src.main
```

### 5. Schedule

Runs automatically at 8:00 AM IST daily via GitHub Actions cron.
To trigger manually: GitHub Actions → Daily RSS Digest → Run workflow.
