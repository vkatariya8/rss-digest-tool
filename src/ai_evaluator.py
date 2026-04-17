import json
import time
import logging
from groq import Groq
from typing import List, Optional
from src.rss_fetcher import Article

logger = logging.getLogger(__name__)


BATCH_SYSTEM_PROMPT = """You are a senior investment analyst at an early-stage VC fund focused on emerging markets. Evaluate whether each article warrants further investigation for potential investment.

RELEVANT if:
- Early-stage startups (pre-seed to Series B) raising capital
- New product launches with clear market traction signals
- Emerging tech trends with commercial potential
- Founder/team changes at promising startups
- Regulatory shifts creating new market opportunities
- Competitive landscape changes in interesting sectors

NOT RELEVANT if:
- Press releases without substance
- Sponsored/promotional content
- Job postings or hiring announcements
- Routine corporate updates of established companies
- General news, politics, sports, entertainment

Available sectors: {sectors}

Respond with ONLY a JSON array where each element corresponds to the article at that index:
[
    {{
        "index": 0,
        "relevant": true/false,
        "relevance_score": "high|medium|low",
        "reason": "1-sentence why this matters for VC",
        "category": "fundraising|product_launch|tech_trend|exit|market_shift|policy|team|other",
        "stage_mentioned": "pre-seed|seed|series-a|series-b|unknown",
        "sectors": ["sector1", "sector2"]
    }},
    ...
]"""


def check_watchlist(article: Article, watchlist: List[str]) -> List[str]:
    text = f"{article.title} {article.summary}".lower()
    return [kw for kw in watchlist if kw.lower() in text]


def evaluate_batch_with_retry(
    batch: List[Article],
    api_key: str,
    config: dict,
    watchlist: List[str],
    max_retries: int = 3,
    base_backoff: int = 60,
) -> List[dict]:
    client = Groq(api_key=api_key)
    sectors = config.get("sectors", [])
    sectors_str = (
        ", ".join(sectors)
        if sectors
        else "ai, fintech, healthtech, edtech, climate, saas, ecommerce, mobility, agritech, web3, cybersecurity, devtools, other"
    )

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
                        "content": BATCH_SYSTEM_PROMPT.format(sectors=sectors_str),
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
                if result.get("relevant"):
                    watchlist_hits = check_watchlist(article, watchlist)
                    logger.info(
                        f"RELEVANT [{result.get('relevance_score', 'unknown').upper()}]: {article.title} - {result.get('reason')}"
                    )
                    if watchlist_hits:
                        logger.info(f"  Watchlist hits: {', '.join(watchlist_hits)}")
                    relevant.append(
                        {
                            "article": article,
                            "reason": result.get("reason", ""),
                            "relevance_score": result.get("relevance_score", "unknown"),
                            "category": result.get("category", "other"),
                            "stage_mentioned": result.get("stage_mentioned", "unknown"),
                            "sectors": result.get("sectors", []),
                            "watchlist_hits": watchlist_hits,
                        }
                    )
                else:
                    logger.info(f"NOT RELEVANT: {article.title}")

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
    articles: List[Article], api_key: str, config: dict, watchlist: List[str]
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
            batch, api_key, config, watchlist, max_retries, base_backoff
        )
        relevant_articles.extend(batch_results)

        if i + batch_size < len(articles):
            logger.info(f"Rate limit: pausing {delay}s...")
            time.sleep(delay)

    return relevant_articles
