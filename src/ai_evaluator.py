import json
import logging
from groq import Groq
from typing import List, Optional
from src.rss_fetcher import Article

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an investment analyst at an early-stage venture capital fund.
Your job is to evaluate whether a news article is relevant for investment opportunities.

An article is RELEVANT if it relates to:
- Early-stage startups raising funding (seed, Series A, etc.)
- New startup launches or product announcements
- Emerging tech trends (AI, biotech, fintech, climate tech, etc.)
- Notable founder exits or acquisitions
- Market shifts that create investment opportunities
- Innovative business models or disruptive technologies
- Government policies affecting startups/VC

An article is NOT RELEVANT if it is:
- General news unrelated to startups/tech/venture
- Opinion pieces without substantive information
- Routine corporate earnings reports of large public companies
- Political news unrelated to business/startups
- Local crime, sports, entertainment

Respond with ONLY a JSON object in this exact format:
{
    "relevant": true/false,
    "reason": "Brief 1-sentence explanation of why this is relevant or not",
    "category": "fundraising|product_launch|tech_trend|exit|market_shift|policy|other"
}"""

MODEL = "llama-3.1-8b-instant"


def evaluate_article(article: Article, api_key: str) -> Optional[dict]:
    client = Groq(api_key=api_key)

    prompt = f"""
Title: {article.title}
Source: {article.source}
Published: {article.published}
URL: {article.link}
Summary: {article.summary}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Evaluate this article:\n{prompt}"},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        if result.get("relevant"):
            logger.info(f"RELEVANT: {article.title} - {result.get('reason')}")
            return {
                "article": article,
                "reason": result.get("reason", ""),
                "category": result.get("category", "other"),
            }
        else:
            logger.info(f"NOT RELEVANT: {article.title}")
            return None

    except Exception as e:
        logger.error(f"Error evaluating article: {e}")
        return None


def evaluate_articles(articles: List[Article], api_key: str) -> List[dict]:
    relevant_articles = []

    for article in articles:
        result = evaluate_article(article, api_key)
        if result:
            relevant_articles.append(result)

    return relevant_articles
