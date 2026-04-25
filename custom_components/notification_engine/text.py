"""Text entities for Notification Engine test selectors."""

from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity


class NotificationEngineTestSelectionText(TextEntity, RestoreEntity):
    """Persistent text entity used by the dashboard test selector."""

    _attr_has_entity_name = False
    _attr_native_min = 0
    _attr_native_max = 255
    _attr_mode = "text"

    def __init__(self, *, key: str, unique_id: str, name: str, icon: str) -> None:
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_value = ""
        self.entity_id = f"text.{key}"

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and isinstance(last_state.state, str):
            self._attr_native_value = last_state.state

    async def async_set_value(self, value: str) -> None:
        """Update entity value."""
        self._attr_native_value = value
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Notification Engine text platform."""
    async_add_entities(
        [
            NotificationEngineTestSelectionText(
                key="notification_engine_test_targets",
                unique_id="notification_engine_test_targets",
                name="Notification Engine test targets",
                icon="mdi:account-multiple-check",
            ),
        ],
        update_before_add=True,
    )
