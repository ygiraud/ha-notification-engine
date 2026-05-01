"""Notification Engine integration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, SupportsResponse, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
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
    DEFAULT_PROCESS_EVENTS_INTERVAL,
    DOMAIN,
    EVENTS_FILENAME,
    SERVICE_CREATE_EVENT,
    SERVICE_DELETE_EVENT,
    SERVICE_LIST_EVENTS,
    SERVICE_PROCESS_EVENTS,
    SERVICE_PURGE_EVENTS,
    SERVICE_SEND_INFO,
)
from .event_engine import NotificationEventEngine
from .services import NotificationEngineServices
from .delivery import process_events_core

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "text"]
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
        _LOGGER.warning(
            "Dashboard url_path '%s' already exists and is not managed by Notification Engine",
            DASHBOARD_URL_PATH,
        )
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

    # update_interval=None: coordinator is event-driven only.
    # Every service call explicitly calls async_request_refresh() — no polling needed.
    domain_data["coordinator"] = DataUpdateCoordinator(
        hass,
        logger=_LOGGER,
        name=f"{DOMAIN}_events",
        update_method=lambda: hass.async_add_executor_job(engine.load_events),
        update_interval=None,
    )
    _apply_runtime_config(domain_data, domain_cfg)
    entries = hass.config_entries.async_entries(DOMAIN)
    if entries:
        _apply_runtime_config(domain_data, _entry_config(entries[0]))

    if domain_data.get("services_registered"):
        return True

    coordinator: DataUpdateCoordinator = domain_data["coordinator"]
    handler = NotificationEngineServices(hass, domain_data, engine, coordinator)

    hass.bus.async_listen("mobile_app_notification_action", handler.async_on_mobile_action)
    hass.bus.async_listen("state_changed", handler.async_on_state_changed)

    hass.services.async_register(DOMAIN, SERVICE_CREATE_EVENT, handler.async_create_event, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_LIST_EVENTS, handler.async_list_events, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_SEND_INFO, handler.async_send_info, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_PROCESS_EVENTS, handler.async_process_events, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_DELETE_EVENT, handler.async_delete_event, supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_PURGE_EVENTS, handler.async_purge_events, supports_response=SupportsResponse.OPTIONAL)

    async def _async_periodic_process_events(now: Any) -> None:
        try:
            await process_events_core(hass, domain_data)
            await coordinator.async_request_refresh()
        except Exception:  # pragma: no cover - defensive HA runtime logging
            _LOGGER.exception("Periodic process_events execution failed")

    domain_data["periodic_process_events_unsub"] = async_track_time_interval(
        hass,
        _async_periodic_process_events,
        DEFAULT_PROCESS_EVENTS_INTERVAL,
    )

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
