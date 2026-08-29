"""Prints notifications to stdout — handy for dry runs and CI logs."""

from __future__ import annotations

import sys

from .base import Notification, Notifier


class ConsoleNotifier(Notifier):
    type_name = "console"

    def send(self, notification: Notification) -> None:
        stream = sys.stderr if self.settings.get("stderr") else sys.stdout
        print(f"\n[{notification.priority.upper()}] {notification.title}", file=stream)
        print(notification.message, file=stream)
        if notification.url:
            print(notification.url, file=stream)
        stream.flush()
