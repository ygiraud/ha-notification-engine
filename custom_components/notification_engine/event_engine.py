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
    return normalized


def make_event(
    key: str,
    source: str = "",
    label: str = "",
    recipients: list[str] | None = None,
    strategy: str = "",
    title: str = "",
    message: str = "",
    actions: list[dict[str, str]] | None = None,
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
            "actions": actions or [],
            "notified_people": [],
            "history": [{"at": now, "action": "created"}],
        }
    )


class NotificationEventEngine:
    """Persistent event engine with atomic writes."""

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
        strategy: str = "",
        title: str = "",
        message: str = "",
        actions: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Create event with idempotent deduplication."""
        recipient_list = recipients or []
        action_list = actions or []
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
            ):
                return {"created": False, "event": event}

        event = make_event(
            key=key,
            source=source,
            label=label,
            recipients=recipient_list,
            strategy=strategy,
            title=title,
            message=message,
            actions=action_list,
        )
        events.append(event)
        self.save_events(events)
        return {"created": True, "event": event}

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
            notified = event.setdefault("notified_people", [])
            if person not in notified:
                now = utc_now_iso()
                notified.append(person)
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
        """Delete one event by id."""
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

    def purge_events(self) -> dict[str, Any]:
        """Delete all events."""
        self.save_events([])
        return {"purged": True, "remaining": 0}
