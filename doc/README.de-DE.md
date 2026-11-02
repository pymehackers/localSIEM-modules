# localSIEM-modules

Dieses README ist auch in folgenden Sprachen verfügbar:\
de-DE, [en-GB](README.en-GB.md), [en-US](../README.md), [es-AR](README.es-AR.md), [es-ES](README.es-ES.md), [fr-FR](README.fr-FR.md), [he-IL](README.he-IL.md), [hi-IN](README.hi-IN.md), [it-IT](README.it-IT.md), [ja-JP](README.ja-JP.md), [ko-KR](README.ko-KR.md), [pt-BR](README.pt-BR.md), [pt-PT](README.pt-PT.md), [ru-RU](README.ru-RU.md), [zh-CN](README.zh-CN.md)

## Was es ist

Die Module von [localSIEM](https://github.com/PYMEHackers/localSIEM), dem schlanken SIEM, das auf demselben Server läuft, den es schützt. Jedes Modul bringt ihm einen Dienst des Servers bei: wo seine Logs liegen, wie sie gelesen werden und welche Regeln gelten. Derzeit gibt es zwei:

- **apache2** (Apache + ModSecurity): führt das Access-Log, das Error-Log und das Audit-Log von ModSecurity jeder Anfrage zusammen, mit Regeln für Brute Force, Enumeration, sensible Dateien, Web-Shells und Datenbankfehler.
- **privesc** (Rechteausweitung): überwacht, was auf dem Server ausgeführt wird (auditd, sudo, su, pkexec, doas, snoopy), und warnt vor den Schritten einer Rechteausweitung zu root.

Ein Modul installiert nie etwas auf dem Server: Es arbeitet mit dem, was der Server bereits hat.

## Screenshots

![Das Modul apache2 in localSIEM](https://raw.githubusercontent.com/PYMEHackers/localSIEM-modules/main/doc/screenshot.png)

## Installation

Die Module werden über die Weboberfläche von localSIEM installiert. Installieren Sie zuerst localSIEM, als `root`:

**Debian 13**:

```bash
curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-debian.sh | bash -s -- --install --allow-from 203.0.113.10
```

**Alpine Linux 3.24**:

```bash
apk add bash curl && curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-alpine.sh | bash -s -- --install --allow-from 203.0.113.10
```

`--allow-from`: die IPs, die die Weboberfläche öffnen dürfen (`https://<server>:10443`).

Öffnen Sie danach in der Weboberfläche **Module › Installierbar**, klicken Sie auf **Repository prüfen**, sehen Sie sich **Voraussetzungen** an und klicken Sie beim Modul auf **Installieren**.

## Die Dokumentation lesen

Erkunden Sie:

- [doc/MANUAL.de-DE.md](MANUAL.de-DE.md), um zu erfahren, wie Sie jedes Modul installieren, einrichten und verwenden.
- [doc/CODE.de-DE.md](CODE.de-DE.md), um zu verstehen, wie die Module aufgebaut sind und wie man ein neues schreibt (für Entwickler und für KI-Modelle).
