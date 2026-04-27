# AGENTS.md

## What This Is
A daily cron job that fetches RSS feeds, evaluates articles with Groq AI for VC investment relevance, and emails a curated HTML digest. No web server, no framework — just a Python script run by GitHub Actions.

## Commands

```bash
# Local test (requires .env with credentials)
python -m src.main

# Pre-flight validation (env, config, feeds, Groq API, SMTP)
python -m src.validate
```

## Architecture

```
src/main.py          → Entry point. Loads config/feeds/watchlist, orchestrates pipeline
src/rss_fetcher.py   → Parses RSS feeds via feedparser, filters by time_window_hours
src/ai_evaluator.py  → Batches articles, calls Groq, retries on failure
src/email_sender.py  → Builds HTML email, sends via Gmail SMTP
src/validate.py      → Pre-flight checks for all dependencies
```

Pipeline: fetch → evaluate (batched) → email (only if relevant articles found)

## Configuration (NOT in secrets)

- **`config.json`**: Model, prompt, sectors, rate limits, retry settings. Edit directly.
- **`feeds.txt`**: One URL per line. `#` for comments.
- **`watchlist.txt`**: Keywords/phrases for priority flagging. `#` for comments.

GitHub Actions secrets only hold credentials: `GROQ_API_KEY`, `SMTP_EMAIL`, `SMTP_PASSWORD`, `RECIPIENT_EMAIL`.

## Local Setup

No `.env.example` exists. Create `.env` with:
```
GROQ_API_KEY=...
SMTP_EMAIL=your@gmail.com
SMTP_PASSWORD=your-app-password
RECIPIENT_EMAIL=target@email.com
```

Run `python -m src.validate` before `python -m src.main` to catch missing creds or broken feeds.

## Important Quirks

- **Dual prompts**: `config.json` has a prompt focused on India, but `ai_evaluator.py:BATCH_SYSTEM_PROMPT` has a hardcoded "emerging markets" prompt. The hardcoded one is what actually gets sent to the API.
- **Batching**: 5 articles per Groq call, 45s delay between batches (configurable in `config.json`).
- **Retry**: 3 retries with exponential backoff (60s, 120s, 240s).
- **No email on empty**: If zero relevant articles, the job exits silently — no "no articles" email.
- **Python 3.11** in CI. No tests exist.
- **`.env` is gitignored** but there's no `.env.example` template.

## CI

GitHub Actions cron: `30 2 * * *` (8:00 AM IST). Manual trigger available via `workflow_dispatch`.
