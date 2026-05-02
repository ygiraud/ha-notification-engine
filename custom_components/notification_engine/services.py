"""Service and event-listener handlers for Notification Engine."""

from __future__ import annotations

import ast
import logging
from typing import Any

from homeassistant.core import Event, HomeAssistant, ServiceCall, ServiceResponse
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .delivery import (
    clear_tag_for_all,
    event_recipients,
    people_config,
    person_enabled,
    process_events_core,
    send_to_notify,
)
from .event_engine import NotificationEventEngine, parse_actions

_LOGGER = logging.getLogger(__name__)


def _normalize_entities(value: Any) -> list[str]:
    """Normalize entity inputs from service data or stored events.

    Accepts None, a bare string, a comma-separated string, a JSON/Python-literal
    list string, a plain list/tuple/set, or a HA target dict {entity_id: ...}.
    Always returns a flat list of non-empty entity id strings.
    """
    if value is None:
        return []

    if isinstance(value, dict):
        # HA service target payload often uses {"entity_id": ...}.
        return _normalize_entities(value.get("entity_id"))

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        # Support JSON/Python-list-like strings coming from UI payloads.
        if raw.startswith("[") and raw.endswith("]"):
            try:
                return _normalize_entities(ast.literal_eval(raw))
            except (ValueError, SyntaxError):
                pass
        return [item.strip() for item in raw.split(",") if item.strip()]

    if isinstance(value, (list, tuple, set)):
        normalized: list[str] = []
        for item in value:
            if isinstance(item, dict):
                entity_id = str(item.get("entity_id", "")).strip()
            else:
                entity_id = str(item).strip()
            if entity_id:
                normalized.append(entity_id)
        return normalized

    return []


def _extract_target_entities(call: ServiceCall) -> list[str]:
    """Extract recipient entity ids from the HA service call target field."""
    data = call.data if isinstance(call.data, dict) else {}
    if data.get("target") is not None:
        return _normalize_entities(data.get("target"))
    if data.get("entity_id") is not None:
        return _normalize_entities(data.get("entity_id"))
    return _normalize_entities(getattr(call, "target", None))


