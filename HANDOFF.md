# HANDOFF.md

## Last Agent

- Name: Codex
- Date: 2026-05-08 Europe/Paris (UTC+2)
- Context: Correctif dashboard suite a un bug utilisateur sur la selection de cibles de test. Le helper `text.notification_engine_test_targets` pouvait contenir des valeurs parasites restaurees par HA (ex: `Test`), puis le dashboard les reinjectait telles quelles dans `target.entity_id`.

---

## Objective

Implement v1.1 features one by one, each tied to a GitHub issue closed via commit message, while keeping the dashboard and agent workflow stable.

---

## Completed Work

- ✅ Le dashboard de test n'affiche plus toutes les entites `person`, seulement celles configurees dans le module
- ✅ `custom_components/notification_engine/sensor.py` expose maintenant `configured_people` dans les attributs du sensor d'evenements
- ✅ `custom_components/notification_engine/dashboards/notification_engine_dashboard.yaml` filtre l'affichage et les cibles de test sur `configured_people`
- ✅ Dashboard de test durci contre les valeurs invalides dans `text.notification_engine_test_targets`
- ✅ `custom_components/notification_engine/dashboards/notification_engine_dashboard.yaml` : la selection des personnes ignore desormais toute entree qui ne commence pas par `person.`
- ✅ Boutons de test `create_event` : `target.entity_id` filtre desormais les valeurs non `person.*` avant appel du service
- ✅ Feature v1.1 #1 (TTL) terminee et validee sur instance HA
- ✅ Feature v1.1 #2 (Re-notification) terminee et testee sur instance HA
- ✅ Feature v1.1 #3 (`purge_events` filters) terminee
- ✅ Feature v1.1 #4 (`get_event` service) terminee
- ✅ Feature v1.1 #5 (`snooze` action) terminee
- ✅ Arbitrage de l'architecture temporelle: polling conserve, cadence ramenee a 1 minute pour TTL, re-notification et snooze
- ✅ `custom_components/notification_engine/event_engine.py` : ajout de `ttl_hours`, `renotify_minutes`, filtres de purge, methodes `get_event()` / `get_event_by_key()`, champ `snoozed_until` et logique `snooze_event()`
- ✅ `custom_components/notification_engine/services.py` : validation stricte de `ttl_hours`, `renotify_minutes` et `older_than_hours`, handlers de services, handler read-only `async_get_event()` et listener mobile pour `SNOOZE_<N>`
- ✅ `custom_components/notification_engine/__init__.py` : traitement periodique de `process_events`, enregistrement du service `notification_engine.get_event` et synchronisation dashboard ajustee
- ✅ `custom_components/notification_engine/delivery.py` : cleanup mobile pour les evenements expires, purges ou snoozees par device
- ✅ `custom_components/notification_engine/services.yaml` : documentation des champs `ttl_hours`, `renotify_minutes`, des filtres `purge_events` et du service `get_event`
- ✅ `tests/test_event_engine.py` : tests TTL, purge selective, timeout mobile, re-notification, `get_event`, snooze et integration dans `process_events`
- ✅ Tests unitaires ajoutes pour garantir qu'un evenement `info` ne declenche jamais de re-notification, pour valider `older_than_hours`, la purge selective, le cas d'un `created_at` invalide, la recherche par `key` / `id`, les erreurs du service, la persistance du snooze, la logique active/due, le reenvoi apres expiration et le listener mobile
- ✅ Tests executes avec succes pour la feature #5: `pytest tests/test_event_engine.py` -> `34 passed`
- ✅ `custom_components/notification_engine/__init__.py` : resolution du vrai `entity_id` du sensor via l'entity registry a partir du `unique_id`
- ✅ Installation du dashboard YAML templatisee avec injection du vrai `entity_id` du sensor d'evenements
- ✅ `custom_components/notification_engine/dashboards/notification_engine_dashboard.yaml` : remplacement du hardcode `sensor.notifications_evenements` par un placeholder injecte a l'installation
- ✅ Traductions du sensor raccourcies en `Events` / `Événements` pour rester coherentes avec `_attr_has_entity_name = True`
- ✅ Verification syntaxique locale via `python3 -m py_compile custom_components/notification_engine/__init__.py custom_components/notification_engine/sensor.py`
- ✅ Verification JSON locale via `json.loads(...)` sur `translations/en.json`, `translations/fr.json` et `strings.json`
- ✅ Graphe `graphify` genere pour le depot (`graphify-out/graph.html`, `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md`)
- ✅ `AGENTS.md` complete avec des regles d'usage et de mise a jour de `graphify`
- ✅ Correctif CI `hassfest`: `graphify-out/` ajoute au `.gitignore` et retire de l'index Git pour eviter qu'un faux `manifest.json` soit pris en compte

