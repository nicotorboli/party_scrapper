from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.models.event import Event
from src.notifiers.callmebot_notifier import CallmebotNotifier


def make_event() -> Event:
    return Event(
        title="Bresh CABA",
        date=datetime(2025, 6, 15),
        venue="Crobar",
        city="Buenos Aires",
        source="bresh",
        ticket_url="https://bresh.com/events/1",
    )


def test_notify_calls_callmebot():
    notifier = CallmebotNotifier(phone="5491100000000", api_key="test123")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "Message queued"

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        notifier.notify(make_event())

        call_args = mock_client.get.call_args[0][0]
        assert "callmebot.com" in call_args
        assert "5491100000000" in call_args
        assert "test123" in call_args


def test_format_contains_title_and_date():
    notifier = CallmebotNotifier(phone="5491100000000", api_key="test123")
    event = make_event()
    msg = notifier._format(event)
    assert "Bresh CABA" in msg
    assert "15/06/2025" in msg
    assert "Buenos Aires" in msg
    assert "Crobar" in msg


def test_notify_does_not_raise_on_http_error():
    notifier = CallmebotNotifier(phone="5491100000000", api_key="bad_key")
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("Connection refused")
        mock_client_cls.return_value = mock_client

        # Should log but not raise
        notifier.notify(make_event())
