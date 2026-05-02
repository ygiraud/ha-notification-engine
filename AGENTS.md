# AGENTS.md

## Project Context

### Project purpose

`ha-notification-engine` is a Home Assistant notification engine integration.

### Architecture

- Home Assistant custom integration: `custom_components/notification_engine`
- Main files:
  - `__init__.py`
  - `config_flow.py`
  - `const.py`
  - `event_engine.py`
  - `sensor.py`
  - `text.py`
  - `services.yaml`
  - `manifest.json`
  - `strings.json`
  - `translations/en.json`
  - `translations/fr.json`
  - `dashboards/notification_engine_dashboard.yaml`
- Runtime persistence file (not versioned): `.storage/notification_engine_events.json`

### Conventions

- Keep repository generic and redistributable (HACS-ready).
- Do not commit personal entities/services (example: `person.<name>`, `notify.mobile_app_<name>`).
- Do not commit local/runtime artifacts:
  - `.storage/notification_engine_events.json`
  - `__pycache__/`
  - `*.pyc`
  - `.DS_Store`
- Preserve service response JSON contract:
  - success: `{"ok": true, ...}`
  - error: `{"ok": false, "error": "..."}`

### Commands

- Home Assistant services exposed by integration:
- `notification_engine.create_event`
- `notification_engine.list_events`
- `notification_engine.send_info`
- `notification_engine.process_events`
- `notification_engine.delete_event`
- `notification_engine.purge_events`

### Notes

- Services, event processing, arrival handling, and mobile actions are implemented in integration code.
- Before publishing (HACS hygiene):
  - Re-scan README examples for personal identifiers.
  - Ensure no runtime/local files are committed.

---

## Mandatory Rules (immutable)

### General Behavior

- Do not agree by default. Challenge ideas when they are technically questionable.
- When disagreeing:
  - Explain why
  - Propose a safer or cleaner alternative
  - Wait for confirmation if it impacts scope or architecture
- Be concise, but explicit when it matters.
- Do not over-explain trivial code.
- Do explain non-obvious decisions.

### Scope Control

- Implement only what is explicitly requested.
- Small, safe, directly related improvements are allowed.
- Any larger refactor, redesign, or optimization must be proposed, not implemented.

### Ambiguity Handling

- Never guess silently.
- If something is unclear:
  - Ask a question if blocking
  - Otherwise, proceed with an explicit assumption

### Code Quality

- Respect the existing code style and conventions.
- Do not introduce new abstractions without clear justification.
- Prefer clarity over cleverness.
- Prefer simple solutions over complex ones.
- Add tests for non-trivial logic when possible.
- If tests are not added, explain why.

---

## How to Work

### Before Making Changes

- Understand the context and intent of the code.
- Identify risks, edge cases, and possible side effects.
- If something looks wrong or risky, call it out before proceeding.

### During Work

- Keep changes minimal and focused.
- Avoid unrelated modifications.
- Do not refactor broadly without approval.
- Maintain consistency with the existing architecture.

### After Changes

- Review your own changes critically.
- Check for unintended side effects.
- Ensure consistency and readability.

---

## Agent Roles & Workflow

### Agent Roles

#### Codex (Implementation Agent)

- Responsible for code implementation and technical changes
- Writes docstrings and inline comments
- Must follow project conventions and AGENTS.md rules

Codex must:
- Implement only what is requested
- Highlight inconsistencies before coding
- Not change design decisions without approval
- Propose improvements but not implement them without validation

#### Claude (Analysis & Review Agent)

- Responsible for analysis, review, and consistency
- Owns developer and user documentation
- Ensures design and implementation alignment

Claude must:
- Challenge decisions
- Identify risks and inconsistencies
- Review implementations
- Improve clarity and structure

---

### Development Workflow

1. Analysis / Design (optional)
2. Implementation (Codex)
3. Review (Claude)
4. Fix (Codex)
5. Repeat

---

### Key Principles

- Workflow is flexible, not rigid
- Use Claude early for complex tasks
- No design change without approval
- Always rely on AGENTS.md and HANDOFF.md

---

### Interaction Pattern

1. User defines task
2. Choose agent
3. Agent works and updates HANDOFF.md
4. Switch agent if needed
5. Repeat

---

## Commits

### Format

```
<type>[optional scope]: <imperative description>

- <technical change>
- <technical change>

Closes #N
```

### Rules

- English, imperative, no trailing period
- No vague messages
- One commit = one intention
- Always append `Closes #N` (GitHub issue number) when the commit fully resolves a tracked issue
- GitHub keywords accepted: `Closes`, `Fixes`, `Resolves` — use `Closes` by default

### Process

1. git status + diff
2. Diagnosis
3. Propose message
4. Wait for approval
5. Commit
6. Push if requested
7. Report details

### Strict Rules

- No commit without approval
- No destructive git commands
- Refuse incoherent commits
- Do not include AGENTS.md / HANDOFF.md unless relevant

---

## v1.1 Features

Work is done feature by feature. Each feature maps to a GitHub issue.
Implement one feature per working session. Close the issue in the commit message with `Closes #N`.

| # | Feature | GitHub Issue | Status |
|---|---|---|---|
| 1 | Event TTL (`ttl_hours` on `create_event`, auto-purge on `process_events`) | #1 | completed |
| 2 | Re-notification (resend unacknowledged `asap` after configurable delay) | #2 | pending |
| 3 | `purge_events` filters (`strategy`, `status`, `older_than_hours`) | #3 | pending |
| 4 | `get_event` service (retrieve single event by `key` or `id`) | #4 | pending |
| 5 | `snooze` action (defer event N minutes from mobile notification) | #5 | pending |

### Implementation Order

Implement in issue number order. Each feature is independent enough to be done in isolation.

1. Event TTL (#1) — adds `ttl_hours` field + auto-purge in `process_events`
2. Re-notification (#2) — new scheduling logic for unacknowledged `asap` events
3. `purge_events` filters (#3) — extends existing service with filter params
4. `get_event` service (#4) — pure read-only service, no side effects
5. `snooze` action (#5) — mobile action handler, defers event N minutes (precision ensured by 1-min polling)

### Per-Feature Checklist

Before starting a feature, Codex must:
- Read AGENTS.md and HANDOFF.md
- Identify all files affected
- Confirm the implementation plan with the user if ambiguous

After completing a feature, Codex must:
- Add or update unit tests
- Update `services.yaml` if a new service or field is added
- Update `strings.json` + `translations/en.json` + `translations/fr.json` if UI strings change
- Update HANDOFF.md
- Propose a commit message following the format above (including `Closes #N`)

---

## Handoff

### Protocol

At start:
- Read AGENTS.md
- Read HANDOFF.md

At end:
- Update HANDOFF.md

### Rules

- HANDOFF.md = shared state
- May be outdated → verify with code
- Do not overwrite blindly
- Must be updated after significant work

---

## HANDOFF Structure

## Last Agent ## Objective ## Completed Work ## Modified Files ## Decisions ## Open Questions / Risks ## Next Steps

---

## HANDOFF Character Policy

Allowed:
- ASCII
- French accents
- ✅ 🔴 🟡

Forbidden → replace:
- — → -
- – → -
- ’ → '
- → → ->
- ← → <-
- « » → "
- ≥ ≤ ≠ → >= <= !=
