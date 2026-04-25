"""Sensor entities for Notification Engine."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN


class NotificationEventsSensor(CoordinatorEntity, SensorEntity):
    """Expose notification events for dashboards/templates."""

    _attr_has_entity_name = False
    _attr_name = "Notifications événements"
    _attr_unique_id = "notification_engine_notifications_evenements"
    _attr_icon = "mdi:message-badge"

    @property
    def native_value(self) -> int:
        events = self.coordinator.data or []
        return len(events) if isinstance(events, list) else 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        events = self.coordinator.data or []
        if not isinstance(events, list):
            events = []
        return {"events": events}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Notification Engine sensor platform."""
    domain_data = hass.data.get(DOMAIN, {})
    coordinator: DataUpdateCoordinator | None = domain_data.get("coordinator")
    if coordinator is None:
        return
    async_add_entities([NotificationEventsSensor(coordinator)], update_before_add=True)
