"""Notification Engine integration."""

from __future__ import annotations

import ast
from datetime import timedelta
import logging
from pathlib import Path
from typing import Any

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
    SERVICE_CREATE_EVENT,
    SERVICE_DELETE_EVENT,
    SERVICE_LIST_EVENTS,
    SERVICE_NOTIFY_PERSON,
    SERVICE_PROCESS_EVENTS,
    SERVICE_PURGE_EVENTS,
)
from .delivery import clear_tag_for_all, event_recipients, people_config, person_enabled, process_events_core, send_to_notify
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
        LOVELACE_CONF_MODE: "yaml",
        LOVELACE_CONF_FILENAME: f"dashboards/{DASHBOARD_FILENAME}",
    }


def _is_our_dashboard_config(config: dict[str, Any] | None) -> bool:
    if not isinstance(config, dict):
        return False
    return str(config.get(LOVELACE_CONF_FILENAME, "")) == f"dashboards/{DASHBOARD_FILENAME}"


@callback
def _register_dashboard_panel(hass: HomeAssistant) -> None:
    from homeassistant.components import frontend
    from homeassistant.components.lovelace import dashboard as lovelace_dashboard
    from homeassistant.components.lovelace.const import DOMAIN as lovelace_domain
    from homeassistant.components.lovelace.const import LOVELACE_DATA

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
        lovelace_domain,
        frontend_url_path=DASHBOARD_URL_PATH,
        require_admin=bool(config[LOVELACE_CONF_REQUIRE_ADMIN]),
        show_in_sidebar=bool(config[LOVELACE_CONF_SHOW_IN_SIDEBAR]),
        sidebar_title=str(config[LOVELACE_CONF_TITLE]),
        sidebar_icon=str(config.get(LOVELACE_CONF_ICON, "")),
        config={"mode": "yaml"},
        update=True,
    )


@callback
def _unregister_dashboard_panel(hass: HomeAssistant) -> None:
    from homeassistant.components import frontend
    from homeassistant.components.lovelace.const import LOVELACE_DATA

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
        await process_events_core(hass, domain_data)
        await coordinator.async_request_refresh()
        return {"ok": True, **result}

    async def _list_events(_: ServiceCall) -> ServiceResponse:
        events = await hass.async_add_executor_job(engine.load_events)
        return {"ok": True, "events": events}

    async def _send_info(call: ServiceCall) -> ServiceResponse:
        title = str(call.data.get("title", ""))
        message = str(call.data.get("message", ""))
        people = people_config(domain_data)
        event_like = {
            "recipients": _extract_target_entities(call.data),
        }
        recipients = event_recipients(event_like, people)
        sent = 0
        for person in recipients:
            person_cfg = people.get(person, {})
            if not person_enabled(person_cfg):
                continue
            notify_service = str(person_cfg.get("notify_service", ""))
            if not notify_service:
                continue
            await send_to_notify(
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
        result = await process_events_core(hass, domain_data)
        await coordinator.async_request_refresh()
        return result

    async def _notify_person(call: ServiceCall) -> ServiceResponse:
        event_id = str(call.data.get("id", ""))
        person = str(call.data.get("person", ""))
        event = await hass.async_add_executor_job(engine.notify_person, event_id, person)
        if event is None:
            return {"ok": False, "error": "event_not_found", "id": event_id}
        await coordinator.async_request_refresh()
        return {"ok": True, "event": event}

    async def _delete_event(call: ServiceCall) -> ServiceResponse:
        event_id = str(call.data.get("id", ""))
        deleted = await hass.async_add_executor_job(engine.delete_event, event_id)
        if deleted is None:
            return {"ok": False, "error": "event_not_found", "id": event_id}
        await clear_tag_for_all(hass, people_config(domain_data), str(deleted.get("tag", f"notif_{event_id}")))
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
            await clear_tag_for_all(hass, people_config(domain_data), tag)
        await coordinator.async_request_refresh()
        return {"ok": True, **result}

    async def _on_mobile_action(event: Event) -> None:
        action_id = str(event.data.get("action", ""))
        if not (action_id.startswith("NOTIF_EVENT_DONE_") or action_id.startswith("NOTIF_CUSTOM_")):
            return

        if action_id.startswith("NOTIF_EVENT_DONE_"):
            event_id = action_id.replace("NOTIF_EVENT_DONE_", "", 1)
            event_obj = await hass.async_add_executor_job(engine.delete_event, event_id)
            if event_obj is not None:
                await clear_tag_for_all(hass, people_config(domain_data), str(event_obj.get("tag", f"notif_{event_id}")))
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
        people = set(people_config(domain_data).keys())
        if entity_id not in people:
            return
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if new_state is None or new_state.state != "home":
            return
        if old_state is not None and old_state.state == "home":
            return
        await process_events_core(hass, domain_data)

    hass.bus.async_listen("state_changed", _on_state_changed)

    hass.services.async_register(DOMAIN, SERVICE_CREATE_EVENT, _create_event, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_LIST_EVENTS, _list_events, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_SEND_INFO, _send_info, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_PROCESS_EVENTS, _process_events, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_NOTIFY_PERSON, _notify_person, supports_response=SupportsResponse.OPTIONAL)
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
