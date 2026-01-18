# Nexecur - Home Assistant Integration (HACS)

![GitHub release](https://img.shields.io/github/release/Loule95450/HACS-Nexecur.svg)
![GitHub repo size](https://img.shields.io/github/repo-size/Loule95450/HACS-Nexecur.svg)
![GitHub License](https://img.shields.io/github/license/Loule95450/HACS-Nexecur.svg)

Integration Home Assistant non-officielle pour les systèmes d'alarme **Nexecur**. Cette intégration supporte les deux versions d'alarme :

- **Videofied** (ancienne version)
- **Hikvision AX PRO** (nouvelle version via GuardingVision Cloud)

---

## Fonctionnalités

### Panneau d'alarme
- Entité `alarm_control_panel` affichant l'état actuel (armé/désarmé)
- Armement total (Away) et partiel (Home/Stay)
- Désarmement depuis Home Assistant
- Polling automatique du statut (toutes les 30 secondes)

### Caméras (Videofied uniquement)
- Entités switch pour activer les flux caméra ("Allumer [Nom Caméra]")
- Entités camera pour visualiser les flux RTSP
- Découverte automatique des nouvelles caméras
- Désactivation automatique après 30 secondes (limitation API)

---

## Installation

### Via HACS (recommandé)

1. Dans HACS, ajoutez ce dépôt comme **Custom Repository** :
   - URL : `https://github.com/Loule95450/HACS-Nexecur`
   - Catégorie : `Integration`
2. Installez l'intégration **Nexecur**
3. Redémarrez Home Assistant
4. Allez dans **Paramètres > Appareils et services > Ajouter une intégration**
5. Recherchez **Nexecur**

### Installation manuelle

1. Téléchargez le dossier `custom_components/nexecur`
2. Copiez-le dans votre dossier `config/custom_components/`
3. Redémarrez Home Assistant

---

## Configuration

### Étape 1 : Choix de la version

Lors de l'ajout de l'intégration, sélectionnez votre version d'alarme :

| Version | Description |
|---------|-------------|
| **Videofied** | Ancienne version Nexecur |
| **Hikvision** | Nouvelle version (AX PRO, GuardingVision) |

---

### Configuration Videofied

| Champ | Description |
|-------|-------------|
| `ID Site` | Code de câblage/raccordement |
| `Mot de passe` | PIN / Code d'accès |
| `Nom de l'appareil` | Optionnel (défaut: "Home Assistant") |

---

### Configuration Hikvision

Choisissez votre méthode de connexion :

#### Connexion par Téléphone

| Champ | Description |
|-------|-------------|
| `Numéro de téléphone` | Votre numéro (ex: 0612345678) |
| `Mot de passe` | Mot de passe du compte Cloud |
| `Indicatif pays` | Code pays (défaut: 33 pour la France) |
| `SSID` | Nom de votre réseau WiFi |
| `Nom de l'appareil` | Optionnel (défaut: "Home Assistant") |

#### Connexion par Email

| Champ | Description |
|-------|-------------|
| `Email` | Adresse email du compte Cloud |
| `Mot de passe` | Mot de passe du compte Cloud |
| `SSID` | Nom de votre réseau WiFi |
| `Nom de l'appareil` | Optionnel (défaut: "Home Assistant") |

> **Note** : Le SSID correspond au nom de votre réseau WiFi sur lequel est connectée votre centrale.

---

## Entités créées

### Panneau d'alarme

| Entité | Description |
|--------|-------------|
| `alarm_control_panel.nexecur_alarm` | Contrôle de l'alarme |

**États possibles :**
- `disarmed` : Désarmé
- `armed_home` : Armement partiel (Stay)
- `armed_away` : Armement total (Away)

**Attributs :**
- `alarm_version` : Version de l'alarme (videofied/hikvision)
- `panel_sp1_available` : Mode SP1 disponible
- `panel_sp2_available` : Mode SP2 disponible

### Switches caméra (Videofied)

| Entité | Description |
|--------|-------------|
| `switch.allumer_[nom_camera]` | Active le flux RTSP de la caméra |

**Comportement :**
- L'activation demande un flux RTSP à l'API Nexecur
- Le switch s'éteint automatiquement après 30 secondes
- L'entité caméra n'apparaît que lorsque le switch est actif

### Caméras (Videofied)

| Entité | Description |
|--------|-------------|
| `camera.nexecur_camera_[id]_[serial]` | Flux vidéo RTSP |

---

## Exemples d'automatisations

### Armer l'alarme au départ

```yaml
automation:
  - alias: "Armer alarme au départ"
    trigger:
      - platform: state
        entity_id: group.famille
        to: "not_home"
    action:
      - service: alarm_control_panel.alarm_arm_away
        target:
          entity_id: alarm_control_panel.nexecur_alarm
```

### Désarmer à l'arrivée

```yaml
automation:
  - alias: "Désarmer alarme à l'arrivée"
    trigger:
      - platform: state
        entity_id: person.moi
        to: "home"
    action:
      - service: alarm_control_panel.alarm_disarm
        target:
          entity_id: alarm_control_panel.nexecur_alarm
```

### Notification sur changement d'état

```yaml
automation:
  - alias: "Notification état alarme"
    trigger:
      - platform: state
        entity_id: alarm_control_panel.nexecur_alarm
    action:
      - service: notify.mobile_app
        data:
          title: "Alarme Nexecur"
          message: "État: {{ states('alarm_control_panel.nexecur_alarm') }}"
```

---

## Dépannage

### Erreur d'authentification

- **Videofied** : Vérifiez l'ID site et le PIN
- **Hikvision** : Vérifiez le numéro/email et le mot de passe Cloud
- Assurez-vous d'utiliser les mêmes identifiants que l'application mobile Nexecur

### L'alarme s'arme mais affiche "désarmé"

Ce problème a été corrigé dans la version 3.0.2+. Mettez à jour l'intégration.

### Les caméras ne s'affichent pas

- Les caméras ne sont disponibles que pour la version **Videofied**
- Activez le switch correspondant pour voir le flux
- Le flux expire après 30 secondes (limitation API)

### Erreur "请输入正确的用户名或密码"

Message chinois signifiant "Identifiants incorrects". Vérifiez :
- Le format du numéro de téléphone
- Le mot de passe Cloud (pas le PIN de l'alarme)
- La méthode de connexion (téléphone vs email)

### L'état ne se met pas à jour

L'intégration interroge l'API toutes les 30 secondes. Attendez le prochain cycle ou rechargez l'intégration.

---

## Informations techniques

### API utilisées

| Version | Endpoint | Authentification |
|---------|----------|------------------|
| Videofied | API Nexecur propriétaire | Token + hachage salé |
| Hikvision | `apiieu.guardingvision.com` | MD5 + Digest Auth ISAPI |

### Modes d'armement

| Status | Videofied | Hikvision |
|--------|-----------|-----------|
| 0 | Désarmé | Désarmé (`disarm`) |
| 1 | SP1 / Home | Stay (`stay`) |
| 2 | SP2 / Away | Away (`away`) |

---

## Changelog

### Version 3.1.0
- Ajout du choix de méthode de connexion (Téléphone/Email) pour Hikvision
- Correction du parsing du statut d'armement (`arming` au lieu de `armedStatus`)
- Support des emails pour l'authentification Cloud

### Version 3.0.0
- Support dual version : Videofied et Hikvision
- Nouveau flux de configuration multi-étapes
- Migration automatique des anciennes configurations

### Version 2.x
- Support Videofied uniquement
- Entités caméra avec switches de flux

---

## License

MIT License - Copyright (c) 2025 Loule95450

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## Avertissement légal

Ce code n'est en aucun cas affilié, autorisé, maintenu, sponsorisé ou approuvé par Nexecur ou l'une de ses filiales. Il s'agit d'une API indépendante et non-officielle. **Utilisez à vos propres risques.**
