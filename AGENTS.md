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

text <type>[optional scope]: <imperative description>  - <technical change> - <technical change> 

### Rules

- English, imperative, no trailing period
- No vague messages
- One commit = one intention

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
