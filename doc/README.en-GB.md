# localSIEM-modules

This README is also available in:\
[de-DE](README.de-DE.md), en-GB, [en-US](../README.md), [es-AR](README.es-AR.md), [es-ES](README.es-ES.md), [fr-FR](README.fr-FR.md), [he-IL](README.he-IL.md), [hi-IN](README.hi-IN.md), [it-IT](README.it-IT.md), [ja-JP](README.ja-JP.md), [ko-KR](README.ko-KR.md), [pt-BR](README.pt-BR.md), [pt-PT](README.pt-PT.md), [ru-RU](README.ru-RU.md), [zh-CN](README.zh-CN.md)

## What is it

The modules of [localSIEM](https://github.com/PYMEHackers/localSIEM), the lightweight SIEM that runs on the same server it protects. Each module teaches it one service of the server: where its logs are, how to read them and which rules apply. Today there are two:

- **apache2** (Apache + ModSecurity): joins the access log, the error log and the ModSecurity audit log of each request, with rules for brute force, enumeration, sensitive files, web shells and database errors.
- **privesc** (Privilege escalation): watches what is run on the server (auditd, sudo, su, pkexec, doas, snoopy) and warns about the steps of an escalation to root.

A module never installs anything on the server: it works with what the server already has.

## Screenshots

![The apache2 module in localSIEM](https://raw.githubusercontent.com/PYMEHackers/localSIEM-modules/main/doc/screenshot.png)

## Install

Modules are installed from the localSIEM web. First install localSIEM, as `root`:

**Debian 13**:

```bash
curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-debian.sh | bash -s -- --install --allow-from 203.0.113.10
```

**Alpine Linux 3.24**:

```bash
apk add bash curl && curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-alpine.sh | bash -s -- --install --allow-from 203.0.113.10
```

`--allow-from`: the IPs allowed to open the web (`https://<server>:10443`).

Then, in the web, open **Modules › Installable**, press **Check the repository**, look at **Requirements** and press **Install** on the module.

## Read the documentation

Explore:

- [doc/MANUAL.en-GB.md](MANUAL.en-GB.md) to learn how to install, set up and use each module.
- [doc/CODE.en-GB.md](CODE.en-GB.md) to understand how they are built and how to write a new one (for developers and for AI models).
