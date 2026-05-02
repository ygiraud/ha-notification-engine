"""Core event engine logic for Notification Engine integration."""

from __future__ import annotations

import ast
import json
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def parse_created_at(value: Any) -> datetime | None:
    """Parse one stored event creation timestamp."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_ttl_hours(value: Any) -> float | None:
    """Normalize ttl_hours to a positive float or None."""
    if value in (None, ""):
        return None
    try:
        ttl_hours = float(value)
    except (TypeError, ValueError):
        raise ValueError("ttl_hours must be a positive number") from None
    if ttl_hours <= 0:
        raise ValueError("ttl_hours must be a positive number")
    return ttl_hours


def normalize_renotify_minutes(value: Any) -> float | None:
    """Normalize renotify_minutes to a positive float or None."""
    if value in (None, ""):
        return None
    try:
        renotify_minutes = float(value)
    except (TypeError, ValueError):
        raise ValueError("renotify_minutes must be a positive number") from None
    if renotify_minutes <= 0:
        raise ValueError("renotify_minutes must be a positive number")
    return renotify_minutes


def ttl_remaining_seconds(
    created_at: Any,
    ttl_hours: Any,
    now: datetime | None = None,
) -> int | None:
    """Return remaining TTL in whole seconds for one event."""
    normalized_ttl_hours = normalize_ttl_hours(ttl_hours)
    if normalized_ttl_hours is None:
        return None
    parsed_created_at = parse_created_at(created_at)
    if parsed_created_at is None:
        return None
    current_time = now or datetime.now(timezone.utc)
    expires_at = parsed_created_at.timestamp() + (normalized_ttl_hours * 3600)
    return max(0, int(expires_at - current_time.timestamp()))


def normalize_older_than_hours(value: Any) -> float | None:
    """Normalize older_than_hours to a positive float or None."""
    if value in (None, ""):
        return None
    try:
        older_than_hours = float(value)
    except (TypeError, ValueError):
        raise ValueError("older_than_hours must be a positive number") from None
    if older_than_hours <= 0:
        raise ValueError("older_than_hours must be a positive number")
    return older_than_hours


def normalize_notified_at(value: Any) -> dict[str, str]:
    """Normalize per-person notification timestamps."""
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, str] = {}
    for person, notified_at in value.items():
        person_key = str(person).strip()
        if not person_key:
            continue
        parsed_notified_at = parse_created_at(notified_at)
        if parsed_notified_at is None:
            continue
        normalized[person_key] = parsed_notified_at.isoformat()
    return normalized

def parse_actions(value: Any) -> list[dict[str, str]]:
    """Parse actions from list/dict-like inputs, JSON or Python literal strings."""

    def normalize(raw: Any) -> list[dict[str, str]] | None:
        if not isinstance(raw, list):
            return None
        parsed: list[dict[str, str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            parsed.append(
                {
                    "action": str(item.get("action", "")),
                    "title": str(item.get("title", "")),
                }
            )
        return parsed

    normalized = normalize(value)
    if normalized is not None:
        return normalized

    if not isinstance(value, str) or not value.strip():
        return []

    current: Any = value
    for _ in range(2):
        if not isinstance(current, str):
            break
        try:
            current = json.loads(current)
        except (json.JSONDecodeError, TypeError, ValueError):
            break
        normalized = normalize(current)
        if normalized is not None:
            return normalized

    try:
        normalized = normalize(ast.literal_eval(value))
        if normalized is not None:
            return normalized
    except (ValueError, SyntaxError):
        pass

    return []


def build_tag(event_id: str) -> str:
    """Build notification tag from event id."""
    return f"notif_{event_id}"


def build_mobile_actions(event_id: str, actions: list[dict[str, str]] | None) -> list[dict[str, str]]:
    """Compute Home Assistant mobile action ids from logical actions."""
    mobile_actions: list[dict[str, str]] = []
    for index, item in enumerate(actions or []):
        raw_action = str(item.get("action", ""))
        title = str(item.get("title", ""))
        if raw_action == "DONE":
            action_id = f"NOTIF_EVENT_DONE_{event_id}"
        else:
            action_id = f"NOTIF_CUSTOM_{event_id}_{index}"
        mobile_actions.append({"action": action_id, "title": title})
    return mobile_actions


def normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    """Normalize event payload and recompute mobile actions."""
    normalized = dict(event)
    event_id = str(normalized.get("id", ""))
    raw_actions = normalized.get("actions", [])
    actions = parse_actions(raw_actions)
    normalized["actions"] = actions
    normalized["mobile_actions"] = build_mobile_actions(event_id, actions)
    resolved_recipients = normalized.get("resolved_recipients", [])
    if not isinstance(resolved_recipients, list):
        resolved_recipients = []
    normalized["resolved_recipients"] = [str(person) for person in resolved_recipients if str(person)]
    normalized["ttl_hours"] = normalize_ttl_hours(normalized.get("ttl_hours"))
    normalized["renotify_minutes"] = normalize_renotify_minutes(normalized.get("renotify_minutes"))
    normalized["notified_at"] = normalize_notified_at(normalized.get("notified_at"))
    return normalized


def make_event(
    key: str,
    source: str = "",
    label: str = "",
    recipients: list[str] | None = None,
    resolved_recipients: list[str] | None = None,
    strategy: str = "",
    title: str = "",
    message: str = "",
    actions: list[dict[str, str]] | None = None,
    ttl_hours: float | None = None,
    renotify_minutes: float | None = None,
) -> dict[str, Any]:
    """Create a new normalized pending event."""
    event_id = f"evt_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    now = utc_now_iso()
    return normalize_event(
        {
            "id": event_id,
            "key": key,
            "strategy": strategy,
            "status": "pending",
            "title": title,
            "message": message,
            "tag": build_tag(event_id),
            "created_at": now,
            "updated_at": now,
            "source_entity": source,
            "context_label": label,
            "recipients": recipients or [],
            "resolved_recipients": resolved_recipients or [],
            "actions": actions or [],
            "ttl_hours": ttl_hours,
            "renotify_minutes": renotify_minutes,
            "notified_people": [],
            "notified_at": {},
            "history": [{"at": now, "action": "created"}],
        }
    )


class NotificationEventEngine:
    """Persistent, file-backed notification event store.

    All writes are atomic: events are serialized to a temporary file then
    renamed over the target path, so a crash mid-write never corrupts the
    store.

    The store is a JSON array of event dicts at events_path
    (.storage/notification_engine_events.json).  Every event is normalized
    on read via normalize_event(), which re-derives computed fields
    (mobile_actions, resolved_recipients) so the on-disk format stays lean.

    Thread-safety: methods are designed to be called from executor threads
    (via hass.async_add_executor_job). Each call does a full read-modify-write
    cycle; concurrent writes are therefore not safe — callers must serialize
    access through the HA event loop.
    """

    def __init__(self, events_path: str) -> None:
        self._events_path = events_path
        self._base_dir = os.path.dirname(events_path)

    def load_events(self) -> list[dict[str, Any]]:
        """Load and normalize events."""
        if not os.path.exists(self._events_path):
            return []

        with open(self._events_path, "r", encoding="utf-8") as file:
            raw = file.read().strip()
            if not raw:
                return []
            data = json.loads(raw)

        if not isinstance(data, list):
            raise ValueError("events.json must contain a JSON list")

        return [normalize_event(event) for event in data if isinstance(event, dict)]

    def save_events(self, events: list[dict[str, Any]]) -> None:
        """Atomically persist events list."""
        os.makedirs(self._base_dir, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix="events_", suffix=".json.tmp", dir=self._base_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(events, file, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._events_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def create_event(
        self,
        key: str,
        source: str = "",
        label: str = "",
        recipients: list[str] | None = None,
        resolved_recipients: list[str] | None = None,
        strategy: str = "",
        title: str = "",
        message: str = "",
        actions: list[dict[str, str]] | None = None,
        ttl_hours: float | None = None,
        renotify_minutes: float | None = None,
    ) -> dict[str, Any]:
        """Create event with idempotent deduplication."""
        recipient_list = recipients or []
        action_list = actions or []
        normalized_ttl_hours = normalize_ttl_hours(ttl_hours)
        normalized_renotify_minutes = normalize_renotify_minutes(renotify_minutes)
        events = self.load_events()

        for event in events:
            if (
                event.get("status") == "pending"
                and event.get("key") == key
                and event.get("source_entity", "") == source
                and event.get("context_label", "") == label
                and event.get("recipients", []) == recipient_list
                and event.get("strategy", "") == strategy
                and event.get("title", "") == title
                and event.get("message", "") == message
                and event.get("actions", []) == action_list
                and event.get("ttl_hours") == normalized_ttl_hours
                and event.get("renotify_minutes") == normalized_renotify_minutes
            ):
                return {"created": False, "event": event}

        event = make_event(
            key=key,
            source=source,
            label=label,
            recipients=recipient_list,
            resolved_recipients=resolved_recipients or [],
            strategy=strategy,
            title=title,
            message=message,
            actions=action_list,
            ttl_hours=normalized_ttl_hours,
            renotify_minutes=normalized_renotify_minutes,
        )
        events.append(event)
        self.save_events(events)
        return {"created": True, "event": event}

    def purge_expired_events(self, now: datetime | None = None) -> dict[str, Any]:
        """Delete pending events whose ttl_hours has elapsed."""
        current_time = now or datetime.now(timezone.utc)
        events = self.load_events()
        kept: list[dict[str, Any]] = []
        expired: list[dict[str, Any]] = []

        for event in events:
            ttl_hours = event.get("ttl_hours")
            created_at = parse_created_at(event.get("created_at"))
            if (
                event.get("status") == "pending"
                and ttl_hours is not None
                and created_at is not None
                and created_at.timestamp() + (float(ttl_hours) * 3600) <= current_time.timestamp()
            ):
                expired.append(event)
                continue
            kept.append(event)

        if expired:
            self.save_events(kept)

        return {"expired": expired, "remaining": len(kept)}

    def ack_event(self, event_id: str, status: str = "done") -> dict[str, Any] | None:
        """Mark one event with a status."""
        events = self.load_events()
        for event in events:
            if event.get("id") != event_id:
                continue
            now = utc_now_iso()
            event["status"] = status
            event["updated_at"] = now
            event.setdefault("history", []).append({"at": now, "action": status})
            self.save_events(events)
            return event
        return None

    def notify_person(self, event_id: str, person: str) -> dict[str, Any] | None:
        """Mark person as notified for one event."""
        events = self.load_events()
        for event in events:
            if event.get("id") != event_id:
                continue
            now = utc_now_iso()
            notified = event.setdefault("notified_people", [])
            if person not in notified:
                notified.append(person)
            notified_at = normalize_notified_at(event.get("notified_at"))
            notified_at[person] = now
            event["notified_at"] = notified_at
            event["updated_at"] = now
            event.setdefault("history", []).append({"at": now, "action": "notified", "person": person})
            self.save_events(events)
            return event
        return None

    def cleanup_events(self) -> dict[str, Any]:
        """Remove all non-pending events."""
        events = self.load_events()
        kept: list[dict[str, Any]] = []
        removed: list[str] = []
        for event in events:
            if event.get("status") == "pending":
                kept.append(event)
            else:
                removed.append(str(event.get("id", "")))
        self.save_events(kept)
        return {"removed": removed, "remaining": len(kept)}

    def delete_event(self, event_id: str) -> dict[str, Any] | None:
        """Delete one event by internal id."""
        events = self.load_events()
        kept: list[dict[str, Any]] = []
        deleted_event: dict[str, Any] | None = None
        for event in events:
            if event.get("id") == event_id:
                deleted_event = event
            else:
                kept.append(event)
        if deleted_event is None:
            return None
        self.save_events(kept)
        return deleted_event

    def delete_event_by_key(self, key: str) -> dict[str, Any] | None:
        """Delete the first pending event matching a logical key."""
        events = self.load_events()
        kept: list[dict[str, Any]] = []
        deleted_event: dict[str, Any] | None = None
        for event in events:
            if deleted_event is None and event.get("key") == key and event.get("status") == "pending":
                deleted_event = event
            else:
                kept.append(event)
        if deleted_event is None:
            return None
        self.save_events(kept)
        return deleted_event

    def purge_events(
        self,
        strategy: str | None = None,
        status: str | None = None,
        older_than_hours: float | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Delete events matching the optional filters."""
        normalized_strategy = str(strategy or "").strip()
        normalized_status = str(status or "").strip()
        normalized_older_than_hours = normalize_older_than_hours(older_than_hours)
        current_time = now or datetime.now(timezone.utc)

        events = self.load_events()
        kept: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []

        for event in events:
            matches = True

            if normalized_strategy and str(event.get("strategy", "")) != normalized_strategy:
                matches = False

            if normalized_status and str(event.get("status", "")) != normalized_status:
                matches = False

            if normalized_older_than_hours is not None:
                created_at = parse_created_at(event.get("created_at"))
                if created_at is None:
                    matches = False
                else:
                    age_seconds = current_time.timestamp() - created_at.timestamp()
                    if age_seconds < normalized_older_than_hours * 3600:
                        matches = False

            if matches:
                removed.append(event)
            else:
                kept.append(event)

        if removed:
            self.save_events(kept)

        return {
            "purged": True,
            "removed": removed,
            "remaining": len(kept),
        }
