"""Notification Engine integration."""

from __future__ import annotations

import ast
from datetime import timedelta
import logging
from pathlib import Path
from typing import Any

from homeassistant.components import frontend
from homeassistant.components.lovelace import dashboard as lovelace_dashboard
from homeassistant.components.lovelace.const import (
    DOMAIN as LOVELACE_DOMAIN,
    LOVELACE_DATA,
    MODE_YAML as LOVELACE_MODE_YAML,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import voluptuous as vol

from .const import (
    CONF_AWAY_REMINDER_MAX_DISTANCE_M,
    CONF_AWAY_REMINDER_MODE,
    CONF_AWAY_REMINDER_TOLERANCE_M,
    CONF_INSTALL_DASHBOARD,
    CONF_PEOPLE,
    DEFAULT_AWAY_REMINDER_MAX_DISTANCE_M,
    DEFAULT_AWAY_REMINDER_MODE,
    DEFAULT_AWAY_REMINDER_TOLERANCE_M,
    DEFAULT_INSTALL_DASHBOARD,
    DOMAIN,
    EVENTS_FILENAME,
    SERVICE_ACK_EVENT,
    SERVICE_CLEANUP_EVENTS,
    SERVICE_CREATE_EVENT,
    SERVICE_DELETE_EVENT,
    SERVICE_LIST_EVENTS,
    SERVICE_NOTIFY_PERSON,
    SERVICE_PROCESS_EVENTS,
    SERVICE_PURGE_EVENTS,
)
from .event_engine import NotificationEventEngine, parse_actions

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "text"]
SERVICE_SEND_INFO = "send_info"
DASHBOARD_FILENAME = "notification_engine_dashboard.yaml"
DASHBOARD_SOURCE = "dashboards/notification_engine_dashboard.yaml"
DASHBOARD_URL_PATH = "notification-engine"
DASHBOARD_TITLE = "Notification Engine"
DASHBOARD_ICON = "mdi:message-badge"
LOVELACE_CONF_FILENAME = "filename"
LOVELACE_CONF_ICON = "icon"
LOVELACE_CONF_MODE = "mode"
LOVELACE_CONF_REQUIRE_ADMIN = "require_admin"
LOVELACE_CONF_SHOW_IN_SIDEBAR = "show_in_sidebar"
LOVELACE_CONF_TITLE = "title"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_PEOPLE, default={}): dict,
                vol.Optional(CONF_AWAY_REMINDER_MODE, default=DEFAULT_AWAY_REMINDER_MODE): cv.string,
                vol.Optional(
                    CONF_AWAY_REMINDER_TOLERANCE_M,
                    default=DEFAULT_AWAY_REMINDER_TOLERANCE_M,
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_AWAY_REMINDER_MAX_DISTANCE_M,
                    default=DEFAULT_AWAY_REMINDER_MAX_DISTANCE_M,
                ): vol.Coerce(float),
                vol.Optional(CONF_INSTALL_DASHBOARD, default=DEFAULT_INSTALL_DASHBOARD): cv.boolean,
            },
            extra=vol.ALLOW_EXTRA,
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def _service_parts(service_name: str) -> tuple[str, str] | None:
    if "." not in service_name:
        return None
    domain, service = service_name.split(".", 1)
    if not domain or not service:
        return None
    return domain, service


