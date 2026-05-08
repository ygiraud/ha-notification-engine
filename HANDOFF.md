# HANDOFF.md

## Last Agent

- Name: Codex
- Date: 2026-05-08 Europe/Paris (UTC+2)
- Context: Port du correctif dashboard depuis `main` vers `v1.2.0` pendant que la branche conserve son travail v1.2 en cours.

---

## Objective

Finaliser la feature "reset de notification au départ" pour la stratégie `present` : quand une personne quitte le domicile sans avoir traité l'event (ex. machine à laver), on efface la notif de son téléphone et on réinitialise son état "notifié" afin qu'elle soit re-notifiée à son prochain retour.

---

## Completed Work

- ✅ v1.1 stable sur `main`
- ✅ Correctif CI `hassfest` : `graphify-out/` ignoré dans Git
- ✅ Feature v1.2 `image_url` implementee sur `create_event` et `send_info`
- ✅ `custom_components/notification_engine/event_engine.py` : persistance de `image_url` et prise en compte dans la deduplication
- ✅ `custom_components/notification_engine/delivery.py` : mapping de `image_url` vers `data.image` dans le payload mobile HA
- ✅ `custom_components/notification_engine/services.py` : propagation de `image_url` depuis les services `create_event` et `send_info`
- ✅ `custom_components/notification_engine/services.yaml` : documentation du champ `image_url`
- ✅ `tests/test_event_engine.py` : tests pour persistance/deduplication, injection dans le payload mobile et chemin `send_info`
- ✅ `custom_components/notification_engine/event_engine.py` : ajout de `unnotify_person()` pour nettoyer `notified_people`, `notified_at` et `snoozed_until`
- ✅ `custom_components/notification_engine/services.py` : `async_on_state_changed()` gère maintenant les départs pour les events `present` en attente
- ✅ `tests/test_event_engine.py` : 5 nouveaux tests couvrent `unnotify_person()` et le cycle arrivée -> départ -> retour
- ✅ Validation locale : `python3 -m py_compile custom_components/notification_engine/*.py tests/test_event_engine.py`
- ✅ Validation locale : `pytest tests/test_event_engine.py` -> `41 passed`
- ✅ Port du correctif dashboard depuis `main`
- ✅ `custom_components/notification_engine/sensor.py` expose maintenant `configured_people` dans les attributs du sensor d'evenements
- ✅ `custom_components/notification_engine/dashboards/notification_engine_dashboard.yaml` n'affiche plus que les personnes configurees dans le module
- ✅ Les boutons de test du dashboard ignorent les valeurs restaurees invalides dans `text.notification_engine_test_targets` et ne ciblent plus que des `person.*` configures

---

## Decisions

- Contrat de reponse JSON `{"ok": true/false, ...}` : IMMUABLE.
- `graphify-out/` reste un artefact local non versionne.
- Le reset au départ s'applique uniquement à la strategy `present`.
- `unnotify_person` doit aussi nettoyer `snoozed_until` (cohérence avec `notify_person` qui le fait dans l'autre sens).
- `people` dans `async_on_state_changed` doit être le dict complet retourné par `people_config()`, pas un `set` de clés.
- Aucun changement de surface de service n'est nécessaire pour cette feature.
- Le port depuis `main` conserve le correctif dashboard, mais pas le bump de version `1.1.1` sur cette branche `v1.2.0-pre`.

---

## Modified Files

- `custom_components/notification_engine/event_engine.py`
- `custom_components/notification_engine/services.py`
- `custom_components/notification_engine/sensor.py`
- `custom_components/notification_engine/dashboards/notification_engine_dashboard.yaml`
- `tests/test_event_engine.py`
- `HANDOFF.md`

---

## Open Questions / Risks

- 🟡 Le correctif `hassfest` doit encore etre confirme par un nouveau run GitHub Actions.
- 🟡 Le support `image_url` repose sur le comportement natif des notifications mobiles HA. Aucun test device reel n'a ete execute.
- 🟡 Le comportement "clear_notification" reste dependant des integrations `mobile_app_*` ciblees. Il n'y a pas eu de validation device reelle sur ce reset.
- 🟡 Le dashboard filtre maintenant sur `configured_people`. Si la config change et que le sensor ne se refresh pas immediatement, l'affichage peut attendre le prochain refresh/coordinator.

---

## Etat du projet au 2026-05-08

### v1.1 - Complete

- ✅ TTL
- ✅ Re-notification
- ✅ `purge_events` filters
- ✅ `get_event`
- ✅ `snooze`
- ✅ Correctif dashboard sur la selection des cibles de test

### v1.2 - In progress

- ✅ `image_url` sur `create_event` et `send_info`
- ✅ Reset on departure - priorite 1
- 🔲 Alternative notify targets - priorite 2 (support de services notify au-dela de `mobile_app_*` : Pushover, Telegram, etc.) - specifie dans `README.md`, non encore conçu

---

## Next Steps

1. Concevoir la feature "Alternative notify targets" en verifiant d'abord l'impact sur `delivery.py`, `services.py`, `README.md` et les tests
2. Valider le correctif `hassfest` et les tests via CI GitHub Actions
3. Si necessaire, declencher un refresh explicite du coordinator apres changement de config pour que `configured_people` se mette a jour immediatement dans le dashboard
