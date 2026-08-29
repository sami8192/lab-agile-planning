import json

import pytest

from iphone_watch.cli import EXIT_CONFIG_ERROR, EXIT_OK, EXIT_RUN_ERRORS, main
from iphone_watch.config import Config
from iphone_watch.monitor import run_once
from iphone_watch.notifiers import NotifierError
from iphone_watch.storage import StateStore


def write_config(tmp_path, *, price_delta=0, notifier=None, **overrides):
    config = {
        "criteria": {"min_screen_inches": 6.5, "min_storage_gb": 256, "conditions": ["new"]},
        "alerts": {"min_drop_percent": 2.0, "min_drop_amount": 10.0, "notify_cooldown_hours": 12},
        "sources": [{"type": "sample", "name": "demo", "price_delta": price_delta}],
        "notifiers": [notifier or {"type": "console", "name": "stdout"}],
        "state_file": str(tmp_path / "state" / "prices.json"),
    }
    config.update(overrides)
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return str(path)


def test_check_runs_and_writes_state(tmp_path, capsys):
    path = write_config(tmp_path)
    assert main(["-c", path, "check"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "5 match the criteria" in out
    assert "no price drops" in out
    assert (tmp_path / "state" / "prices.json").is_file()


def test_check_detects_a_drop_on_the_second_pass(tmp_path, capsys):
    main(["-c", write_config(tmp_path), "check"])
    capsys.readouterr()
    assert main(["-c", write_config(tmp_path, price_delta=-150), "check"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "5 price drop(s)" in out
    assert "push sent" in out
    assert "iPhone 17 Pro Max 256GB (Unlocked): $1,199 → $1,049" in out


def test_dry_run_leaves_state_untouched(tmp_path):
    path = write_config(tmp_path)
    assert main(["-c", path, "check", "--dry-run"]) == EXIT_OK
    assert not (tmp_path / "state" / "prices.json").exists()


def test_explain_lists_rejections(tmp_path, capsys):
    assert main(["-c", write_config(tmp_path), "check", "--dry-run", "--explain"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "condition is refurbished" in out
    assert "below the 6.5\" minimum" in out
    assert "locked to AT&T" in out
    assert "requires a new line" in out


def test_json_output_is_machine_readable(tmp_path, capsys):
    main(["-c", write_config(tmp_path), "check"])
    capsys.readouterr()
    main(["-c", write_config(tmp_path, price_delta=-150), "check", "--json"])
    # The console notifier prints the push itself first; the report follows as JSON.
    out = capsys.readouterr().out
    payload = json.loads(out[out.index("{"):])
    assert payload["eligible"] == 5
    assert payload["notified"] is True
    assert payload["drops"][0]["drop_percent"] > 0
    assert payload["drops"][0]["storage_gb"] >= 256
    assert payload["drops"][0]["screen_inches"] >= 6.5


def test_watch_once_performs_a_single_pass(tmp_path, capsys):
    assert main(["-c", write_config(tmp_path), "watch", "--once", "--interval", "1"]) == EXIT_OK
    assert "watching every 1s" in capsys.readouterr().out


def test_state_command_reports_history(tmp_path, capsys):
    path = write_config(tmp_path)
    main(["-c", path, "check"])
    capsys.readouterr()
    assert main(["-c", path, "state"]) == EXIT_OK
    assert "tracked listing(s)" in capsys.readouterr().out
    assert main(["-c", path, "state", "--json"]) == EXIT_OK
    assert "demo:demo-air-256" in capsys.readouterr().out


def test_state_command_without_history(tmp_path, capsys):
    assert main(["-c", write_config(tmp_path), "state"]) == EXIT_OK
    assert "no price history yet" in capsys.readouterr().out


def test_models_command_marks_large_screens(capsys):
    assert main(["models"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "✓ iPhone 17 Pro Max" in out
    assert "  iPhone 17 Pro " in out  # 6.3" does not qualify


def test_backends_command_lists_types(capsys):
    assert main(["backends"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "ntfy" in out and "bestbuy" in out


def test_test_notify_sends_through_every_notifier(tmp_path, capsys):
    assert main(["-c", write_config(tmp_path), "test-notify"]) == EXIT_OK
    assert "iPhone price watch is live" in capsys.readouterr().out


def test_missing_config_exits_with_a_config_error(tmp_path, capsys):
    assert main(["-c", str(tmp_path / "nope.json"), "check"]) == EXIT_CONFIG_ERROR
    assert "config error" in capsys.readouterr().err


def test_state_file_override(tmp_path):
    override = tmp_path / "custom.json"
    main(["-c", write_config(tmp_path), "--state-file", str(override), "check"])
    assert override.is_file()


def test_source_failures_are_reported_but_do_not_crash(tmp_path, capsys):
    path = write_config(tmp_path)
    config = json.loads(open(path).read())
    config["sources"].append({"type": "sample", "name": "broken", "path": str(tmp_path / "missing.json")})
    open(path, "w").write(json.dumps(config))
    assert main(["-c", path, "check"]) == EXIT_RUN_ERRORS
    captured = capsys.readouterr()
    assert "5 match the criteria" in captured.out  # the healthy source still ran
    assert "sample fixture not found" in captured.err


def test_failed_push_leaves_state_unchanged_so_the_alert_is_retried(tmp_path, monkeypatch):
    from iphone_watch import monitor as monitor_module

    path = write_config(tmp_path)
    main(["-c", path, "check"])
    before = (tmp_path / "state" / "prices.json").read_text()

    class Boom:
        name = "boom"

        def send(self, notification):
            raise NotifierError("push failed")

    monkeypatch.setattr(monitor_module, "build_notifier", lambda entry: Boom())
    config = Config.load(write_config(tmp_path, price_delta=-150))
    result = run_once(config)
    assert result.drops and not result.notified
    assert (tmp_path / "state" / "prices.json").read_text() == before


def test_successful_push_stamps_the_cooldown(tmp_path):
    main(["-c", write_config(tmp_path), "check"])
    main(["-c", write_config(tmp_path, price_delta=-150), "check"])
    store = StateStore(str(tmp_path / "state" / "prices.json"))
    tracked = store.get("demo:demo-17-pro-max-256")
    assert tracked.last_notified is not None
    assert tracked.last_notified_price == tracked.last_price
