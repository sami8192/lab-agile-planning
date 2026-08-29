import json

import pytest

from iphone_watch.http import HttpError
from iphone_watch.notifiers import NOTIFIER_TYPES, Notification, NotifierError, build_notifier
from iphone_watch.notifiers import ntfy as ntfy_module
from iphone_watch.notifiers import pushover as pushover_module
from iphone_watch.notifiers import webhook as webhook_module

NOTE = Notification(
    title="iPhone price drop: iPhone 17 Pro Max 256GB",
    message="• iPhone 17 Pro Max 256GB: $1,199 → $1,049 (-12.5%)",
    url="https://example.com/x",
    priority="high",
    data={"drops": [{"key": "demo:a"}]},
)


def test_registry_exposes_every_type():
    assert set(NOTIFIER_TYPES) == {"ntfy", "pushover", "webhook", "console"}
    with pytest.raises(NotifierError):
        build_notifier({"type": "nope"})


def test_ntfy_posts_to_the_topic(monkeypatch):
    seen = {}

    def fake_request(url, **kwargs):
        seen["url"] = url
        seen.update(kwargs)
        return ""

    monkeypatch.setattr(ntfy_module, "request", fake_request)
    build_notifier({"type": "ntfy", "topic": "my-topic", "token": "tok"}).send(NOTE)
    assert seen["url"] == "https://ntfy.sh/my-topic"
    assert seen["method"] == "POST"
    assert seen["headers"]["Priority"] == "4"
    assert seen["headers"]["Click"] == "https://example.com/x"
    assert seen["headers"]["Authorization"] == "Bearer tok"
    assert b"1,049" in seen["data"]


def test_ntfy_honours_a_self_hosted_server(monkeypatch):
    seen = {}
    monkeypatch.setattr(ntfy_module, "request", lambda url, **kwargs: seen.update(url=url) or "")
    build_notifier({"type": "ntfy", "topic": "t", "server": "https://push.example.com/"}).send(NOTE)
    assert seen["url"] == "https://push.example.com/t"


def test_ntfy_requires_a_topic():
    with pytest.raises(NotifierError) as excinfo:
        build_notifier({"type": "ntfy", "name": "phone"}).send(NOTE)
    assert "topic" in str(excinfo.value)


def test_ntfy_wraps_transport_errors(monkeypatch):
    def boom(url, **kwargs):
        raise HttpError("network error")

    monkeypatch.setattr(ntfy_module, "request", boom)
    with pytest.raises(NotifierError):
        build_notifier({"type": "ntfy", "topic": "t"}).send(NOTE)


def test_pushover_sends_form_fields(monkeypatch):
    seen = {}
    monkeypatch.setattr(pushover_module, "request", lambda url, **kwargs: seen.update(url=url, **kwargs) or "")
    build_notifier({"type": "pushover", "token": "app", "user": "usr", "sound": "cashregister"}).send(NOTE)
    assert seen["url"].endswith("/messages.json")
    assert seen["data"]["token"] == "app"
    assert seen["data"]["user"] == "usr"
    assert seen["data"]["priority"] == "1"
    assert seen["data"]["url"] == "https://example.com/x"
    assert seen["data"]["sound"] == "cashregister"


def test_pushover_requires_credentials():
    with pytest.raises(NotifierError):
        build_notifier({"type": "pushover", "token": "app"}).send(NOTE)


def test_webhook_sends_a_structured_payload(monkeypatch):
    seen = {}
    monkeypatch.setattr(webhook_module, "request", lambda url, **kwargs: seen.update(url=url, **kwargs) or "")
    build_notifier({"type": "webhook", "url": "https://hooks.example/x"}).send(NOTE)
    assert seen["json_body"]["title"] == NOTE.title
    assert seen["json_body"]["drops"] == [{"key": "demo:a"}]


def test_webhook_renders_a_template(monkeypatch):
    seen = {}
    monkeypatch.setattr(webhook_module, "request", lambda url, **kwargs: seen.update(**kwargs) or "")
    build_notifier(
        {"type": "webhook", "url": "https://hooks.slack.com/x", "template": {"text": "{title}\n{message}\n{url}"}}
    ).send(NOTE)
    text = seen["json_body"]["text"]
    assert text.startswith(NOTE.title)
    assert "https://example.com/x" in text
    assert json.dumps(seen["json_body"])  # stays valid JSON after substitution


def test_console_prints(capsys):
    build_notifier({"type": "console"}).send(NOTE)
    out = capsys.readouterr().out
    assert NOTE.title in out and "https://example.com/x" in out
