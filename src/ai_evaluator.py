import json
import logging
from groq import Groq
from typing import List, Optional
from src.rss_fetcher import Article

logger = logging.getLogger(__name__)


def evaluate_article(article: Article, api_key: str, config: dict) -> Optional[dict]:
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
            model=config["model"],
            messages=[
                {"role": "system", "content": config["prompt"]},
                {"role": "user", "content": f"Evaluate this article:\n{prompt}"},
            ],
            temperature=config.get("temperature", 0.1),
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


def evaluate_articles(
    articles: List[Article], api_key: str, config: dict
) -> List[dict]:
    relevant_articles = []

    for article in articles:
        result = evaluate_article(article, api_key, config)
        if result:
            relevant_articles.append(result)

    return relevant_articles
