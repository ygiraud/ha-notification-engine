"""Unit tests for the pure event engine module."""

from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import types


ROOT_DIR = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT_DIR / "custom_components" / "notification_engine"


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


custom_components_package = types.ModuleType("custom_components")
custom_components_package.__path__ = [str(ROOT_DIR / "custom_components")]
sys.modules.setdefault("custom_components", custom_components_package)

notification_package = types.ModuleType("custom_components.notification_engine")
notification_package.__path__ = [str(PACKAGE_DIR)]
sys.modules.setdefault("custom_components.notification_engine", notification_package)

_load_module("custom_components.notification_engine.const", PACKAGE_DIR / "const.py")
EVENT_ENGINE_MODULE = _load_module(
    "custom_components.notification_engine.event_engine",
    PACKAGE_DIR / "event_engine.py",
)
DELIVERY_MODULE = _load_module(
    "custom_components.notification_engine.delivery",
    PACKAGE_DIR / "delivery.py",
)

NotificationEventEngine = EVENT_ENGINE_MODULE.NotificationEventEngine
build_mobile_actions = EVENT_ENGINE_MODULE.build_mobile_actions
parse_actions = EVENT_ENGINE_MODULE.parse_actions
select_nearest_recipients = DELIVERY_MODULE.select_nearest_recipients
send_to_notify = DELIVERY_MODULE.send_to_notify


def test_parse_actions_accepts_json_and_python_literal() -> None:
    payload = '[{"action":"DONE","title":"OK"},{"action":"OPEN","title":"Open"}]'

    assert parse_actions(payload) == [
        {"action": "DONE", "title": "OK"},
        {"action": "OPEN", "title": "Open"},
    ]
    assert parse_actions(str(json.loads(payload))) == [
        {"action": "DONE", "title": "OK"},
        {"action": "OPEN", "title": "Open"},
    ]


def test_parse_actions_ignores_invalid_payloads() -> None:
    assert parse_actions(None) == []
    assert parse_actions("") == []
    assert parse_actions("invalid") == []
    assert parse_actions([{"action": "DONE", "title": "OK"}, "bad"]) == [
        {"action": "DONE", "title": "OK"}
    ]


def test_build_mobile_actions_maps_done_and_custom_actions() -> None:
    assert build_mobile_actions(
        "evt_123",
        [
            {"action": "DONE", "title": "Done"},
            {"action": "OPEN", "title": "Open"},
        ],
    ) == [
        {"action": "NOTIF_EVENT_DONE_evt_123", "title": "Done"},
        {"action": "NOTIF_CUSTOM_evt_123_1", "title": "Open"},
    ]


def test_select_nearest_recipients_uses_tolerance_and_fallback() -> None:
    class _State:
        def __init__(self, state: str) -> None:
            self.state = state

    class _States:
        def __init__(self, mapping) -> None:
            self._mapping = mapping

        def get(self, entity_id: str):
            return self._mapping.get(entity_id)

    class _Hass:
        def __init__(self, mapping) -> None:
            self.states = _States(mapping)

    people = {
        "person.alice": {"proximity_sensor": "sensor.alice_distance"},
        "person.bob": {"proximity_sensor": "sensor.bob_distance"},
        "person.carol": {"proximity_sensor": "sensor.carol_distance"},
    }
    hass = _Hass(
        {
            "sensor.alice_distance": _State("100"),
            "sensor.bob_distance": _State("150"),
            "sensor.carol_distance": _State("9000"),
        }
    )

    assert select_nearest_recipients(
        hass,
        people,
        ["person.alice", "person.bob", "person.carol"],
        tolerance=75.0,
        max_distance=1000.0,
    ) == ["person.alice", "person.bob"]

    assert select_nearest_recipients(
        hass,
        people,
        ["person.alice", "person.bob"],
        tolerance=10.0,
        max_distance=50.0,
    ) == ["person.alice", "person.bob"]


