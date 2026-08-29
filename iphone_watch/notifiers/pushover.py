"""Push via Pushover (iOS/Android app, one-off purchase)."""

from __future__ import annotations

from ..http import HttpError, request
from .base import Notification, Notifier, NotifierError

ENDPOINT = "https://api.pushover.net/1/messages.json"
PRIORITY_MAP = {"low": "-1", "default": "0", "high": "1", "urgent": "1"}


class PushoverNotifier(Notifier):
    """Settings: ``token`` (application key) and ``user`` (user/group key)."""

    type_name = "pushover"

    def send(self, notification: Notification) -> None:
        payload = {
            "token": self._require("token"),
            "user": self._require("user"),
            "title": notification.title,
            "message": notification.message,
            "priority": PRIORITY_MAP.get(notification.priority, "0"),
        }
        if notification.url:
            payload["url"] = notification.url
            payload["url_title"] = "Open listing"
        if self.settings.get("device"):
            payload["device"] = str(self.settings["device"])
        if self.settings.get("sound"):
            payload["sound"] = str(self.settings["sound"])
        try:
            request(ENDPOINT, method="POST", data=payload, timeout=float(self.settings.get("timeout", 15)))
        except HttpError as exc:
            raise NotifierError(f"pushover push failed: {exc}") from exc