---

## Modified Files

- `custom_components/notification_engine/dashboards/notification_engine_dashboard.yaml`
- `custom_components/notification_engine/sensor.py`
- `HANDOFF.md`
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
- `.gitignore`
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
- `purge_events` conserve son comportement historique sans filtre (purge totale), mais accepte maintenant des filtres optionnels combines en mode `AND` sur `strategy`, `status` et `older_than_hours`.
- `older_than_hours` est optionnel et doit etre strictement positif. Valeur invalide -> erreur de service `invalid_older_than_hours`.
- Avec un filtre `older_than_hours`, un evenement sans `created_at` exploitable n'est pas purge.
- `get_event` est un service read-only. Par `id`, il retourne l'evenement exact. Par `key`, il retourne le premier evenement `pending` correspondant, pour rester coherent avec `delete_event`.
- Le handler `get_event` retourne `missing_key_or_id` si aucun identifiant n'est fourni, et `event_not_found` si rien ne correspond.
- La purge TTL s'applique uniquement aux evenements `pending` et se declenche au debut de `process_events`.
- Les evenements expires suppriment aussi leur `tag` de notification sur les devices configures.
- La re-notification est calculee par personne, a partir du dernier envoi enregistre, et cesse des que l'evenement n'est plus `pending`.
- `renotify_minutes` definit un delai minimal avant re-emission. L'envoi effectif depend encore du prochain passage de `process_events`.
- `DEFAULT_PROCESS_EVENTS_INTERVAL` passe de 5 minutes a 1 minute (`const.py`) pour donner une precision adequate a TTL, re-notification et snooze.
- L'architecture polling est conservee, pas de `async_track_point_in_time` pour le moment: solution plus simple, robuste aux redemarrages HA et suffisante a cette echelle.
- Les notifications envoyees pour un evenement avec TTL embarquent aussi un `timeout` mobile calcule sur le TTL restant.
- `snooze` est gere par actions mobiles `SNOOZE_<N>` sans nouveau champ sur `create_event`.
- Le snooze est par personne, stocke dans `snoozed_until`, et bloque l'envoi tant que l'echeance n'est pas atteinte.
- Quand le snooze expire, une unique notification repart pour cette personne, puis l'entree `snoozed_until` est nettoyee lors du nouvel envoi.
- L'identite de la personne est transmise dans le payload mobile via `person_entity` / `action_data.person_entity` pour permettre au listener de resoudre l'acteur de facon deterministe.
- `has_entity_name = True` est conserve pour le sensor.
- Le dashboard ne doit plus supposer un `entity_id` stable base sur le nom traduit.
- Le point d'ancrage stable du dashboard devient le `unique_id` du sensor: `notification_engine_notifications_evenements`.
- Pas de refactor plus large du dashboard: correctif minimal par injection du `entity_id` au moment de la copie du YAML.
- Pas de test ajoute pour le correctif dashboard: la logique touche a Home Assistant (`entity_registry`, config entries, Lovelace) et n'est pas testable ici sans dependances HA.
- `graphify` devient l'outil recommande pour l'analyse transversale du depot.
- `graphify-out/` doit rester un artefact local non versionne. Son `manifest.json` n'est pas un manifest Home Assistant valide et peut casser `hassfest`.
- Le graphe doit etre mis a jour apres des changements significatifs d'architecture, de services, de dashboard, de config flow ou de documentation reliee.
- v1.1 inclut le `snooze` (deplace depuis v1.2).
- v1.2 : uniquement les cibles notify alternatives (Pushover, Telegram, etc.).

---

## Open Questions / Risks

