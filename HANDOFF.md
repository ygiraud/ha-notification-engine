# HANDOFF.md

## Last Agent

- Name: Codex
- Date: 2026-05-05 Europe/Paris (UTC+2)
- Context: Feature v1.1 #1 validee sur instance HA, puis stabilisation du dashboard Lovelace apres migration du sensor vers `has_entity_name = True` et ajout des consignes `graphify` dans la documentation agent.

---

## Objective

Implement v1.1 features one by one, each tied to a GitHub issue closed via commit message, while keeping the dashboard and agent workflow stable.

---

## Completed Work

- ✅ Feature v1.1 #1 (TTL) terminee et validee sur instance HA
- ✅ `custom_components/notification_engine/event_engine.py` : ajout de `ttl_hours`, purge TTL selective et timeout mobile calcule sur le TTL restant
- ✅ `custom_components/notification_engine/services.py` : validation stricte de `ttl_hours` et integration dans les handlers de services
- ✅ `custom_components/notification_engine/__init__.py` : traitement periodique de `process_events` toutes les 5 minutes et synchronisation dashboard ajustee
- ✅ `custom_components/notification_engine/delivery.py` : cleanup mobile pour les evenements expires
- ✅ `custom_components/notification_engine/services.yaml` : documentation du champ `ttl_hours`
- ✅ `tests/test_event_engine.py` : tests TTL, purge selective, timeout mobile et integration dans `process_events`
- ✅ `custom_components/notification_engine/__init__.py` : resolution du vrai `entity_id` du sensor via l'entity registry a partir du `unique_id`
- ✅ Installation du dashboard YAML templatisee avec injection du vrai `entity_id` du sensor d'evenements
- ✅ `custom_components/notification_engine/dashboards/notification_engine_dashboard.yaml` : remplacement du hardcode `sensor.notifications_evenements` par un placeholder injecte a l'installation
- ✅ Traductions du sensor raccourcies en `Events` / `Événements` pour rester coherentes avec `_attr_has_entity_name = True`
- ✅ Verification syntaxique locale via `python3 -m py_compile custom_components/notification_engine/__init__.py custom_components/notification_engine/sensor.py`
- ✅ Verification JSON locale via `json.loads(...)` sur `translations/en.json`, `translations/fr.json` et `strings.json`
- ✅ Graphe `graphify` genere pour le depot (`graphify-out/graph.html`, `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md`)
- ✅ `AGENTS.md` complete avec des regles d'usage et de mise a jour de `graphify`

---

## Modified Files

- `custom_components/notification_engine/__init__.py`
- `custom_components/notification_engine/const.py`
- `custom_components/notification_engine/delivery.py`
- `custom_components/notification_engine/event_engine.py`
- `custom_components/notification_engine/services.py`
- `custom_components/notification_engine/services.yaml`
- `custom_components/notification_engine/dashboards/notification_engine_dashboard.yaml`
- `custom_components/notification_engine/translations/en.json`
- `custom_components/notification_engine/translations/fr.json`
- `tests/test_event_engine.py`
- `AGENTS.md`
- `HANDOFF.md`

---

## Decisions

- Contrat de reponse JSON `{"ok": true/false, ...}` : IMMUABLE.
- Tests : Python pur uniquement (pas de dependance HA dans les tests).
- `pytest-homeassistant-custom-component` : REPORTE. Trop lourd pour ce projet.
- `alert` bypass DND : iOS critical + Android `alarm_stream`. Semantique "alerte = critique" sans flag supplementaire.
- `ttl_hours` est optionnel et doit etre strictement positif. Valeur invalide -> erreur de service `invalid_ttl_hours`.
- La purge TTL s'applique uniquement aux evenements `pending` et se declenche au debut de `process_events`.
- Les evenements expires suppriment aussi leur `tag` de notification sur les devices configures.
- `process_events` est maintenant aussi declenche periodiquement toutes les 5 minutes pour rendre le TTL utile sans action manuelle.
- Les notifications envoyees pour un evenement avec TTL embarquent aussi un `timeout` mobile calcule sur le TTL restant.
- `has_entity_name = True` est conserve pour le sensor.
- Le dashboard ne doit plus supposer un `entity_id` stable base sur le nom traduit.
- Le point d'ancrage stable du dashboard devient le `unique_id` du sensor: `notification_engine_notifications_evenements`.
- Pas de refactor plus large du dashboard: correctif minimal par injection du `entity_id` au moment de la copie du YAML.
- Pas de test ajoute pour le correctif dashboard: la logique touche a Home Assistant (`entity_registry`, config entries, Lovelace) et n'est pas testable ici sans dependances HA.
- `graphify` devient l'outil recommande pour l'analyse transversale du depot.
- Le graphe doit etre mis a jour apres des changements significatifs d'architecture, de services, de dashboard, de config flow ou de documentation reliee.
- v1.1 inclut le `snooze` (deplace depuis v1.2).
- v1.2 : uniquement les cibles notify alternatives (Pushover, Telegram, etc.).

---

## Open Questions / Risks

- 🟡 `_attr_has_entity_name = True` sur `sensor.py` : non verifie sur instance HA reelle.
- 🟡 `alert` payload critique : verifie par test unitaire uniquement, pas sur device iOS/Android reel.
- ✅ Purge TTL et cleanup mobile verifies sur instance HA apres ajout du `timeout` et du traitement periodique.
- 🟡 `snooze` : necessite un mobile action handler dedie. Architecture a confirmer avant implementation (cf. AGENTS.md Per-Feature Checklist).
- 🟡 Sur une installation existante, l'entity registry peut conserver un ancien `entity_id` ou un slug different selon l'historique local. Le dashboard suivra ce `entity_id` reel apres reinstallation / resynchronisation, mais ce comportement n'a pas ete verifie sur instance HA reelle ici.
- 🟡 Si la resolution par `unique_id` echoue au moment de l'installation du dashboard, fallback sur `sensor.notifications_evenements`. Ce fallback evite un fichier vide mais peut rester faux sur certaines installations atypiques.
- 🟡 Le correctif dashboard a ete verifie syntaxiquement et structurellement, pas sur une instance Home Assistant reelle dans cet environnement.

---

## Etat du projet au 2026-05-05

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

## Next Steps

1. Utilisateur : terminer le rebase et verifier que l'etat Git est propre
2. Utilisateur : valider le commit final de la feature #1 (`Closes #1`) si ce n'est pas deja fait apres le rebase
3. Claude : relire l'implementation TTL si une revue croisee est souhaitee
4. Codex : passer ensuite a la feature #2 (Re-notification) dans une session separee
