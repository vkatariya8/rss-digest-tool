import os
import json
import logging
from dotenv import load_dotenv
from src.rss_fetcher import fetch_articles
from src.ai_evaluator import evaluate_articles
from src.email_sender import send_digest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_config():
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config.json"
    )
    with open(config_path, "r") as f:
        return json.load(f)


def load_feeds():
    feeds_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "feeds.txt")
    with open(feeds_path, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def load_watchlist():
    watchlist_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "watchlist.txt"
    )
    if not os.path.exists(watchlist_path):
        logger.info("No watchlist.txt found. Running without watchlist.")
        return []
    with open(watchlist_path, "r") as f:
        items = [
            line.strip() for line in f if line.strip() and not line.startswith("#")
        ]
    if not items:
        logger.info("Watchlist is empty. Running without watchlist.")
    else:
        logger.info(f"Watchlist: {len(items)} keywords loaded")
    return items


def main():
    load_dotenv()

    groq_api_key = os.getenv("GROQ_API_KEY")
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    recipient_email = os.getenv("RECIPIENT_EMAIL")

    if not all([groq_api_key, smtp_email, smtp_password, recipient_email]):
        raise ValueError("Missing required environment variables")

    config = load_config()
    feed_urls = load_feeds()
    watchlist = load_watchlist()

    logger.info(f"Fetching articles from {len(feed_urls)} feed(s)...")
    articles = fetch_articles(feed_urls)
    logger.info(f"Total articles fetched: {len(articles)}")

    if not articles:
        logger.info("No articles found. Exiting.")
        return

    logger.info("Evaluating articles with Groq (batched)...")
    relevant = evaluate_articles(articles, groq_api_key, config, watchlist)
    logger.info(f"Relevant articles: {len(relevant)}")

    if relevant:
        logger.info("Sending digest email...")
        send_digest(relevant, smtp_email, smtp_password, recipient_email)
        logger.info("Digest sent successfully!")
    else:
        logger.info("No relevant articles found. No email sent.")


if __name__ == "__main__":
    main()
