from __future__ import annotations

import logging
import urllib.parse

import httpx

from src.models.event import Event
from src.notifiers.base_notifier import BaseNotifier

logger = logging.getLogger(__name__)

_API_URL = "https://api.callmebot.com/whatsapp.php"


class CallmebotNotifier(BaseNotifier):
    def __init__(self, phone: str, api_key: str) -> None:
        self._phone = phone
        self._api_key = api_key

    def notify(self, event: Event) -> None:
        message = self._format(event)
        try:
            self._send(message)
            logger.info("WhatsApp sent for event '%s' (%s)", event.title, event.id)
        except Exception:
            logger.exception("Failed to send WhatsApp for event '%s'", event.title)

    def _format(self, event: Event) -> str:
        date_str = event.date.strftime("%d/%m/%Y")
        venue_part = f" @ {event.venue}" if event.venue else ""
        return (
            f"🎉 *Nuevo evento detectado!*\n"
            f"*{event.title}*\n"
            f"📅 {date_str}\n"
            f"📍 {event.city}{venue_part}\n"
            f"🎫 {event.ticket_url}\n"
            f"_(via {event.source})_"
        )

    def _send(self, message: str) -> None:
        params = {
            "phone": self._phone,
            "text": message,
            "apikey": self._api_key,
        }
        url = f"{_API_URL}?{urllib.parse.urlencode(params)}"
        with httpx.Client(timeout=15) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                logger.warning("Callmebot returned %s: %s", resp.status_code, resp.text)
            else:
                logger.debug("Callmebot response: %s", resp.text)
