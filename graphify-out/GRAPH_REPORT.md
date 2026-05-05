# Graph Report - .  (2026-05-05)

## Corpus Check
- Corpus is ~22,736 words - fits in a single context window. You may not need a graph.

## Summary
- 208 nodes · 331 edges · 11 communities (10 shown, 1 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 45 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Delivery Services|Delivery Services]]
- [[_COMMUNITY_Event Store API|Event Store API]]
- [[_COMMUNITY_Lovelace Dashboard|Lovelace Dashboard]]
- [[_COMMUNITY_Integration Setup|Integration Setup]]
- [[_COMMUNITY_Event Model Actions|Event Model Actions]]
- [[_COMMUNITY_Config Flow|Config Flow]]
- [[_COMMUNITY_Events Sensor|Events Sensor]]
- [[_COMMUNITY_Test Selector Text|Test Selector Text]]
- [[_COMMUNITY_Icon Branding|Icon Branding]]
- [[_COMMUNITY_Logo Branding|Logo Branding]]
- [[_COMMUNITY_Mobile Action|Mobile Action]]

## God Nodes (most connected - your core abstractions)
1. `NotificationEventEngine` - 21 edges
2. `Home Assistant Notification Engine` - 14 edges
3. `NotificationEngineServices` - 13 edges
4. `notification_engine.create_event` - 13 edges
5. `process_events_core()` - 11 edges
6. `people_config()` - 9 edges
7. `NotificationEngineTestSelectionText` - 8 edges
8. `clear_tag_for_all()` - 7 edges
9. `async_setup()` - 7 edges
10. `Notification Engine Dashboard` - 7 edges

## Surprising Connections (you probably didn't know these)
- `test_send_to_notify_adds_critical_mobile_payload_only_for_alert_strategy()` --calls--> `send_to_notify()`  [INFERRED]
  tests/test_event_engine.py → custom_components/notification_engine/delivery.py
- `get_event Service` --semantically_similar_to--> `notification_engine.list_events`  [INFERRED] [semantically similar]
  README.md → custom_components/notification_engine/services.yaml
- `test_parse_actions_accepts_json_and_python_literal()` --calls--> `parse_actions()`  [INFERRED]
  tests/test_event_engine.py → custom_components/notification_engine/event_engine.py
- `test_parse_actions_ignores_invalid_payloads()` --calls--> `parse_actions()`  [INFERRED]
  tests/test_event_engine.py → custom_components/notification_engine/event_engine.py
- `test_create_event_is_idempotent_for_same_pending_payload()` --calls--> `NotificationEventEngine`  [INFERRED]
  tests/test_event_engine.py → custom_components/notification_engine/event_engine.py

## Hyperedges (group relationships)
- **Delivery Strategy Set** — readme_strategy_present, readme_strategy_asap, readme_strategy_away_reminder [EXTRACTED 1.00]
- **Urgent And Transient Modes** — readme_strategy_alert, readme_strategy_info, readme_mobile_dnd_behavior [EXTRACTED 1.00]
- **Dashboard Event Views** — dashboard_alert_section, dashboard_presence_section, dashboard_asap_section [EXTRACTED 1.00]
- **Notification Engine Icon Composition** — icon_brand_icon, icon_bell_symbol, icon_gear_symbol, icon_circular_ring [EXTRACTED 0.97]
- **Notification Engine Logo Composition** — logo_notification_engine_logo, logo_notification_engine_brand, logo_bell_icon, logo_gear_icon, logo_tagline_smart_centralized_reliable [EXTRACTED 0.97]

## Communities (11 total, 1 thin omitted)

### Community 0 - "Delivery Services"
Cohesion: 0.07
Nodes (37): active_people_entities(), clear_tag_for_all(), event_recipients(), is_home(), people_config(), person_enabled(), process_events_core(), Delivery helpers for Notification Engine. (+29 more)

