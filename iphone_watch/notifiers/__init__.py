"""Notifier registry: maps a config ``type`` onto a Notifier implementation."""

from __future__ import annotations

from .base import Notification, Notifier, NotifierError
from .console import ConsoleNotifier
from .ntfy import NtfyNotifier
from .pushover import PushoverNotifier
from .webhook import WebhookNotifier

NOTIFIER_TYPES: dict[str, type[Notifier]] = {
    cls.type_name: cls
    for cls in (NtfyNotifier, PushoverNotifier, WebhookNotifier, ConsoleNotifier)
}


def build_notifier(settings: dict) -> Notifier:
    """Instantiate the notifier described by a ``notifiers[]`` config entry."""
    type_name = str(settings.get("type", "")).lower()
    try:
        cls = NOTIFIER_TYPES[type_name]
    except KeyError:
        raise NotifierError(
            f"unknown notifier type {type_name!r}; available: {', '.join(sorted(NOTIFIER_TYPES))}"
        ) from None
    return cls(settings)


__all__ = ["Notification", "Notifier", "NotifierError", "NOTIFIER_TYPES", "build_notifier"]