- 🟡 `_attr_has_entity_name = True` sur `sensor.py` : non verifie sur instance HA reelle.
- 🟡 `alert` payload critique : valide sur iOS (Critical Alerts + Focus bypass OK), non verifie sur Android (`alarm_stream` + DND bypass a tester).
- ✅ Purge TTL et cleanup mobile verifies sur instance HA apres ajout du `timeout` et du traitement periodique.
- 🟡 Le moteur reste base sur `process_events` + polling periodique. La precision des echeances reste donc bornee a 1 minute.
- 🟡 Sur une installation existante, l'entity registry peut conserver un ancien `entity_id` ou un slug different selon l'historique local. Le dashboard suivra ce `entity_id` reel apres reinstallation / resynchronisation, mais ce comportement n'a pas ete verifie sur instance HA reelle ici.
- 🟡 Si la resolution par `unique_id` echoue au moment de l'installation du dashboard, fallback sur `sensor.notifications_evenements`. Ce fallback evite un fichier vide mais peut rester faux sur certaines installations atypiques.
- 🟡 Le correctif dashboard a ete verifie syntaxiquement et structurellement, pas sur une instance Home Assistant reelle dans cet environnement.
- 🟡 Le diagnostic `hassfest` repose sur l'hypothese que l'action scanne le faux `graphify-out/manifest.json`. Le correctif est coherent avec la panne observee, mais doit etre confirme par un nouveau run GitHub Actions.

---

## Etat du projet au 2026-05-05

### v1.0.0 - Complete

- ✅ All v1.0.0 features shipped (see previous HANDOFF entries)
- ✅ Commit + tag v1.0.0 done by user
- ✅ Roadmap updated: snooze moved from v1.2 -> v1.1
- ✅ AGENTS.md updated: GitHub issue closing convention + v1.1 feature table

### v1.1 - Complete

5 features implemented and reviewed:

| # | Feature | GitHub Issue | Status |
|---|---|---|---|
| 1 | Event TTL | #1 | ✅ completed |
| 2 | Re-notification | #2 | ✅ completed |
| 3 | `purge_events` filters | #3 | ✅ completed |
| 4 | `get_event` service | #4 | ✅ completed |
| 5 | `snooze` action | #5 | ✅ completed |

Pre-release tag: `v1.1.0-rc.1` (testing in progress)

---

## Structure des fichiers cles

```
custom_components/notification_engine/
  __init__.py        # Setup, dashboard, config
  services.py        # NotificationEngineServices (handlers + listeners)
  delivery.py        # Livraison, HomeAssistantError
  event_engine.py    # Moteur pur (TTL, re-notification, snooze)
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

1. Utilisateur : tester la pre-release `v1.1.0-rc.1` sur instance HA
2. Claude / Codex : traiter les bugs remontes pendant la periode de test
3. Utilisateur : tagger `v1.1.0` et publier la release HACS une fois les tests concluants

---

## Analyse feature v1.2 — Image dans les notifications

### Contexte

L'app mobile HA supporte nativement un champ `image` dans le `data` du payload notify. Il peut être une URL HTTP/HTTPS publique ou un chemin `/local/` servi par HA (dossier `www/` de la config). Cette feature ajoute un champ optionnel `image_url` sur `create_event` et `send_info`.

### Fichiers à modifier (4)

**`event_engine.py`**
- Ajouter `image_url: str = ""` à la signature de `make_event`
- Persister `image_url` dans le dict retourné par `make_event`
- Ajouter `image_url` dans la déduplication de `create_event` (comparer `event.get("image_url", "") == image_url`)
- Dans `normalize_event` : passer le champ tel quel, pas de logique particulière

**`delivery.py`**
- Dans `send_to_notify` : ajouter un paramètre `image_url: str = ""`
- Si `image_url` est non vide, injecter `payload["data"]["image"] = image_url` (la clé HA s'appelle `image`, pas `image_url`)
- Dans `process_events_core` : passer `image_url=str(event.get("image_url", ""))` à l'appel `send_to_notify`

**`services.py`**
- Dans `async_create_event` : récupérer `str(call.data.get("image_url", ""))`, le passer à `engine.create_event`
- Dans `async_send_info` : idem, passer directement à `send_to_notify`
- Mettre à jour la signature de l'appel à `engine.create_event` (12 args → 13)

**`services.yaml`**
- Ajouter le champ `image_url` (optionnel, `selector: text:`) aux services `create_event` et `send_info`

### Points d'attention

- Le champ s'appelle `image` dans le payload HA mais `image_url` côté service pour être explicite (cohérent avec la convention du projet).
- Ne pas valider le format de l'URL dans le moteur — laisser HA gérer les erreurs de fetch d'image.
- Ajouter `image_url` dans les tests de déduplication de `test_event_engine.py`.
- Le champ `image_url` n'est pas un critère de sélection de destinataires, il est juste pass-through.
- Compatible avec toutes les strategies sans cas particulier.
