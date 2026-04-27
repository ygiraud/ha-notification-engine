# Home Assistant Notification Engine

Push notification engine for Home Assistant, with persistent events and delivery strategies.

French version: [README.fr.md](README.fr.md)

## Features

- `notification_engine.*` services to create, process, acknowledge, and purge events
- Persistent event storage in `.storage/notification_engine_events.json`
- Delivery strategies:
  - `present`
  - `asap`
  - `away_reminder`
  - `alert`
  - `info`
- Mobile actions handling (`DONE` and custom actions) inside the integration
- Lovelace YAML dashboard install/sync from integration options

## Repository structure

```text
custom_components/
  notification_engine/
    __init__.py
    config_flow.py
    const.py
    event_engine.py
    manifest.json
    sensor.py
    services.yaml
    text.py
    dashboards/
      notification_engine_dashboard.yaml
    translations/
      en.json
      fr.json
```

## Requirements

- Home Assistant with the mobile app configured (`notify.mobile_app_*`)
- Distance sensors configured per person (`proximity_sensor`) to use `away_reminder` distance behavior
- For the included dashboard:
  - `auto-entities`
  - `mushroom`
  - `button-card`

## Installation

1. Install with HACS (custom repository) or copy `custom_components/notification_engine/` into `/config/custom_components/notification_engine/`.
2. Restart Home Assistant.
3. Add integration: Settings > Devices & Services > Add Integration > `Notification Engine`.
4. Configure people in the integration UI.
5. Optional: enable `Install dashboard in sidebar` to install/sync the dashboard YAML and show it in the sidebar.

## Available services

- `notification_engine.create_event`
- `notification_engine.list_events`
- `notification_engine.send_info`
- `notification_engine.process_events`
- `notification_engine.ack_event`
- `notification_engine.notify_person`
- `notification_engine.cleanup_events`
- `notification_engine.delete_event`
- `notification_engine.purge_events`

Service response contract:

- success: `{"ok": true, ...}`
- error: `{"ok": false, "error": "..."}`

## Lovelace dashboard

Versioned dashboard file:

- `custom_components/notification_engine/dashboards/notification_engine_dashboard.yaml`

Support entity created automatically by the integration:

- `text.notification_engine_test_targets` (multi-person test target selection)

Usage note:

- In the `Test recipients` card, clicking the card resets the selection.

## Delivery strategies

- `present`: send only to people currently at `home`.
- `asap`: send immediately if person is `home`, otherwise send on next return to `home`.
- `away_reminder`: distance-based send logic using `people.<person>.proximity_sensor`.
  - mode `all`: send to all targeted people.
  - mode `nearest`: send to the nearest person(s) based on `away_reminder_tolerance_m` and `away_reminder_max_distance_m`.
- `alert`: immediate send to all targeted people.
- `info`: immediate send to all targeted people, then auto-delete the event after delivery.

## Current limitation

- DND bypass is not implemented yet for phone notifications.
- DND bypass is planned for a future release.

## Troubleshooting

If an event is created but no notification is sent, check:

- the person exists in `notification_engine.people`
- `enabled: true`
- `notify_service` is valid and working
- service `target` matches configured `person.*` entities

`away_reminder` fallback behavior when distance cannot be used:

- missing `proximity_sensor`
- missing sensor entity
- non-numeric sensor state
- no valid distance sensors available among recipients

In these cases, the integration falls back to sending to all targeted people.

## Repository hygiene

Do not commit:

- `.storage/notification_engine_events.json`
- `__pycache__/`
- `*.pyc`
- `.DS_Store`
