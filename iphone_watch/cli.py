"""Command line interface for the iPhone price watcher."""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from typing import Optional, Sequence

from . import __version__
from .config import Config, ConfigError
from .models import IPHONE_SCREEN_INCHES
from .monitor import RunResult, money, run_once, _as_dict
from .notifiers import Notification, NotifierError, build_notifier
from .sources import SOURCE_TYPES, SourceError
from .notifiers import NOTIFIER_TYPES
from .storage import StateStore

EXIT_OK = 0
EXIT_RUN_ERRORS = 1
EXIT_CONFIG_ERROR = 2

_stop = False


def _handle_signal(signum, frame):  # pragma: no cover - signal path
    global _stop
    _stop = True
    print("\nstopping after the current pass…", file=sys.stderr)


def _setup_logging(verbosity: int) -> None:
    level = logging.WARNING if verbosity <= 0 else (logging.INFO if verbosity == 1 else logging.DEBUG)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")


def _load_config(args) -> Config:
    config = Config.load(args.config)
    if getattr(args, "state_file", None):
        config.state_file = args.state_file
    return config


def _report(result: RunResult, args) -> None:
    if getattr(args, "json", False):
        print(json.dumps(
            {
                "fetched": result.fetched,
                "eligible": result.eligible,
                "notified": result.notified,
                "drops": [_as_dict(drop) for drop in result.drops],
                "errors": result.errors,
            },
            indent=2,
        ))
        return

    print(f"fetched {result.fetched} listing(s); {result.eligible} match the criteria")
    if result.drops:
        print(f"\n{len(result.drops)} price drop(s):")
        for drop in result.drops:
            print(f"  {drop.headline}")
            if drop.listing.url:
                print(f"    {drop.listing.url}")
        print("\npush sent" if result.notified else "\nno push sent (dry run)" )
    else:
        print("no price drops this pass")
    if getattr(args, "explain", False) and result.rejections:
        print(f"\nskipped {len(result.rejections)} listing(s):")
        for rejection in result.rejections:
            print(f"  - {rejection.listing.title or rejection.listing.key}: {rejection.reason}")
    for error in result.errors:
        print(f"error: {error}", file=sys.stderr)


def cmd_check(args) -> int:
    config = _load_config(args)
    result = run_once(config, dry_run=args.dry_run)
    _report(result, args)
    return EXIT_RUN_ERRORS if result.errors else EXIT_OK


def cmd_watch(args) -> int:
    config = _load_config(args)
    interval = args.interval or config.interval_seconds
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    print(f"watching every {interval}s — Ctrl-C to stop")
    status = EXIT_OK
    while not _stop:
        started = time.time()
        try:
            result = run_once(config, dry_run=args.dry_run)
            _report(result, args)
            if result.errors:
                status = EXIT_RUN_ERRORS
        except Exception as exc:  # keep the loop alive across transient failures
            print(f"error: pass failed: {exc}", file=sys.stderr)
            status = EXIT_RUN_ERRORS
        if args.once:
            break
        # Sleep in short slices so Ctrl-C is responsive.
        deadline = started + interval
        while not _stop and time.time() < deadline:
            time.sleep(min(1.0, deadline - time.time()))
    return status


def cmd_state(args) -> int:
    config = _load_config(args)
    store = StateStore(config.state_file)
    if not store.listings:
        print(f"no price history yet ({config.state_file})")
        return EXIT_OK
    if args.json:
        print(json.dumps({key: t.to_dict() for key, t in store.listings.items()}, indent=2))
        return EXIT_OK
    print(f"{len(store.listings)} tracked listing(s) in {config.state_file}\n")
    for key, tracked in sorted(store.listings.items(), key=lambda kv: kv[1].last_price):
        trend = ""
        if tracked.first_price and tracked.last_price != tracked.first_price:
            delta = tracked.last_price - tracked.first_price
            trend = f"  ({'+' if delta > 0 else ''}{delta:,.2f} since first seen)"
        print(f"{tracked.title or key}")
        print(
            f"  now {money(tracked.last_price, tracked.currency)}"
            f" | best {money(tracked.best_price, tracked.currency)}"
            f" | first {money(tracked.first_price, tracked.currency)}{trend}"
        )
        print(f"  last seen {tracked.last_seen}  [{key}]")
    return EXIT_OK


