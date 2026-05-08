"""Sensor entities for Notification Engine."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import CONF_PEOPLE, DOMAIN


class NotificationEventsSensor(CoordinatorEntity, SensorEntity):
    """Expose notification events count and list for dashboards/templates."""

    _attr_has_entity_name = True
    _attr_translation_key = "events"
    _attr_unique_id = "notification_engine_notifications_evenements"
    _attr_icon = "mdi:message-badge"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        domain_data: dict[str, Any],
    ) -> None:
        """Initialise the sensor with runtime config access."""
        super().__init__(coordinator)
        self._domain_data = domain_data

    @property
    def native_value(self) -> int:
        events = self.coordinator.data or []
        return len(events) if isinstance(events, list) else 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        events = self.coordinator.data or []
        if not isinstance(events, list):
            events = []
        configured_people = self._domain_data.get(CONF_PEOPLE, {})
        if not isinstance(configured_people, dict):
            configured_people = {}
        return {
            "events": events,
            "configured_people": list(configured_people.keys()),
        }


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
    async_add_entities(
        [NotificationEventsSensor(coordinator, domain_data)],
        update_before_add=True,
    )
