from __future__ import annotations

import logging
import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from src.models.event import Event
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_MONTHS_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def _parse_date(text: str) -> datetime | None:
    text = text.lower().strip()
    # "15 de junio" / "15 junio 2025"
    m = re.search(r"(\d{1,2})\s+(?:de\s+)?(\w+)(?:\s+(\d{4}))?", text)
    if not m:
        return None
    day = int(m.group(1))
    month = _MONTHS_ES.get(m.group(2))
    year = int(m.group(3)) if m.group(3) else datetime.now().year
    if not month:
        return None
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


class AllAccessScraper(BaseScraper):
    def __init__(self, url: str = "https://www.allaccess.com.ar/", timeout: int = 30) -> None:
        self._url = url
        self._timeout = timeout

    @property
    def source_name(self) -> str:
        return "allaccess"

    def scrape(self) -> list[Event]:
        try:
            return self._fetch_and_parse()
        except Exception:
            logger.exception("AllAccess scraper failed")
            return []

    def _fetch_and_parse(self) -> list[Event]:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; PartyScrapper/1.0)"}
        with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
            resp = client.get(self._url, headers=headers)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        events: list[Event] = []

        # AllAccess renders event links as <a href="/event/slug">
        for link in soup.select("a[href*='/event/']"):
            event = self._parse_event_card(link)
            if event:
                events.append(event)

        logger.info("AllAccess: found %d events", len(events))
        return events

    def _parse_event_card(self, tag) -> Event | None:
        href = tag.get("href", "")
        ticket_url = f"https://www.allaccess.com.ar{href}" if href.startswith("/") else href

        # Title: look for img alt, heading, or link text
        title = ""
        img = tag.find("img")
        if img and img.get("alt"):
            title = img["alt"].strip()
        if not title:
            heading = tag.find(["h2", "h3", "h4", "strong", "span"])
            title = heading.get_text(strip=True) if heading else tag.get_text(strip=True)
        if not title or len(title) < 3:
            return None

        # Date: look for text nodes that contain date-like patterns
        date_text = ""
        for el in tag.find_all(string=True):
            text = el.strip()
            if re.search(r"\d{1,2}\s+(?:de\s+)?\w+", text):
                date_text = text
                break

        date = _parse_date(date_text) if date_text else datetime(datetime.now().year, 12, 31)

        # Venue / city: look for location spans
        venue = ""
        city = "Buenos Aires"
        for el in tag.find_all(["span", "p", "div"]):
            text = el.get_text(strip=True)
            if "@" in text or "venue" in text.lower():
                venue = text
                break

        return Event(
            title=title,
            date=date,
            venue=venue,
            city=city,
            source=self.source_name,
            ticket_url=ticket_url,
        )
