"""Delivery helpers for Notification Engine."""

from __future__ import annotations

import logging
from typing import Any

from .const import (
    CONF_AWAY_REMINDER_MAX_DISTANCE_M,
    CONF_AWAY_REMINDER_MODE,
    CONF_AWAY_REMINDER_TOLERANCE_M,
    CONF_PEOPLE,
    DEFAULT_AWAY_REMINDER_MAX_DISTANCE_M,
    DEFAULT_AWAY_REMINDER_MODE,
    DEFAULT_AWAY_REMINDER_TOLERANCE_M,
)
from .event_engine import NotificationEventEngine

_LOGGER = logging.getLogger(__name__)


def _service_parts(service_name: str) -> tuple[str, str] | None:
    if "." not in service_name:
        return None
    domain, service = service_name.split(".", 1)
    if not domain or not service:
        return None
    return domain, service


def people_config(domain_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return normalized people config from runtime domain data."""
    raw = domain_data.get(CONF_PEOPLE, {})
    if not isinstance(raw, dict):
        return {}
    return {str(key): value for key, value in raw.items() if isinstance(value, dict)}


def person_enabled(person_cfg: dict[str, Any]) -> bool:
    """Return whether one person config is enabled."""
    enabled = person_cfg.get("enabled")
    return True if enabled is None else bool(enabled)


def active_people_entities(people: dict[str, dict[str, Any]]) -> list[str]:
    """Return all enabled person entities from integration config."""
    return [person for person, person_cfg in people.items() if person_enabled(person_cfg)]


def event_recipients(event: dict[str, Any], people: dict[str, dict[str, Any]]) -> list[str]:
    """Return explicit recipients or all active people as fallback."""
    seen: set[str] = set()
    result: list[str] = []

    recipients = event.get("recipients", [])
    if not isinstance(recipients, list):
        recipients = []

    for item in recipients:
        person = str(item)
        if person and person not in seen:
            seen.add(person)
            result.append(person)

    if result:
        return result

    for person in active_people_entities(people):
        if person not in seen:
            seen.add(person)
            result.append(person)

    return result


def is_home(hass: Any, person_entity: str) -> bool:
    """Return whether the person entity is currently home."""
    state = hass.states.get(person_entity)
    return state is not None and state.state == "home"


def select_nearest_recipients(
    hass: Any,
    people: dict[str, dict[str, Any]],
    candidates: list[str],
    *,
    tolerance: float,
    max_distance: float,
) -> list[str]:
    """Select nearest recipients with tolerance and fallback to all candidates."""
    distances: list[tuple[str, float]] = []
    for person in candidates:
        sensor = str(people.get(person, {}).get("proximity_sensor", ""))
        if not sensor:
            continue
        sensor_state = hass.states.get(sensor)
        if sensor_state is None:
            continue
        try:
            distance = float(sensor_state.state)
        except (TypeError, ValueError):
            continue
        distances.append((person, distance))

    if not distances:
        return candidates

    nearest = min(distance for _, distance in distances)
    if nearest > max_distance:
        return candidates

    selected = [person for person, distance in distances if distance <= nearest + tolerance]
    return selected or candidates


async def send_to_notify(
    hass: Any,
    notify_service: str,
    *,
    title: str,
    message: str,
    tag: str,
    actions: list[dict[str, Any]],
    strategy: str = "",
) -> None:
    """Dispatch one notification to a Home Assistant notify service."""
    parts = _service_parts(notify_service)
    if parts is None:
        return
    domain, service = parts
    payload: dict[str, Any] = {
        "title": title,
        "message": message,
        "data": {"tag": tag, "group": tag},
    }
    if strategy == "info":
        payload["data"]["icon"] = "mdi:information"
    elif strategy == "alert":
        payload["data"]["icon"] = "mdi:alert-circle"
        payload["data"]["ttl"] = 0
        payload["data"]["priority"] = "high"
        payload["data"]["channel"] = "alarm_stream"
        payload["data"]["push"] = {
            "interruption-level": "critical",
            "sound": {
                "name": "default",
                "critical": 1,
                "volume": 1.0,
            },
        }
    if actions:
        payload["data"]["actions"] = actions[:3]
    await hass.services.async_call(domain, service, payload, blocking=True)


async def clear_tag_for_all(hass: Any, people: dict[str, dict[str, Any]], tag: str) -> None:
    """Clear one notification tag on every enabled mobile target."""
    for person_config in people.values():
        if not person_enabled(person_config):
            continue
        notify_service = str(person_config.get("notify_service", ""))
        parts = _service_parts(notify_service)
        if parts is None:
            continue
        domain, service = parts
        await hass.services.async_call(
            domain,
            service,
            {"message": "clear_notification", "data": {"tag": tag}},
            blocking=True,
        )


async def process_events_core(hass: Any, domain_data: dict[str, Any]) -> dict[str, Any]:
    """Deliver pending events according to their strategy and runtime config."""
    engine: NotificationEventEngine = domain_data["engine"]
    people = people_config(domain_data)
    mode = str(domain_data.get(CONF_AWAY_REMINDER_MODE, DEFAULT_AWAY_REMINDER_MODE))
    tolerance = float(domain_data.get(CONF_AWAY_REMINDER_TOLERANCE_M, DEFAULT_AWAY_REMINDER_TOLERANCE_M))
    max_distance = float(domain_data.get(CONF_AWAY_REMINDER_MAX_DISTANCE_M, DEFAULT_AWAY_REMINDER_MAX_DISTANCE_M))

    events = await hass.async_add_executor_job(engine.load_events)
    sent = 0

    for event in events:
        if event.get("status") != "pending":
            continue

        recipients = event_recipients(event, people)
        notified = set(event.get("notified_people", []))
        strategy = str(event.get("strategy", ""))

        if strategy in ("present", "asap"):
            selected = [person for person in recipients if is_home(hass, person)]
        elif strategy in ("alert", "info"):
            selected = recipients
        elif strategy == "away_reminder":
            if mode != "nearest":
                selected = recipients
            else:
                selected = select_nearest_recipients(
                    hass,
                    people,
                    recipients,
                    tolerance=tolerance,
                    max_distance=max_distance,
                )
        else:
            selected = []

        for person in selected:
            if person in notified:
                continue
            person_cfg = people.get(person, {})
            if not person_enabled(person_cfg):
                continue
            notify_service = str(person_cfg.get("notify_service", ""))
            if not notify_service:
                continue
            try:
                await send_to_notify(
                    hass,
                    notify_service,
                    title=str(event.get("title", "")),
                    message=str(event.get("message", "")),
                    tag=str(event.get("tag", "")),
                    actions=list(event.get("mobile_actions", [])),
                    strategy=strategy,
                )
            except Exception:  # noqa: BLE001
                _LOGGER.exception(
                    "Failed to send notification for event %s to %s via %s",
                    str(event.get("id", "")),
                    person,
                    notify_service,
                )
                continue
            await hass.async_add_executor_job(engine.notify_person, str(event.get("id", "")), person)
            notified.add(person)
            sent += 1

        if strategy == "info":
            deliverable = [
                person
                for person in recipients
                if person_enabled(people.get(person, {}))
                and bool(str(people.get(person, {}).get("notify_service", "")))
            ]
            if all(person in notified for person in deliverable):
                await hass.async_add_executor_job(engine.delete_event, str(event.get("id", "")))

    return {"ok": True, "sent": sent}
