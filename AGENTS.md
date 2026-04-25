# AGENTS.md

This file gives guidance to coding agents working in this repository.

## Project purpose

`ha-notification-engine` is a Home Assistant notification engine:
- Native integration: `custom_components/notification_engine`
- Persistent event store: `.storage/notification_engine_events.json` (runtime file, not versioned)
- Home Assistant configuration via `notification_engine:` in `configuration.yaml`

## Key rules for contributors

- Keep this repository generic and redistributable (HACS-ready).
- Do not commit personal entities/services (example: `person.<name>`, `notify.mobile_app_<name>`).
- Do not commit local/runtime artifacts:
  - `.storage/notification_engine_events.json`
  - `__pycache__/`
  - `*.pyc`
  - `.DS_Store`
- Preserve JSON contract of service responses:
  - success: `{"ok": true, ...}`
  - error: `{"ok": false, "error": "..."}`

## Architecture overview

```
custom_components/
  notification_engine/
    __init__.py
    config_flow.py
    const.py
    dashboards/
      notification_engine_dashboard.yaml
    event_engine.py
    manifest.json
    sensor.py
    services.yaml
    strings.json
    text.py
    translations/
      en.json
      fr.json
```

## Service usage

```bash
notification_engine.create_event
notification_engine.list_events
notification_engine.send_info
notification_engine.process_events
notification_engine.ack_event
notification_engine.notify_person
notification_engine.cleanup_events
notification_engine.delete_event
notification_engine.purge_events
```

## Home Assistant integration notes

- Services are provided by `custom_components/notification_engine`.
- Event processing, arrival handling, and mobile actions are implemented directly in integration code.

## Release hygiene (HACS)

Before publishing:
- Re-scan for personal identifiers in README examples.
- Ensure no runtime files are committed.
