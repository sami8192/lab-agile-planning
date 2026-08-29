"""Configuration loading, environment expansion and defaults."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

DEFAULT_CONFIG_PATHS = ("config.json", "config.example.json")

# ${VAR} or ${VAR:-fallback}
_ENV_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


class ConfigError(ValueError):
    """Raised when a config file is missing required values or malformed."""


def expand_env(value: Any) -> Any:
    """Recursively replace ``${VAR}`` placeholders with environment values."""
    if isinstance(value, str):
        def repl(match: re.Match) -> str:
            return os.environ.get(match.group(1), match.group(2) or "")
        return _ENV_RE.sub(repl, value)
    if isinstance(value, list):
        return [expand_env(item) for item in value]
    if isinstance(value, dict):
        return {key: expand_env(item) for key, item in value.items()}
    return value


@dataclass
class Criteria:
    """What counts as a phone worth watching."""

    min_screen_inches: float = 6.5
    min_storage_gb: int = 256
    conditions: tuple[str, ...] = ("new",)
    models: tuple[str, ...] = ()          # empty = any model that passes the rules
    exclude_models: tuple[str, ...] = ()
    max_price: Optional[float] = None
    currency: Optional[str] = "USD"
    require_in_stock: bool = True
    allow_unknown_models: bool = False    # unknown screen size => not provably large
    require_unlocked: bool = True         # reject phones locked to another carrier
    allowed_carriers: tuple[str, ...] = ("unlocked", "t-mobile")
    allow_unknown_carrier: bool = True    # most retail listings never say
    exclude_new_line_offers: bool = True  # prices that need a new line / trade-in

    @classmethod
    def from_dict(cls, data: dict) -> "Criteria":
        data = dict(data or {})
        return cls(
            min_screen_inches=float(data.get("min_screen_inches", 6.5)),
            min_storage_gb=int(data.get("min_storage_gb", 256)),
            conditions=tuple(c.lower() for c in data.get("conditions", ["new"])),
            models=tuple(data.get("models", ())),
            exclude_models=tuple(data.get("exclude_models", ())),
            max_price=(float(data["max_price"]) if data.get("max_price") is not None else None),
            currency=data.get("currency", "USD"),
            require_in_stock=bool(data.get("require_in_stock", True)),
            allow_unknown_models=bool(data.get("allow_unknown_models", False)),
            require_unlocked=bool(data.get("require_unlocked", True)),
            allowed_carriers=tuple(
                str(c).strip().lower().replace(" ", "-") for c in data.get("allowed_carriers", ["unlocked", "t-mobile"])
            ),
            allow_unknown_carrier=bool(data.get("allow_unknown_carrier", True)),
            exclude_new_line_offers=bool(data.get("exclude_new_line_offers", True)),
        )


@dataclass
class AlertRules:
    """When a price change is worth a push notification."""

    min_drop_percent: float = 2.0
    min_drop_amount: float = 10.0
    baseline: str = "best"                # "best" (lowest ever seen) or "last"
    notify_cooldown_hours: float = 12.0
    notify_on_first_seen: bool = False
    group_notifications: bool = True
    max_items_per_notification: int = 5

    @classmethod
    def from_dict(cls, data: dict) -> "AlertRules":
        data = dict(data or {})
        baseline = str(data.get("baseline", "best")).lower()
        if baseline not in ("best", "last"):
            raise ConfigError("alerts.baseline must be 'best' or 'last'")
        return cls(
            min_drop_percent=float(data.get("min_drop_percent", 2.0)),
            min_drop_amount=float(data.get("min_drop_amount", 10.0)),
            baseline=baseline,
            notify_cooldown_hours=float(data.get("notify_cooldown_hours", 12.0)),
            notify_on_first_seen=bool(data.get("notify_on_first_seen", False)),
            group_notifications=bool(data.get("group_notifications", True)),
            max_items_per_notification=int(data.get("max_items_per_notification", 5)),
        )


@dataclass
class Config:
    criteria: Criteria = field(default_factory=Criteria)
    alerts: AlertRules = field(default_factory=AlertRules)
    sources: list[dict] = field(default_factory=list)
    notifiers: list[dict] = field(default_factory=list)
    state_file: str = "state/prices.json"
    interval_seconds: int = 900
    path: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict, path: Optional[str] = None) -> "Config":
        data = expand_env(dict(data or {}))
        sources = [s for s in data.get("sources", []) if s.get("enabled", True)]
        notifiers = [n for n in data.get("notifiers", []) if n.get("enabled", True)]
        if not sources:
            raise ConfigError("no enabled entries under 'sources'")
        if not notifiers:
            raise ConfigError("no enabled entries under 'notifiers'")
        for entry in sources + notifiers:
            if not entry.get("type"):
                raise ConfigError(f"entry is missing a 'type': {entry!r}")
        return cls(
            criteria=Criteria.from_dict(data.get("criteria", {})),
            alerts=AlertRules.from_dict(data.get("alerts", {})),
            sources=sources,
            notifiers=notifiers,
            state_file=data.get("state_file", "state/prices.json"),
            interval_seconds=int(data.get("interval_seconds", 900)),
            path=path,
        )

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Config":
        candidates = [path] if path else list(DEFAULT_CONFIG_PATHS)
        for candidate in candidates:
            if candidate and Path(candidate).is_file():
                raw = Path(candidate).read_text(encoding="utf-8")
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ConfigError(f"{candidate} is not valid JSON: {exc}") from exc
                return cls.from_dict(data, path=candidate)
        raise ConfigError(
            "no config file found (looked for: %s); copy config.example.json to config.json"
            % ", ".join(c for c in candidates if c)
        )
