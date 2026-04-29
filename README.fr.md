# Home Assistant Notification Engine

Moteur de notifications push pour Home Assistant, avec persistance d'événements et stratégies de diffusion.

Version anglaise: [README.md](README.md)

## Fonctionnalités

- Services `notification_engine.*` pour créer, traiter, supprimer et purger des événements
- Persistance des événements dans `.storage/notification_engine_events.json`
- Stratégies de diffusion:
  - `present`
  - `asap`
  - `away_reminder`
  - `alert`
  - `info`
- Gestion des actions mobiles (`DONE` et actions custom) dans l'intégration
- Dashboard Lovelace YAML installable/synchronisable depuis les options de l'intégration

## Structure du dépôt

```text
custom_components/
  notification_engine/
    __init__.py
    config_flow.py
    const.py
    event_engine.py
    manifest.json
    sensor.py
    services.yaml
    text.py
    dashboards/
      notification_engine_dashboard.yaml
    translations/
      en.json
      fr.json
```

## Prérequis

- Home Assistant avec mobile app configurée (`notify.mobile_app_*`)
- Capteurs de distance configurés par personne (`proximity_sensor`) pour utiliser `away_reminder` en mode distance
- Pour le dashboard fourni:
  - `auto-entities`
  - `mushroom`
  - `button-card`

## Installation

1. Installer via HACS (repo custom) ou copier `custom_components/notification_engine/` dans `/config/custom_components/notification_engine/`.
2. Redémarrer Home Assistant.
3. Ajouter l'intégration: Paramètres > Appareils et services > Ajouter une intégration > `Notification Engine`.
4. Configurer les personnes dans l'UI de l'intégration.
5. Optionnel: activer `Install dashboard in sidebar` pour installer/synchroniser le dashboard YAML et l'afficher dans la barre latérale.

## Services disponibles

- `notification_engine.create_event`
- `notification_engine.list_events`
- `notification_engine.send_info`
- `notification_engine.process_events`
- `notification_engine.notify_person`
- `notification_engine.delete_event`
- `notification_engine.purge_events`

Contrat de réponse des services:

- succès: `{"ok": true, ...}`
- erreur: `{"ok": false, "error": "..."}`

## Dashboard Lovelace

Fichier dashboard versionné:

- `custom_components/notification_engine/dashboards/notification_engine_dashboard.yaml`

Entité de support créée automatiquement par l'intégration:

- `text.notification_engine_test_targets` (sélection multi-personnes pour les tests)

Note d'usage:

- Dans la carte `Destinataires de test`, cliquer sur la carte réinitialise la sélection.

## Stratégies de diffusion

- `present`: envoi uniquement aux personnes actuellement à `home`.
- `asap`: envoi immédiat si la personne est `home`, sinon envoi au prochain retour à `home`.
- `away_reminder`: logique basée sur la distance via `people.<person>.proximity_sensor`.
  - mode `all`: envoi à toutes les personnes ciblées.
  - mode `nearest`: envoi à la/aux personne(s) la/les plus proche(s) selon `away_reminder_tolerance_m` et `away_reminder_max_distance_m`.
- `alert`: envoi immédiat à toutes les personnes ciblées.
- `info`: envoi immédiat à toutes les personnes ciblées, puis suppression automatique de l'événement après diffusion.

## Breaking changes en 0.2.0

- `notification_engine.ack_event` a été supprimé.
- `notification_engine.cleanup_events` a été supprimé au profit de `notification_engine.purge_events`.
- Les actions mobiles `DONE` suppriment désormais directement l'événement au lieu de changer son statut.

## Limitation actuelle

- Le bypass DND n'est pas implémenté pour l'instant sur les notifications mobiles.
- Le bypass DND est prévu pour une version future.

## Dépannage

Si un événement est créé mais qu'aucune notification n'est envoyée, vérifier:

- la personne existe dans `notification_engine.people`
- `enabled: true`
- `notify_service` est valide et fonctionnel
- le `target` du service correspond à des entités `person.*` configurées

Fallback `away_reminder` quand la distance est inexploitable:

- `proximity_sensor` absent
- entité capteur absente
- valeur capteur non numérique
- aucun capteur de distance valide disponible parmi les cibles

Dans ces cas, l'intégration retombe sur un envoi à toutes les personnes ciblées.

## Hygiène du dépôt

Ne pas versionner:

- `.storage/notification_engine_events.json`
- `__pycache__/`
- `*.pyc`
- `.DS_Store`
