"""Push via ntfy.sh — free, no account, install the ntfy app and subscribe."""

from __future__ import annotations

from ..http import HttpError, request
from .base import Notification, Notifier, NotifierError

PRIORITY_MAP = {"low": "2", "default": "3", "high": "4", "urgent": "5"}


class NtfyNotifier(Notifier):
    """Sends a push to an ntfy topic.

    Settings:
        ``topic``   topic name (required) — keep it unguessable, it is the secret
        ``server``  defaults to ``https://ntfy.sh``
        ``token``   access token for protected topics / self-hosted servers
    """

    type_name = "ntfy"

    def send(self, notification: Notification) -> None:
        topic = self._require("topic")
        server = str(self.settings.get("server", "https://ntfy.sh")).rstrip("/")
        headers = {
            "Title": notification.title.encode("ascii", "ignore").decode() or "iPhone price drop",
            "Priority": PRIORITY_MAP.get(notification.priority, "3"),
            "Content-Type": "text/plain; charset=utf-8",
        }
        tags = notification.tags or ["iphone", "money_with_wings"]
        headers["Tags"] = ",".join(tags)
        if notification.url:
            headers["Click"] = notification.url
        if self.settings.get("token"):
            headers["Authorization"] = f"Bearer {self.settings['token']}"
        try:
            request(
                f"{server}/{topic}",
                method="POST",
                data=notification.message.encode("utf-8"),
                headers=headers,
                timeout=float(self.settings.get("timeout", 15)),
            )
        except HttpError as exc:
            raise NotifierError(f"ntfy push failed: {exc}") from exc
