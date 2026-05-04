# HANDOFF.md

## Last Agent

- Name: Codex
- Date: 2026-05-07 Europe/Paris (UTC+2)
- Context: Rebase de `v1.2.0` sur `main`, avec conservation du correctif CI `hassfest` sur `graphify-out/` et integration de la feature v1.2 `image_url` jusqu'au payload mobile HA.

---

## Objective

Continue v1.2 work on top of `main` while preserving the completed v1.1 baseline and recent CI hygiene fixes.

---

## Completed Work

- ✅ v1.1 est integree et stable sur la branche de base
- ✅ Correctif CI `hassfest`: `graphify-out/` ignore dans Git et retire de l'index
- ✅ Feature v1.2 `image_url` implementee sur `create_event` et `send_info`
- ✅ `custom_components/notification_engine/event_engine.py` : persistance de `image_url` et prise en compte dans la deduplication
- ✅ `custom_components/notification_engine/delivery.py` : mapping de `image_url` vers `data.image` dans le payload mobile Home Assistant
- ✅ `custom_components/notification_engine/services.py` : propagation de `image_url` depuis les services `create_event` et `send_info`
- ✅ `custom_components/notification_engine/services.yaml` : documentation du champ `image_url`
- ✅ `tests/test_event_engine.py` : tests pour persistance/deduplication, injection dans le payload mobile et chemin `send_info`
- ✅ Validation locale de la feature `image_url` executee avec succes lors de son implementation:
- `python3 -m py_compile custom_components/notification_engine/*.py tests/test_event_engine.py`
- `pytest tests/test_event_engine.py` -> `36 passed`

---

## Modified Files

- `custom_components/notification_engine/event_engine.py`
- `custom_components/notification_engine/delivery.py`
- `custom_components/notification_engine/services.py`
- `custom_components/notification_engine/services.yaml`
- `custom_components/notification_engine/manifest.json`
- `tests/test_event_engine.py`
- `.gitignore`
- `HANDOFF.md`

---

## Decisions

- Contrat de reponse JSON `{"ok": true/false, ...}` : IMMUABLE.
- `graphify-out/` reste un artefact local non versionne. Son `manifest.json` n'est pas un manifest Home Assistant valide et peut casser `hassfest`.
- `image_url` est optionnel sur `create_event` et `send_info`.
- `image_url` est stocke tel quel dans l'evenement.
- Le payload Home Assistant utilise la cle `data.image`, pas `image_url`.
- La deduplication de `create_event` doit tenir compte de `image_url`.
- La branche `v1.2.0` conserve une version de manifest `1.2.0-pre` pendant le developpement.

---

## Open Questions / Risks

- 🟡 Le correctif `hassfest` doit encore etre confirme par un nouveau run GitHub Actions.
- 🟡 Le support `image_url` repose sur le comportement natif des notifications mobiles Home Assistant. Aucun test device reel n'a ete execute ici.
- 🟡 La suite fonctionnelle de v1.2 apres `image_url` reste a prioriser.

---

## Etat du projet au 2026-05-07

### v1.1 - Complete

- ✅ TTL
- ✅ Re-notification
- ✅ `purge_events` filters
- ✅ `get_event`
- ✅ `snooze`

### v1.2 - In progress

- ✅ `image_url` sur `create_event`
- ✅ `image_url` sur `send_info`
- 🟡 Suite v1.2 a definir

---

## Next Steps

1. Verifier que le rebase de `v1.2.0` sur `main` est propre et termine
2. Relancer la CI, en particulier `hassfest`
3. Prioriser la prochaine feature v1.2 apres `image_url`