def cmd_models(args) -> int:
    threshold = args.min_screen_inches
    print(f'models with a screen of at least {threshold}" qualify as "large screen":\n')
    for model, inches in sorted(IPHONE_SCREEN_INCHES.items(), key=lambda kv: (-kv[1], kv[0])):
        mark = "✓" if inches >= threshold else " "
        print(f"  {mark} {model:<22} {inches}\"")
    return EXIT_OK


def cmd_backends(args) -> int:
    print("sources:")
    for name, cls in sorted(SOURCE_TYPES.items()):
        print(f"  {name:<14} {(cls.__doc__ or '').strip().splitlines()[0]}")
    print("\nnotifiers:")
    for name, cls in sorted(NOTIFIER_TYPES.items()):
        doc = (cls.__doc__ or "").strip().splitlines()
        print(f"  {name:<14} {doc[0] if doc else ''}")
    return EXIT_OK


def cmd_test_notify(args) -> int:
    config = _load_config(args)
    notification = Notification(
        title="iPhone price watch is live",
        message=(
            "Test push.\n"
            f'Watching new iPhones with a screen of at least {config.criteria.min_screen_inches}" '
            f"and at least {config.criteria.min_storage_gb}GB of storage."
        ),
        priority="default",
        tags=["white_check_mark"],
    )
    failures = 0
    for entry in config.notifiers:
        notifier = build_notifier(entry)
        try:
            notifier.send(notification)
            print(f"sent via {notifier.name}")
        except NotifierError as exc:
            failures += 1
            print(f"error: {exc}", file=sys.stderr)
    return EXIT_RUN_ERRORS if failures else EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="iphone-watch",
        description="Watch new large-screen iPhones (256GB+) for price drops and push an alert.",
    )
    parser.add_argument("--version", action="version", version=f"iphone-watch {__version__}")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="repeat for debug logging")
    parser.add_argument("-c", "--config", help="path to the config file (default: config.json)")
    parser.add_argument("--state-file", help="override config.state_file")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="run one pass now")
    check.add_argument("--dry-run", action="store_true", help="detect drops but send nothing and keep state unchanged")
    check.add_argument("--explain", action="store_true", help="list skipped listings and why")
    check.add_argument("--json", action="store_true", help="machine-readable output")
    check.set_defaults(func=cmd_check)

    watch = sub.add_parser("watch", help="keep checking on an interval")
    watch.add_argument("--interval", type=int, help="seconds between passes (default: config.interval_seconds)")
    watch.add_argument("--dry-run", action="store_true")
    watch.add_argument("--explain", action="store_true")
    watch.add_argument("--json", action="store_true")
    watch.add_argument("--once", action="store_true", help="stop after the first pass (useful in cron)")
    watch.set_defaults(func=cmd_watch)

    state = sub.add_parser("state", help="show the tracked price history")
    state.add_argument("--json", action="store_true")
    state.set_defaults(func=cmd_state)

    models = sub.add_parser("models", help="show iPhone screen sizes and which count as large")
    models.add_argument("--min-screen-inches", type=float, default=6.5)
    models.set_defaults(func=cmd_models)

    sub.add_parser("backends", help="list available source and notifier types").set_defaults(func=cmd_backends)
    sub.add_parser("test-notify", help="send a test push through every configured notifier").set_defaults(
        func=cmd_test_notify
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    except (SourceError, NotifierError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_RUN_ERRORS
    except BrokenPipeError:  # e.g. `… | head`
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return EXIT_OK
    except KeyboardInterrupt:  # pragma: no cover
        return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
