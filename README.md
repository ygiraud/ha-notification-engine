<div align="center">

# 🔔 Home Assistant Notification Engine

**Push notification engine for Home Assistant — persistent events, smart delivery strategies, and mobile DND bypass.**

[![CI](https://github.com/ygiraud/ha-notification-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/ygiraud/ha-notification-engine/actions/workflows/ci.yml)
[![HACS Validation](https://github.com/ygiraud/ha-notification-engine/actions/workflows/ci.yml/badge.svg?job=HACS+Validation)](https://github.com/ygiraud/ha-notification-engine/actions/workflows/ci.yml)
[![Hassfest](https://github.com/ygiraud/ha-notification-engine/actions/workflows/ci.yml/badge.svg?job=Hassfest)](https://github.com/ygiraud/ha-notification-engine/actions/workflows/ci.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-0.2.3-blue.svg)](https://github.com/ygiraud/ha-notification-engine/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🇫🇷 [Version française](README.fr.md)

</div>

---

## 📋 Table of Contents

- [Features](#-features)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Delivery Strategies](#-delivery-strategies)
- [Available Services](#-available-services)
- [Automation Examples](#-automation-examples)
- [Lovelace Dashboard](#-lovelace-dashboard)
- [Mobile DND Behavior](#-mobile-dnd-behavior)
- [Troubleshooting](#-troubleshooting)
- [Repository Structure](#-repository-structure)

---

## ✨ Features

- **Persistent events** stored in `.storage/notification_engine_events.json` — survive restarts
- **5 delivery strategies** adapted to presence, distance, and urgency
- **Idempotent deduplication** via event keys — create the same event twice, it's sent once
- **Mobile action handling** (`DONE` and custom actions) managed directly by the integration
- **Lovelace dashboard** installable and syncable from the integration options
- **Bilingual** — UI available in English and French

---

## 📦 Requirements

| Requirement | Details |
|---|---|
| Home Assistant | With mobile app configured (`notify.mobile_app_*`) |
| Distance sensors | Required per person for `away_reminder` strategy (`proximity_sensor`) |
| `auto-entities` | For the included Lovelace dashboard |
| `mushroom` | For the included Lovelace dashboard |
| `button-card` | For the included Lovelace dashboard |

---

## 🚀 Installation

### Via HACS (recommended)

1. In HACS, go to **Integrations** → ⋮ → **Custom repositories**
2. Add `https://github.com/ygiraud/ha-notification-engine` with category **Integration**
3. Click **Download**
4. Restart Home Assistant

### Manual

1. Copy `custom_components/notification_engine/` into your `/config/custom_components/` folder
2. Restart Home Assistant

### Setup

1. Go to **Settings → Devices & Services → Add Integration** → search `Notification Engine`
2. Configure people (name, `person.*` entity, `notify_service`, `proximity_sensor`)
3. _(Optional)_ Enable **Install dashboard in sidebar** to install the Lovelace dashboard

---

## 📬 Delivery Strategies

| Strategy | When to use | Behavior |
|---|---|---|
| `present` | Contextual info for people at home | Sent only if the person is currently `home` |
| `asap` | Tasks to do when someone gets home | Sent immediately if `home`, otherwise on next return |
| `away_reminder` | Delegate tasks to the nearest person | Distance-based: sends to nearest or all, with configurable tolerance |
| `alert` | 🚨 Urgent — requires immediate action | Sent to everyone immediately, bypasses mobile DND/Focus |
| `info` | Transient notifications | Sent to everyone immediately, then auto-deleted after delivery |

### `away_reminder` modes

| Mode | Behavior |
|---|---|
| `all` | Send to all targeted people |
| `nearest` | Send to the nearest person(s) based on `away_reminder_tolerance_m` and `away_reminder_max_distance_m` |

> **Fallback:** if no valid distance sensor is available (missing, non-numeric state), the integration falls back to sending to all targeted people.

---

## 🛠 Available Services

| Service | Description |
|---|---|
| `notification_engine.create_event` | Create a notification event (idempotent) |
| `notification_engine.list_events` | List all pending events |
| `notification_engine.send_info` | Send a transient info notification |
| `notification_engine.process_events` | Trigger event processing manually |
| `notification_engine.delete_event` | Delete an event by key or internal id |
| `notification_engine.purge_events` | Delete all events |

**Response contract:**

```yaml
# Success
{"ok": true, ...}

# Error
{"ok": false, "error": "..."}
```

---

## 💡 Automation Examples

### `present` — Send only when someone is home

Useful for home-context reminders (e.g. lights left on, laundry done).

```yaml
automation:
  alias: "Notify: washing machine done (present only)"
  trigger:
    - platform: state
      entity_id: sensor.washing_machine
      to: "done"
  action:
    - service: notification_engine.create_event
      target:
        entity_id: person.alice
      data:
        key: washing_machine_done
        strategy: present
        title: "🫧 Laundry done"
        message: "The washing machine has finished. Don't forget to hang it!"
        actions: '[{"action":"DONE","title":"✅ Done"}]'
```

---

### `asap` — Send on next return home

Useful for tasks that need to be done when someone arrives.

```yaml
automation:
  alias: "Notify: pick up parcel when home"
  trigger:
    - platform: state
      entity_id: binary_sensor.doorbell_parcel
      to: "on"
  action:
    - service: notification_engine.create_event
      target:
        entity_id:
          - person.alice
          - person.bob
      data:
        key: parcel_pickup
        strategy: asap
        title: "📦 Parcel arrived"
        message: "A parcel was delivered. Please bring it inside."
        actions: '[{"action":"DONE","title":"✅ Collected"}]'
```

---

### `away_reminder` — Notify the nearest person

Useful for delegating tasks to whoever is closest (e.g. groceries, picking up kids).

```yaml
automation:
  alias: "Notify: buy bread (nearest person)"
  trigger:
    - platform: time
      at: "17:00:00"
  action:
    - service: notification_engine.create_event
      target:
        entity_id:
          - person.alice
          - person.bob
      data:
        key: buy_bread
        strategy: away_reminder
        title: "🥖 Buy bread"
        message: "Don't forget to pick up bread on your way home."
        actions: '[{"action":"DONE","title":"✅ Got it"}]'
```

---

### `alert` — Urgent / bypass DND

Use sparingly — this will break through Focus/Do Not Disturb on iOS and Android.

```yaml
automation:
  alias: "Alert: water leak detected"
  trigger:
    - platform: state
      entity_id: binary_sensor.water_leak_kitchen
      to: "on"
  action:
    - service: notification_engine.create_event
      target:
        entity_id:
          - person.alice
          - person.bob
      data:
        key: water_leak_kitchen
        strategy: alert
        title: "🚨 Water leak!"
        message: "A leak was detected in the kitchen. Immediate action required."
        actions: '[{"action":"DONE","title":"✅ Handled"}]'
```

---

### `info` — Transient notification (auto-deleted)

Useful for one-shot status updates that don't need acknowledgement.

```yaml
automation:
  alias: "Info: Home Assistant restarted"
  trigger:
    - platform: homeassistant
      event: start
  action:
    - service: notification_engine.create_event
      target:
        entity_id:
          - person.alice
          - person.bob
      data:
        key: ha_restarted
        strategy: info
        title: "🏠 Home Assistant started"
        message: "Home Assistant has restarted successfully."
```

---

### Delete or purge events

```yaml
# Delete a specific event by key
- service: notification_engine.delete_event
  data:
    key: washing_machine_done

# Purge all events
- service: notification_engine.purge_events
```

---

## 📊 Lovelace Dashboard

A pre-built dashboard is included and can be installed directly from the integration options.

**File location:**
```
custom_components/notification_engine/dashboards/notification_engine_dashboard.yaml
```

**Support entity** (created automatically):
- `text.notification_engine_test_targets` — multi-person target selection for testing


---

## 📱 Mobile DND Behavior

| Strategy | Android | iOS |
|---|---|---|
| `alert` | `ttl: 0`, `priority: high`, `channel: alarm_stream` | `interruption-level: critical` with critical sound |
| All others | No DND bypass | No DND bypass |

> ⚠️ **`alert` is intentionally intrusive.** On iPhone it is designed to break through Focus / Do Not Disturb and play an audible critical alert. On Android, the final behavior also depends on how the device handles the `alarm_stream` notification channel and its system notification settings.
>
> Use `alert` only for situations requiring immediate action. Prefer `info`, `present`, `asap`, or `away_reminder` for non-critical events.

---

## 🔧 Troubleshooting

**Event created but no notification sent?**

Check the following:
- The person exists in `notification_engine.people`
- `enabled: true` is set for the person
- `notify_service` is valid and working (test it manually from Developer Tools)
- The service `target` matches configured `person.*` entities

**`away_reminder` not using distance?**

The integration falls back to sending to all targeted people when:
- `proximity_sensor` is not configured for the person
- The sensor entity does not exist in HA
- The sensor state is non-numeric
- No valid distance sensor is available among the recipients

---

## 📁 Repository Structure

```text
custom_components/
  notification_engine/
    __init__.py          # Integration setup & service registration
    config_flow.py       # UI configuration flow
    const.py             # Constants
    event_engine.py      # Core delivery logic
    manifest.json        # Integration metadata
    sensor.py            # Sensor entities
    services.yaml        # Service definitions
    text.py              # Text entities
    dashboards/
      notification_engine_dashboard.yaml
    translations/
      en.json
      fr.json
tests/
  test_event_engine.py
.github/
  workflows/
    ci.yml               # CI: tests, HACS validation, Hassfest
```

> **Repository hygiene** — do not commit: `.storage/notification_engine_events.json`, `__pycache__/`, `*.pyc`, `.DS_Store`
