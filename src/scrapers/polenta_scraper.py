from __future__ import annotations

import logging
import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup, Tag

from src.models.event import Event
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_MONTHS_ES = {
    "ene": 1, "enero": 1, "feb": 2, "febrero": 2, "mar": 3, "marzo": 3,
    "abr": 4, "abril": 4, "may": 5, "mayo": 5, "jun": 6, "junio": 6,
    "jul": 7, "julio": 7, "ago": 8, "agosto": 8, "sep": 9, "septiembre": 9,
    "oct": 10, "octubre": 10, "nov": 11, "noviembre": 11, "dic": 12, "diciembre": 12,
}


def _parse_date(text: str) -> datetime | None:
    text = text.lower().strip()
    m = re.search(r"(\d{1,2})\s+(?:de\s+)?(\w+)(?:\s+(\d{4}))?", text)
    if not m:
        return None
    day = int(m.group(1))
    month_str = m.group(2)[:3]
    month = _MONTHS_ES.get(month_str) or _MONTHS_ES.get(m.group(2))
    year = int(m.group(3)) if m.group(3) else datetime.now().year
    if not month:
        return None
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


class PolentaScraper(BaseScraper):
    def __init__(self, url: str = "https://fiestapolenta.com/", timeout: int = 30) -> None:
        self._url = url
        self._timeout = timeout

    @property
    def source_name(self) -> str:
        return "polenta"

    def scrape(self) -> list[Event]:
        try:
            return self._fetch_and_parse()
        except Exception:
            logger.exception("Polenta scraper failed")
            return []

    def _fetch_and_parse(self) -> list[Event]:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; PartyScrapper/1.0)"}
        with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
            resp = client.get(self._url, headers=headers)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        events: list[Event] = []

        # fiestapolenta.com lists events as rows with date + city + ticket link
        # Strategy: look for any anchor that points to known ticket platforms
        ticket_domains = ("passline", "venti", "alpogo", "ra.co", "ticketek", "allaccess")

        for link in soup.find_all("a", href=True):
            href: str = link["href"]
            if not any(d in href for d in ticket_domains):
                continue
            event = self._parse_event_row(link, href)
            if event:
                events.append(event)

        # Fallback: parse structured date rows from the page body
        if not events:
            events = self._parse_date_rows(soup)

        logger.info("Polenta: found %d events", len(events))
        return events

    def _parse_event_row(self, tag: Tag, ticket_url: str) -> Event | None:
        # Walk up to find the parent row that contains date + city info
        parent = tag.parent
        for _ in range(4):
            if parent is None:
                break
            text = parent.get_text(" ", strip=True)
            if re.search(r"\d{1,2}\s+(?:de\s+)?\w+", text):
                break
            parent = parent.parent

        container_text = parent.get_text(" ", strip=True) if parent else tag.get_text(strip=True)

        date = _parse_date(container_text) or datetime(datetime.now().year, 12, 31)

        # City is usually the most prominent noun after the date
        city_match = re.search(
            r"(?:buenos aires|caba|córdoba|rosario|mendoza|quilmes|palermo|"
            r"tigre|avellaneda|lomas|lanús|san isidro)",
            container_text.lower(),
        )
        city = city_match.group(0).title() if city_match else "Buenos Aires"

        # Venue: parenthetical or text after @
        venue_match = re.search(r"@\s*(.+?)(?:\s*[-|]|$)", container_text)
        venue = venue_match.group(1).strip() if venue_match else ""

        return Event(
            title="Fiesta Polenta",
            date=date,
            venue=venue,
            city=city,
            source=self.source_name,
            ticket_url=ticket_url,
        )

    def _parse_date_rows(self, soup: BeautifulSoup) -> list[Event]:
        """Fallback: extract any text block that looks like a date + city pair."""
        events: list[Event] = []
        for el in soup.find_all(string=re.compile(r"\d{1,2}\s+(?:de\s+)?\w+")):
            text = el.strip()
            date = _parse_date(text)
            if not date:
                continue
            city_m = re.search(
                r"buenos aires|caba|córdoba|rosario|quilmes|palermo|tigre|avellaneda",
                text.lower(),
            )
            city = city_m.group(0).title() if city_m else ""
            events.append(Event(
                title="Fiesta Polenta",
                date=date,
                venue="",
                city=city,
                source=self.source_name,
                ticket_url=self._url,
            ))
        return events
