"""Config flow for Notification Engine."""

from __future__ import annotations

import json
import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

from .const import (
    CONF_AWAY_REMINDER_MAX_DISTANCE_M,
    CONF_AWAY_REMINDER_MODE,
    CONF_AWAY_REMINDER_TOLERANCE_M,
    CONF_INSTALL_DASHBOARD,
    CONF_PEOPLE,
    CONF_PEOPLE_ENTITIES,
    DEFAULT_AWAY_REMINDER_MAX_DISTANCE_M,
    DEFAULT_AWAY_REMINDER_MODE,
    DEFAULT_AWAY_REMINDER_TOLERANCE_M,
    DEFAULT_INSTALL_DASHBOARD,
    DOMAIN,
)

def _normalize_people(data: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(data, dict):
        raise ValueError("people must be an object")
    parsed: dict[str, dict[str, Any]] = {}
    for key, value in data.items():
        if not isinstance(value, dict):
            continue
        enabled = value.get("enabled")
        parsed[str(key)] = {
            "enabled": True if enabled is None else bool(enabled),
            "notify_service": str(value.get("notify_service", "")),
            "proximity_sensor": str(value.get("proximity_sensor", "")),
        }
    return parsed


def _normalize_people_entities(data: Any) -> list[str]:
    if data is None:
        return []
    if isinstance(data, str):
        raw = data.strip()
        return [raw] if raw else []
    if isinstance(data, list):
        return [str(item).strip() for item in data if str(item).strip()]
    raise ValueError("people_entities must be a list")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")


def _guess_notify_service(hass: HomeAssistant, person_entity: str) -> str:
    services = hass.services.async_services().get("notify", {})
    mobile_services = [f"notify.{name}" for name in services.keys() if str(name).startswith("mobile_app_")]
    if not mobile_services:
        return ""

    object_id = person_entity.split(".", 1)[1] if "." in person_entity else person_entity
    person_state = hass.states.get(person_entity)
    person_name = _slug(person_state.name) if person_state else ""

    best = ""
    best_score = -1
    for service in mobile_services:
        score = 0
        if service.endswith(object_id):
            score = 4
        elif object_id in service:
            score = 3
        elif person_name and person_name in service:
            score = 2
        if score > best_score:
            best_score = score
            best = service
    return best


def _guess_proximity_sensor(hass: HomeAssistant, person_entity: str) -> str:
    person_state = hass.states.get(person_entity)
    object_id = person_entity.split(".", 1)[1] if "." in person_entity else person_entity
    tokens = {_slug(object_id)}
    if person_state is not None:
        name_slug = _slug(person_state.name)
        if name_slug:
            tokens.add(name_slug)

    keyword_sets = (
        ("distance", "home"),
        ("distance", "maison"),
        ("distance",),
        ("proximity",),
    )

    candidates: list[str] = []
    for state in hass.states.async_all("sensor"):
        entity_id = state.entity_id
        entity_id_l = entity_id.lower()
        if not any(token and token in entity_id_l for token in tokens):
            continue
        friendly_l = _slug(str(state.name))
        haystack = f"{entity_id_l} {friendly_l}"
        for keywords in keyword_sets:
            if all(word in haystack for word in keywords):
                candidates.append(entity_id)
                break

    # Prefer deterministic, exact-ish matches.
    if not candidates:
        return ""
    candidates = sorted(set(candidates))
    for entity_id in candidates:
        eid = entity_id.lower()
        if any(token and token in eid for token in tokens) and "distance" in eid:
            return entity_id
    return candidates[0]


def _build_people_from_selection(
    hass: HomeAssistant,
    selected_people: list[str],
    overrides: dict[str, dict[str, Any]],
    existing_people: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    people: dict[str, dict[str, Any]] = {}
    for person_entity in selected_people:
        base = dict(existing_people.get(person_entity, {}))
        cfg = {
            "enabled": True if base.get("enabled") is None else bool(base.get("enabled", True)),
            "notify_service": str(base.get("notify_service", "")),
            "proximity_sensor": str(base.get("proximity_sensor", "")),
        }
        if not cfg["notify_service"]:
            cfg["notify_service"] = _guess_notify_service(hass, person_entity)
        if not cfg["proximity_sensor"]:
            cfg["proximity_sensor"] = _guess_proximity_sensor(hass, person_entity)
        override = overrides.get(person_entity, {})
        if isinstance(override, dict):
            if "enabled" in override:
                cfg["enabled"] = bool(override.get("enabled"))
            if "notify_service" in override:
                cfg["notify_service"] = str(override.get("notify_service", ""))
            if "proximity_sensor" in override:
                cfg["proximity_sensor"] = str(override.get("proximity_sensor", ""))
        people[person_entity] = cfg
    return people


def _schema_with_defaults(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_PEOPLE_ENTITIES,
                default=defaults.get(CONF_PEOPLE_ENTITIES, []),
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain=["person"], multiple=True)),
            vol.Required(
                CONF_AWAY_REMINDER_MODE,
                default=str(defaults.get(CONF_AWAY_REMINDER_MODE, DEFAULT_AWAY_REMINDER_MODE)),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["all", "nearest"],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_AWAY_REMINDER_TOLERANCE_M,
                default=float(defaults.get(CONF_AWAY_REMINDER_TOLERANCE_M, DEFAULT_AWAY_REMINDER_TOLERANCE_M)),
            ): vol.Coerce(float),
            vol.Required(
                CONF_AWAY_REMINDER_MAX_DISTANCE_M,
                default=float(
                    defaults.get(CONF_AWAY_REMINDER_MAX_DISTANCE_M, DEFAULT_AWAY_REMINDER_MAX_DISTANCE_M)
                ),
            ): vol.Coerce(float),
            vol.Required(
                CONF_INSTALL_DASHBOARD,
                default=bool(defaults.get(CONF_INSTALL_DASHBOARD, DEFAULT_INSTALL_DASHBOARD)),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_PEOPLE,
                default=defaults.get(CONF_PEOPLE, {}),
            ): selector.ObjectSelector(),
        }
    )


class NotificationEngineConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle Notification Engine config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        defaults = {
            CONF_PEOPLE_ENTITIES: [],
            CONF_AWAY_REMINDER_MODE: DEFAULT_AWAY_REMINDER_MODE,
            CONF_AWAY_REMINDER_TOLERANCE_M: DEFAULT_AWAY_REMINDER_TOLERANCE_M,
            CONF_AWAY_REMINDER_MAX_DISTANCE_M: DEFAULT_AWAY_REMINDER_MAX_DISTANCE_M,
            CONF_INSTALL_DASHBOARD: DEFAULT_INSTALL_DASHBOARD,
            CONF_PEOPLE: {},
        }

        if user_input is not None:
            try:
                selected_people = _normalize_people_entities(user_input.get(CONF_PEOPLE_ENTITIES, []))
                people = _normalize_people(user_input.get(CONF_PEOPLE, {}))
            except (ValueError, TypeError):
                errors[CONF_PEOPLE] = "invalid_people_json"
            else:
                built_people = _build_people_from_selection(self.hass, selected_people, people, {})
                data = {
                    CONF_AWAY_REMINDER_MODE: str(user_input.get(CONF_AWAY_REMINDER_MODE, DEFAULT_AWAY_REMINDER_MODE)),
                    CONF_AWAY_REMINDER_TOLERANCE_M: float(
                        user_input.get(CONF_AWAY_REMINDER_TOLERANCE_M, DEFAULT_AWAY_REMINDER_TOLERANCE_M)
                    ),
                    CONF_AWAY_REMINDER_MAX_DISTANCE_M: float(
                        user_input.get(
                            CONF_AWAY_REMINDER_MAX_DISTANCE_M, DEFAULT_AWAY_REMINDER_MAX_DISTANCE_M
                        )
                    ),
                    CONF_INSTALL_DASHBOARD: bool(
                        user_input.get(CONF_INSTALL_DASHBOARD, DEFAULT_INSTALL_DASHBOARD)
                    ),
                    CONF_PEOPLE: built_people,
                }
                return self.async_create_entry(title="Notification Engine", data=data)

            defaults = {
                CONF_PEOPLE_ENTITIES: user_input.get(CONF_PEOPLE_ENTITIES, []),
                CONF_AWAY_REMINDER_MODE: user_input.get(CONF_AWAY_REMINDER_MODE, DEFAULT_AWAY_REMINDER_MODE),
                CONF_AWAY_REMINDER_TOLERANCE_M: user_input.get(
                    CONF_AWAY_REMINDER_TOLERANCE_M, DEFAULT_AWAY_REMINDER_TOLERANCE_M
                ),
                CONF_AWAY_REMINDER_MAX_DISTANCE_M: user_input.get(
                    CONF_AWAY_REMINDER_MAX_DISTANCE_M, DEFAULT_AWAY_REMINDER_MAX_DISTANCE_M
                ),
                CONF_INSTALL_DASHBOARD: user_input.get(CONF_INSTALL_DASHBOARD, DEFAULT_INSTALL_DASHBOARD),
                CONF_PEOPLE: user_input.get(CONF_PEOPLE, {}),
            }

        return self.async_show_form(step_id="user", data_schema=_schema_with_defaults(defaults), errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return NotificationEngineOptionsFlow(config_entry)


class NotificationEngineOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Notification Engine."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage options."""
        errors: dict[str, str] = {}
        merged = dict(self._config_entry.data)
        merged.update(self._config_entry.options)
        people_defaults = merged.get(CONF_PEOPLE, {})
        merged.setdefault(CONF_PEOPLE_ENTITIES, list(people_defaults.keys()) if isinstance(people_defaults, dict) else [])
        merged.setdefault(CONF_INSTALL_DASHBOARD, DEFAULT_INSTALL_DASHBOARD)

        if user_input is not None:
            try:
                selected_people = _normalize_people_entities(user_input.get(CONF_PEOPLE_ENTITIES, []))
                people = _normalize_people(user_input.get(CONF_PEOPLE, {}))
            except (ValueError, TypeError):
                errors[CONF_PEOPLE] = "invalid_people_json"
            else:
                existing_people = merged.get(CONF_PEOPLE, {})
                if not isinstance(existing_people, dict):
                    existing_people = {}
                built_people = _build_people_from_selection(self.hass, selected_people, people, existing_people)
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_AWAY_REMINDER_MODE: str(
                            user_input.get(CONF_AWAY_REMINDER_MODE, DEFAULT_AWAY_REMINDER_MODE)
                        ),
                        CONF_AWAY_REMINDER_TOLERANCE_M: float(
                            user_input.get(CONF_AWAY_REMINDER_TOLERANCE_M, DEFAULT_AWAY_REMINDER_TOLERANCE_M)
                        ),
                        CONF_AWAY_REMINDER_MAX_DISTANCE_M: float(
                            user_input.get(
                                CONF_AWAY_REMINDER_MAX_DISTANCE_M, DEFAULT_AWAY_REMINDER_MAX_DISTANCE_M
                            )
                        ),
                        CONF_INSTALL_DASHBOARD: bool(
                            user_input.get(CONF_INSTALL_DASHBOARD, DEFAULT_INSTALL_DASHBOARD)
                        ),
                        CONF_PEOPLE: built_people,
                    },
                )

        return self.async_show_form(step_id="init", data_schema=_schema_with_defaults(merged), errors=errors)
