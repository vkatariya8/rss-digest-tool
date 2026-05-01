import json
import time
import logging
from groq import Groq
from typing import List
from src.rss_fetcher import Article

logger = logging.getLogger(__name__)


BATCH_SYSTEM_PROMPT = """You are a ruthless filter for a VC analyst focused EXCLUSIVELY on early-stage tech startups in India. Your job is to REJECT most articles — only pass through content with genuine investment signal.

DEFAULT: Reject. Only mark relevant if the article clearly passes ALL these tests:
1. INDIA-PRIMARY: The article is primarily about India — not a global piece that mentions India in one paragraph
2. TECH STARTUP: Involves an actual tech startup (not enterprise, not traditional business, not government)
3. ACTIONABLE SIGNAL: Contains concrete information (funding amount, product launch, metrics, names) — not opinion or trends

REJECT immediately if:
- Global news that mentions India only tangentially ("...including India" or "expanding to India")
- PR-speak with no substance ("excited to announce", "thrilled to partner", "industry leader")
- Thought leadership / opinion pieces / trend predictions without concrete startup news
- Established companies (10+ years old, publicly traded, household names)
- Non-tech sectors: pure manufacturing, real estate, traditional retail, agriculture (unless AgriTech startup)
- General industry reports or market analysis without specific startup news
- Job postings, executive appointments at large companies, corporate restructuring

RELEVANT only if:
- Indian tech startup (seed to Series B) raising capital with amount disclosed
- Indian tech founder launching a product with concrete traction signals
- Acquisition/exit of an Indian tech startup
- Indian tech policy change directly affecting startups (not general business regulation)

Be skeptical. When in doubt, reject.

Respond with ONLY a JSON array where each element corresponds to the article at that index:
[
    {
        "index": 0,
        "relevant": true/false,
        "relevance_score": "high|medium|low",
        "reason": "1-sentence why this matters for VC"
    },
    ...
]"""


def evaluate_batch_with_retry(
    batch: List[Article],
    api_key: str,
    config: dict,
    max_retries: int = 3,
    base_backoff: int = 60,
) -> List[dict]:
    client = Groq(api_key=api_key)

    articles_json = json.dumps(
        [
            {
                "index": i,
                "title": a.title,
                "source": a.source,
                "published": a.published,
                "url": a.link,
                "summary": a.summary,
            }
            for i, a in enumerate(batch)
        ],
        indent=2,
    )

    prompt = f"Articles to evaluate:\n{articles_json}"

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=config["model"],
                messages=[
                    {
                        "role": "system",
                        "content": BATCH_SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=config.get("temperature", 0.1),
                response_format={"type": "json_object"},
            )

            results = json.loads(response.choices[0].message.content)

            if isinstance(results, dict) and "results" in results:
                results = results["results"]

            relevant = []
            for result in results:
                idx = result.get("index", 0)
                if idx >= len(batch):
                    continue

                article = batch[idx]
                score = result.get("relevance_score", "unknown").lower()
                if result.get("relevant") and score != "low":
                    logger.info(
                        f"RELEVANT [{result.get('relevance_score', 'unknown').upper()}]: {article.title} - {result.get('reason')}"
                    )
                    relevant.append(
                        {
                            "article": article,
                            "reason": result.get("reason", ""),
                            "relevance_score": result.get("relevance_score", "unknown"),
                        }
                    )
                else:
                    logger.info(f"NOT RELEVANT: {article.title}")
                if result.get("relevant") and score == "low":
                    logger.info(f"LOW SCORE (excluded): {article.title}")

            return relevant

        except Exception as e:
            if attempt < max_retries - 1:
                backoff = base_backoff * (2**attempt)
                logger.warning(
                    f"Batch evaluation failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {backoff}s..."
                )
                time.sleep(backoff)
            else:
                logger.error(
                    f"Batch evaluation failed after {max_retries} attempts: {e}"
                )
                return []

    return []


def evaluate_articles(
    articles: List[Article], api_key: str, config: dict
) -> List[dict]:
    relevant_articles = []
    rate_limit = config.get("rate_limit", {"delay_seconds": 45, "batch_size": 5})
    retry_config = config.get("retry", {"max_retries": 3, "base_backoff": 60})
    delay = rate_limit.get("delay_seconds", 45)
    batch_size = rate_limit.get("batch_size", 5)
    max_retries = retry_config.get("max_retries", 3)
    base_backoff = retry_config.get("base_backoff", 60)

    for i in range(0, len(articles), batch_size):
        batch = articles[i : i + batch_size]
        logger.info(
            f"Evaluating batch {i // batch_size + 1} ({len(batch)} articles)..."
        )

        batch_results = evaluate_batch_with_retry(
            batch, api_key, config, max_retries, base_backoff
        )
        relevant_articles.extend(batch_results)

        if i + batch_size < len(articles):
            logger.info(f"Rate limit: pausing {delay}s...")
            time.sleep(delay)

    return relevant_articles
