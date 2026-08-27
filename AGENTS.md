# party_scrapper

Party-event scraper that monitors Argentine event sites (Bresh, AllAccess, La Polenta,
Wasabi, …) and sends a WhatsApp notification when an event shows up near Buenos Aires / CABA /
Zona Sur, so you can buy tickets early.

Full-stack Python, SOLID and design patterns throughout.

## Stack

- **Python 3.13**
- **Scraping:** `httpx` + `BeautifulSoup` (html.parser) for static sites; `playwright`
  (headless Chromium) for JS-rendered pages (Bresh / Next.js)
- **Scheduling:** `APScheduler` 3.x — `BlockingScheduler` + `IntervalTrigger`
- **Notifications:** WhatsApp via the CallMeBot free API
- **Storage:** SQLite via SQLAlchemy 2.x (sync)
- **Config:** `.env` (python-dotenv) + `config/config.yaml`

## Commands

```bash
pip install -r requirements.txt
playwright install chromium        # first time only
cp .env.example .env               # then fill it in

python -m src.main --run-now       # one pass
python -m src.main --schedule      # every 6h, runs immediately once

pytest tests/ -v                   # all tests
pytest tests/test_city_filter.py -v
```

## Architecture

```
Orchestrator
├── BaseScraper (Strategy)    → scrape() -> list[Event]
│   ├── AllAccessScraper      httpx + BS4, static HTML
│   ├── PolentaScraper        httpx + BS4, ticket-link detection
│   ├── WasabiScraper         httpx + BS4, ticket-link detection
│   └── BreshScraper          Playwright, XHR interception + DOM fallback
├── CityFilter                keyword match on event.city + event.venue
├── EventRepository           SQLite dedup (seen_events table)
└── BaseNotifier (Observer)   → notify(event)
    └── CallmebotNotifier     GET api.callmebot.com/whatsapp.php
```

**DI:** `src/main.py` wires everything; no component imports another directly (only via ABCs).

## Dedup

`Event.id = sha256(source + title + date.date())[:16]` — stops duplicate WhatsApp messages
across scheduler runs. Stored in the SQLite DB (auto-created, gitignored).

## Conventions

- Structure of a test file: `UPPER_CASE` constants first, then `describe`/cases, helpers last.
- Env vars: `CALLMEBOT_PHONE` (Argentina: `549` + number, no `0`, no `15`), `CALLMEBOT_API_KEY`,
  optional `TARGET_CITIES` (comma-separated) to override the city keywords.

## Adding a scraper

1. `src/scrapers/<name>_scraper.py` subclassing `BaseScraper`
2. Add its block under `scrapers:` in `config/config.yaml`
3. Instantiate and append it in `src/main.py::_build_orchestrator`
