import feedparser
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class Article:
    title: str
    link: str
    summary: str
    published: str
    source: str


def fetch_articles(feed_urls: List[str]) -> List[Article]:
    articles = []

    for url in feed_urls:
        try:
            logger.info(f"Fetching feed: {url}")
            feed = feedparser.parse(url)

            if feed.bozo and not feed.entries:
                logger.error(f"Failed to parse feed: {url}")
                continue

            source = feed.feed.get("title", url)

            for entry in feed.entries:
                article = Article(
                    title=entry.get("title", "Untitled"),
                    link=entry.get("link", ""),
                    summary=entry.get("summary", ""),
                    published=entry.get("published", ""),
                    source=source,
                )
                articles.append(article)

            logger.info(f"Found {len(feed.entries)} articles from {source}")

        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            continue

    return articles
