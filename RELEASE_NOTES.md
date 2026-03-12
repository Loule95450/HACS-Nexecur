## ✨ Nouvelles fonctionnalités

### 🔐 Code de sécurité pour l'alarme

#### Code de désactivation (disarm)
- Ajout d'un code optionnel pour sécuriser le désarmement de l'alarme
- Une fois défini, ce code ne peut plus être modifié ou supprimé (pour des raisons de sécurité)
- Pour modifier le code, il faut supprimer l'intégration et la reconfigurer

#### Code d'activation (arm)
- Ajout d'un code optionnel pour sécuriser l'armement de l'alarme
- Ce code peut être ajouté, modifié ou supprimé à tout moment via les Options
- Possibilité d'avoir un code différent pour l'armement et le désarmement

#### Options d'intégration
- Via les Options de l'intégration, vous pouvez maintenant :
  - Ajouter un code de désactivation (si non défini)
  - Modifier ou supprimer le code d'activation à tout moment
  - Ajouter un code d'activation après la configuration initiale

---

## 🧪 Tests

- Ajout de 17 tests unitaires pour la fonctionnalité des codes
- Tests pour la logique de verrouillage du code de désarmement
- Tests pour les scénarios de codes identiques/différents

---

## 📝 Notes

- Ces fonctionnalités sont entièrement optionnelles
- Si vous ne définissez aucun code, l'intégration fonctionne comme avant
- Les codes fonctionnent avec les deux versions (Videofied et Hikvision)

---

## What's Changed
* Add optional disarm code feature by @Loule95450 in #1
* Add options flow for existing configs by @Loule95450
* Add arm code feature (editable) by @Loule95450
* Add unit tests for codes by @Loule95450

**Full Changelog**: https://github.com/Loule95450/HACS-Nexecur/compare/3.2.4...3.3.0
