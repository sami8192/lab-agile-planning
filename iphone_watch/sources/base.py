"""Source interface shared by every price feed."""

from __future__ import annotations

from typing import Iterable

from ..models import Listing


class SourceError(RuntimeError):
    """Raised when a source cannot produce listings (bad credentials, API down…)."""


class Source:
    """A place to look up iPhone offers.

    Subclasses read their settings from the ``sources[]`` entry in the config
    and return :class:`~iphone_watch.models.Listing` objects from :meth:`fetch`.
    """

    type_name = "base"

    def __init__(self, settings: dict):
        self.settings = dict(settings or {})
        self.name = self.settings.get("name") or self.type_name

    def fetch(self) -> Iterable[Listing]:  # pragma: no cover - interface only
        raise NotImplementedError

    def _require(self, key: str) -> str:
        value = self.settings.get(key)
        if not value:
            raise SourceError(f"source '{self.name}' is missing required setting '{key}'")
        return str(value)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{self.__class__.__name__} name={self.name!r}>"