def _people_config(domain_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = domain_data.get(CONF_PEOPLE, {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def _person_enabled(person_cfg: dict[str, Any]) -> bool:
    enabled = person_cfg.get("enabled")
    return True if enabled is None else bool(enabled)


def _normalize_entities(value: Any) -> list[str]:
    """Normalize entity inputs from service data or stored events."""
    if value is None:
        return []

    if isinstance(value, dict):
        # Home Assistant service target payload often uses {"entity_id": ...}.
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


def _active_people_entities(people: dict[str, dict[str, Any]]) -> list[str]:
    """Return all enabled person entities from integration config."""
    return [person for person, person_cfg in people.items() if _person_enabled(person_cfg)]


def _extract_target_entities(data: dict[str, Any]) -> list[str]:
    """Extract recipients from Home Assistant standard service target."""
    return _normalize_entities(data.get("target"))


def _entry_config(entry: ConfigEntry) -> dict[str, Any]:
    merged = dict(entry.data)
    merged.update(entry.options)
    return merged


def _apply_runtime_config(domain_data: dict[str, Any], cfg: dict[str, Any]) -> None:
    domain_data[CONF_PEOPLE] = cfg.get(CONF_PEOPLE, {})
    domain_data[CONF_AWAY_REMINDER_MODE] = str(cfg.get(CONF_AWAY_REMINDER_MODE, DEFAULT_AWAY_REMINDER_MODE))
    domain_data[CONF_AWAY_REMINDER_TOLERANCE_M] = float(
        cfg.get(CONF_AWAY_REMINDER_TOLERANCE_M, DEFAULT_AWAY_REMINDER_TOLERANCE_M)
    )
    domain_data[CONF_AWAY_REMINDER_MAX_DISTANCE_M] = float(
        cfg.get(CONF_AWAY_REMINDER_MAX_DISTANCE_M, DEFAULT_AWAY_REMINDER_MAX_DISTANCE_M)
    )
    domain_data[CONF_INSTALL_DASHBOARD] = bool(cfg.get(CONF_INSTALL_DASHBOARD, DEFAULT_INSTALL_DASHBOARD))


def _install_dashboard_file(hass: HomeAssistant) -> bool:
    source_path = Path(__file__).resolve().parent / DASHBOARD_SOURCE
    if not source_path.is_file():
        _LOGGER.warning("Dashboard template not found at %s", source_path)
        return False

    target_path = Path(hass.config.path("dashboards", DASHBOARD_FILENAME))
    target_path.parent.mkdir(parents=True, exist_ok=True)

    source_text = source_path.read_text(encoding="utf-8")
    if target_path.is_file():
        current_text = target_path.read_text(encoding="utf-8")
        if current_text == source_text:
            return False

    target_path.write_text(source_text, encoding="utf-8")
    return True


def _dashboard_config() -> dict[str, Any]:
    return {
        LOVELACE_CONF_TITLE: DASHBOARD_TITLE,
        LOVELACE_CONF_ICON: DASHBOARD_ICON,
        LOVELACE_CONF_SHOW_IN_SIDEBAR: True,
        LOVELACE_CONF_REQUIRE_ADMIN: False,
        LOVELACE_CONF_MODE: LOVELACE_MODE_YAML,
        LOVELACE_CONF_FILENAME: f"dashboards/{DASHBOARD_FILENAME}",
    }


def _is_our_dashboard_config(config: dict[str, Any] | None) -> bool:
    if not isinstance(config, dict):
        return False
    return str(config.get(LOVELACE_CONF_FILENAME, "")) == f"dashboards/{DASHBOARD_FILENAME}"


@callback
def _register_dashboard_panel(hass: HomeAssistant) -> None:
    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        _LOGGER.warning("Lovelace is not initialized yet; cannot register dashboard panel")
        return

    existing = lovelace_data.dashboards.get(DASHBOARD_URL_PATH)
    if existing is not None and not _is_our_dashboard_config(existing.config):
        _LOGGER.warning("Dashboard url_path '%s' already exists and is not managed by Notification Engine", DASHBOARD_URL_PATH)
        return

    config = _dashboard_config()
    lovelace_data.dashboards[DASHBOARD_URL_PATH] = lovelace_dashboard.LovelaceYAML(hass, DASHBOARD_URL_PATH, config)
    frontend.async_register_built_in_panel(
        hass,
        LOVELACE_DOMAIN,
        frontend_url_path=DASHBOARD_URL_PATH,
        require_admin=bool(config[LOVELACE_CONF_REQUIRE_ADMIN]),
        show_in_sidebar=bool(config[LOVELACE_CONF_SHOW_IN_SIDEBAR]),
        sidebar_title=str(config[LOVELACE_CONF_TITLE]),
        sidebar_icon=str(config.get(LOVELACE_CONF_ICON, "")),
        config={"mode": LOVELACE_MODE_YAML},
        update=True,
    )


@callback
def _unregister_dashboard_panel(hass: HomeAssistant) -> None:
    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        return

    existing = lovelace_data.dashboards.get(DASHBOARD_URL_PATH)
    if existing is None or not _is_our_dashboard_config(existing.config):
        return

    lovelace_data.dashboards.pop(DASHBOARD_URL_PATH, None)
    frontend.async_remove_panel(hass, DASHBOARD_URL_PATH)


async def _sync_dashboard(hass: HomeAssistant, cfg: dict[str, Any]) -> None:
    enabled = bool(cfg.get(CONF_INSTALL_DASHBOARD, DEFAULT_INSTALL_DASHBOARD))
    if not enabled:
        _unregister_dashboard_panel(hass)
        return

    changed = await hass.async_add_executor_job(_install_dashboard_file, hass)
    if changed:
        _LOGGER.info("Notification Engine dashboard installed at %s", hass.config.path("dashboards", DASHBOARD_FILENAME))
    _register_dashboard_panel(hass)


def _event_recipients(event: dict[str, Any], people: dict[str, dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    recipients = _normalize_entities(event.get("recipients", []))
    for item in recipients:
        person = str(item)
        if person and person not in seen:
            seen.add(person)
            result.append(person)

    if result:
        return result

    # Fallback: notify all active people when no explicit recipient is set.
    for person in _active_people_entities(people):
        if person not in seen:
            seen.add(person)
            result.append(person)

    return result


def _is_home(hass: HomeAssistant, person_entity: str) -> bool:
    state = hass.states.get(person_entity)
    return state is not None and state.state == "home"


async def _send_to_notify(
    hass: HomeAssistant,
    notify_service: str,
    *,
    title: str,
    message: str,
    tag: str,
    actions: list[dict[str, Any]],
    strategy: str = "",
) -> None:
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
    if actions:
        payload["data"]["actions"] = actions[:3]
    await hass.services.async_call(domain, service, payload, blocking=True)


async def _clear_tag_for_all(hass: HomeAssistant, people: dict[str, dict[str, Any]], tag: str) -> None:
    for person_config in people.values():
        if not _person_enabled(person_config):
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


async def _process_events_core(hass: HomeAssistant) -> dict[str, Any]:
    domain_data = hass.data[DOMAIN]
    engine: NotificationEventEngine = domain_data["engine"]
    people = _people_config(domain_data)
    mode = str(domain_data.get(CONF_AWAY_REMINDER_MODE, DEFAULT_AWAY_REMINDER_MODE))
    tolerance = float(domain_data.get(CONF_AWAY_REMINDER_TOLERANCE_M, DEFAULT_AWAY_REMINDER_TOLERANCE_M))
    max_distance = float(domain_data.get(CONF_AWAY_REMINDER_MAX_DISTANCE_M, DEFAULT_AWAY_REMINDER_MAX_DISTANCE_M))

    events = await hass.async_add_executor_job(engine.load_events)
    sent = 0

    for event in events:
        if event.get("status") != "pending":
            continue

        recipients = _event_recipients(event, people)
        notified = set(event.get("notified_people", []))
        strategy = str(event.get("strategy", ""))

        if strategy in ("present", "asap"):
            selected = [person for person in recipients if _is_home(hass, person)]
        elif strategy in ("alert", "info"):
            selected = recipients
        elif strategy == "away_reminder":
            candidates = recipients
            if mode != "nearest":
                selected = candidates
            else:
                distances: list[tuple[str, float]] = []
                for person in candidates:
                    sensor = str(people.get(person, {}).get("proximity_sensor", ""))
                    if not sensor:
                        continue
                    sensor_state = hass.states.get(sensor)
                    if sensor_state is None:
                        continue
                    try:
                        dist = float(sensor_state.state)
                    except (TypeError, ValueError):
                        continue
                    distances.append((person, dist))
                if not distances:
                    selected = candidates
                else:
                    nearest = min(dist for _, dist in distances)
                    if nearest > max_distance:
                        selected = candidates
                    else:
                        selected = [person for person, dist in distances if dist <= nearest + tolerance]
                        if not selected:
                            selected = candidates
        else:
            selected = []

        for person in selected:
            if person in notified:
                continue
            person_cfg = people.get(person, {})
            if not _person_enabled(person_cfg):
                continue
            notify_service = str(person_cfg.get("notify_service", ""))
            if not notify_service:
                continue
            try:
                await _send_to_notify(
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

        # Fire-and-forget strategy: once all deliverable recipients got the info,
        # remove the event from HA storage (mobile notifications remain on devices).
        if strategy == "info":
            deliverable = [
                person
                for person in recipients
                if _person_enabled(people.get(person, {}))
                and bool(str(people.get(person, {}).get("notify_service", "")))
            ]
            if all(person in notified for person in deliverable):
                await hass.async_add_executor_job(engine.delete_event, str(event.get("id", "")))

    return {"ok": True, "sent": sent}


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Notification Engine and register services/listeners."""
    domain_cfg = config.get(DOMAIN, {})
    if not isinstance(domain_cfg, dict):
        domain_cfg = {}

    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data["engine"] = NotificationEventEngine(hass.config.path(".storage", EVENTS_FILENAME))
    engine: NotificationEventEngine = domain_data["engine"]
    domain_data["coordinator"] = DataUpdateCoordinator(
        hass,
        logger=_LOGGER,
        name=f"{DOMAIN}_events",
        update_method=lambda: hass.async_add_executor_job(engine.load_events),
        update_interval=timedelta(seconds=30),
    )
    _apply_runtime_config(domain_data, domain_cfg)
    entries = hass.config_entries.async_entries(DOMAIN)
    if entries:
        _apply_runtime_config(domain_data, _entry_config(entries[0]))

    if domain_data.get("services_registered"):
        return True

    coordinator: DataUpdateCoordinator = domain_data["coordinator"]

    async def _create_event(call: ServiceCall) -> ServiceResponse:
        result = await hass.async_add_executor_job(
            engine.create_event,
            str(call.data.get("key", "")),
            str(call.data.get("source_entity", "")),
            str(call.data.get("context_label", "")),
            _extract_target_entities(call.data),
            str(call.data.get("strategy", "")),
            str(call.data.get("title", "")),
            str(call.data.get("message", "")),
            parse_actions(call.data.get("actions", [])),
        )
        await _process_events_core(hass)
        await coordinator.async_request_refresh()
        return {"ok": True, **result}

    async def _list_events(_: ServiceCall) -> ServiceResponse:
        events = await hass.async_add_executor_job(engine.load_events)
        return {"ok": True, "events": events}

    async def _send_info(call: ServiceCall) -> ServiceResponse:
        title = str(call.data.get("title", ""))
        message = str(call.data.get("message", ""))
        people = _people_config(domain_data)
        event_like = {
            "recipients": _extract_target_entities(call.data),
        }
        recipients = _event_recipients(event_like, people)
        sent = 0
        for person in recipients:
            person_cfg = people.get(person, {})
            if not _person_enabled(person_cfg):
                continue
            notify_service = str(person_cfg.get("notify_service", ""))
            if not notify_service:
                continue
            await _send_to_notify(
                hass,
                notify_service,
                title=title,
                message=message,
                tag=f"info_{person}",
                actions=[],
                strategy="info",
            )
            sent += 1
        await coordinator.async_request_refresh()
        return {"ok": True, "sent": sent}

    async def _process_events(_: ServiceCall) -> ServiceResponse:
        result = await _process_events_core(hass)
        await coordinator.async_request_refresh()
        return result

    async def _ack_event(call: ServiceCall) -> ServiceResponse:
        event_id = str(call.data.get("id", ""))
        status = str(call.data.get("status", "done"))
        event = await hass.async_add_executor_job(engine.ack_event, event_id, status)
        if event is None:
            return {"ok": False, "error": "event_not_found", "id": event_id}
        if status != "pending":
            await _clear_tag_for_all(hass, _people_config(domain_data), str(event.get("tag", f"notif_{event_id}")))
        await coordinator.async_request_refresh()
        return {"ok": True, "event": event}

    async def _notify_person(call: ServiceCall) -> ServiceResponse:
        event_id = str(call.data.get("id", ""))
        person = str(call.data.get("person", ""))
        event = await hass.async_add_executor_job(engine.notify_person, event_id, person)
        if event is None:
            return {"ok": False, "error": "event_not_found", "id": event_id}
        await coordinator.async_request_refresh()
        return {"ok": True, "event": event}

    async def _cleanup_events(_: ServiceCall) -> ServiceResponse:
        events_before = await hass.async_add_executor_job(engine.load_events)
        result = await hass.async_add_executor_job(engine.cleanup_events)
        tags_to_clear = {
            str(event.get("tag", ""))
            for event in events_before
            if isinstance(event, dict) and event.get("status") != "pending" and str(event.get("tag", ""))
        }
        for tag in tags_to_clear:
            await _clear_tag_for_all(hass, _people_config(domain_data), tag)
        await coordinator.async_request_refresh()
        return {"ok": True, **result}

    async def _delete_event(call: ServiceCall) -> ServiceResponse:
        event_id = str(call.data.get("id", ""))
        deleted = await hass.async_add_executor_job(engine.delete_event, event_id)
        if deleted is None:
            return {"ok": False, "error": "event_not_found", "id": event_id}
        await _clear_tag_for_all(hass, _people_config(domain_data), str(deleted.get("tag", f"notif_{event_id}")))
        await coordinator.async_request_refresh()
        return {"ok": True, "deleted": True, "event": deleted}

    async def _purge_events(_: ServiceCall) -> ServiceResponse:
        events_before = await hass.async_add_executor_job(engine.load_events)
        result = await hass.async_add_executor_job(engine.purge_events)
        tags_to_clear = {
            str(event.get("tag", ""))
            for event in events_before
            if isinstance(event, dict) and str(event.get("tag", ""))
        }
        for tag in tags_to_clear:
            await _clear_tag_for_all(hass, _people_config(domain_data), tag)
        await coordinator.async_request_refresh()
        return {"ok": True, **result}

    async def _on_mobile_action(event: Event) -> None:
        action_id = str(event.data.get("action", ""))
        if not (action_id.startswith("NOTIF_EVENT_DONE_") or action_id.startswith("NOTIF_CUSTOM_")):
            return

        if action_id.startswith("NOTIF_EVENT_DONE_"):
            event_id = action_id.replace("NOTIF_EVENT_DONE_", "", 1)
            event_obj = await hass.async_add_executor_job(engine.ack_event, event_id, "done")
            if event_obj is not None:
                await _clear_tag_for_all(hass, _people_config(domain_data), str(event_obj.get("tag", f"notif_{event_id}")))
                await hass.async_add_executor_job(engine.cleanup_events)
                await coordinator.async_request_refresh()
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
        events = await hass.async_add_executor_job(engine.load_events)
        event_obj = next((item for item in events if str(item.get("id", "")) == event_id), None)
        if event_obj is None:
            return
        actions = event_obj.get("actions", [])
        custom = actions[action_index] if isinstance(actions, list) and len(actions) > action_index else {}
        hass.bus.async_fire(
            "notification_engine_custom_action",
            {
                "id": event_id,
                "action": str(custom.get("action", "")),
                "title": str(custom.get("title", "")),
                "source_entity": str(event_obj.get("source_entity", "")),
                "tag": str(event_obj.get("tag", f"notif_{event_id}")),
            },
        )

    hass.bus.async_listen("mobile_app_notification_action", _on_mobile_action)

    async def _on_state_changed(event: Event) -> None:
        entity_id = str(event.data.get("entity_id", ""))
        if not entity_id.startswith("person."):
            return
        people = set(_people_config(domain_data).keys())
        if entity_id not in people:
            return
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if new_state is None or new_state.state != "home":
            return
        if old_state is not None and old_state.state == "home":
            return
        await _process_events_core(hass)

    hass.bus.async_listen("state_changed", _on_state_changed)

    hass.services.async_register(DOMAIN, SERVICE_CREATE_EVENT, _create_event, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_LIST_EVENTS, _list_events, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_SEND_INFO, _send_info, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_PROCESS_EVENTS, _process_events, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_ACK_EVENT, _ack_event, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_NOTIFY_PERSON, _notify_person, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_CLEANUP_EVENTS, _cleanup_events, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_DELETE_EVENT, _delete_event, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_PURGE_EVENTS, _purge_events, supports_response=SupportsResponse.OPTIONAL)

    domain_data["services_registered"] = True
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Notification Engine from a config entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data[entry.entry_id] = {}
    cfg = _entry_config(entry)
    _apply_runtime_config(domain_data, cfg)
    await _sync_dashboard(hass, cfg)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _update_listener(hass: HomeAssistant, updated_entry: ConfigEntry) -> None:
        updated_cfg = _entry_config(updated_entry)
        _apply_runtime_config(hass.data[DOMAIN], updated_cfg)
        await _sync_dashboard(hass, updated_cfg)

    entry.async_on_unload(entry.add_update_listener(_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    _unregister_dashboard_panel(hass)
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
