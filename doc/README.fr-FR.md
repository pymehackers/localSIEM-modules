# localSIEM-modules

Ce README est également disponible en :\
[de-DE](README.de-DE.md), [en-GB](README.en-GB.md), [en-US](../README.md), [es-AR](README.es-AR.md), [es-ES](README.es-ES.md), fr-FR, [he-IL](README.he-IL.md), [hi-IN](README.hi-IN.md), [it-IT](README.it-IT.md), [ja-JP](README.ja-JP.md), [ko-KR](README.ko-KR.md), [pt-BR](README.pt-BR.md), [pt-PT](README.pt-PT.md), [ru-RU](README.ru-RU.md), [zh-CN](README.zh-CN.md)

## Qu'est-ce que c'est

Les modules de [localSIEM](https://github.com/PYMEHackers/localSIEM), le SIEM léger qui fonctionne sur le serveur même qu'il protège. Chaque module lui apprend un service du serveur : où se trouvent ses journaux, comment les lire et quelles règles s'appliquent. Il y en a deux aujourd'hui :

- **apache2** (Apache + ModSecurity) : réunit le journal d'accès, le journal d'erreurs et le journal d'audit de ModSecurity de chaque requête, avec des règles pour la force brute, l'énumération, les fichiers sensibles, les web shells et les erreurs de base de données.
- **privesc** (Élévation de privilèges) : surveille ce qui est exécuté sur le serveur (auditd, sudo, su, pkexec, doas, snoopy) et signale les étapes d'une élévation vers root.

Un module n'installe jamais rien sur le serveur : il fonctionne avec ce que le serveur possède déjà.

## Captures d'écran

![Le module apache2 dans localSIEM](https://raw.githubusercontent.com/PYMEHackers/localSIEM-modules/main/doc/screenshot.png)

## Installation

Les modules s'installent depuis l'interface web de localSIEM. Installez d'abord localSIEM, en tant que `root` :

**Debian 13** :

```bash
curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-debian.sh | bash -s -- --install --allow-from 203.0.113.10
```

**Alpine Linux 3.24** :

```bash
apk add bash curl && curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-alpine.sh | bash -s -- --install --allow-from 203.0.113.10
```

`--allow-from` : les IP autorisées à ouvrir l'interface web (`https://<server>:10443`).

Ensuite, dans l'interface web, ouvrez **Modules › Installables**, cliquez sur **Consulter le dépôt**, consultez **Prérequis** et cliquez sur **Installer** pour le module.

## Lire la documentation

Explorez :

- [doc/MANUAL.fr-FR.md](MANUAL.fr-FR.md) pour apprendre à installer, configurer et utiliser chaque module.
- [doc/CODE.fr-FR.md](CODE.fr-FR.md) pour comprendre comment ils sont construits et comment en écrire un nouveau (pour les développeurs et pour les modèles d'IA).
