from __future__ import annotations

import json
import logging
import re
from datetime import datetime

from src.models.event import Event
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


def _parse_iso(date_str: str) -> datetime | None:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str[:19], fmt)
        except ValueError:
            continue
    return None


class BreshScraper(BaseScraper):
    """
    Bresh runs on Next.js. We intercept the JSON payload returned by the
    /_next/data/ endpoint (which Next.js fetches for getServerSideProps /
    getStaticProps pages) instead of parsing the rendered HTML.
    Falls back to Playwright DOM scraping if the JSON route isn't available.
    """

    def __init__(
        self,
        url: str = "https://www.bresh.com/events",
        timeout: int = 60,
        headless: bool = True,
    ) -> None:
        self._url = url
        self._timeout = timeout
        self._headless = headless

    @property
    def source_name(self) -> str:
        return "bresh"

    def scrape(self) -> list[Event]:
        try:
            events = self._scrape_with_playwright()
            logger.info("Bresh: found %d events", len(events))
            return events
        except Exception:
            logger.exception("Bresh scraper failed")
            return []

    def _scrape_with_playwright(self) -> list[Event]:
        from playwright.sync_api import sync_playwright

        events: list[Event] = []
        intercepted_json: list[dict] = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self._headless)
            page = browser.new_page()

            # Intercept XHR / fetch responses that look like event data
            def handle_response(response):
                url = response.url
                if "event" in url.lower() and response.status == 200:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        try:
                            intercepted_json.append(response.json())
                        except Exception:
                            pass

            page.on("response", handle_response)
            page.goto(self._url, timeout=self._timeout * 1000, wait_until="networkidle")

            # Try to parse intercepted JSON first
            for payload in intercepted_json:
                events.extend(self._parse_json_payload(payload))

            # Fallback: parse DOM
            if not events:
                events = self._parse_dom(page)

            browser.close()

        return events

    def _parse_json_payload(self, data: dict | list) -> list[Event]:
        events: list[Event] = []
        items = data if isinstance(data, list) else self._flatten_json(data)
        for item in items:
            if not isinstance(item, dict):
                continue
            title = item.get("name") or item.get("title") or item.get("eventName", "")
            if not title:
                continue
            date_raw = item.get("date") or item.get("startDate") or item.get("start_date", "")
            date = _parse_iso(date_raw) if date_raw else datetime(datetime.now().year, 12, 31)
            venue = item.get("venue") or item.get("location") or item.get("place") or ""
            if isinstance(venue, dict):
                venue = venue.get("name", "")
            city = item.get("city") or item.get("ciudad") or ""
            if isinstance(city, dict):
                city = city.get("name", "")
            ticket_url = item.get("ticketUrl") or item.get("url") or self._url
            events.append(Event(
                title=str(title),
                date=date or datetime(datetime.now().year, 12, 31),
                venue=str(venue),
                city=str(city),
                source=self.source_name,
                ticket_url=str(ticket_url),
            ))
        return events

    def _flatten_json(self, data: dict, depth: int = 0) -> list:
        """Recursively extract all list values from a nested dict."""
        if depth > 6:
            return []
        results = []
        for v in data.values():
            if isinstance(v, list):
                results.extend(v)
            elif isinstance(v, dict):
                results.extend(self._flatten_json(v, depth + 1))
        return results

    def _parse_dom(self, page) -> list[Event]:
        """Fallback DOM parser using Playwright locators."""
        events: list[Event] = []
        # Common card selectors for event listing pages
        card_selectors = [
            "[data-testid*='event']",
            ".event-card",
            "article",
            "[class*='event']",
            "[class*='Event']",
        ]

        for selector in card_selectors:
            cards = page.locator(selector).all()
            if not cards:
                continue
            for card in cards:
                try:
                    text = card.inner_text()
                    event = self._parse_card_text(text, page.url)
                    if event:
                        events.append(event)
                except Exception:
                    continue
            if events:
                break

        return events

    def _parse_card_text(self, text: str, base_url: str) -> Event | None:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not lines:
            return None

        title = lines[0]
        date_str = next((l for l in lines if re.search(r"\d{4}|\d{1,2}/\d{1,2}", l)), "")
        date = _parse_iso(date_str) if re.match(r"\d{4}", date_str) else None
        if not date:
            date = datetime(datetime.now().year, 12, 31)

        city = next(
            (l for l in lines if re.search(
                r"buenos aires|caba|córdoba|rosario|mendoza|quilmes", l.lower()
            )), ""
        )

        return Event(
            title=title,
            date=date,
            venue=" | ".join(lines[1:3]),
            city=city,
            source=self.source_name,
            ticket_url=base_url,
        )
