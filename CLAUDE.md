# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Role

Experienced full-stack developer applying SOLID principles and design patterns throughout the codebase.

## Project Overview

Party event scraper that monitors Argentine event/party websites (Bresh, AllAccess, La Polenta, Wasabi, etc.) and sends WhatsApp notifications when events are detected near Buenos Aires / CABA / Zona Sur, enabling early ticket purchases.

## Stack

- **Python 3.13**
- **Scraping:** `httpx` + `BeautifulSoup` (html.parser) for static sites; `playwright` (headless Chromium) for JS-rendered pages (Bresh/Next.js)
- **Scheduling:** `APScheduler` 3.x — `BlockingScheduler` with `IntervalTrigger`
- **Notifications:** WhatsApp via Callmebot free API
- **Storage:** SQLite via SQLAlchemy 2.x (sync)
- **Config:** `.env` (python-dotenv) + `config/config.yaml`

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browser (first time only)
playwright install chromium

# Copy and fill env vars
cp .env.example .env

# Run scraper once
python -m src.main --run-now

# Run on schedule (every 6h, starts immediately)
python -m src.main --schedule

# Run all tests
pytest tests/ -v

# Run a single test file
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
├── EventRepository           SQLite deduplication (seen_events table)
└── BaseNotifier (Observer)   → notify(event)
    └── CallmebotNotifier     GET api.callmebot.com/whatsapp.php
```

**DI pattern:** `main.py` wires everything; no component imports another directly (except via ABCs). To add a new scraper, subclass `BaseScraper`, register it in `main.py::_build_orchestrator`.

## Event ID / Deduplication

`Event.id = sha256(source + title + date.date())[:16]` — prevents duplicate WhatsApp messages across scheduler runs. Stored in `data/events.db` (auto-created).

## Environment Variables

```
CALLMEBOT_PHONE=549XXXXXXXXXX   # Argentina: 549 + número sin 0 ni 15
CALLMEBOT_API_KEY=XXXXXX
# Optional override of city keywords:
# TARGET_CITIES=buenos aires,quilmes,avellaneda
```

## Adding a New Scraper

1. Create `src/scrapers/<name>_scraper.py` subclassing `BaseScraper`
2. Add its config block to `config/config.yaml` under `scrapers:`
3. Instantiate and append to `scrapers` list in `src/main.py::_build_orchestrator`
