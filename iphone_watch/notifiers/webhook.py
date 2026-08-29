"""Generic webhook notifier — Slack, Discord, Home Assistant, IFTTT, …"""

from __future__ import annotations

import json

from ..http import HttpError, request
from .base import Notification, Notifier, NotifierError


class WebhookNotifier(Notifier):
    """POSTs the notification as JSON.

    Settings:
        ``url``       webhook endpoint (required)
        ``headers``   extra headers (auth tokens)
        ``template``  optional JSON body whose string values may contain
                      ``{title}``, ``{message}`` and ``{url}`` placeholders;
                      without it a structured payload is sent.
    """

    type_name = "webhook"

    def send(self, notification: Notification) -> None:
        url = self._require("url")
        template = self.settings.get("template")
        if template:
            body = json.loads(
                json.dumps(template)
                .replace("{title}", json.dumps(notification.title)[1:-1])
                .replace("{message}", json.dumps(notification.message)[1:-1])
                .replace("{url}", json.dumps(notification.url or "")[1:-1])
            )
        else:
            body = {
                "title": notification.title,
                "message": notification.message,
                "url": notification.url,
                "priority": notification.priority,
                "drops": notification.data.get("drops", []),
            }
        try:
            request(
                url,
                method="POST",
                json_body=body,
                headers=self.settings.get("headers"),
                timeout=float(self.settings.get("timeout", 15)),
            )
        except HttpError as exc:
            raise NotifierError(f"webhook push failed: {exc}") from exc