class NotificationEngineServices:
    """Encapsulates all HA service and event handlers for Notification Engine.

    Holds references to the shared runtime objects (hass, domain_data, engine,
    coordinator). domain_data is mutated in place by _apply_runtime_config so
    every handler always reads the latest configuration without needing a
    separate update path.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        domain_data: dict[str, Any],
        engine: NotificationEventEngine,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialise with the runtime dependencies shared across all handlers."""
        self._hass = hass
        self._domain_data = domain_data
        self._engine = engine
        self._coordinator = coordinator

    # ------------------------------------------------------------------
    # Service handlers
    # ------------------------------------------------------------------

    async def async_create_event(self, call: ServiceCall) -> ServiceResponse:
        """Create a notification event and trigger immediate delivery."""
        explicit_recipients = _extract_target_entities(call)
        resolved_recipients = event_recipients(
            {"recipients": explicit_recipients}, people_config(self._domain_data)
        )
        result = await self._hass.async_add_executor_job(
            self._engine.create_event,
            str(call.data.get("key", "")),
            str(call.data.get("source_entity", "")),
            str(call.data.get("context_label", "")),
            explicit_recipients,
            resolved_recipients,
            str(call.data.get("strategy", "")),
            str(call.data.get("title", "")),
            str(call.data.get("message", "")),
            parse_actions(call.data.get("actions", [])),
        )
        await process_events_core(self._hass, self._domain_data)
        await self._coordinator.async_request_refresh()
        return {"ok": True, **result}

    async def async_list_events(self, call: ServiceCall) -> ServiceResponse:
        """Return all stored notification events."""
        events = await self._hass.async_add_executor_job(self._engine.load_events)
        return {"ok": True, "events": events}

    async def async_send_info(self, call: ServiceCall) -> ServiceResponse:
        """Send a transient notification without creating a persistent event."""
        title = str(call.data.get("title", ""))
        message = str(call.data.get("message", ""))
        people = people_config(self._domain_data)
        recipients = event_recipients({"recipients": _extract_target_entities(call)}, people)
        sent = 0
        for person in recipients:
            person_cfg = people.get(person, {})
            if not person_enabled(person_cfg):
                continue
            notify_service = str(person_cfg.get("notify_service", ""))
            if not notify_service:
                continue
            await send_to_notify(
                self._hass,
                notify_service,
                title=title,
                message=message,
                tag=f"info_{person}",
                actions=[],
                strategy="info",
            )
            sent += 1
        await self._coordinator.async_request_refresh()
        return {"ok": True, "sent": sent}

    async def async_process_events(self, call: ServiceCall) -> ServiceResponse:
        """Manually trigger event processing and dispatch pending notifications."""
        result = await process_events_core(self._hass, self._domain_data)
        await self._coordinator.async_request_refresh()
        return result

    async def async_delete_event(self, call: ServiceCall) -> ServiceResponse:
        """Delete one event by logical key (recommended) or internal id."""
        key = str(call.data.get("key", "")).strip()
        event_id = str(call.data.get("id", "")).strip()
        if key:
            deleted = await self._hass.async_add_executor_job(
                self._engine.delete_event_by_key, key
            )
            lookup = key
        elif event_id:
            deleted = await self._hass.async_add_executor_job(
                self._engine.delete_event, event_id
            )
            lookup = event_id
        else:
            return {"ok": False, "error": "missing_key_or_id"}
        if deleted is None:
            return {"ok": False, "error": "event_not_found", "lookup": lookup}
        await clear_tag_for_all(
            self._hass,
            people_config(self._domain_data),
            str(deleted.get("tag", f"notif_{deleted.get('id', '')}")),
        )
        await self._coordinator.async_request_refresh()
        return {"ok": True, "deleted": True, "event": deleted}

    async def async_purge_events(self, call: ServiceCall) -> ServiceResponse:
        """Delete all stored events and clear their tags on every device."""
        events_before = await self._hass.async_add_executor_job(self._engine.load_events)
        result = await self._hass.async_add_executor_job(self._engine.purge_events)
        tags_to_clear = {
            str(event.get("tag", ""))
            for event in events_before
            if isinstance(event, dict) and str(event.get("tag", ""))
        }
        for tag in tags_to_clear:
            await clear_tag_for_all(self._hass, people_config(self._domain_data), tag)
        await self._coordinator.async_request_refresh()
        return {"ok": True, **result}

    # ------------------------------------------------------------------
    # Event listeners
    # ------------------------------------------------------------------

    async def async_on_mobile_action(self, event: Event) -> None:
        """Handle mobile app notification action events (DONE and custom actions)."""
        action_id = str(event.data.get("action", ""))
        if not (
            action_id.startswith("NOTIF_EVENT_DONE_")
            or action_id.startswith("NOTIF_CUSTOM_")
        ):
            return

        if action_id.startswith("NOTIF_EVENT_DONE_"):
            event_id = action_id.replace("NOTIF_EVENT_DONE_", "", 1)
            event_obj = await self._hass.async_add_executor_job(
                self._engine.delete_event, event_id
            )
            if event_obj is not None:
                await clear_tag_for_all(
                    self._hass,
                    people_config(self._domain_data),
                    str(event_obj.get("tag", f"notif_{event_id}")),
                )
                await self._coordinator.async_request_refresh()
            return

        stripped = action_id.replace("NOTIF_CUSTOM_", "", 1)
        parts = stripped.rsplit("_", 1)
        if len(parts) != 2:
            return
        event_id, index_raw = parts
        try:
            action_index = int(index_raw)
        except ValueError:
            return
        events = await self._hass.async_add_executor_job(self._engine.load_events)
        event_obj = next(
            (item for item in events if str(item.get("id", "")) == event_id), None
        )
        if event_obj is None:
            return
        actions = event_obj.get("actions", [])
        custom = (
            actions[action_index]
            if isinstance(actions, list) and len(actions) > action_index
            else {}
        )
        self._hass.bus.async_fire(
            "notification_engine_custom_action",
            {
                "id": event_id,
                "action": str(custom.get("action", "")),
                "title": str(custom.get("title", "")),
                "source_entity": str(event_obj.get("source_entity", "")),
                "tag": str(event_obj.get("tag", f"notif_{event_id}")),
            },
        )

    async def async_on_state_changed(self, event: Event) -> None:
        """Trigger event processing when a tracked person arrives home."""
        entity_id = str(event.data.get("entity_id", ""))
        if not entity_id.startswith("person."):
            return
        people = set(people_config(self._domain_data).keys())
        if entity_id not in people:
            return
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if new_state is None or new_state.state != "home":
            return
        if old_state is not None and old_state.state == "home":
            return
        await process_events_core(self._hass, self._domain_data)
