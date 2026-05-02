# HANDOFF.md

## Last Agent

- Name: Codex
- Date: 2026-05-05 Europe/Paris (UTC+2)
- Context: Features v1.1 #1 et #2 validees sur HA, arbitrage de l'architecture temporelle (polling 1 minute + design snooze), puis stabilisation du dashboard Lovelace apres migration du sensor vers `has_entity_name = True` et ajout des consignes `graphify` dans la documentation agent.

---

## Objective

Implement v1.1 features one by one, each tied to a GitHub issue closed via commit message, while keeping the dashboard and agent workflow stable.

---

## Completed Work

- ✅ Feature v1.1 #1 (TTL) terminee et validee sur instance HA
- ✅ Feature v1.1 #2 (Re-notification) terminee et testee sur instance HA
- ✅ Arbitrage de l'architecture temporelle: polling conserve, cadence ramenee a 1 minute pour TTL, re-notification et futur snooze
- ✅ `custom_components/notification_engine/event_engine.py` : ajout de `ttl_hours`, `renotify_minutes`, purge TTL selective, timeout mobile calcule sur le TTL restant et re-notification basee sur les derniers envois par personne
- ✅ `custom_components/notification_engine/services.py` : validation stricte de `ttl_hours` et `renotify_minutes`, integration dans les handlers de services
- ✅ `custom_components/notification_engine/__init__.py` : traitement periodique de `process_events` et synchronisation dashboard ajustee
- ✅ `custom_components/notification_engine/delivery.py` : cleanup mobile pour les evenements expires
- ✅ `custom_components/notification_engine/services.yaml` : documentation des champs `ttl_hours` et `renotify_minutes`
- ✅ `tests/test_event_engine.py` : tests TTL, purge selective, timeout mobile, re-notification et integration dans `process_events`
- ✅ Test unitaire ajoute pour garantir qu'un evenement `info` ne declenche jamais de re-notification, meme avec `renotify_minutes`
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
- `renotify_minutes` est optionnel, strictement positif, et est pris en compte pour toutes les strategies sauf `info`.
- La purge TTL s'applique uniquement aux evenements `pending` et se declenche au debut de `process_events`.
- Les evenements expires suppriment aussi leur `tag` de notification sur les devices configures.
- La re-notification est calculee par personne, a partir du dernier envoi enregistre, et cesse des que l'evenement n'est plus `pending`.
- `renotify_minutes` definit un delai minimal avant re-emission. L'envoi effectif depend encore du prochain passage de `process_events`.
- `DEFAULT_PROCESS_EVENTS_INTERVAL` passe de 5 minutes a 1 minute (`const.py`) pour donner une precision adequate a TTL, re-notification et futur snooze.
- L'architecture polling est conservee, pas de `async_track_point_in_time` pour le moment: solution plus simple, robuste aux redemarrages HA et suffisante a cette echelle.
- Les notifications envoyees pour un evenement avec TTL embarquent aussi un `timeout` mobile calcule sur le TTL restant.
- `has_entity_name = True` est conserve pour le sensor.
- Le dashboard ne doit plus supposer un `entity_id` stable base sur le nom traduit.
- Le point d'ancrage stable du dashboard devient le `unique_id` du sensor: `notification_engine_notifications_evenements`.
- Pas de refactor plus large du dashboard: correctif minimal par injection du `entity_id` au moment de la copie du YAML.
- Pas de test ajoute pour le correctif dashboard: la logique touche a Home Assistant (`entity_registry`, config entries, Lovelace) et n'est pas testable ici sans dependances HA.
- `graphify` devient l'outil recommande pour l'analyse transversale du depot.
- Le graphe doit etre mis a jour apres des changements significatifs d'architecture, de services, de dashboard, de config flow ou de documentation reliee.
- `snooze` : architecture arbitree. Voir section "Architecture snooze (#5)" ci-dessous.
- v1.1 inclut le `snooze` (deplace depuis v1.2).
- v1.2 : uniquement les cibles notify alternatives (Pushover, Telegram, etc.).

---

## Open Questions / Risks

- 🟡 `_attr_has_entity_name = True` sur `sensor.py` : non verifie sur instance HA reelle.
- 🟡 `alert` payload critique : valide sur iOS (Critical Alerts + Focus bypass OK), non verifie sur Android (`alarm_stream` + DND bypass a tester).
- ✅ Purge TTL et cleanup mobile verifies sur instance HA apres ajout du `timeout` et du traitement periodique.
- 🟡 Le moteur reste base sur `process_events` + polling periodique. La precision des echeances reste donc bornee a 1 minute.
- 🟡 `snooze` : necessite encore l'implementation du mobile action handler dedie, meme si l'architecture est tranchee.
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
| 2 | Re-notification | #2 | completed |
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

- Re-notification : quand le snooze expire et que la notification repart, `notified_at[person]` est mis a jour. Le timer de re-notification repart de zero.
- TTL : la purge TTL s'execute en premier. Un evenement expire ne sera jamais snooze-traite. TTL gagne toujours.
- Perimetre : snooze par personne. Alice qui snooze n'affecte pas Bob.

---

## Next Steps

1. Utilisateur : terminer le rebase et verifier que l'etat Git est propre
2. Codex : passer ensuite a la feature #3 (`purge_events` filters) dans une session separee
