import json
import time
import logging
from groq import Groq
from typing import List
from src.rss_fetcher import Article

logger = logging.getLogger(__name__)


BATCH_SYSTEM_PROMPT = """You are a senior investment analyst at an early-stage VC fund focused EXCLUSIVELY on technology startups in India. Your job is to evaluate articles and decide whether they warrant further investigation for potential investment in the Indian tech startup ecosystem.

STRICT RULE — Relevance gate:
An article is ONLY relevant if it explicitly involves India AND technology startups. This includes Indian tech startups raising capital, Indian founders building tech ventures, Indian tech policy/regulation, or Indian tech market dynamics. Articles about non-tech sectors (e.g. traditional manufacturing, real estate, pure retail) or startups outside India are NOT relevant unless they have a clear, direct implication for Indian tech startups.

RELEVANT if:
- Early-stage Indian technology startups (pre-seed to Series B) raising capital
- Indian tech founders or India-focused tech teams building new ventures
- New tech product launches by Indian startups with clear traction signals
- Emerging technology trends with direct commercial potential for Indian startups
- Founder/team changes at promising Indian tech startups
- Indian regulatory or policy shifts affecting the tech startup ecosystem
- Competitive landscape changes specifically in the Indian tech market

NOT RELEVANT if:
- Non-Indian startups or markets with no India angle
- Non-technology sectors (manufacturing, real estate, traditional retail, agriculture without a tech angle, etc.)
- Press releases without substance
- Sponsored/promotional content
- Job postings or hiring announcements
- Routine corporate updates of established companies
- General news, politics, sports, entertainment

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
