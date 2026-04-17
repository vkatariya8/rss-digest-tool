import os
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


def main():
    load_dotenv()

    groq_api_key = os.getenv("GROQ_API_KEY")
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    recipient_email = os.getenv("RECIPIENT_EMAIL")

    feed_urls = os.getenv("RSS_FEED_URLS", "").split(",")
    feed_urls = [url.strip() for url in feed_urls if url.strip()]

    if not all([groq_api_key, smtp_email, smtp_password, recipient_email, feed_urls]):
        raise ValueError("Missing required environment variables")

    logger.info(f"Fetching articles from {len(feed_urls)} feed(s)...")
    articles = fetch_articles(feed_urls)
    logger.info(f"Total articles fetched: {len(articles)}")

    if not articles:
        logger.info("No articles found. Exiting.")
        return

    logger.info("Evaluating articles with Groq...")
    relevant = evaluate_articles(articles, groq_api_key)
    logger.info(f"Relevant articles: {len(relevant)}")

    if relevant:
        logger.info("Sending digest email...")
        send_digest(relevant, smtp_email, smtp_password, recipient_email)
        logger.info("Digest sent successfully!")
    else:
        logger.info("No relevant articles found. No email sent.")


if __name__ == "__main__":
    main()
