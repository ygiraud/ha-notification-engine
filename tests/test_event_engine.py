"""Unit tests for the pure event engine module."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
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

homeassistant_package = types.ModuleType("homeassistant")
homeassistant_package.__path__ = []
sys.modules.setdefault("homeassistant", homeassistant_package)

homeassistant_exceptions = types.ModuleType("homeassistant.exceptions")


class HomeAssistantError(Exception):
    """Minimal Home Assistant error stub for pure unit tests."""


homeassistant_exceptions.HomeAssistantError = HomeAssistantError
sys.modules.setdefault("homeassistant.exceptions", homeassistant_exceptions)

homeassistant_core = types.ModuleType("homeassistant.core")


class Event:
    """Minimal Home Assistant Event stub for pure unit tests."""


class HomeAssistant:
    """Minimal Home Assistant stub for type imports."""


class ServiceCall:
    """Minimal ServiceCall stub with data and target."""

    def __init__(self, data=None, target=None) -> None:
        self.data = data or {}
        self.target = target


ServiceResponse = dict

homeassistant_core.Event = Event
homeassistant_core.HomeAssistant = HomeAssistant
homeassistant_core.ServiceCall = ServiceCall
homeassistant_core.ServiceResponse = ServiceResponse
sys.modules.setdefault("homeassistant.core", homeassistant_core)

homeassistant_helpers = types.ModuleType("homeassistant.helpers")
homeassistant_helpers.__path__ = []
sys.modules.setdefault("homeassistant.helpers", homeassistant_helpers)

homeassistant_helpers_update_coordinator = types.ModuleType(
    "homeassistant.helpers.update_coordinator"
)


class DataUpdateCoordinator:
    """Minimal coordinator stub for type imports."""


homeassistant_helpers_update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
sys.modules.setdefault(
    "homeassistant.helpers.update_coordinator",
    homeassistant_helpers_update_coordinator,
)

_load_module("custom_components.notification_engine.const", PACKAGE_DIR / "const.py")
EVENT_ENGINE_MODULE = _load_module(
    "custom_components.notification_engine.event_engine",
    PACKAGE_DIR / "event_engine.py",
)
DELIVERY_MODULE = _load_module(
    "custom_components.notification_engine.delivery",
    PACKAGE_DIR / "delivery.py",
)
SERVICES_MODULE = _load_module(
    "custom_components.notification_engine.services",
    PACKAGE_DIR / "services.py",
)

NotificationEventEngine = EVENT_ENGINE_MODULE.NotificationEventEngine
NotificationEngineServices = SERVICES_MODULE.NotificationEngineServices
build_mobile_actions = EVENT_ENGINE_MODULE.build_mobile_actions
normalize_older_than_hours = EVENT_ENGINE_MODULE.normalize_older_than_hours
normalize_renotify_minutes = EVENT_ENGINE_MODULE.normalize_renotify_minutes
parse_actions = EVENT_ENGINE_MODULE.parse_actions
process_events_core = DELIVERY_MODULE.process_events_core
is_snooze_due_for_person = DELIVERY_MODULE.is_snooze_due_for_person
is_snoozed_for_person = DELIVERY_MODULE.is_snoozed_for_person
select_nearest_recipients = DELIVERY_MODULE.select_nearest_recipients
send_to_notify = DELIVERY_MODULE.send_to_notify
should_renotify_person = DELIVERY_MODULE.should_renotify_person
parse_older_than_hours = SERVICES_MODULE._parse_older_than_hours
extract_target_entities = SERVICES_MODULE._extract_target_entities
ttl_remaining_seconds = EVENT_ENGINE_MODULE.ttl_remaining_seconds


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


def test_extract_target_entities_supports_data_entity_id_and_target_dict() -> None:
    assert extract_target_entities(
        ServiceCall(data={"entity_id": ["person.yoan", "person.magalie"]})
    ) == ["person.yoan", "person.magalie"]
    assert extract_target_entities(
        ServiceCall(target={"entity_id": ["person.yoan"]})
    ) == ["person.yoan"]
    assert extract_target_entities(
        ServiceCall(data={"target": {"entity_id": "person.yoan"}})
    ) == ["person.yoan"]


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


def test_ttl_remaining_seconds_returns_zero_once_expired() -> None:
    now = datetime(2026, 5, 2, 7, 0, 0, tzinfo=timezone.utc)

    assert ttl_remaining_seconds(
        "2026-05-02T06:00:00+00:00",
        2,
        now,
    ) == 3600
    assert ttl_remaining_seconds(
        "2026-05-02T06:00:00+00:00",
        1,
        now,
    ) == 0


def test_normalize_and_parse_older_than_hours_reject_invalid_values() -> None:
    assert normalize_older_than_hours(None) is None
    assert normalize_older_than_hours("2.5") == 2.5
    assert parse_older_than_hours("1") == 1.0
    assert parse_older_than_hours("") is None
    assert parse_older_than_hours(0) is None
    assert parse_older_than_hours("bad") is None


def test_normalize_renotify_minutes_requires_positive_number() -> None:
    assert normalize_renotify_minutes(None) is None
    assert normalize_renotify_minutes("") is None
    assert normalize_renotify_minutes(30) == 30.0

    try:
        normalize_renotify_minutes(0)
    except ValueError as exc:
        assert str(exc) == "renotify_minutes must be a positive number"
    else:
        raise AssertionError("Expected ValueError for renotify_minutes=0")


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
            timeout_seconds=45,
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
            timeout_seconds=None,
        )
    )

    alert_payload = hass.services.calls[0][2]
    info_payload = hass.services.calls[1][2]

    assert alert_payload["data"]["ttl"] == 0
    assert alert_payload["data"]["timeout"] == 45
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


def test_create_event_stores_ttl_hours_and_deduplicates_on_it(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))

    first = engine.create_event(key="door", title="Door", message="Open", ttl_hours=2)
    duplicate = engine.create_event(key="door", title="Door", message="Open", ttl_hours=2)
    distinct = engine.create_event(key="door", title="Door", message="Open", ttl_hours=3)

    assert first["event"]["ttl_hours"] == 2.0
    assert duplicate["created"] is False
    assert distinct["created"] is True
    assert len(engine.load_events()) == 2


def test_create_event_stores_renotify_minutes_and_deduplicates_on_it(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))

    first = engine.create_event(
        key="door",
        strategy="asap",
        title="Door",
        message="Open",
        renotify_minutes=30,
    )
    duplicate = engine.create_event(
        key="door",
        strategy="asap",
        title="Door",
        message="Open",
        renotify_minutes=30,
    )
    distinct = engine.create_event(
        key="door",
        strategy="asap",
        title="Door",
        message="Open",
        renotify_minutes=60,
    )

    assert first["event"]["renotify_minutes"] == 30.0
    assert duplicate["created"] is False
    assert distinct["created"] is True
    assert len(engine.load_events()) == 2


def test_create_event_rejects_non_positive_ttl_hours(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))

    try:
        engine.create_event(key="door", title="Door", message="Open", ttl_hours=0)
    except ValueError as exc:
        assert str(exc) == "ttl_hours must be a positive number"
    else:
        raise AssertionError("Expected ValueError for ttl_hours=0")


def test_delete_event_by_key_deletes_first_pending_match_only(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    first = engine.create_event(key="door", title="Door", message="Open")["event"]
    second = engine.create_event(key="window", title="Window", message="Open")["event"]
    third = engine.create_event(key="door", title="Door", message="Still open")["event"]

    deleted = engine.delete_event_by_key("door")

    assert deleted is not None
    assert deleted["id"] == first["id"]
    assert [event["id"] for event in engine.load_events()] == [second["id"], third["id"]]

    missing = engine.delete_event_by_key("unknown")

    assert missing is None
    assert [event["id"] for event in engine.load_events()] == [second["id"], third["id"]]


def test_get_event_by_key_returns_first_pending_match_only(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    first = engine.create_event(key="door", title="Door", message="Open")["event"]
    second = engine.create_event(key="window", title="Window", message="Open")["event"]
    third = engine.create_event(key="door", title="Door", message="Still open")["event"]

    engine.ack_event(first["id"], "done")

    found = engine.get_event_by_key("door")
    missing = engine.get_event_by_key("unknown")

    assert found is not None
    assert found["id"] == third["id"]
    assert engine.get_event(second["id"]) is not None
    assert missing is None


def test_async_get_event_returns_by_key_or_id_and_errors(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    first = engine.create_event(key="door", title="Door", message="Open")["event"]
    second = engine.create_event(key="door", title="Door", message="Still open")["event"]
    engine.ack_event(first["id"], "done")

    class _Coordinator:
        async def async_request_refresh(self) -> None:
            return None

    class _Hass:
        async def async_add_executor_job(self, func, *args):
            return func(*args)

    handler = NotificationEngineServices(
        _Hass(),
        {"people": {}},
        engine,
        _Coordinator(),
    )

    by_key = asyncio.run(handler.async_get_event(ServiceCall(data={"key": "door"})))
    by_id = asyncio.run(handler.async_get_event(ServiceCall(data={"id": first["id"]})))
    missing_lookup = asyncio.run(handler.async_get_event(ServiceCall(data={"key": "unknown"})))
    missing_params = asyncio.run(handler.async_get_event(ServiceCall(data={})))

    assert by_key == {"ok": True, "event": engine.get_event(second["id"])}
    assert by_id == {"ok": True, "event": engine.get_event(first["id"])}
    assert missing_lookup == {"ok": False, "error": "event_not_found", "lookup": "unknown"}
    assert missing_params == {"ok": False, "error": "missing_key_or_id"}


def test_notify_person_updates_timestamp_and_appends_history_for_resend(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    created = engine.create_event(key="alarm", title="Alarm", message="Triggered")
    event_id = created["event"]["id"]

    engine.notify_person(event_id, "person.alice")
    engine.notify_person(event_id, "person.alice")

    stored = engine.load_events()[0]
    notified_entries = [item for item in stored["history"] if item.get("action") == "notified"]
    assert stored["notified_people"] == ["person.alice"]
    assert stored["notified_at"]["person.alice"]
    assert len(notified_entries) == 2


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

    assert result["purged"] is True
    assert len(result["removed"]) == 2
    assert result["remaining"] == 0
    assert engine.load_events() == []


def test_purge_events_filters_with_and_semantics(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    old_pending_alert = engine.create_event(
        key="old-pending-alert",
        title="One",
        message="First",
        strategy="alert",
    )["event"]
    old_done_alert = engine.create_event(
        key="old-done-alert",
        title="Two",
        message="Second",
        strategy="alert",
    )["event"]
    fresh_pending_alert = engine.create_event(
        key="fresh-pending-alert",
        title="Three",
        message="Third",
        strategy="alert",
    )["event"]
    old_pending_info = engine.create_event(
        key="old-pending-info",
        title="Four",
        message="Fourth",
        strategy="info",
    )["event"]

    engine.ack_event(old_done_alert["id"], "done")

    now = datetime(2026, 5, 2, 12, 0, 0, tzinfo=timezone.utc)
    events = engine.load_events()
    for event in events:
        if event["id"] in {
            old_pending_alert["id"],
            old_done_alert["id"],
            old_pending_info["id"],
        }:
            event["created_at"] = (now - timedelta(hours=3)).isoformat()
        elif event["id"] == fresh_pending_alert["id"]:
            event["created_at"] = (now - timedelta(minutes=30)).isoformat()
    engine.save_events(events)

    result = engine.purge_events(
        strategy="alert",
        status="pending",
        older_than_hours=2,
        now=now,
    )

    assert [event["id"] for event in result["removed"]] == [old_pending_alert["id"]]
    assert [event["id"] for event in engine.load_events()] == [
        old_done_alert["id"],
        fresh_pending_alert["id"],
        old_pending_info["id"],
    ]


def test_purge_events_with_age_filter_keeps_events_without_created_at(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    removable = engine.create_event(key="old", title="Old", message="Old")["event"]
    missing_created_at = engine.create_event(key="unknown", title="Unknown", message="Unknown")["event"]

    now = datetime(2026, 5, 2, 12, 0, 0, tzinfo=timezone.utc)
    events = engine.load_events()
    for event in events:
        if event["id"] == removable["id"]:
            event["created_at"] = (now - timedelta(hours=4)).isoformat()
        elif event["id"] == missing_created_at["id"]:
            event["created_at"] = ""
    engine.save_events(events)

    result = engine.purge_events(older_than_hours=2, now=now)

    assert [event["id"] for event in result["removed"]] == [removable["id"]]
    assert [event["id"] for event in engine.load_events()] == [missing_created_at["id"]]


def test_purge_expired_events_removes_only_elapsed_pending_events(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    expired = engine.create_event(key="expired", title="Expired", message="Old", ttl_hours=1)["event"]
    fresh = engine.create_event(key="fresh", title="Fresh", message="New", ttl_hours=4)["event"]
    no_ttl = engine.create_event(key="no-ttl", title="No TTL", message="Keep")["event"]

    events = engine.load_events()
    now = datetime.now(timezone.utc)
    for event in events:
        if event["id"] == expired["id"]:
            event["created_at"] = (now - timedelta(hours=2)).isoformat()
        elif event["id"] == fresh["id"]:
            event["created_at"] = (now - timedelta(minutes=30)).isoformat()
    engine.save_events(events)

    result = engine.purge_expired_events(now)

    assert [event["id"] for event in result["expired"]] == [expired["id"]]
    assert [event["id"] for event in engine.load_events()] == [fresh["id"], no_ttl["id"]]


def test_process_events_core_purges_expired_events_and_clears_tags(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    expired = engine.create_event(
        key="expired",
        title="Expired",
        message="Old",
        recipients=["person.alice"],
        ttl_hours=1,
    )["event"]
    active = engine.create_event(
        key="active",
        title="Active",
        message="Current",
        recipients=["person.alice"],
    )["event"]

    events = engine.load_events()
    now = datetime.now(timezone.utc)
    for event in events:
        if event["id"] == expired["id"]:
            event["created_at"] = (now - timedelta(hours=2)).isoformat()
    engine.save_events(events)

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

    class _States:
        def get(self, entity_id: str):
            return None

    class _Hass:
        def __init__(self) -> None:
            self.services = _Services()
            self.states = _States()

        async def async_add_executor_job(self, func, *args):
            return func(*args)

    hass = _Hass()
    domain_data = {
        "engine": engine,
        "people": {
            "person.alice": {
                "notify_service": "notify.mobile_app_alice",
                "enabled": True,
            }
        },
    }

    result = asyncio.run(process_events_core(hass, domain_data))

    assert result == {"ok": True, "sent": 0}
    assert [event["id"] for event in engine.load_events()] == [active["id"]]
    assert hass.services.calls == [
        (
            "notify",
            "mobile_app_alice",
            {"message": "clear_notification", "data": {"tag": expired["tag"]}},
            True,
        )
    ]


def test_process_events_core_sets_mobile_timeout_from_remaining_ttl(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    created = engine.create_event(
        key="ttl-send",
        strategy="alert",
        title="TTL send",
        message="Short-lived",
        recipients=["person.alice"],
        ttl_hours=1,
    )["event"]

    events = engine.load_events()
    now = datetime.now(timezone.utc)
    for event in events:
        if event["id"] == created["id"]:
            event["created_at"] = (now - timedelta(minutes=30)).isoformat()
    engine.save_events(events)

    class _State:
        def __init__(self, state: str) -> None:
            self.state = state

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

    class _States:
        def get(self, entity_id: str):
            if entity_id == "person.alice":
                return _State("home")
            return None

    class _Hass:
        def __init__(self) -> None:
            self.services = _Services()
            self.states = _States()

        async def async_add_executor_job(self, func, *args):
            return func(*args)

    hass = _Hass()
    domain_data = {
        "engine": engine,
        "people": {
            "person.alice": {
                "notify_service": "notify.mobile_app_alice",
                "enabled": True,
            }
        },
    }

    result = asyncio.run(process_events_core(hass, domain_data))

    assert result == {"ok": True, "sent": 1}
    notify_payload = hass.services.calls[0][2]
    assert notify_payload["data"]["timeout"] > 1700
    assert notify_payload["data"]["timeout"] <= 1800


def test_should_renotify_person_only_when_delay_elapsed() -> None:
    now = datetime(2026, 5, 2, 7, 0, 0, tzinfo=timezone.utc)
    event = {
        "renotify_minutes": 30,
        "notified_at": {"person.alice": "2026-05-02T06:20:00+00:00"},
    }

    assert should_renotify_person(event, "person.alice", now) is True
    assert should_renotify_person(event, "person.bob", now) is False
    assert should_renotify_person(
        {
            "renotify_minutes": 30,
            "notified_at": {"person.alice": "2026-05-02T06:40:00+00:00"},
        },
        "person.alice",
        now,
    ) is False


def test_snooze_helpers_distinguish_active_and_due_snooze() -> None:
    now = datetime(2026, 5, 2, 7, 0, 0, tzinfo=timezone.utc)
    active_event = {
        "snoozed_until": {"person.alice": "2026-05-02T07:15:00+00:00"},
    }
    due_event = {
        "snoozed_until": {"person.alice": "2026-05-02T06:45:00+00:00"},
    }

    assert is_snoozed_for_person(active_event, "person.alice", now) is True
    assert is_snooze_due_for_person(active_event, "person.alice", now) is False
    assert is_snoozed_for_person(due_event, "person.alice", now) is False
    assert is_snooze_due_for_person(due_event, "person.alice", now) is True


def test_snooze_event_sets_deadline_and_notify_person_clears_it(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    created = engine.create_event(key="door", title="Door", message="Open")["event"]
    now = datetime(2026, 5, 2, 7, 0, 0, tzinfo=timezone.utc)

    snoozed = engine.snooze_event(created["tag"], "person.alice", 30, now=now)

    assert snoozed is not None
    stored = engine.load_events()[0]
    assert stored["snoozed_until"]["person.alice"] == "2026-05-02T07:30:00+00:00"
    assert any(item.get("action") == "snoozed" for item in stored["history"])

    engine.notify_person(created["id"], "person.alice")

    after_notify = engine.load_events()[0]
    assert "person.alice" not in after_notify["snoozed_until"]


def test_process_events_core_renotifies_unacknowledged_asap_after_delay(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    created = engine.create_event(
        key="renotify",
        strategy="asap",
        title="Reminder",
        message="Do the thing",
        recipients=["person.alice"],
        renotify_minutes=30,
    )["event"]

    class _State:
        def __init__(self, state: str) -> None:
            self.state = state

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

    class _States:
        def get(self, entity_id: str):
            if entity_id == "person.alice":
                return _State("home")
            return None

    class _Hass:
        def __init__(self) -> None:
            self.services = _Services()
            self.states = _States()

        async def async_add_executor_job(self, func, *args):
            return func(*args)

    hass = _Hass()
    domain_data = {
        "engine": engine,
        "people": {
            "person.alice": {
                "notify_service": "notify.mobile_app_alice",
                "enabled": True,
            }
        },
    }

    first = asyncio.run(process_events_core(hass, domain_data))
    second = asyncio.run(process_events_core(hass, domain_data))

    events = engine.load_events()
    now = datetime.now(timezone.utc)
    for event in events:
        if event["id"] == created["id"]:
            event["notified_at"]["person.alice"] = (now - timedelta(minutes=31)).isoformat()
    engine.save_events(events)

    third = asyncio.run(process_events_core(hass, domain_data))
    stored = engine.load_events()[0]
    notified_entries = [item for item in stored["history"] if item.get("action") == "notified"]

    assert first == {"ok": True, "sent": 1}
    assert second == {"ok": True, "sent": 0}
    assert third == {"ok": True, "sent": 1}
    assert len(hass.services.calls) == 2
    assert stored["notified_people"] == ["person.alice"]
    assert len(notified_entries) == 2


def test_process_events_core_skips_active_snooze_and_resends_once_due(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    created = engine.create_event(
        key="snooze",
        strategy="alert",
        title="Reminder",
        message="Deferred",
        recipients=["person.alice"],
    )["event"]

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

    class _States:
        def get(self, entity_id: str):
            return None

    class _Hass:
        def __init__(self) -> None:
            self.services = _Services()
            self.states = _States()

        async def async_add_executor_job(self, func, *args):
            return func(*args)

    now = datetime.now(timezone.utc)
    events = engine.load_events()
    for event in events:
        if event["id"] == created["id"]:
            event["notified_people"] = ["person.alice"]
            event["notified_at"] = {
                "person.alice": (now - timedelta(minutes=5)).isoformat()
            }
            event["snoozed_until"] = {
                "person.alice": (now + timedelta(minutes=10)).isoformat()
            }
    engine.save_events(events)

    hass = _Hass()
    domain_data = {
        "engine": engine,
        "people": {
            "person.alice": {
                "notify_service": "notify.mobile_app_alice",
                "enabled": True,
            }
        },
    }

    skipped = asyncio.run(process_events_core(hass, domain_data))
    assert skipped == {"ok": True, "sent": 0}
    assert hass.services.calls == []

    events = engine.load_events()
    for event in events:
        if event["id"] == created["id"]:
            event["snoozed_until"] = {
                "person.alice": (now - timedelta(minutes=1)).isoformat()
            }
    engine.save_events(events)

    resent = asyncio.run(process_events_core(hass, domain_data))
    assert resent == {"ok": True, "sent": 1}
    assert len(hass.services.calls) == 1
    payload = hass.services.calls[0][2]
    assert payload["data"]["person_entity"] == "person.alice"
    assert payload["data"]["action_data"] == {"person_entity": "person.alice"}
    stored = engine.load_events()[0]
    assert "person.alice" not in stored["snoozed_until"]


def test_async_on_mobile_action_snoozes_for_acting_person(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    created = engine.create_event(
        key="snooze-action",
        title="Reminder",
        message="Tap snooze",
        recipients=["person.alice"],
        actions=[{"action": "SNOOZE_30", "title": "Later"}],
    )["event"]

    class _Coordinator:
        def __init__(self) -> None:
            self.refresh_calls = 0

        async def async_request_refresh(self) -> None:
            self.refresh_calls += 1

    class _Bus:
        def __init__(self) -> None:
            self.calls = []

        def async_fire(self, event_type: str, event_data: dict[str, object]) -> None:
            self.calls.append((event_type, event_data))

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
            self.bus = _Bus()
            self.services = _Services()

        async def async_add_executor_job(self, func, *args):
            return func(*args)

    coordinator = _Coordinator()
    hass = _Hass()
    handler = NotificationEngineServices(
        hass,
        {
            "people": {
                "person.alice": {
                    "notify_service": "notify.mobile_app_alice",
                    "enabled": True,
                }
            }
        },
        engine,
        coordinator,
    )

    mobile_event = Event()
    mobile_event.data = {
        "action": f"NOTIF_CUSTOM_{created['id']}_0",
        "person_entity": "person.alice",
    }

    asyncio.run(handler.async_on_mobile_action(mobile_event))

    stored = engine.load_events()[0]
    assert "person.alice" in stored["snoozed_until"]
    assert coordinator.refresh_calls == 1
    assert hass.bus.calls == []
    assert hass.services.calls == [
        (
            "notify",
            "mobile_app_alice",
            {"message": "clear_notification", "data": {"tag": created["tag"]}},
            True,
        )
    ]


def test_process_events_core_renotifies_alert_after_delay(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    created = engine.create_event(
        key="renotify-alert",
        strategy="alert",
        title="Critical reminder",
        message="Still pending",
        recipients=["person.alice"],
        renotify_minutes=30,
    )["event"]

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

    class _States:
        def get(self, entity_id: str):
            return None

    class _Hass:
        def __init__(self) -> None:
            self.services = _Services()
            self.states = _States()

        async def async_add_executor_job(self, func, *args):
            return func(*args)

    hass = _Hass()
    domain_data = {
        "engine": engine,
        "people": {
            "person.alice": {
                "notify_service": "notify.mobile_app_alice",
                "enabled": True,
            }
        },
    }

    first = asyncio.run(process_events_core(hass, domain_data))

    events = engine.load_events()
    now = datetime.now(timezone.utc)
    for event in events:
        if event["id"] == created["id"]:
            event["notified_at"]["person.alice"] = (now - timedelta(minutes=31)).isoformat()
    engine.save_events(events)

    second = asyncio.run(process_events_core(hass, domain_data))

    assert first == {"ok": True, "sent": 1}
    assert second == {"ok": True, "sent": 1}
    assert len(hass.services.calls) == 2


def test_process_events_core_info_never_renotifies_even_if_configured(tmp_path) -> None:
    engine = NotificationEventEngine(str(tmp_path / "events.json"))
    created = engine.create_event(
        key="renotify-info",
        strategy="info",
        title="FYI",
        message="Just so you know",
        recipients=["person.alice"],
        renotify_minutes=1,
    )["event"]

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

    class _States:
        def get(self, entity_id: str):
            return None

    class _Hass:
        def __init__(self) -> None:
            self.services = _Services()
            self.states = _States()

        async def async_add_executor_job(self, func, *args):
            return func(*args)

    events = engine.load_events()
    now = datetime.now(timezone.utc)
    for event in events:
        if event["id"] == created["id"]:
            event["notified_people"] = ["person.alice"]
            event["notified_at"] = {
                "person.alice": (now - timedelta(minutes=2)).isoformat()
            }
            event["history"].append(
                {
                    "at": now.isoformat(),
                    "action": "notified",
                    "person": "person.alice",
                }
            )
    engine.save_events(events)

    hass = _Hass()
    domain_data = {
        "engine": engine,
        "people": {
            "person.alice": {
                "notify_service": "notify.mobile_app_alice",
                "enabled": True,
            }
        },
    }

    first = asyncio.run(process_events_core(hass, domain_data))
    second = asyncio.run(process_events_core(hass, domain_data))

    assert first == {"ok": True, "sent": 0}
    assert second == {"ok": True, "sent": 0}
    assert hass.services.calls == []
    assert engine.load_events() == []
