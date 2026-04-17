import os
import sys
import json
import logging
import smtplib
from groq import Groq
import feedparser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        logger.info(f"  PASS: {name}")
        passed += 1
    else:
        logger.error(f"  FAIL: {name} {detail}")
        failed += 1


def validate_env():
    logger.info("Checking environment variables...")
    from dotenv import load_dotenv

    load_dotenv()
    check("GROQ_API_KEY set", bool(os.getenv("GROQ_API_KEY")))
    check("SMTP_EMAIL set", bool(os.getenv("SMTP_EMAIL")))
    check("SMTP_PASSWORD set", bool(os.getenv("SMTP_PASSWORD")))
    check("RECIPIENT_EMAIL set", bool(os.getenv("RECIPIENT_EMAIL")))


def validate_config():
    logger.info("Checking config.json...")
    config_path = os.path.join(BASE_DIR, "config.json")
    check("config.json exists", os.path.exists(config_path))
    if not os.path.exists(config_path):
        return None
    try:
        with open(config_path) as f:
            config = json.load(f)
        check("Valid JSON", True)
        check("Has 'model' key", "model" in config)
        check("Has 'temperature' key", "temperature" in config)
        check("Has 'rate_limit' key", "rate_limit" in config)
        return config
    except json.JSONDecodeError as e:
        check("Valid JSON", False, str(e))
        return None


def validate_feeds():
    logger.info("Checking feeds.txt...")
    feeds_path = os.path.join(BASE_DIR, "feeds.txt")
    check("feeds.txt exists", os.path.exists(feeds_path))
    if not os.path.exists(feeds_path):
        return
    with open(feeds_path) as f:
        feeds = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    check(f"{len(feeds)} feed URLs found", len(feeds) > 0)
    for feed in feeds:
        check(
            f"Feed reachable: {feed[:50]}...",
            feedparser.parse(feed).bozo == False
            or len(feedparser.parse(feed).entries) > 0,
        )


def validate_watchlist():
    logger.info("Checking watchlist.txt...")
    watchlist_path = os.path.join(BASE_DIR, "watchlist.txt")
    if not os.path.exists(watchlist_path):
        logger.info("  watchlist.txt not found (optional, skipping)")
        return
    with open(watchlist_path) as f:
        items = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    check(f"{len(items)} watchlist items found", True)


def validate_groq():
    logger.info("Checking Groq API...")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        check("Groq API key available", False)
        return
    try:
        client = Groq(api_key=api_key)
        config = validate_config()
        model = (
            config.get("model", "llama-3.3-70b-versatile")
            if config
            else "llama-3.3-70b-versatile"
        )
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=10,
        )
        check(
            f"Groq API works (model: {model})",
            bool(response.choices[0].message.content),
        )
    except Exception as e:
        check("Groq API works", False, str(e))


def validate_smtp():
    logger.info("Checking SMTP connection...")
    email = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_PASSWORD")
    if not email or not password:
        check("SMTP credentials available", False)
        return
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(email, password)
        check("SMTP login successful", True)
    except Exception as e:
        check("SMTP login successful", False, str(e))


def main():
    logger.info("=" * 50)
    logger.info("RSS Digest Tool - Pre-flight Validation")
    logger.info("=" * 50)

    validate_env()
    validate_config()
    validate_feeds()
    validate_watchlist()
    validate_groq()
    validate_smtp()

    logger.info("=" * 50)
    logger.info(f"Results: {passed} passed, {failed} failed")
    logger.info("=" * 50)

    if failed > 0:
        logger.error("Validation failed. Fix issues before running.")
        sys.exit(1)
    else:
        logger.info("All checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
