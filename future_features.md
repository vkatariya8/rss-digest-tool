# Future Features

## Full Article Content Fetching

**Problem:** RSS summaries are often 1-2 sentences, not enough context for accurate LLM evaluation.

**Solution:** Use `trafilatura` to fetch and extract full article text before evaluation.

**Implementation plan:**
1. Add `trafilatura` to `requirements.txt`
2. In `rss_fetcher.py` or a new `content_fetcher.py`, fetch full article text from the URL
3. Pass full text to the LLM instead of just the summary
4. Add a `fetch_full_content` toggle in `config.json` (default: false, since it slows things down)

**Trade-offs:**
- Better accuracy (LLM has full context)
- Slower execution (HTTP request per article)
- Higher token usage per LLM call
- Still well within Groq free tier limits

**Dependencies:** `trafilatura` or `readability-lxml`

---

## Other Ideas
- Historical memory (seen_articles.json to avoid re-evaluating)
- Digest summary stats (top sectors, trends over time)
- Slack/Google Chat webhook as alternative to email
- Web dashboard to browse past digests
