"""Entry point: python -m src.main [--run-now | --schedule]"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _load_config() -> dict:
    cfg_path = Path(__file__).parent.parent / "config" / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


def _build_orchestrator(cfg: dict):
    from src.filters.city_filter import CityFilter
    from src.notifiers.callmebot_notifier import CallmebotNotifier
    from src.scrapers.allaccess_scraper import AllAccessScraper
    from src.scrapers.bresh_scraper import BreshScraper
    from src.scrapers.polenta_scraper import PolentaScraper
    from src.scrapers.wasabi_scraper import WasabiScraper
    from src.storage.database import build_engine, build_session_factory
    from src.storage.event_repository import EventRepository
    from src.orchestrator import Orchestrator

    scraper_cfg = cfg.get("scrapers", {})

    scrapers = []
    if scraper_cfg.get("allaccess", {}).get("enabled", True):
        c = scraper_cfg["allaccess"]
        scrapers.append(AllAccessScraper(url=c["url"], timeout=c.get("timeout_seconds", 30)))
    if scraper_cfg.get("polenta", {}).get("enabled", True):
        c = scraper_cfg["polenta"]
        scrapers.append(PolentaScraper(url=c["url"], timeout=c.get("timeout_seconds", 30)))
    if scraper_cfg.get("wasabi", {}).get("enabled", True):
        c = scraper_cfg["wasabi"]
        scrapers.append(WasabiScraper(url=c["url"], timeout=c.get("timeout_seconds", 30)))
    if scraper_cfg.get("bresh", {}).get("enabled", True):
        c = scraper_cfg["bresh"]
        scrapers.append(BreshScraper(
            url=c["url"],
            timeout=c.get("timeout_seconds", 60),
            headless=c.get("headless", True),
        ))

    # City keywords: env override takes precedence over config.yaml
    env_cities = os.getenv("TARGET_CITIES")
    if env_cities:
        keywords = [k.strip() for k in env_cities.split(",")]
    else:
        keywords = cfg.get("city_filter", {}).get("keywords", ["buenos aires"])

    city_filter = CityFilter(keywords)

    engine = build_engine()
    session_factory = build_session_factory(engine)
    repository = EventRepository(session_factory)

    phone = os.getenv("CALLMEBOT_PHONE", "")
    api_key = os.getenv("CALLMEBOT_API_KEY", "")
    if not phone or not api_key:
        logger.error(
            "CALLMEBOT_PHONE and CALLMEBOT_API_KEY must be set in .env — aborting"
        )
        sys.exit(1)
    notifiers = [CallmebotNotifier(phone=phone, api_key=api_key)]

    return Orchestrator(
        scrapers=scrapers,
        city_filter=city_filter,
        repository=repository,
        notifiers=notifiers,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Party event scrapper")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--run-now", action="store_true", help="Run once and exit")
    group.add_argument("--schedule", action="store_true", help="Run on a recurring schedule")
    args = parser.parse_args()

    cfg = _load_config()
    orchestrator = _build_orchestrator(cfg)

    if args.schedule:
        from src.scheduler import start
        interval = cfg.get("schedule", {}).get("interval_hours", 6)
        start(orchestrator, interval_hours=interval)
    else:
        # Default: --run-now
        count = orchestrator.run()
        logger.info("Done. %d new event(s) notified.", count)


if __name__ == "__main__":
    main()
