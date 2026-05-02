# HANDOFF.md

## Last Agent

- Name: Codex
- Date: 2026-05-02 Europe/Paris (UTC+2)
- Context: Feature v1.1 #2 implemented and tested on HA: optional re-notification via `renotify_minutes`, plus architecture concern identified around time-based scheduling.

---

## Objective

Implement v1.1 features one by one, each tied to a GitHub issue closed via commit message.

---

## Etat du projet au 2026-05-01

### v1.0.0 - Complete

- ✅ All v1.0.0 features shipped (see previous HANDOFF entries)
- ✅ Commit + tag v1.0.0 done by user
- ✅ Roadmap updated: snooze moved from v1.2 -> v1.1
- ✅ AGENTS.md updated: GitHub issue closing convention + v1.1 feature table

### v1.1 - In progress

5 features tracked for implementation:

| # | Feature | GitHub Issue | Status |
|---|---|---|---|
| 1 | Event TTL | #1 | completed |
| 2 | Re-notification | #2 | completed |
| 3 | `purge_events` filters | #3 | pending |
| 4 | `get_event` service | #4 | pending |
| 5 | `snooze` action | #5 | pending |

---

## Decisions actives

- Contrat de reponse JSON `{"ok": true/false, ...}` : IMMUABLE.
- Tests : Python pur uniquement (pas de dependance HA dans les tests).
- `pytest-homeassistant-custom-component` : REPORTE. Trop lourd pour ce projet.
- `alert` bypass DND : iOS critical + Android `alarm_stream`. Semantique "alerte = critique" sans flag supplementaire.
- `ttl_hours` est optionnel et doit etre strictement positif. Valeur invalide -> erreur de service `invalid_ttl_hours`.
- La purge TTL s'applique uniquement aux evenements `pending` et se declenche au debut de `process_events`.
- Les evenements expires suppriment aussi leur `tag` de notification sur les devices configures.
- `process_events` est maintenant aussi declenche periodiquement toutes les 5 minutes pour rendre le TTL utile sans action manuelle.
- Les notifications envoyees pour un evenement avec TTL embarquent aussi un `timeout` mobile calcule sur le TTL restant.
- `renotify_minutes` est optionnel, strictement positif, et est pris en compte pour toutes les strategies sauf `info`.
- La re-notification est calculee par personne, a partir du dernier envoi enregistre, et cesse des que l'evenement n'est plus `pending`.
- `renotify_minutes` definit un delai minimal avant re-emission. L'envoi effectif depend encore du prochain passage de `process_events`.
- `DEFAULT_PROCESS_EVENTS_INTERVAL` passe de 5 minutes a 1 minute (`const.py`) pour donner une precision adequate a TTL, re-notification et futur snooze. Architecture polling conservee (pas de `async_track_point_in_time`) : simple, resiliente aux redemarrages HA, overhead negligeable.
- `snooze` : architecture arbitree. Voir section "Architecture snooze (#5)" ci-dessous.
- v1.1 inclut le `snooze` (deplace depuis v1.2).
- v1.2 : uniquement les cibles notify alternatives (Pushover, Telegram, etc.).

---

## Risques ouverts

- 🟡 `alert` payload critique : valide sur iOS (Critical Alerts + Focus bypass OK). Non verifie sur Android (`alarm_stream` + DND bypass a tester).

---

## Structure des fichiers cles

```
custom_components/notification_engine/
  __init__.py        # Setup, dashboard, config
  services.py        # NotificationEngineServices (handlers + listeners)
  delivery.py        # Livraison, HomeAssistantError
  event_engine.py    # Moteur pur (TTL, re-notification, snooze iront ici)
  sensor.py          # _attr_has_entity_name = True
  const.py           # Constantes centralisees
  services.yaml      # Definitions des services HA
  strings.json       # Chaines UI (source)
  translations/
    en.json
    fr.json
tests/
  test_event_engine.py
```

---

## Completed Work

- Ajout du champ optionnel `ttl_hours` sur `create_event` avec validation stricte (> 0).
- Persistance de `ttl_hours` dans `event_engine.py` et prise en compte dans la deduplication.
- Ajout de `purge_expired_events()` et purge automatique au debut de `process_events`.
- Nettoyage des tags de notification pour les evenements expires.
- Ajout d'un declenchement periodique de `process_events` toutes les 5 minutes.
- Ajout d'un `timeout` mobile calcule a partir du TTL restant pour auto-effacer les notifications cote telephone.
- Ajout du champ optionnel `renotify_minutes` sur `create_event`.
- Persistance de `renotify_minutes` et des timestamps de notification par personne dans `event_engine.py`.
- Re-notification des evenements non acquittes apres le delai configure pour toutes les strategies sauf `info`.
- Tests HA concluants sur la logique de re-notification, avec reserve sur la granularite du scheduling.
- Documentation service mise a jour dans `services.yaml`.
- Tests unitaires ajoutes pour stockage TTL, validation, purge selective, timeout mobile, re-notification et integration dans `process_events`.
- Ajout d'un test unitaire couvrant explicitement qu'un evenement `info` ne declenche jamais de re-notification, meme si `renotify_minutes` est configure.
- Validation manuelle reussie sur instance HA : creation avec `ttl_hours`, expiration, suppression de l'evenement et disparition de la notification mobile.

---

## Modified Files

- `custom_components/notification_engine/event_engine.py`
- `custom_components/notification_engine/services.py`
- `custom_components/notification_engine/delivery.py`
- `custom_components/notification_engine/__init__.py`
- `custom_components/notification_engine/const.py`
- `custom_components/notification_engine/services.yaml`
- `tests/test_event_engine.py`
- `HANDOFF.md`

---

## Architecture snooze (#5)

### Declenchement

L'utilisateur ajoute une action de pattern `SNOOZE_<N>` dans le champ `actions` de `create_event` (N = minutes) :

```yaml
actions: '[{"action":"SNOOZE_30","title":"🔕 30 min"},{"action":"DONE","title":"✅ Fait"}]'
```

Le listener `mobile_app_notification_action` existant detecte les actions matchant `SNOOZE_\d+`, extrait N, et appelle `engine.snooze_event(tag, person_entity, minutes=N)`. Aucun nouveau champ sur `create_event`.

### Modele de donnees

Nouveau champ `snoozed_until` dans l'evenement : dict par personne, calque sur `notified_at`.

```json
{
  "snoozed_until": {
    "person.alice": "2026-05-02T10:30:00+00:00"
  }
}
```

### Comportement dans `process_events`

Avant d'envoyer a une personne : si `now < snoozed_until[person]`, skip. Apres expiration, la notification repart normalement.

### Interactions

- **Re-notification** : quand le snooze expire et que la notification repart, `notified_at[person]` est mis a jour. Le timer de re-notification repart de zero.
- **TTL** : la purge TTL s'execute en premier. Un evenement expire ne sera jamais snooze-traite. TTL gagne toujours.
- **Perimetre** : snooze par personne. Alice qui snooze n'affecte pas Bob.

---

## Next Steps

1. Codex : continuer avec la feature #3 (`purge_events` filters)
