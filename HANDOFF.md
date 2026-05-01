# HANDOFF.md

## Last Agent

- Name: Codex
- Date: 2026-05-02 Europe/Paris (UTC+2)
- Context: Feature v1.1 #1 validated on HA instance after follow-up fixes: periodic processing added and mobile notification timeout aligned with event TTL.

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
| 2 | Re-notification | #2 | pending |
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
- v1.1 inclut le `snooze` (deplace depuis v1.2).
- v1.2 : uniquement les cibles notify alternatives (Pushover, Telegram, etc.).

---

## Risques ouverts

- 🟡 `_attr_has_entity_name = True` sur `sensor.py` : non verifie sur instance HA reelle.
- 🟡 `alert` payload critique : verifie par test unitaire uniquement, pas sur device iOS/Android reel.
- ✅ Purge TTL et cleanup mobile verifies sur instance HA apres ajout du `timeout` et du traitement periodique.
- 🟡 `snooze` : necessite un mobile action handler dedie. Architecture a confirmer avant implementation (cf. AGENTS.md Per-Feature Checklist).

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
- Documentation service mise a jour dans `services.yaml`.
- Tests unitaires ajoutes pour stockage TTL, validation, purge selective, timeout mobile et integration dans `process_events`.
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

## Next Steps

1. Utilisateur : valider le commit final de la feature #1 (`Closes #1`)
2. Claude : relire l'implementation TTL si une revue croisee est souhaitee
3. Codex : passer ensuite a la feature #2 (Re-notification) dans une session separee
