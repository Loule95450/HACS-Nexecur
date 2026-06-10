## ✨ Nouveautés

### Option « Inverser le statut » (Videofied)

Chez certaines installations Videofied, le mapping SP1/SP2 est inversé (SP1 = Complet, SP2 = Nuit). Une nouvelle option permet de corriger l'affichage :

- Disponible à la configuration initiale et dans les Options de l'intégration (Videofied uniquement)
- L'intégration se recharge automatiquement quand l'option change — plus besoin de redémarrer Home Assistant

Merci à @asavaryao pour les tests et les retours détaillés ! (#10, #11)

## 🔒 Sécurité

Suite à un audit de sécurité complet de l'intégration :

- Le token d'authentification n'est plus exposé dans les attributs de l'entité alarme (liste blanche d'attributs)
- L'URL de flux caméra n'est plus exposée dans les attributs du switch ni écrite dans les logs
- Le `sessionId` Hikvision n'apparaît plus dans les logs de debug
- HTTPS est désormais forcé pour le domaine API renvoyé par le cloud Hikvision
- L'état de l'alarme Hikvision ne retombe plus sur « désarmé » par défaut en cas d'échec API : l'entité devient indisponible (fail-safe)
- Les échecs d'armement/désarmement remontent maintenant une erreur visible dans l'interface au lieu d'un faux succès
- Durcissement divers (validation anti-injection d'en-têtes dans le tunnel ISAPI, logs assainis)

---

## What's Changed
* feat: Add invert_status option for SP1/SP2 mapping by @Loule95450 in #11
* security: Harden secret handling and fail-safe alarm state by @Loule95450

**Full Changelog**: https://github.com/Loule95450/HACS-Nexecur/compare/3.4.3...4.0.0
