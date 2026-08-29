"""Notifier interface and the push payload passed to every backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


class NotifierError(RuntimeError):
    """Raised when a push could not be delivered."""


@dataclass
class Notification:
    """One push notification, in a backend-neutral shape."""

    title: str
    message: str
    url: Optional[str] = None
    priority: str = "default"      # low | default | high | urgent
    tags: list = field(default_factory=list)
    data: dict = field(default_factory=dict)


class Notifier:
    """Delivers a :class:`Notification` to the user's phone."""

    type_name = "base"

    def __init__(self, settings: dict):
        self.settings = dict(settings or {})
        self.name = self.settings.get("name") or self.type_name

    def send(self, notification: Notification) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def _require(self, key: str) -> str:
        value = self.settings.get(key)
        if not value:
            raise NotifierError(
                f"notifier '{self.name}' is missing required setting '{key}' "
                "(check the matching environment variable)"
            )
        return str(value)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{self.__class__.__name__} name={self.name!r}>"
