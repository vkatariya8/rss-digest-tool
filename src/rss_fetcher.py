import feedparser
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Article:
    title: str
    link: str
    summary: str
    published: str
    source: str


def parse_date(date_str: str) -> Optional[datetime]:
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


DEVANAGARI_RANGE = range(0x0900, 0x0980)

def contains_hindi(text: str, threshold: float = 0.05) -> bool:
    if not text:
        return False
    devanagari = sum(1 for c in text if ord(c) in DEVANAGARI_RANGE)
    return (devanagari / len(text)) > threshold


def fetch_articles(feed_urls: List[str], hours: int = 24) -> List[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    articles = []
    skipped = 0
    skipped_hindi = 0

    for url in feed_urls:
        try:
            logger.info(f"Fetching feed: {url}")
            feed = feedparser.parse(url)

            if feed.bozo and not feed.entries:
                logger.error(f"Failed to parse feed: {url}")
                continue

            source = feed.feed.get("title", url)
            feed_articles = 0

            for entry in feed.entries:
                pub_date = parse_date(entry.get("published", ""))
                if pub_date and pub_date < cutoff:
                    skipped += 1
                    continue

                title = entry.get("title", "Untitled")
                summary = entry.get("summary", "")

                if contains_hindi(title) or contains_hindi(summary):
                    skipped_hindi += 1
                    continue

                article = Article(
                    title=title,
                    link=entry.get("link", ""),
                    summary=summary,
                    published=entry.get("published", ""),
                    source=source,
                )
                articles.append(article)
                feed_articles += 1

            logger.info(
                f"Found {feed_articles} recent articles from {source} ({len(feed.entries)} total, {len(feed.entries) - feed_articles} older than {hours}h)"
            )

        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            continue

    if skipped:
        logger.info(f"Skipped {skipped} articles older than {hours} hours")
    if skipped_hindi:
        logger.info(f"Skipped {skipped_hindi} Hindi articles")

    return articles
