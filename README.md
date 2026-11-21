# Nexecur - Home Assistant Integration (HACS)

![GitHub release](https://img.shields.io/github/release/Loule95450/HACS-Nexecur.svg)
![GitHub repo size](https://img.shields.io/github/repo-size/Loule95450/HACS-Nexecur.svg)
![GitHub License](https://img.shields.io/github/license/Loule95450/HACS-Nexecur.svg)
[![Tests](https://github.com/Loule95450/HACS-Nexecur/actions/workflows/tests.yml/badge.svg)](https://github.com/Loule95450/HACS-Nexecur/actions/workflows/tests.yml)
[![Hassfest](https://github.com/Loule95450/HACS-Nexecur/actions/workflows/hassfest.yml/badge.svg)](https://github.com/Loule95450/HACS-Nexecur/actions/workflows/hassfest.yml)
[![Validate](https://github.com/Loule95450/HACS-Nexecur/actions/workflows/validate.yml/badge.svg)](https://github.com/Loule95450/HACS-Nexecur/actions/workflows/validate.yml)

[![Ajouter à HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Loule95450&repository=HACS-Nexecur&category=integration)
[![Ajouter l'intégration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=nexecur)

Integration Home Assistant non-officielle pour les systèmes d'alarme **Nexecur**. Cette intégration supporte les deux versions d'alarme :

- **Videofied** (ancienne version)
- **Hikvision AX PRO** (nouvelle version via GuardingVision Cloud)

---

## Fonctionnalités

### Panneau d'alarme
- Entité `alarm_control_panel` reflétant tous les statuts de la centrale :
  désarmé, armement en cours, armé, **intrusion en cours**, centrale déconnectée
- Armement total, partiel 1 (Home) et partiel 2 (Night, Videofied)
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

**En un clic**, si Home Assistant est ouvert dans ce navigateur :

[![Ajouter à HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Loule95450&repository=HACS-Nexecur&category=integration)

Ce bouton ouvre le dépôt dans HACS sur **votre** instance. Cliquez ensuite sur
**Télécharger**, redémarrez Home Assistant, puis ajoutez l'intégration :

[![Ajouter l'intégration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=nexecur)

<details>
<summary>À la main, si les boutons ne fonctionnent pas</summary>

1. Dans HACS, ajoutez ce dépôt comme **Custom Repository** :
   - URL : `https://github.com/Loule95450/HACS-Nexecur`
   - Catégorie : `Integration`
2. Installez l'intégration **Nexecur**
3. Redémarrez Home Assistant
4. Allez dans **Paramètres > Appareils et services > Ajouter une intégration**
5. Recherchez **Nexecur**

</details>

> ⚠️ **Une seule intégration Nexecur à la fois.** Une autre intégration
> ([cerede2000/ha_nexecur](https://github.com/cerede2000/ha_nexecur)) utilise le
> même domaine `nexecur` et le même dossier `custom_components/nexecur`. Les deux
> ne peuvent pas cohabiter : désinstallez l'autre et supprimez
> `config/custom_components/nexecur` à la main avant d'installer celle-ci, sinon
> vous obtenez un mélange de fichiers et des erreurs d'authentification.

### Installation manuelle

1. Téléchargez le dossier `custom_components/nexecur`
2. Copiez-le dans votre dossier `config/custom_components/`
3. Redémarrez Home Assistant

---

## Configuration

### Étape 1 : Choix de la version

Lors de l'ajout de l'intégration, sélectionnez votre version d'alarme :

| Version | Description | Identifiants |
|---------|-------------|--------------|
| **Videofied** | Ancienne version Nexecur | ID site + PIN de l'application **Mon Nexecur** |
| **Hikvision** | Nouvelle version (AX PRO, GuardingVision) | Téléphone ou email + mot de passe du **compte Cloud** |

> **Les deux versions ne partagent aucun compte.** Ce sont deux services
> différents. Des identifiants parfaitement valides sur l'un sont *inconnus* sur
> l'autre : si la connexion échoue avec « Ce compte est inconnu », vous avez
> choisi la mauvaise version.

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
- `armed_away` : Armement total
- `armed_home` : Armement partiel 1 (SP1)
- `armed_night` : Armement partiel 2 (SP2, Videofied)
- `arming` : Armement en cours
- `triggered` : **Intrusion en cours**
- `unknown` : La centrale ne renvoie pas d'information d'armement
- `unavailable` : La centrale est déconnectée du cloud

> Un statut que la centrale ne documente pas n'est **jamais** affiché comme
> `disarmed` : montrer « désarmé » pendant une intrusion empêcherait toute
> automatisation de se déclencher.

**Attributs :**
- `alarm_version` : Version de l'alarme (videofied/hikvision)
- `panel_status` : Statut brut renvoyé par la centrale
- `panel_sp1_available` / `panel_sp2_available` : Modes partiels disponibles
- `partial_1_name` / `partial_2_name` : Noms des modes partiels tels que définis
  dans l'application Mon Nexecur (Videofied)
- `nexecur_event` : Évènement ponctuel (`camera_detection`, `intrusion_restored`,
  `panel_connected`, `panel_disconnected`)

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

### « Ce compte est inconnu du cloud Hikvision »

Le cloud ne connaît pas ce compte — ce n'est pas un problème de mot de passe.
Dans la quasi-totalité des cas, c'est la **mauvaise version** qui a été choisie :
si votre application est **Mon Nexecur**, revenez à l'étape 1 et sélectionnez
**Videofied**.

Avant la version 5.0.1, ce cas s'affichait comme un simple « Échec de
l'authentification », ce qui envoyait chercher une faute de frappe dans des
identifiants corrects.

### L'alarme s'arme mais affiche "désarmé"

Mettez à jour l'intégration : depuis la version 5.0.0, tous les statuts
documentés de la centrale sont reconnus et un statut inconnu n'est plus affiché
comme « désarmé ».

### Depuis la 5.0.0, « Absent » arme un mode partiel

Votre centrale est câblée à l'envers de la table documentée. Activez l'option
**« Inverser le statut »** dans **Paramètres > Appareils et services > Nexecur >
Configurer**. L'intégration se recharge toute seule.

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

### Statuts de la centrale

| Status | Videofied | État Home Assistant | Hikvision |
|--------|-----------|---------------------|-----------|
| 0 | Désarmé | `disarmed` | Désarmé (`disarm`) |
| 1 | Armement total | `armed_away` | Stay (`stay`) |
| 2 | Partiel 1 (SP1) | `armed_home` | Away (`away`) |
| 3 | Partiel 2 (SP2) | `armed_night` | — |
| 4 | Armement en cours | `arming` | — |
| 5 | Intrusion | `triggered` | — |
| 6 | Intrusion terminée | `disarmed` + `nexecur_event` | — |
| 10 | Centrale déconnectée | `unavailable` | — |
| 11 | Centrale reconnectée | `nexecur_event` | — |
| 12 | Détection caméra | `nexecur_event` | — |

Si chez vous l'armement total correspond à SP1 et non au statut 1, activez
l'option **« Inverser le statut »** dans les options de l'intégration.

---

## Changelog

### Version 5.0.1

- Les détecteurs, claviers et sirènes que la centrale ne remonte plus peuvent
  être **supprimés** depuis Home Assistant. Jusqu'ici un détecteur remplacé
  restait indéfiniment dans la liste, toutes ses entités indisponibles, et
  Home Assistant refusait de le supprimer (Hikvision uniquement).
  Merci à @sleberrigaud.
- Un compte inconnu du cloud Hikvision (code 1013) et un compte verrouillé
  (code 1015) sont enfin **distingués d'un mot de passe refusé**. Le premier cas
  signale presque toujours une erreur de version à l'étape 1.
- Les clés de traduction utilisées par le formulaire de configuration sont
  vérifiées par les tests : une clé manquante affichait son nom brut.

### Version 5.0.0

**⚠️ Changement de comportement sur les installations Videofied.**

- Les statuts documentés de la centrale sont désormais respectés :
  **1 = armement total**, 2 = partiel 1, 3 = partiel 2. C'est ce que l'option
  « Inverser le statut » produisait à la main ; elle est donc **décochée
  automatiquement** à la mise à jour sur les installations qui l'utilisaient.
  Si après la mise à jour le bouton « Absent » arme un mode partiel, recochez-la.
- Les statuts 3 à 12 sont enfin reconnus : **une intrusion (statut 5) remonte
  en `triggered`** au lieu d'être affichée comme « désarmé », l'armement en cours
  en `arming`, et une centrale déconnectée rend l'entité `unavailable`.
- Nouveau mode `armed_night` pour le partiel 2 (service `alarm_arm_night`).
- Armement total disponible même quand le site n'expose aucun mode partiel.
- Le PIN n'est plus envoyé en clair à l'appel `salt`.
- Un ordre d'alarme n'est **jamais renvoyé** après une erreur HTTP 500 ou un
  délai dépassé : le doublon pourrait armer ou désarmer deux fois.
- Un seul ordre à la fois (verrou), et un délai de 30 s par requête.
- Erreurs distinctes : compte verrouillé, service indisponible, PIN rejeté,
  au lieu d'un unique « Échec de l'authentification ».
- Les noms des modes partiels définis dans l'application sont exposés en
  attributs (`partial_1_name`, `partial_2_name`).
- La CI exécute enfin la suite de tests, et ajoute la validation Hassfest.

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