def test_send_to_notify_adds_critical_mobile_payload_only_for_alert_strategy() -> None:
    class _Services:
        def __init__(self) -> None:
            self.calls = []

        async def async_call(
            self,
            domain: str,
            service: str,
            payload: dict[str, object],
            *,
            blocking: bool,
        ) -> None:
            self.calls.append((domain, service, payload, blocking))

    class _Hass:
        def __init__(self) -> None:
            self.services = _Services()

    hass = _Hass()

    asyncio.run(
        send_to_notify(
            hass,
            "notify.mobile_app_alice",
            title="Alert",
            message="Immediate action required",
            tag="alert-tag",
            actions=[],
            strategy="alert",
        )
    )
    asyncio.run(
        send_to_notify(
            hass,
            "notify.mobile_app_alice",
            title="Info",
            message="FYI",
            tag="info-tag",
            actions=[],
            strategy="info",
        )
    )

    alert_payload = hass.services.calls[0][2]
    info_payload = hass.services.calls[1][2]

    assert alert_payload["data"]["ttl"] == 0
    assert alert_payload["data"]["priority"] == "high"
    assert alert_payload["data"]["channel"] == "alarm_stream"
    assert alert_payload["data"]["push"] == {
        "interruption-level": "critical",
        "sound": {
            "name": "default",
            "critical": 1,
            "volume": 1.0,
        },
    }
    assert "ttl" not in info_payload["data"]
    assert "priority" not in info_payload["data"]
    assert "channel" not in info_payload["data"]
    assert "push" not in info_payload["data"]


def test_create_event_is_idempotent_for_same_pending_payload(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))

    first = engine.create_event(
        key="washing_machine_done",
        source="sensor.washing_machine",
        label="laundry",
        recipients=["person.alice"],
        strategy="alert",
        title="Machine done",
        message="Laundry is ready",
        actions=[{"action": "DONE", "title": "OK"}],
    )
    second = engine.create_event(
        key="washing_machine_done",
        source="sensor.washing_machine",
        label="laundry",
        recipients=["person.alice"],
        strategy="alert",
        title="Machine done",
        message="Laundry is ready",
        actions=[{"action": "DONE", "title": "OK"}],
    )

    assert first["created"] is True
    assert second["created"] is False
    assert second["event"]["id"] == first["event"]["id"]
    assert len(engine.load_events()) == 1


def test_create_event_recreates_after_deletion(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    created = engine.create_event(key="door", title="Door", message="Open")
    event_id = created["event"]["id"]

    deleted = engine.delete_event(event_id)
    recreated = engine.create_event(key="door", title="Door", message="Open")

    assert deleted is not None
    assert recreated["created"] is True
    assert recreated["event"]["id"] != event_id


def test_notify_person_updates_history_once(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    created = engine.create_event(key="alarm", title="Alarm", message="Triggered")
    event_id = created["event"]["id"]

    engine.notify_person(event_id, "person.alice")
    engine.notify_person(event_id, "person.alice")

    stored = engine.load_events()[0]
    notified_entries = [item for item in stored["history"] if item.get("action") == "notified"]
    assert stored["notified_people"] == ["person.alice"]
    assert len(notified_entries) == 1


def test_create_event_keeps_explicit_recipients_empty_but_stores_resolved_fallback(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))

    created = engine.create_event(
        key="fallback",
        recipients=[],
        resolved_recipients=["person.alice", "person.bob"],
        title="Fallback",
        message="All active people",
    )

    stored = created["event"]
    assert stored["recipients"] == []
    assert stored["resolved_recipients"] == ["person.alice", "person.bob"]
    assert engine.load_events()[0]["resolved_recipients"] == ["person.alice", "person.bob"]


def test_ack_and_cleanup_preserve_current_internal_behavior(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    first = engine.create_event(key="event-1", title="One", message="First")["event"]
    second = engine.create_event(key="event-2", title="Two", message="Second")["event"]

    acked = engine.ack_event(first["id"], "done")
    cleanup = engine.cleanup_events()

    assert acked is not None
    assert acked["status"] == "done"
    assert any(item.get("action") == "done" for item in acked["history"])
    assert cleanup == {"removed": [first["id"]], "remaining": 1}
    assert [event["id"] for event in engine.load_events()] == [second["id"]]


def test_purge_events_clears_all_events(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    engine.create_event(key="event-1", title="One", message="First")
    engine.create_event(key="event-2", title="Two", message="Second")

    result = engine.purge_events()

    assert result == {"purged": True, "remaining": 0}
    assert engine.load_events() == []
