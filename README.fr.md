<div align="center">

# 🔔 Home Assistant Notification Engine

**Moteur de notifications push pour Home Assistant — événements persistants, stratégies de diffusion intelligentes et bypass DND mobile.**

[![CI](https://github.com/ygiraud/ha-notification-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/ygiraud/ha-notification-engine/actions/workflows/ci.yml)
[![HACS Validation](https://github.com/ygiraud/ha-notification-engine/actions/workflows/ci.yml/badge.svg?job=HACS+Validation)](https://github.com/ygiraud/ha-notification-engine/actions/workflows/ci.yml)
[![Hassfest](https://github.com/ygiraud/ha-notification-engine/actions/workflows/ci.yml/badge.svg?job=Hassfest)](https://github.com/ygiraud/ha-notification-engine/actions/workflows/ci.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-1.0.1-blue.svg)](https://github.com/ygiraud/ha-notification-engine/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🇬🇧 [English version](README.md)

</div>

---

## 📋 Table des matières

- [Fonctionnalités](#-fonctionnalités)
- [Prérequis](#-prérequis)
- [Installation](#-installation)
- [Stratégies de diffusion](#-stratégies-de-diffusion)
- [Services disponibles](#-services-disponibles)
- [Exemples d'automatisations](#-exemples-dautomatisations)
- [Dashboard Lovelace](#-dashboard-lovelace)
- [Comportement DND mobile](#-comportement-dnd-mobile)
- [Dépannage](#-dépannage)
- [Structure du dépôt](#-structure-du-dépôt)

---

## ✨ Fonctionnalités

- **Événements persistants** stockés dans `.storage/notification_engine_events.json` — survivent aux redémarrages
- **5 stratégies de diffusion** adaptées à la présence, la distance et l'urgence
- **Déduplication idempotente** via des clés d'événement — créer deux fois le même événement n'envoie qu'une notification
- **Gestion des actions mobiles** (`DONE` et actions custom) directement dans l'intégration
- **Dashboard Lovelace** installable et synchronisable depuis les options de l'intégration
- **Bilingue** — interface disponible en français et en anglais

---

## 📦 Prérequis

| Prérequis | Détails |
|---|---|
| Home Assistant | Avec mobile app configurée (`notify.mobile_app_*`) |
| Capteurs de distance | Requis par personne pour la stratégie `away_reminder` (`proximity_sensor`) |
| `auto-entities` | Pour le dashboard Lovelace inclus |
| `mushroom` | Pour le dashboard Lovelace inclus |
| `button-card` | Pour le dashboard Lovelace inclus |

---

## 🚀 Installation

### Via HACS (recommandé)

1. Dans HACS, aller dans **Intégrations** → ⋮ → **Dépôts personnalisés**
2. Ajouter `https://github.com/ygiraud/ha-notification-engine` avec la catégorie **Intégration**
3. Cliquer sur **Télécharger**
4. Redémarrer Home Assistant

### Manuel

1. Copier `custom_components/notification_engine/` dans le dossier `/config/custom_components/`
2. Redémarrer Home Assistant

### Configuration initiale

1. Aller dans **Paramètres → Appareils et services → Ajouter une intégration** → chercher `Notification Engine`
2. Configurer les personnes (nom, entité `person.*`, `notify_service`, `proximity_sensor`)
3. _(Optionnel)_ Activer **Installer le dashboard dans la barre latérale** pour synchroniser le dashboard Lovelace

---

## 📬 Stratégies de diffusion

| Stratégie | Quand l'utiliser | Comportement |
|---|---|---|
| `present` | Info contextuelle pour les personnes à la maison | Envoi uniquement si la personne est actuellement à `home` |
| `asap` | Tâches à faire au retour à la maison | Envoi immédiat si `home`, sinon au prochain retour |
| `away_reminder` | Déléguer une tâche à la personne la plus proche | Basé sur la distance : envoie au plus proche ou à tous, avec tolérance configurable |
| `alert` | 🚨 Urgent — action immédiate requise | Envoi immédiat à tous, bypass DND/Focus mobile |
| `info` | Notifications éphémères | Envoi immédiat à tous, puis suppression automatique après diffusion |

### Modes `away_reminder`

| Mode | Comportement |
|---|---|
| `all` | Envoie à toutes les personnes ciblées |
| `nearest` | Envoie à la/aux personne(s) la/les plus proche(s) selon `away_reminder_tolerance_m` et `away_reminder_max_distance_m` |

> **Fallback :** si aucun capteur de distance valide n'est disponible (absent, valeur non numérique), l'intégration retombe sur un envoi à toutes les personnes ciblées.

---

## 🛠 Services disponibles

| Service | Description |
|---|---|
| `notification_engine.create_event` | Créer un événement de notification (idempotent) |
| `notification_engine.list_events` | Lister tous les événements en attente |
| `notification_engine.send_info` | Envoyer une notification info éphémère |
| `notification_engine.process_events` | Déclencher manuellement le traitement des événements |
| `notification_engine.delete_event` | Supprimer un événement par clé logique ou id interne |
| `notification_engine.purge_events` | Supprimer tous les événements |

**Contrat de réponse :**

```yaml
# Succès
{"ok": true, ...}

# Erreur
{"ok": false, "error": "..."}
```

---

## 💡 Exemples d'automatisations

### `present` — Envoyer uniquement si la personne est à la maison

Utile pour les rappels contextuels (ex. linge terminé, lumières oubliées).

```yaml
automation:
  alias: "Notif: machine à laver terminée (present)"
  trigger:
    - platform: state
      entity_id: sensor.lave_linge
      to: "done"
  action:
    - service: notification_engine.create_event
      target:
        entity_id: person.alice
      data:
        key: lave_linge_termine
        strategy: present
        title: "🫧 Linge terminé"
        message: "La machine a fini. N'oublie pas d'étendre !"
        actions: '[{"action":"DONE","title":"✅ Fait"}]'
```

---

### `asap` — Envoyer au prochain retour à la maison

Utile pour les tâches à effectuer dès l'arrivée.

```yaml
automation:
  alias: "Notif: colis reçu — à ramasser"
  trigger:
    - platform: state
      entity_id: binary_sensor.sonnette_colis
      to: "on"
  action:
    - service: notification_engine.create_event
      target:
        entity_id:
          - person.alice
          - person.bob
      data:
        key: colis_a_ramasser
        strategy: asap
        title: "📦 Colis livré"
        message: "Un colis est arrivé. Pense à le rentrer."
        actions: '[{"action":"DONE","title":"✅ Récupéré"}]'
```

---

### `away_reminder` — Notifier la personne la plus proche

Utile pour déléguer une tâche à celui qui est le plus proche (ex. courses, récupérer les enfants).

```yaml
automation:
  alias: "Notif: acheter du pain (personne la plus proche)"
  trigger:
    - platform: time
      at: "17:00:00"
  action:
    - service: notification_engine.create_event
      target:
        entity_id:
          - person.alice
          - person.bob
      data:
        key: acheter_pain
        strategy: away_reminder
        title: "🥖 Acheter du pain"
        message: "N'oublie pas de prendre du pain en rentrant."
        actions: '[{"action":"DONE","title":"✅ Pris"}]'
```

---

### `alert` — Urgent / bypass DND

À utiliser avec parcimonie — traverse le mode Focus/Ne pas déranger sur iOS et Android.

```yaml
automation:
  alias: "Alerte: fuite d'eau détectée"
  trigger:
    - platform: state
      entity_id: binary_sensor.detecteur_fuite_cuisine
      to: "on"
  action:
    - service: notification_engine.create_event
      target:
        entity_id:
          - person.alice
          - person.bob
      data:
        key: fuite_eau_cuisine
        strategy: alert
        title: "🚨 Fuite d'eau !"
        message: "Une fuite a été détectée dans la cuisine. Action immédiate requise."
        actions: '[{"action":"DONE","title":"✅ Géré"}]'
```

---

### `info` — Notification éphémère (supprimée automatiquement)

Utile pour les mises à jour de statut ponctuelles qui ne nécessitent pas d'accusé de réception.

```yaml
automation:
  alias: "Info: Home Assistant redémarré"
  trigger:
    - platform: homeassistant
      event: start
  action:
    - service: notification_engine.create_event
      target:
        entity_id:
          - person.alice
          - person.bob
      data:
        key: ha_redemarrage
        strategy: info
        title: "🏠 Home Assistant démarré"
        message: "Home Assistant a redémarré avec succès."
```

---

### Supprimer ou purger des événements

```yaml
# Supprimer un événement spécifique par clé
- service: notification_engine.delete_event
  data:
    key: lave_linge_termine

# Purger tous les événements
- service: notification_engine.purge_events
```

---

## 📊 Dashboard Lovelace

Un dashboard pré-construit est inclus et peut être installé directement depuis les options de l'intégration.

**Emplacement du fichier :**
```
custom_components/notification_engine/dashboards/notification_engine_dashboard.yaml
```

**Entité de support** (créée automatiquement) :
- `text.notification_engine_test_targets` — sélection multi-personnes pour les tests


---

## 📱 Comportement DND mobile

| Stratégie | Android | iOS |
|---|---|---|
| `alert` | `ttl: 0`, `priority: high`, `channel: alarm_stream` | `interruption-level: critical` avec son critique |
| Toutes les autres | Pas de bypass DND | Pas de bypass DND |

> ⚠️ **`alert` est volontairement intrusif.** Sur iPhone, il est conçu pour traverser Focus / Ne pas déranger et produire une alerte sonore critique. Sur Android, le comportement final dépend aussi de la façon dont l'appareil gère le canal `alarm_stream` et ses paramètres système de notifications.
>
> Utiliser `alert` uniquement pour les situations qui exigent une action immédiate. Pour le non critique, préférer `info`, `present`, `asap` ou `away_reminder`.

---

## 🔧 Dépannage

**Événement créé mais aucune notification envoyée ?**

Vérifier les points suivants :
- La personne existe dans `notification_engine.people`
- `enabled: true` est configuré pour la personne
- `notify_service` est valide et fonctionnel (tester manuellement depuis les Outils de développement)
- Le `target` du service correspond à des entités `person.*` configurées

**`away_reminder` n'utilise pas la distance ?**

L'intégration retombe sur un envoi à toutes les personnes ciblées quand :
- `proximity_sensor` n'est pas configuré pour la personne
- L'entité capteur n'existe pas dans HA
- L'état du capteur est non numérique
- Aucun capteur de distance valide n'est disponible parmi les cibles

---

## 📁 Structure du dépôt

```text
custom_components/
  notification_engine/
    __init__.py          # Initialisation de l'intégration & enregistrement des services
    config_flow.py       # Flux de configuration UI
    const.py             # Constantes
    event_engine.py      # Logique de diffusion principale
    manifest.json        # Métadonnées de l'intégration
    sensor.py            # Entités capteurs
    services.yaml        # Définition des services
    text.py              # Entités texte
    dashboards/
      notification_engine_dashboard.yaml
    translations/
      en.json
      fr.json
tests/
  test_event_engine.py
.github/
  workflows/
    ci.yml               # CI : tests, validation HACS, Hassfest
```

> **Hygiène du dépôt** — ne pas versionner : `.storage/notification_engine_events.json`, `__pycache__/`, `*.pyc`, `.DS_Store`

---

## 🗺 Roadmap

### v1.1.0

- **TTL des événements** — champ optionnel `ttl_hours` sur `create_event` ; les événements expirés sont supprimés automatiquement lors du `process_events`
- **Re-notification** — renvoi d'un événement `asap` non acquitté après un délai configurable
- **Filtres sur `purge_events`** — filtrer par stratégie, statut ou ancienneté (`older_than_hours`)
- **Service `get_event`** — récupérer un événement par `key` ou `id`, utile pour les conditions de templates dans les automatisations

### v1.2.0

- **Action `snooze`** — reporter un événement de N minutes depuis la notification mobile, sans le supprimer
- **Cibles notify alternatives** — support des services notify au-delà de `mobile_app_*` (Pushover, Telegram, etc.)
