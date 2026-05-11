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

- ✅ Le correctif `hassfest` confirme par CI GitHub Actions.
- ✅ `image_url` valide sur device reel — l'image apparait correctement dans la notification push.
- ✅ `clear_notification` valide sur device reel — la notif disparait bien au depart.
- ✅ Dashboard / coordinator : risque accepte. En pratique, tout changement de config entraine un reload de la config entry qui recrée le sensor.

---

## Etat du projet au 2026-05-08

### v1.1 - Complete

- ✅ TTL
- ✅ Re-notification
- ✅ `purge_events` filters
- ✅ `get_event`
- ✅ `snooze`
- ✅ Correctif dashboard sur la selection des cibles de test

### v1.2 - Pret pour release

- ✅ `image_url` sur `create_event` et `send_info`
- ✅ Reset on departure
- ✅ Correctif dashboard (filtrage `configured_people`, boutons de test)
- ✅ Validation CI + device

---

## Next Steps

1. Taguer `v1.2.0` sur la branche `v1.2.0-pre` et merger dans `main`
