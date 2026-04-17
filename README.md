# RSS Digest Tool for VC

Daily AI-powered RSS feed digest that filters startup news for early-stage VC investment relevance.

## Setup

### 1. Get API Keys

**Google Gemini API Key:**
- Go to https://aistudio.google.com/app/apikey
- Create a free API key

**Gmail App Password:**
- Go to your Google Account → Security
- Enable 2-Step Verification if not already enabled
- Go to App Passwords → Generate a new password for "Mail"
- Save the 16-character password

### 2. Configure Secrets (for GitHub Actions)

In your GitHub repo, go to Settings → Secrets and variables → Actions → New repository secret:

| Secret Name | Value |
|---|---|
| `GEMINI_API_KEY` | Your Gemini API key |
| `SMTP_EMAIL` | Your Gmail address |
| `SMTP_PASSWORD` | Your Gmail App Password |
| `RECIPIENT_EMAIL` | Email to receive digest |
| `RSS_FEED_URLS` | Comma-separated feed URLs |

### 3. Test Locally

```bash
cp .env.example .env
# Edit .env with your credentials
pip install -r requirements.txt
python -m src.main
```

### 4. Schedule

Runs automatically at 8:00 AM IST daily via GitHub Actions cron.
To trigger manually: GitHub Actions → Daily RSS Digest → Run workflow.

## Adding More Feeds

Update the `RSS_FEED_URLS` secret with comma-separated URLs:
```
RSS_FEED_URLS=https://feed1.com/rss,https://feed2.com/rss,https://feed3.com/rss
```