### Community 1 - "Event Store API"
Cohesion: 0.07
Nodes (29): Exception, NotificationEventEngine, Persistent, file-backed notification event store.      All writes are atomic: ev, Load and normalize events., Atomically persist events list., Create event with idempotent deduplication., Mark one event with a status., Mark person as notified for one event. (+21 more)

### Community 2 - "Lovelace Dashboard"
Cohesion: 0.12
Nodes (31): HACS Hygiene, Alertes Section, ASAP Section, Away Reminder Section, Events Sensor Entity, Notification Engine Dashboard, Presence Section, Dashboard Test Panel (+23 more)

### Community 3 - "Integration Setup"
Cohesion: 0.18
Nodes (17): _apply_runtime_config(), async_setup(), async_setup_entry(), async_unload_entry(), _dashboard_config(), _entry_config(), _is_our_dashboard_config(), Notification Engine integration. (+9 more)

### Community 4 - "Event Model Actions"
Cohesion: 0.15
Nodes (16): build_mobile_actions(), build_tag(), make_event(), normalize_event(), parse_actions(), Core event engine logic for Notification Engine integration., Create a new normalized pending event., Return current UTC time as ISO string. (+8 more)

### Community 5 - "Config Flow"
Cohesion: 0.21
Nodes (13): async_get_options_flow(), _build_people_from_selection(), _guess_notify_service(), _guess_proximity_sensor(), _normalize_people(), _normalize_people_entities(), NotificationEngineConfigFlow, NotificationEngineOptionsFlow (+5 more)

### Community 6 - "Events Sensor"
Cohesion: 0.18
Nodes (8): CoordinatorEntity, Constants for the Notification Engine integration., async_setup_entry(), NotificationEventsSensor, Sensor entities for Notification Engine., Expose notification events count and list for dashboards/templates., Set up Notification Engine sensor platform., SensorEntity

### Community 7 - "Test Selector Text"
Cohesion: 0.2
Nodes (7): async_setup_entry(), NotificationEngineTestSelectionText, Text entities for Notification Engine test selectors., Persistent text entity used by the dashboard test selector., Set up Notification Engine text platform., RestoreEntity, TextEntity

### Community 8 - "Icon Branding"
Cohesion: 0.7
Nodes (5): Bell Symbol, Notification Engine Brand Icon, Circular Ring Motif, Notification Engine Brand Icon File, Gear Symbol

### Community 9 - "Logo Branding"
Cohesion: 0.7
Nodes (5): Bell Icon, Gear Icon, Notification Engine, Notification Engine Logo, Smart Centralized Reliable

## Knowledge Gaps
- **65 isolated node(s):** `Unit tests for the pure event engine module.`, `Minimal Home Assistant error stub for pure unit tests.`, `Minimal Home Assistant Event stub for pure unit tests.`, `Minimal Home Assistant stub for type imports.`, `Minimal ServiceCall stub with data and target.` (+60 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `NotificationEventEngine` connect `Event Store API` to `Delivery Services`, `Integration Setup`, `Event Model Actions`?**
  _High betweenness centrality (0.160) - this node is a cross-community bridge._
- **Why does `NotificationEngineServices` connect `Delivery Services` to `Event Store API`, `Integration Setup`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `async_setup()` connect `Integration Setup` to `Delivery Services`, `Event Store API`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `NotificationEventEngine` (e.g. with `NotificationEngineServices` and `test_create_event_is_idempotent_for_same_pending_payload()`) actually correct?**
  _`NotificationEventEngine` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `NotificationEngineServices` (e.g. with `NotificationEventEngine` and `async_setup()`) actually correct?**
  _`NotificationEngineServices` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `notification_engine.create_event` (e.g. with `notification_engine.list_events` and `notification_engine.process_events`) actually correct?**
  _`notification_engine.create_event` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `process_events_core()` (e.g. with `.async_create_event()` and `.async_process_events()`) actually correct?**
  _`process_events_core()` has 3 INFERRED edges - model-reasoned connections that need verification._