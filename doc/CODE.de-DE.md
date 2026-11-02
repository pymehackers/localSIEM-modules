# Code-Referenz von localSIEM-modules

Dieses CODE ist auch in folgenden Sprachen verfügbar:\
de-DE, [en-GB](CODE.en-GB.md), [en-US](CODE.md), [es-AR](CODE.es-AR.md), [es-ES](CODE.es-ES.md), [fr-FR](CODE.fr-FR.md), [he-IL](CODE.he-IL.md), [hi-IN](CODE.hi-IN.md), [it-IT](CODE.it-IT.md), [ja-JP](CODE.ja-JP.md), [ko-KR](CODE.ko-KR.md), [pt-BR](CODE.pt-BR.md), [pt-PT](CODE.pt-PT.md), [ru-RU](CODE.ru-RU.md), [zh-CN](CODE.zh-CN.md)

## Index

1. [Architektur und Designentscheidungen](#architecture)
2. [Modulübersicht](#modules)
3. [Wichtige Symbole](#symbols)
4. [Hauptaufrufpfade](#flows)
5. [Einstiegspunkte](#routes)
6. [Auswirkungsanalyse](#impact)
7. [Erweiterungspunkte](#extensions)

[Installation](README.de-DE.md) · [Benutzerhandbuch](MANUAL.de-DE.md) · [Code-Referenz von localSIEM](../../localSIEM/doc/CODE.de-DE.md)

<a id="architecture"></a>
## 1. Architektur und Designentscheidungen

Dieses Projekt enthält die installierbaren Module von localSIEM (Schwesterprojekt `../localSIEM`). Es hat weder einen Dienst noch ein eigenes Installationsprogramm: Module werden ausschließlich über die Weboberfläche von localSIEM installiert, unter Module › Installierbar (aktualisiert und deinstalliert werden sie unter Module › Installiert), die dieses Repository (Branch `main`) herunterlädt und jeden Modulordner, `mod-<name>/`, nach `/opt/localsiem/modules/<name>/` kopiert; das Installationsprogramm von localSIEM installiert nur den Kern, nie ein Modul, und localSIEM hat keine eigenen Module. Die Prozesse von localSIEM (Collector, Weboberfläche, `manage.py`) laden es. Das Präfix `mod-` gehört nur zum Namen des Ordners in diesem Repository: Das Modul selbst (die `id` seiner `module.json`, seine Optionen, seine Einstellungen und sein installierter Ordner) behält seinen Namen ohne dieses Präfix. Derzeit gibt es zwei Module: `apache2` (Ordner `mod-apache2/`) und `privesc` (Ordner `mod-privesc/`).

### Warum die Module außerhalb des Kerns liegen

Der Kern von localSIEM ([backend/core/](../../localSIEM/backend/core/)) ist generisch: Speicherung, Suche, Regel-Engine, Gruppierung, SOC-Warteschlange, Heartbeat und Zustandsüberwachung wissen nichts über Apache. Was ein Dienst bedeutet (wo seine Logs liegen, wie sie in Einheiten zerlegt und geparst werden, wie Einträge zu einem Ereignis werden, was als bereits behoben gilt, seine Regeln und seine Voraussetzungen), liegt in einem Modul. Die Module in einem eigenen Projekt zu halten, bedeutet:

- Ein Modul ist versioniert (`version`), gibt die niedrigste localSIEM-Version an, die es benötigt (`core`), und wird ohne neues Release von localSIEM aktualisiert, hinzugefügt oder deaktiviert;
- der Kern importiert kein Modul namentlich und hat kein eigenes Modul: Die Registry ([backend/core/registry.py](../../localSIEM/backend/core/registry.py)) durchsucht nur `/opt/localsiem/modules/` (`LOCALSIEM_MODULES_PATH` in Entwicklungskopien), wohin die Weboberfläche die Module dieses Repositorys installiert;
- ein Modul, das nicht geladen werden kann, hält die anderen nie auf: Sein Fehler wird in der Weboberfläche (Zustand «Fehler») und von `manage.py modules` aufgeführt;
- ein Modul ändert nie den Kern: `backend/core/module.py` und `backend/core/registry.py` sind der gesamte Vertrag.

### Der Vertrag: module.json, locales und eine Module-Unterklasse

**`module.json`** (geprüft von `fReadManifest`):

| Schlüssel | Standard | Bedeutung | apache2 | privesc |
|---|---|---|---|---|
| `id` | erforderlich | Name des Modulordners ohne das Präfix `mod-` (der Name des installierten Ordners), `[a-z][a-z0-9_]{1,31}`; auch der `vName` der Klasse | `apache2` | `privesc` |
| `version` | `"0"` | Version des Moduls, angezeigt in der Weboberfläche und von `manage.py modules` | `1.3.2` | `1.1.2` |
| `core` | `"0"` | Niedrigste localSIEM-Version, die es benötigt; ist sie höher als die `cVersion` des installierten localSIEM, wird das Modul nicht geladen | `2.2.0` | `2.2.0` |
| `entry` | erforderlich | `"file:Class"`: `file` ohne `.py` (`[a-z][a-z0-9_]{0,63}`), `Class` eine Unterklasse von `Module` | `module:ApacheModule` | `module:PrivescModule` |
| `default_enabled` | `true` | Ob es läuft, bis der Administrator entscheidet (`modules.<id>.enabled`) | `true` | `true` |
| `read_paths` | `[]` | Absolute Ordner, die localSIEM als root für den Benutzer `localsiem` lesbar macht (der Befehl, den die Weboberfläche nach der Installation, nach **Neu konfigurieren** und nach einer Aktualisierung, die sie ändert, anzeigt) | `["/var/log/apache2"]` | `["/var/log/audit"]` |
| `install_requirements` | `{}` | Befehle, die die vom Modul benötigte Software als root auf dem Server installieren, für jedes System (`debian`, `alpine`): ein Befehl pro Zeile, ohne Shell-Operatoren, weil die Weboberfläche sie auch mit vorangestelltem `sudo` anzeigt (`fCheckInstallRequirements` des Kerns). Angezeigt unter Module › Installierbar › Voraussetzungen, nie ausgeführt | Debian: Apache, ModSecurity 2, das CRS, `a2enmod`, die empfohlene Konfiguration von ModSecurity, falls keine vorhanden ist, Neustart; Alpine: Apache | Debian: auditd und rsyslog; Alpine: auditd |
| `setup_option` | — | Von keinem Modul verwendet: Der Kern ignoriert es (die Registry verwirft es), weil ein Modul nie den Server ändert; `module.json`-Dateien älterer Versionen können es noch enthalten | nicht gesetzt | nicht gesetzt (`--configure-privesc` wurde in 1.1.0 entfernt) |
| `settings` | `[]` | Beschreibung jeder Einstellung: Die Weboberfläche baut daraus ihr Formular | 6 Einstellungen | 13 Einstellungen |

Jede Einstellung hat einen `key` (`[a-z][a-z0-9_]{1,31}`), einen `type`, meist einen `default` und die Attribute ihres Typs. `fValidateSettings` / `fCleanValue` / `fCleanRecords` prüfen, was der Administrator speichert:

| Typ | Attribute | Steuerelement der Weboberfläche | Akzeptierte Werte |
|---|---|---|---|
| `boolean` | — | Kontrollkästchen | `true` / `false` |
| `integer` | `min`, `max` | Zahlenfeld | eine ganze Zahl innerhalb von `min`..`max` |
| `string` | `max_length` (500) | Textfeld | Text ohne Steuerzeichen, getrimmt, bis zu `max_length` |
| `path` | — | Textfeld in Festbreitenschrift | leer oder absolut (beginnt mit `/`), bis zu 1024 Zeichen |
| `choice` | `choices` (erforderlich), `required` | Liste (mit «—», wenn nicht erforderlich) | einer der Werte aus `choices` oder leer |
| `records` | `fields` (erforderlich: Einstellungen der anderen Typen), `max_items` (50) | ein Block pro Datensatz mit Hinzufügen und Entfernen | eine Liste von bis zu `max_items` Datensätzen; jedes Feld wird geprüft, `required`-Felder dürfen nicht leer sein, und leere Felder werden verworfen |

**`locales/<language>.json`** (de-DE, en-GB, en-US, es-AR, es-ES, fr-FR, he-IL, hi-IN, it-IT, ja-JP, ko-KR, pt-BR, pt-PT, ru-RU, zh-CN), gelesen von `fReadTexts` und angezeigt von der Weboberfläche (`modules.js fModuleText`, das auf en-US und dann auf den Schlüssel zurückfällt):

```json
{
  "name": "Apache + ModSecurity",
  "summary": "...",
  "settings": {
    "<key>": {"label": "...", "help": "..."},
    "<records key>": {"label": "...", "help": "...", "add": "...", "remove": "...", "empty": "...", "fields": {"<field>": "..."}}
  },
  "choices": {"<value>": "..."},
  "install_requirements": {"note": "...", "debian": "...", "alpine": "..."}
}
```

Eine fehlende oder beschädigte Locale-Datei verliert nur ihre Sprache.

**Die `Module`-Unterklasse** ([backend/core/module.py](../../localSIEM/backend/core/module.py)). Die Registry erzeugt sie als `Class(pSettings, pMasker, pStorage, pManifest)`. Ihre Hooks:

| Hook | Aufgerufen von | Standard | `ApacheModule` | `PrivescModule` |
|---|---|---|---|---|
| `mStart()` | Collector, einmal, sobald der Speicher bereit ist | nichts | speichert `apache.first_start` (Beginn der Lerntage) | speichert `privesc.first_start`; lädt `privesc.sessions`, `privesc.surface` und `privesc.health` |
| `mEnabled()`, `mModuleSettings()`, `mReload()` | Collector, Weboberfläche | aus `modules.<id>` über den Standardwerten von `module.json` | geerbt | geerbt; `mReload` leert außerdem den Cache von `mSettings` |
| `mDiscoveryInterval()` | Collector (das kürzeste der aktivierten Module, mindestens 60 s) | `discovery_interval_seconds` oder 3600 | geerbt | geerbt (Standard 300) |
| `mDiscover()` | Collector (Start, Intervall, Neuladen, Anforderung der Diagnose), `manage.py doctor` | `[]` | Quellen `{key, path, kind, format, vhost, audit_type, storage_dir}` aus der Apache-Konfiguration und den manuellen Quellen | `fDiscoverSources`: das Audit-Log und syslog |
| `mCreateFramer(pSource)` | Collector, pro Quelle | `LineFramer` | `AuditFramer` für das native serielle Audit-Log | geerbt (`LineFramer`) |
| `mParse(pSource, pUnit, pReceived)` | Collector, pro Einheit | erforderlich | Eintrag von `access`, `error` oder `audit` | Eintrag von `audit` oder `syslog` |
| `mCreateCorrelator()` | Collector, beim Start | erforderlich | `Correlator` (Zeitfenster und schwache Korrelation aus den Einstellungen des Kerns) | `Correlator`: Audit-Einträge nach Seriennummer (EOE oder 2 s); syslog-Zeilen sofort |
| `mBuildEvent(pTransaction)` | Collector, pro fälliger Transaktion | erforderlich | Ereignis mit `action` und `detections` | Ereignis mit den Flags, auf die die Regeln prüfen; keine eigenen Detektionen |
| `mRulesPath()` / `mRuleFunctions()` | Collector, beim Laden der Regeln | `None` / `{}` | `rules/` seines Ordners / `{"apache2.new_php": mIsNewPhp}` | `rules/` seines Ordners / geerbt `{}` |
| `mDetectionFromSignal(pEvent, pSignal)` | Collector, pro Regelsignal (optional: wird mit `hasattr` gesucht) | generische Detektion | Detektion mit Details der Anfrage und `{rule: {id, count}}` | Detektion mit Benutzer, Befehl, Programm, Sitzung, übergeordnetem Prozess, Datei... |
| `mEnrich(pDetection)` | Collector, mit der Gruppe, bevor der Alarm erstellt wird | `{}` | Kontext der IP in der letzten Stunde | Kontext der Sitzung: Beginn gesehen, Zugang, SSH-Adresse, letzte 20 Befehle |
| `mDoctor()` | Collector (Zustand `<id>.doctor`), `manage.py doctor` | `[]` | `fRunDoctor` | `fRunDoctor` (auditd und was seine Regeln aufgezeichnet haben, syslog, snoopy, was das Modul sieht, Dateien der Version 1.0.0, Angriffsfläche) |
| `mHealth(pNow)` | Collector, alle 60 s, nur aktivierte Module | `[]` | ModSecurity nicht geladen oder Off, echte Client-IP fehlt (höchstens alle 300 s) | speichert die Sitzungen; Scan-Ergebnisse; alle 300 s: auditd gestoppt, beschreibbare sensible Dateien (stündlich), startet den Scan nach setuid-Programmen |
| `mSkipped()` | Zustand des Collectors, `manage.py doctor` | `[]` | Logs über Pipe, vom `GlobalLog` abgedeckte Logs, Access-Logs ohne Daten (`format_without_data`) | syslog nicht gelesen (auditd läuft, `syslog_mode` never), Audit-Log fehlt |
| `mSetLowDisk(pLowDisk)` | Collector, Füllstand des Datenträgers | nichts | speichert keine Header und Körper des Audit-Logs mehr | geerbt |
| `mDisplayRecord(pRecord)` | Weboberfläche, Detailansicht der Anfrage | `{}` | Header und Körper des gespeicherten Audit-Eintrags (`fAuditDisplay`) | geerbt |
| `mRequirements()` | Kern, localSIEM 2.2.0 oder neuer: erste Installation, Start und Neuladen des Collectors, **Neu konfigurieren** in der Weboberfläche, `manage.py modules` und `doctor` | `[]` (keine Voraussetzungen) | `apache_config` und `modsecurity` (`fRequirementChecks`) | `command_source`: jede Quelle, die `localsiem` lesen kann, das Audit-Log (auditd läuft, nicht in einem Container) oder syslog (mit snoopy, falls installiert); `audit_log` / `syslog`, wenn eine Quelle existiert, aber nicht gelesen werden kann |

Der Kern hat weder `mSetupSnippet` noch `mApplySetup` mehr: Module haben keine Einrichtungsoptionen und ändern nie den Server.

Einträge sind Dicts mit `time`, `received`, `module` (die ID: Der Collector wählt anhand davon den Korrelator), `source`, `source_key`, `correlation`, `parse_status` (`ok`, `partial`, `unparsed`), `fields` und `raw` (maskiert) sowie optional `search` (der für die Volltextsuche indizierte Text). Ereignisse haben die Spalten der Ereignistabelle (`lEventColumns` in `storage_sqlite.py`) sowie `record_ids`, `rule_hits` und `detections`. Eine Detektion hat `module`, `vhost`, `ip`, `category`, `severity`, `rule`, `type`, `description`, `search`, `details`, `time` und `uid`.

### Voraussetzungen: Ein Modul installiert nie, was es überwacht

Die Installation eines Moduls installiert nie die Software, die es überwacht: Das Modul apache2 installiert weder Apache noch ModSecurity, und das Modul privesc installiert weder auditd noch einen syslog-Daemon noch snoopy (seine Voraussetzung, `command_source`, ist jede Quelle, die der Benutzer `localsiem` lesen kann: das Audit-Log bei laufendem auditd außerhalb eines Containers oder syslog; `fRequirementChecks` von `mod-privesc/doctor.py`). Das Modul selbst legt in `mRequirements()` fest, was es benötigt, bevor es aktiviert werden kann (localSIEM 2.2.0 oder neuer): eine Liste von Prüfungen im Format der Diagnose, die erfüllt ist, wenn keine den Status `error` hat. Das Modul apache2 gibt `apache_config` (eine Apache-Konfiguration wird gefunden: `apache2.conf`, `httpd.conf` oder die Datei der Einstellung `config_file`) und `modsecurity` (`mod_security2` ist geladen; ModSecurity 3 zählt nicht) zurück, die `fRequirementChecks` aus den ersten Prüfungen der Diagnose übernimmt; ohne Apache sind beide Fehler. Was diese Software installiert, wird in `install_requirements` von `module.json` angegeben: Die Weboberfläche zeigt es vor der Installation des Moduls an (Module › Installierbar › Voraussetzungen), für das System des Servers, und führt es nie aus. Der Kern:

- installiert das Modul deaktiviert (`modules.<id>.enabled = false`), wenn bei seiner ersten Installation eine Voraussetzung fehlt und der Administrator nie entschieden hat; eine Aktualisierung ändert `enabled` nie;
- lässt nicht zu, dass es aktiviert wird, solange eine Voraussetzung fehlt: Der Schalter ist gesperrt, und die Weboberfläche zeigt die Voraussetzungen mit ihrem `fix`;
- deaktiviert nie von selbst ein aktiviertes Modul, das eine Voraussetzung verliert: Seine Diagnose und seine Zustandswarnungen (`mHealth`: «ModSecurity is no longer loaded») melden es, und es zu deaktivieren würde sie zum Schweigen bringen;
- prüft die Voraussetzungen erneut, wenn der Collector startet oder neu lädt, und mit **Neu konfigurieren** auf der Seite des Moduls (auch wenn es deaktiviert ist): Sind sie erfüllt, gibt er den Schalter frei, der Administrator aktiviert das Modul, und die Weboberfläche zeigt den als root auszuführenden Befehl, mit dem `localsiem` die nach der Installation erstellten Logs lesen kann (`read_paths`).

### Als Namespace-Paket geladen

Es gibt nirgends eine `__init__.py` (implizite Namespace-Pakete von Python 3.13). `fRegisterPackage` erzeugt das Paket `localsiem_modules` mit dem Modulordner als `__path__`, und `fLoadClass` importiert `localsiem_modules.<id>.<file>` und prüft, dass die Klasse ein `Module` ist und ihr `vName` der `id` entspricht. Folgen für den Code eines Moduls:

- seine eigenen Dateien werden **relativ** importiert (`from .parsers import AccessParser`);
- der Kern wird als **`backend.core...`** importiert (`from backend.core.module import Module`): Die Prozesse von localSIEM setzen den Ordner von localSIEM in `sys.path`;
- nur die Standardbibliothek und die Abhängigkeiten von localSIEM (seine virtuelle Umgebung `/opt/localsiem/venv/`, zum Beispiel PyYAML) sind verfügbar: localSIEM installiert nichts für ein Modul.

### Formular der Einstellungen, aus dem Manifest erstellt

Ein Modul hat kein eigenes HTML. Die Weboberfläche liest `settings` aus `module.json` und die Texte aus `locales/`, baut das Formular (`modules.js fBuildSettings`, `fRecordsEditor`), validiert das Gespeicherte mit `fValidateSettings` und speichert nur die Werte, die der Administrator gespeichert hat, in `settings.json` unter `modules.<id>`; dort liegt auch `enabled`. Das Modul liest `mModuleSettings()`: die Standardwerte aus `module.json`, darüber die gespeicherten Werte. Das Hinzufügen einer Einstellung erfordert daher keine Änderung an der Weboberfläche oder am Kern.

Einstellungen des Kerns, die das Modul apache2 ebenfalls aus `self.dSettings` liest: `host`, `correlation_window_seconds` (5), `weak_correlation_seconds` (2), `below_threshold_severity` (`low`) und `health.single_ip_percent` / `health.single_ip_minimum_requests` (90 / 100). `mModuleSettings()` übergibt außerdem Schlüssel, die unter `modules.apache2` gespeichert sind und die `module.json` nicht deklariert: `mDiscover` liest auf diese Weise `document_roots` (`{vhost: folder}`, über den erkannten DocumentRoots); dies lässt sich nur durch Bearbeiten von `settings.json` festlegen.

### Das Prinzip der «ergriffenen Aktion»

Nur was noch niemand behoben hat, geht an das SOC. Im Modul apache2 wird die ergriffene Aktion aus der zuverlässigsten Quelle gelesen: dem Audit-Log (`Action: Intercepted (phase N)` im nativen Format, `audit_data.action.intercepted/phase` in JSON), dann dem error.log (`Access denied with code NNN (phase N)`). Ein 403 ohne jede Spur von ModSecurity ist keine Blockierung (`fields.doubtful_block`).

| Situation | `action` | Detektion (an das SOC) |
|---|---|---|
| In den Phasen 1-2 abgefangen (die Anwendung hat sie nie erhalten) | `blocked` | keine: `mAssess` gibt `None` zurück; wird im Kontext späterer Alarme mitgezählt |
| In den Phasen 3-4 abgefangen | `none` | ja, `blocked_late` (hoch), oder `success_indicator` bei einem Datenbankfehler |
| Treffer mit der Engine in `DetectionOnly` | `none` | ja |
| Treffer unterhalb des Anomalie-Schwellenwerts | `none` | ja, `below_threshold` (niedrig) |
| Signale der YAML-Regeln | `none` | ja |

Die Schweregrade stammen aus `severity.yaml` (`fLoadSeverityTable`; eine fehlende Datei oder ein ungültiger Wert behält den eingebauten Standardwert): `crs_not_blocked_2xx` hoch, `crs_not_blocked_other` mittel, `blocked_late` hoch, `success_indicator` kritisch (nicht blockierte ausgehende Regel 950-955 oder ein Datenbankfehler in derselben Anfrage), `below_threshold` niedrig (die Einstellung `below_threshold_severity` des Kerns hat Vorrang). «Oberhalb des Schwellenwerts» bedeutet, dass eine 949xxx-Regel angeschlagen hat oder der von ModSecurity angegebene Score den Schwellenwert erreicht hat; ein aus den Schweregraden der Regeln berechneter Score ist nur eine Schätzung und entscheidet nicht. Der Schwellenwert ist der aus den Meldungen, sonst `anomaly_threshold`, sonst der aus `crs-setup.conf`, sonst 5.

### Wie das Modul apache2 funktioniert

1. **Erkennung** (`discovery.py`): `ApacheConfig` liest die Konfiguration direkt (`Include`, `IncludeOptional`, `Define`, `${VARS}` aus den `envvars` von Debian, `<VirtualHost>`, `<IfModule>` abgeglichen mit den geladenen Modulen), als Benutzer `localsiem` und ohne `apache2ctl`. `fDiscoverSources` wandelt `CustomLog`/`GlobalLog`/`TransferLog`, `ErrorLog` und `SecAuditLog` in Quellen mit dem stabilen Schlüssel `apache:<kind>:<real path>` um. Ein `GlobalLog`, dessen Format `%v` hat, deckt alle vhosts ab (die anderen Access-Logs werden übersprungen); Logs über Pipe und syslog werden übersprungen, ebenso die Access-Logs, deren Format keine `%`-Direktive hat (Apache schreibt einen Kurznamen, den kein `LogFormat` definiert, so wie er ist: `format_without_data`, außer ein anderes `CustomLog` mit Daten schreibt in dieselbe Datei; die Diagnose weist darauf hin, ohne Behebung, da das Format der Logs nie geändert wird); manuelle Quellen kommen zuerst, und eine Datei wird nur einmal gelesen.
2. **Zerlegung und Parsing** (`parsers.py`, `logformat.py`, `modsec.py`): Access-Zeilen werden mit einem regulären Ausdruck geparst, der aus ihrem `LogFormat` erzeugt wird (das zuletzt funktionierende Format wird zuerst versucht); Error-Zeilen werden klassifiziert (`modsecurity`, `database`, `php`, `crash`, `apache`); Audit-Einträge werden als JSON (eine Zeile, vor `matched_rules` abgeschnitten), nativ seriell (`AuditFramer` fügt `--id-A--` bis `--id-Z--` zusammen) oder parallel (die Indexzeile verweist auf eine Datei unter `SecAuditLogStorageDir`) gelesen. Alles wird maskiert; was nicht passt, wird als `unparsed` aufbewahrt.
3. **Korrelation** (`correlate.py`): Einträge mit derselben `UNIQUE_ID` bilden eine Transaktion, die das Korrelationsfenster und die Watermark der Quellen abwartet, die gerade aufholen; eine Access-Zeile ohne `UNIQUE_ID` (die Formate, die Apache standardmäßig schreibt) wird von `mPair`, wenn sie oder die Einträge ihrer Anfrage fällig sind, mit den Einträgen von ModSecurity gepaart, die keine Access-Zeile haben: gleiche Client-IP, Uhrzeit innerhalb von ±2 s (die Zeile hat ganze Sekunden) sowie gleiche Methode, URI, Status und gleicher Pfad, wenn beide Seiten sie kennen; es gewinnt der Kandidat, der in den meisten davon übereinstimmt, dann der nächstgelegene, dann der älteste, und das Ereignis wird als schwach markiert. error.log-Zeilen ohne `UNIQUE_ID` schließen sich sofort der nächstgelegenen Transaktion ihrer IP an. Eine Transaktion mit einer `UNIQUE_ID` und einer ModSecurity-Zeile aus dem error.log wartet, während Audit-Einträge eintreffen (`vAuditSeen`), außerdem auf ihren eigenen Audit-Eintrag (`mWaitsForAudit`), höchstens `cAuditWaitSeconds` (120 s) ab ihrem ersten Eintrag: ModSecurity schreibt die Zeilen seiner Regeln, während die Anfrage läuft, und den Audit-Eintrag, wenn sie endet, sodass eine langsame Anfrage sonst zu zwei Ereignissen würde; sobald der Audit-Eintrag eintrifft, hat die Access-Zeile noch `cAfterAuditSeconds` (2 s) Zeit.
4. **Ereignis** (`ApacheModule.mBuildEvent`): Felder werden aus access, dann audit, dann error übernommen; der vhost aus `%v` oder, ohne ihn, aus dem Host-Header und dem lokalen Port des Audit-Eintrags (`mVhostName`); bei einer Access-Zeile mit ganzen Sekunden die Uhrzeit des Audit-Eintrags; `fSummarize` liefert Regeln, Kategorien, Score, Schwellenwert und Abfangen; die ergriffene Aktion und `mAssess` entscheiden über die Detektion.
5. **Regeln, Anreicherung, Diagnose und Zustand**: Die YAML-Regeln aus `rules/` laufen bei jedem Ereignis (Engine des Kerns); `mEnrich` fügt den Kontext der IP hinzu; `fRunDoctor` prüft die Voraussetzungen und beschreibt die Logs, ohne etwas zu ändern; `mHealth` überwacht ModSecurity und die echte Client-IP. Das Modul hat keine Einrichtungsoption: Als root gibt localSIEM `localsiem` nur Lesezugriff auf `/var/log/apache2`.

### Wissenswerte Designentscheidungen

- **Kein eigenes Installationsprogramm**: Die Module werden ausschließlich über die Weboberfläche von localSIEM installiert (Module › Installierbar), aktualisiert (**Aktualisieren**, unter Module › Installiert) und deinstalliert (**Deinstallieren**); sie lädt dieses Repository herunter und installiert sie mit `backend/core/catalog.py` (sicheres Entpacken, jeweils nur eine Installation, atomarer Austausch des Ordners). Was root erfordert (Lesezugriff auf die `read_paths`), erledigt localSIEM: Nach der Installation (und nach einer Aktualisierung, die `read_paths` ändert) zeigt die Weboberfläche den als root auszuführenden Befehl.
- **Die Logs des Kunden werden nur gelesen**: Ein Modul schreibt nie in die Logs der Dienste, die es überwacht, rotiert, kürzt, verschiebt oder löscht sie nie und ändert nie ihr Format; das Modul apache2 ändert auch nie die Konfiguration von Apache oder ModSecurity (es hat keine `setup_option`). Schreibt ein Server seine Logs in einem eigenen Format (ein eigenes `LogFormat`, die Client-IP von `mod_remoteip`), passt sich das Modul an: `AccessFormat` baut den Parser jedes Access-Logs aus dessen `LogFormat`, und `fCanPair` / `Correlator.mPair` führen die Zeilen ohne `UNIQUE_ID` zusammen. Die Diagnose beschreibt nur die Logs und was localSIEM aus ihnen lesen kann oder nicht: Die Prüfungen `log_format`, `log_format_without_data`, `remoteip`, `audit_log` und `sanitise` haben keinen `fix`; nur was kein Log ist (ModSecurity, das CRS, `SecRuleEngine`, `mod_unique_id`, die Leseberechtigungen von `localsiem`), hat einen. `--configure-apache` wurde in Version 1.3.0 entfernt; `localsiem_combined` bleibt in `dKnownFormats` für die Server, die es bereits schreiben, und das Installationsprogramm von localSIEM löscht die `localsiem.conf`, die ältere Versionen geschrieben haben (`--uninstall`, `--reinstall`).
- **Teil K** (`matched_rules`) und **Teil E** (Antwortkörper) des Audit-Logs werden nie gespeichert. Header und Körper verbleiben nur im maskierten Rohdatensatz; die Detailansicht der Anfrage baut sie wieder auf (`fAuditDisplay`). Der Volltextindex erhält einen reduzierten Text (`search`: Anfragezeile, Host, User-Agent sowie ID, Meldung und Daten jeder Regel).
- **Der Rohtext wird aus den maskierten Teilen neu aufgebaut**: Der ursprüngliche Audit-Eintrag kann Passwörter und Cookies enthalten.
- **Die Weboberfläche und die Werkzeuge erzeugen das Modul ohne Speicher** (`pStorage` ist `None` in `WebContext.mModule` und `manage.py`): Der Konstruktor und die Hooks, die sie aufrufen, dürfen den Speicher nicht verwenden.
- **Zustand in der Ereignisdatenbank**: `apache.first_start` (Lerntage), `apache.health` (was bereits gemeldet wurde, damit ein Neustart es nicht wiederholt) und `apache2.doctor` (vom Collector geschrieben). Die ersten beiden behalten, wie die Quellschlüssel `apache:<kind>:<real path>`, den Namen, den das Modul hatte, bevor es apache2 hieß: Ein Server, der das Modul `apache` hatte, behält seine Lerntage, sein Zustandsgedächtnis und seine Lesepositionen (mit einem neuen Quellschlüssel würde jedes Log unter 5 MiB erneut von Anfang an gelesen). Die Zeitangaben des Zustandsgedächtnisses liegen im nativen Format des Projekts vor (`2026-10-29@13-59-59.723`, UTC); ein von einer älteren Version mit Epochensekunden gespeicherter Zustand wird beim Laden konvertiert.
- **Sicherheit der Pfade**: `mIsNewPhp` lehnt `..` ab und bleibt innerhalb des DocumentRoot; `fReadConcurrentEntry` bleibt innerhalb von `SecAuditLogStorageDir` und liest höchstens 8 MiB; der Korrelator hält höchstens 50 000 ausstehende Transaktionen.

### Wie das Modul privesc funktioniert

Die Frage lautet nicht «Hat jemand `whoami` ausgeführt?» (Administratoren tun das jeden Tag), sondern «Geht diese Sitzung den Weg einer Rechteausweitung, und ist sie am Ziel angekommen?». Das Modul wandelt zwei Quellen in Ereignisse mit einer einheitlichen Bedeutung um (`vhost` die Person, `method` die Art, `uri` der Befehl, `path` das Programm oder die Datei, `ip` die SSH-Adresse, `score` die unterschiedlichen Aufklärungsbefehle der Sitzung), berechnet Flags darauf und lässt YAML-Regeln entscheiden, was an das SOC geht.

1. **Erkennung** (`discovery.py`): `fDiscoverSources` liefert das Audit-Log (`fAuditLogPath`: Einstellung, `log_file` aus `auditd.conf`, `/var/log/audit/audit.log`; auch wenn auditd läuft und `localsiem` es noch nicht lesen kann, damit der Kern dies meldet) und syslog (`fSyslogPath`), wenn `syslog_mode` es vorsieht (`auto`: auditd läuft nicht, sein Log ist nicht lesbar oder snoopy ist installiert). Außerdem sammelt es, was die Diagnose benötigt: Container (`fContainer`, ohne root lesbar: `/run/systemd/container`, `/run/.containerenv`, `/.dockerenv`, `/proc/self/cgroup`, `systemd-detect-virt`), Binärdatei und PID von auditd, snoopy, ob jedes Log gelesen werden kann (`fReadState`: `readable`, `unreadable` oder `missing`) und die Dateien, die Version 1.0.0 hinterlassen hat (`fLegacyLeftovers`). `Accounts` liest `/etc/passwd`, `/etc/group` und `UID_MIN` erneut, wenn sie sich ändern, und ordnet eine UID als `root`, `admin` (Mitglied von `admin_groups`), `user` oder `service` ein.
2. **Parsing** (`parsers.py`): `fParseAuditLine` liest `type=... msg=audit(<time>:<serial>): k=v ...`, den User-Space-Teil `msg='...'` und den angereicherten Teil nach `\x1d`, fügt die Argumente von `EXECVE` zusammen (auch die in `aN[i]`-Stücke aufgeteilten), dekodiert die hexadezimalen Werte (`proctitle`, `cmd`, `cwd`, `name`, `exe`, `aN`...) und **baut den Rohtext aus den dekodierten und maskierten Werten neu auf** (die hexadezimale Darstellung eines Passworts würde es bewahren); `search` erhält den dekodierten Befehl. `fParseSyslogLine` liest ISO- und klassische Zeitstempel (mit oder ohne das `facility.priority` von busybox), und `fParseSyslogMessage` versteht snoopy (seine Standardformate von 2.4 und 2.5, einschließlich `uid:alice(1000)/root(0)`, und das von Version 1.0.0 gesetzte), sudo, su (util-linux und busybox), pkexec, doas, `pam_unix` und sshd. `fMaskCommand` maskiert Passwörter in Befehlszeilen vor dem Maskierer des Kerns.
3. **Korrelation** (`correlate.py`): Audit-Einträge mit derselben Seriennummer bilden eine Transaktion, die bei `EOE` fällig ist, sofort bei User-Space-Typen mit nur einem Eintrag (`USER_*`, `CRED_*`, `DAEMON_*`...) oder nach 2 s ohne Einträge; höchstens 50 000 ausstehend. syslog-Zeilen sind sofort fällig.
4. **Ereignis** (`PrivescModule.mBuildEvent`): `mAuditEvent` verzweigt nach Typ: `EXECVE` → `mAuditExec` (setuid-Bit des Programms aus dem `PATH`-Eintrag oder `stat`, `suid_escape`, wenn die euid 0 ist, die reale UID nicht und das Programm nicht setuid ist, aus `BPRM_FCAPS` erlangte Capabilities, `root_without_door`, `parent_interpreter`, wenn eine Shell als root läuft, die von einem Interpreter eines anderen Benutzers als root gestartet wurde, der übergeordnete Prozess aus dem Prozessspeicher); `USER_*`/`LOGIN` → `mAuditUser` (gestartete Sitzung, SSH-Adresse, Zugänge: `USER_START`/`USER_CMD` von sudo, su, pkexec, doas, run0, systemd; Fehlschläge); `CONFIG_CHANGE` (`audit_disabled`, `audit_rule_removed` für jede entfernte Regel), `DAEMON_*` (`auditd_stopped_manually`, wenn der Absender nicht PID 1 ist), `ANOM_ABEND` (`crash_suspicious`); jeder andere `SYSCALL` → `mAuditSyscall`, das ihn nach seinem Systemaufruf (`fSyscallName`: der Name aus dem angereicherten Format oder die Nummer in der Tabelle seiner Architektur), seinen Argumenten und seinen `PATH`-Einträgen klassifiziert, nie nach dem Schlüssel der Regel: `denied` (Öffnen, Ausführen oder Kürzen mit `EACCES`/`EPERM` für eine Person fehlgeschlagen), `kmod`, `ptrace` (`ptrace_attach` für `PTRACE_ATTACH`/`PTRACE_SEIZE`), `chmod` (Modus mit dem setuid- oder setgid-Bit, nicht auf einem Ordner, mit `writer_allowed`) und `file` (eine Änderung eines Pfades aus `lSensitivePaths`, mit `sensitive_group` und `writer_allowed`; der Schlüssel, über `dKeyHints`, nur, wenn kein Pfad aufgelöst werden kann). `mSyslogEvent` behandelt snoopy als `exec` (`suid_escape` aus `stat`; ohne `filename` das Programm aus dem ersten Wort des Befehls) sowie sudo, su, pkexec, doas, login und pam. Jeder Befehl durchläuft `mAnalyzeCommand`: Aufklärungstoken (`fReconToken`) und unterschiedliche Token der Sitzung im Zeitfenster (`recon_burst`, `recon_massive`, `score`), von einer Shell ausgeführte Downloads (`cDownloadOnelinerRegex` oder ein Downloader, gefolgt von einer Shell mit demselben übergeordneten Prozess), `compile_in_tmp`, die letzten Befehle der Sitzung und, für Dienstkonten, das Programm (`fProgramKey`) im Vergleich zu seinem Verlauf (`mPathFirstSeen` des Kerns, nach `learning_days`: `new_program`). `ignored` markiert die ignorierten Benutzer.
5. **Regeln, Anreicherung, Diagnose und Zustand**: Die 35 YAML-Regeln aus `rules/` entscheiden über jede Detektion (`mDetectionFromSignal`); `mEnrich` fügt den Kontext der Sitzung hinzu; `fRunDoctor` beschreibt auditd und was seine Regeln aufgezeichnet haben, syslog, snoopy, was das Modul sieht und was nicht, die Dateien der Version 1.0.0 und die Angriffsfläche; `mHealth` meldet gestopptes auditd, beschreibbare sensible Dateien und das Ergebnis des Scans nach setuid-Programmen (`SurfaceScanner`, ein Thread). Das Modul hat keine Einrichtungsoption und ändert nichts am Server.

### Designentscheidungen des Moduls privesc

- **Zwei Quellen, eine Bedeutung.** auditd kann von einem Benutzer nicht umgangen werden, läuft aber nicht in Containern (das Audit des Kernels ist nicht in Namespaces aufgeteilt); snoopy sieht in Containern jedes Programm, benötigt aber syslog; syslog allein liefert nur sudo, su, pkexec und doas. Keine Quelle sieht die Builtins der Shell. Die Regeln prüfen Spalten und Flags, nie die Quelle, sodass eine Quelle hinzugefügt werden kann, ohne sie anzutasten. Derselbe Befehl, zweimal gesehen, ergibt einen einzigen Alarm: Der Kern gruppiert Detektionen nach Modul, Benutzer, IP, Kategorie und Schweregrad.
- **Häufungen, nicht Befehle.** Aufklärung ist ein Token pro Art von Frage (`whoami`, `read:/etc/passwd`, `find:-perm:`...), und nur die Anzahl unterschiedlicher Token einer Sitzung in einem Zeitfenster löst einen Alarm aus, mit einem höheren Schwellenwert für Administratoren und einem dritten für Skripte. Die Schwellenwerte sind Einstellungen, keine Regelschwellenwerte: Die Regel prüft nur `recon_burst` / `recon_massive`.
- **Der Erfolg ist das Wichtigste.** `suid_escape` (ein Programm, das nicht setuid ist und mit euid 0 und einer realen UID ungleich 0 läuft) und `root_without_door` (root in einer Sitzung, deren Beginn gesehen wurde und die nie über sudo, su, pkexec oder doas gegangen ist) sind die beiden kritischen Anzeichen dafür, dass eine Rechteausweitung gelungen ist, nahezu ohne Fehlalarme. Eine Sitzung, deren Beginn nicht gesehen wurde (Sitzungen, die vor dem Modul geöffnet wurden, Sitzungen, die nach einem Tag Inaktivität vergessen wurden), wird nie markiert.
- **Sitzungen überstehen Neustarts.** `SessionTracker` bewahrt den Beginn, die SSH-Adresse und den Zugang jeder Sitzung im Zustand `privesc.sessions` auf (höchstens jede Minute gespeichert); die Aufklärungstoken und die letzten Befehle bleiben im Speicher. Sitzungen, die einen Tag lang inaktiv sind, werden verworfen.
- **Nur was der Server bereits hat.** Das Modul installiert nie etwas und ändert nie etwas außerhalb von `/opt/localsiem`: Es lädt keine Audit-Regeln, tastet weder `auditd.conf` noch `snoopy.ini` an und installiert keinen Hook. Version 1.0.0 tat dies (`--configure-privesc`: Audit-Regeln mit den Schlüsseln `lsiem_*`, `log_group = adm`, ein Bash-Hook, das Format von snoopy); Version 1.1.0 hat es entfernt. Die Audit-Einträge werden daher nach ihrem Typ, ihrem Systemaufruf und ihren Pfaden klassifiziert, sodass beliebige Audit-Regeln funktionieren (die des Servers, die STIG-Beispielregeln oder die `lsiem_*`-Regeln, die 1.0.0 hinterlassen hat); der Schlüssel wird für die Suchen in `fields.key` aufbewahrt und ist nur ein Hinweis (`dKeyHints`). Die Nummern der Systemaufrufe werden pro Architektur gelesen (`dSyscallTables`: x86_64, i386 und die generische Tabelle von aarch64, riscv64 und loongarch64), wenn das Log keine angereicherten Namen hat. Die Diagnose beschreibt, was die Regeln des Servers aufzeichnen und was nicht; ihr `fix` ist nur ein zu installierendes Paket oder der Lesezugriff von `localsiem`.
- **Lesbar heißt lesbar.** Die Voraussetzung wird durch eine Quelle erfüllt, die existiert und die `localsiem` öffnen kann (`fReadState`), nicht dadurch, dass ein Programm installiert ist: Bei einer Erstinstallation gehören die Logs meist root, daher bleibt das Modul deaktiviert, bis der Befehl für root (`manage.py setup-modules`) ausgeführt und **Neu konfigurieren** angeklickt wurde.
- **Paketmanager sind keine Angreifer.** Änderungen an sensiblen Dateien und setuid-Bits, die von den Konto- und Paketwerkzeugen (`sAllowedWriters`) oder von Programmen vorgenommen werden, deren bekannte Vorfahren Paketmanager sind, setzen `writer_allowed`, und die Regeln überspringen sie.
- **Der Scan blockiert nie den Collector.** `SurfaceScanner` durchläuft die `scan_paths` in einem eigenen Thread, ohne das Dateisystem jedes Pfades zu verlassen, wobei `/proc`, `/sys` und die Ordner von Containern übersprungen werden, bis zu 3 Millionen Dateien oder 15 Minuten; `mHealth` übernimmt das Ergebnis, wenn es bereit ist. Der erste Scan ist die Referenz; spätere melden, was neu ist.
- **Die Weboberfläche und die Werkzeuge erzeugen das Modul ohne Speicher**: `mDiscover`, `mDoctor` und `mRequirements` verwenden ihn nie, und `mAnalyzeCommand` ruft `mPathFirstSeen` nur auf, wenn es existiert.
- **Zustand in der Ereignisdatenbank**: `privesc.first_start` (Lerntage), `privesc.sessions`, `privesc.surface` (die Referenz des Scans und der Diagnose), `privesc.health` (was bereits gemeldet wurde, ob auditd lief) und `privesc.doctor` (vom Collector geschrieben). Die gesehenen Programme der Dienstkonten sind Zeilen von `seen_paths` mit dem vhost `privesc:<account>`. Die Zeitangaben von `privesc.health` (dem Zustandsgedächtnis) und von `privesc.sessions` (`last` jeder Sitzung) liegen im nativen Format des Projekts vor (`2026-10-29@13-59-59.723`, UTC); ein von einer älteren Version mit Epochensekunden gespeicherter Zustand wird beim Laden konvertiert.

<a id="modules"></a>
## 2. Modulübersicht

| Modul | Pfad | Zuständigkeit | Hängt ab von | Verwendet von |
|---|---|---|---|---|
| Manifest | [mod-apache2/module.json](../mod-apache2/module.json) | ID, Version, minimaler Kern, Einstiegspunkt, Lesepfade, Einstellungen (keine Einrichtungsoption) | — | Registry, Weboberfläche, `manage.py` |
| Apache-Modul | [mod-apache2/module.py](../mod-apache2/module.py) | `ApacheModule`: Hooks, ergriffene Aktion, Schweregrad, Detektionen, Regelfunktion, Anreicherung, Zustand | correlate, discovery, doctor, modsec, parsers; Kern `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | Collector, Weboberfläche, `manage.py` |
| Erkennung | [mod-apache2/discovery.py](../mod-apache2/discovery.py) | `ApacheConfig` (Parser der Konfiguration), Quellen und übersprungene Logs, DocumentRoots | logformat (`dKnownFormats`) | module, doctor |
| Diagnose | [mod-apache2/doctor.py](../mod-apache2/doctor.py) | Prüfungen der Voraussetzungen; beschreibt die Logs (Format, Audit-Log, Maskierung), ohne vorzuschlagen, sie zu ändern | discovery | module |
| Access-Formate | [mod-apache2/logformat.py](../mod-apache2/logformat.py) | `LogFormat` zu regulärem Ausdruck, Zeitangaben nach UTC, Anfragezeile | Kern `timeutil` | parsers, discovery |
| Parser | [mod-apache2/parsers.py](../mod-apache2/parsers.py) | access, error, audit (JSON, nativ, parallel), `AuditFramer`, `fAuditDisplay` | logformat, modsec; Kern `masking`, `timeutil` | module |
| ModSecurity | [mod-apache2/modsec.py](../mod-apache2/modsec.py) | Meldungen, Kategorien, CRS-Bereiche, Scores, Abfangen | — | parsers, module |
| Korrelation | [mod-apache2/correlate.py](../mod-apache2/correlate.py) | `UNIQUE_ID`, Paarung ohne sie (`mPair`), Zeitfenster, Watermark | Kern `timeutil` | module (Collector) |
| Schweregradtabelle | [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) | Schweregrade der Detektionen von ModSecurity | — | module (`fLoadSeverityTable`) |
| Regeln | [mod-apache2/rules/](../mod-apache2/rules/) | Sechs YAML-Regeln | Regel-Engine des Kerns, `mIsNewPhp` | Collector (`RulesEngine`), Weboberfläche (`fRules`) |
| Texte | [mod-apache2/locales/](../mod-apache2/locales/) | Name, Zusammenfassung, Bezeichnungen und Hilfe der Einstellungen, Auswahlwerte | — | Weboberfläche |
| privesc: Manifest | [mod-privesc/module.json](../mod-privesc/module.json) | ID, Version, minimaler Kern, Einstiegspunkt, Lesepfade, 13 Einstellungen (keine Einrichtungsoption) | — | Registry, Weboberfläche, `manage.py` |
| privesc: Modul | [mod-privesc/module.py](../mod-privesc/module.py) | `PrivescModule`: Hooks, Ereignisse der beiden Quellen, Klassifizierung der Audit-Einträge (sensible Pfade, Systemaufrufe pro Architektur), Flags, Detektionen der Regeln, Anreicherung, Zustand, Scan-Ergebnisse | commands, correlate, discovery, doctor, parsers, surface; Kern `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | Collector, Weboberfläche, `manage.py` |
| privesc: Erkennung | [mod-privesc/discovery.py](../mod-privesc/discovery.py) | Quellen, Container, auditd, snoopy, syslog, ob jedes Log gelesen werden kann, von Version 1.0.0 hinterlassene Dateien, `Accounts` (Benutzer, Gruppen, Kontoart) | — | module, doctor |
| privesc: Parser | [mod-privesc/parsers.py](../mod-privesc/parsers.py) | Audit-Einträge (hexadezimal, `msg='...'`, angereichert), syslog-Zeilen (snoopy in seinen üblichen Formaten, sudo, su, pkexec, doas, pam, sshd), Maskierung von Befehlszeilen | Kern `masking`, `timeutil` | module |
| privesc: Korrelation | [mod-privesc/correlate.py](../mod-privesc/correlate.py) | Audit-Einträge nach Seriennummer (EOE, User-Space-Einträge, 2 s); syslog-Zeilen sofort | — | module (Collector) |
| privesc: Befehle | [mod-privesc/commands.py](../mod-privesc/commands.py) | Aufklärungstoken, Programm eines Dienstkontos, Shells, Interpreter, Downloader, Zugänge, Compiler; `SessionTracker` | Kern `timeutil` | module |
| privesc: Angriffsfläche | [mod-privesc/surface.py](../mod-privesc/surface.py) | `SurfaceScanner` (setuid, setgid, Capabilities), GTFOBins, beschreibbare sensible Dateien, privilegierte Gruppen | — | module, doctor |
| privesc: Diagnose | [mod-privesc/doctor.py](../mod-privesc/doctor.py) | Beschreibt auditd, sein Log und was seine Regeln aufgezeichnet haben, syslog, snoopy, was das Modul sieht, die Dateien der Version 1.0.0 und die Angriffsfläche (Behebungen: nur Pakete und Lesezugriff); Voraussetzung `command_source` (jede lesbare Quelle) | discovery, surface; Kern `timeutil` | module |
| privesc: Regeln | [mod-privesc/rules/](../mod-privesc/rules/) | 35 YAML-Regeln | Regel-Engine des Kerns | Collector (`RulesEngine`), Weboberfläche (`fRules`) |
| privesc: Schweregradtabelle | [mod-privesc/severity.yaml](../mod-privesc/severity.yaml) | Schweregrade der vom Modul erstellten Detektionen (Scan, sensible Dateien) | — | module (`fLoadSeverityTable`) |
| privesc: Texte | [mod-privesc/locales/](../mod-privesc/locales/) | Name, Zusammenfassung, Bezeichnungen und Hilfe der Einstellungen, Auswahlwerte | — | Weboberfläche |
| Kern: Schnittstelle | [backend/core/module.py](../../localSIEM/backend/core/module.py) | `Module`, `LineFramer` | Registry | Module |
| Kern: Registry | [backend/core/registry.py](../../localSIEM/backend/core/registry.py) | Module finden, prüfen und laden; Standardwerte und Validierung der Einstellungen | `config` | Collector, Weboberfläche, `manage.py`, `backend/core/catalog.py` |
| Kern: Weboberfläche | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) | Seiten der Module (Installiert, Installierbar, die Seite eines Moduls) und API | Registry, Katalog, Regeln | Browser |
| Kern: Katalog | [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) | Herunterladen und sicheres Entpacken des Repositorys, Liste mit der Aktion jedes Moduls (`install`, `update`, `incompatible`, `invalid`...) und `newer`, atomare Installation oder Aktualisierung (`previous`, `access_changed`), Deinstallation, Befehl für root: Module › Installierbar sowie **Aktualisieren** / **Deinstallieren** unter Module › Installiert, der einzige Weg, Module zu installieren | Registry | Weboberfläche |

<a id="symbols"></a>
## 3. Wichtige Symbole

| Symbol | Datei:Zeile | Funktion |
|---|---|---|
| `ApacheModule` | [mod-apache2/module.py:68](../mod-apache2/module.py#L68) | Das Modul apache2 (`vName = "apache2"`) |
| `fLoadSeverityTable` | [mod-apache2/module.py:54](../mod-apache2/module.py#L54) | `severity.yaml` über den eingebauten Standardwerten |
| `ApacheModule.mDiscover` | [mod-apache2/module.py:95](../mod-apache2/module.py#L95) | Parst die Konfiguration, Quellen, übersprungene Logs, DocumentRoots |
| `ApacheModule.mThreshold` | [mod-apache2/module.py:105](../mod-apache2/module.py#L105) | Anomalie-Schwellenwert: Einstellung, CRS oder 5 |
| `ApacheModule.mParse` | [mod-apache2/module.py:136](../mod-apache2/module.py#L136) | Einheit zu Eintrag, je nach Art der Quelle |
| `ApacheModule.mBuildEvent` | [mod-apache2/module.py:176](../mod-apache2/module.py#L176) | Transaktion zu Ereignis: Felder, ergriffene Aktion, Scores, Detektion |
| `ApacheModule.mVhostName` | [mod-apache2/module.py:311](../mod-apache2/module.py#L311) | Host-Header oder Hostname von ModSecurity zu dem vhost, den Apache gewählt hat (was `%v` protokolliert) |
| `ApacheModule.mAssess` | [mod-apache2/module.py:323](../mod-apache2/module.py#L323) | Schweregrad, Regelname, Beschreibung und Details dessen, was an das SOC geht |
| `ApacheModule.mDetectionFromSignal` | [mod-apache2/module.py:385](../mod-apache2/module.py#L385) | Signal einer YAML-Regel zu Detektion |
| `ApacheModule.mIsNewPhp` | [mod-apache2/module.py:414](../mod-apache2/module.py#L414) | Regelfunktion `apache2.new_php` |
| `ApacheModule.mEnrich` | [mod-apache2/module.py:442](../mod-apache2/module.py#L442) | Kontext der IP (letzte Stunde) für den Alarm |
| `ApacheModule.mHealth` | [mod-apache2/module.py:461](../mod-apache2/module.py#L461) | ModSecurity nicht geladen oder Off; echte Client-IP fehlt |
| `ApacheModule.mDisplayRecord` | [mod-apache2/module.py:538](../mod-apache2/module.py#L538) | Header und Körper für die Detailansicht der Anfrage |
| `ApacheModule.mRequirements` | [mod-apache2/module.py:545](../mod-apache2/module.py#L545) | Apache und ModSecurity 2: was das Modul benötigt, bevor es aktiviert werden kann |
| `ApacheConfig` | [mod-apache2/discovery.py:105](../mod-apache2/discovery.py#L105) | Parser der Apache-Konfiguration |
| `ApacheConfig.mDirective` | [mod-apache2/discovery.py:228](../mod-apache2/discovery.py#L228) | Gelesene Direktiven (Logs, vhosts, Module, ModSecurity) |
| `ApacheConfig.mVhostName` | [mod-apache2/discovery.py:358](../mod-apache2/discovery.py#L358) | Vhost einer Anfrage anhand ihres Host-Headers sowie lokaler Adresse und Port, so wie Apache ihn wählt |
| `fSourceKey` / `fDiscoverSources` | [mod-apache2/discovery.py:403](../mod-apache2/discovery.py#L403) / [:408](../mod-apache2/discovery.py#L408) | Stabiler Quellschlüssel; zu lesende und übersprungene Quellen |
| `fRunDoctor` | [mod-apache2/doctor.py:46](../mod-apache2/doctor.py#L46) | Prüfungen der Voraussetzungen `{id, status, title, detail, fix}` |
| `fCanPair` | [mod-apache2/doctor.py:26](../mod-apache2/doctor.py#L26) | Ob ein Access-Format ohne `UNIQUE_ID` zusammengeführt werden kann (Client-IP, Uhrzeit, Anfragezeile, Status) |
| `fRequirementChecks` | [mod-apache2/doctor.py:174](../mod-apache2/doctor.py#L174) | Die Prüfungen `apache_config` und `modsecurity` der Diagnose oder, ohne Apache, beide als Fehler, mit dem Befehl, der sie installiert |
| `AccessFormat` / `dKnownFormats` | [mod-apache2/logformat.py:60](../mod-apache2/logformat.py#L60) / [:15](../mod-apache2/logformat.py#L15) | `LogFormat` zu regulärem Ausdruck; bekannte Kurznamen |
| `AccessParser` | [mod-apache2/parsers.py:59](../mod-apache2/parsers.py#L59) | access.log-Zeile zu Eintrag |
| `fParseErrorLine` | [mod-apache2/parsers.py:147](../mod-apache2/parsers.py#L147) | error.log-Zeile: ModSecurity, Datenbank, PHP, Absturz |
| `AuditFramer` | [mod-apache2/parsers.py:233](../mod-apache2/parsers.py#L233) | Native Einträge über mehrere Zeilen; sichere Commit-Position |
| `fParseAuditRecord` / `fFinishAudit` | [mod-apache2/parsers.py:277](../mod-apache2/parsers.py#L277) / [:426](../mod-apache2/parsers.py#L426) | Audit-Eintrag in JSON oder nativ; Maskierung, Rohtext und indizierter Text |
| `fAuditDisplay` / `fReadConcurrentEntry` | [mod-apache2/parsers.py:495](../mod-apache2/parsers.py#L495) / [:577](../mod-apache2/parsers.py#L577) | Detailansicht eines gespeicherten Eintrags; Datei eines parallelen Eintrags |
| `fParseMessage` / `fSummarize` | [mod-apache2/modsec.py:52](../mod-apache2/modsec.py#L52) / [:152](../mod-apache2/modsec.py#L152) | Eine Meldung von ModSecurity; Regeln, Kategorien, Score, Schwellenwert, Abfangen |
| `Correlator` | [mod-apache2/correlate.py:57](../mod-apache2/correlate.py#L57) | `mAdd` ([:148](../mod-apache2/correlate.py#L148)), `mPair` ([:207](../mod-apache2/correlate.py#L207)), `mDue` ([:248](../mod-apache2/correlate.py#L248)), `mWaitsForAudit` ([:271](../mod-apache2/correlate.py#L271)), `mPendingCount` |
| `PrivescModule` | [mod-privesc/module.py:226](../mod-privesc/module.py#L226) | Das Modul privesc (`vName = "privesc"`) |
| `PrivescModule.mBuildEvent` | [mod-privesc/module.py:341](../mod-privesc/module.py#L341) | Transaktion zu Ereignis, je nach Quelle; `ignored`; leere Felder werden verworfen (`fCleanFields` behält 0) |
| `PrivescModule.mAnalyzeCommand` | [mod-privesc/module.py:366](../mod-privesc/module.py#L366) | Aufklärung der Sitzung, von einer Shell ausgeführter Download, Kompilieren in `/tmp`, letzte Befehle, neues Programm eines Dienstkontos |
| `PrivescModule.mAuditEvent` / `mAuditExec` / `mAuditUser` | [mod-privesc/module.py:427](../mod-privesc/module.py#L427) / [:587](../mod-privesc/module.py#L587) / [:661](../mod-privesc/module.py#L661) | Audit-Transaktion nach Typ; ausgeführte Programme (`suid_escape`, `root_without_door`, `parent_interpreter`, Capabilities); Anmeldungen, Zugänge und Fehlschläge |
| `PrivescModule.mAuditSyscall` | [mod-privesc/module.py:509](../mod-privesc/module.py#L509) | Jeder andere Systemaufruf nach Name, Argumenten und Pfaden: `denied`, `kmod`, `ptrace`, `chmod`, `file` (`sensitive_group`) oder `syscall` |
| `fSyscallName` / `fSensitiveGroup` | [mod-privesc/module.py:184](../mod-privesc/module.py#L184) / [:210](../mod-privesc/module.py#L210) | Name eines Systemaufrufs (angereicherter Name oder Nummer pro Architektur); Gruppe eines sensiblen Pfades (`lSensitivePaths`) |
| `PrivescModule.mSyslogEvent` | [mod-privesc/module.py:702](../mod-privesc/module.py#L702) | snoopy, sudo, su, pkexec, doas, Anmeldungen |
| `PrivescModule.mWriterAllowed` | [mod-privesc/module.py:412](../mod-privesc/module.py#L412) | Der Schreiber einer sensiblen Datei oder ein bekannter Vorfahr ist ein Konto- oder Paketwerkzeug |
| `PrivescModule.mDetectionFromSignal` / `mEnrich` | [mod-privesc/module.py:781](../mod-privesc/module.py#L781) / [:818](../mod-privesc/module.py#L818) | Signal einer Regel zu Detektion; Kontext der Sitzung für den Alarm |
| `PrivescModule.mHealth` / `mSurfaceResult` | [mod-privesc/module.py:851](../mod-privesc/module.py#L851) / [:903](../mod-privesc/module.py#L903) | Gespeicherte Sitzungen, gestopptes auditd, sensible Dateien, gestarteter Scan; neue setuid-Programme und Capabilities |
| `fDiscoverSources` / `fReadState` / `fLegacyLeftovers` | [mod-privesc/discovery.py:291](../mod-privesc/discovery.py#L291) / [:160](../mod-privesc/discovery.py#L160) / [:175](../mod-privesc/discovery.py#L175) | Quellen, übersprungene Quellen und Informationen für die Diagnose; ob ein Log gelesen werden kann; von Version 1.0.0 hinterlassene Dateien |
| `fContainer` / `fAuditdPid` | [mod-privesc/discovery.py:54](../mod-privesc/discovery.py#L54) / [:96](../mod-privesc/discovery.py#L96) | Art des Containers (ohne root); PID eines laufenden auditd |
| `Accounts` | [mod-privesc/discovery.py:190](../mod-privesc/discovery.py#L190) | Namen von UIDs, Gruppen, `UID_MIN`, Kontoart (`mAccountType`) |
| `fParseAuditLine` / `fParseSyslogLine` | [mod-privesc/parsers.py:83](../mod-privesc/parsers.py#L83) / [:316](../mod-privesc/parsers.py#L316) | Einträge der beiden Quellen |
| `fMaskCommand` | [mod-privesc/parsers.py:45](../mod-privesc/parsers.py#L45) | Passwörter von Befehlszeilen, danach der Maskierer des Kerns |
| `Correlator` (privesc) | [mod-privesc/correlate.py:20](../mod-privesc/correlate.py#L20) | Audit-Einträge nach Seriennummer; die anderen sofort |
| `fReconToken` / `fProgramKey` / `fCommandArgs` | [mod-privesc/commands.py:115](../mod-privesc/commands.py#L115) / [:180](../mod-privesc/commands.py#L180) / [:91](../mod-privesc/commands.py#L91) | Aufklärungstoken eines Befehls; Programm eines Dienstkontos; Wörter eines eingegebenen Befehls |
| `SessionTracker` | [mod-privesc/commands.py:202](../mod-privesc/commands.py#L202) | Sitzungen (Beginn, IP, Zugang, Aufklärung, letzte Befehle), Prozesse, Downloads; `mExport`/`mImport` |
| `SurfaceScanner` / `fCheckSensitiveFiles` | [mod-privesc/surface.py:167](../mod-privesc/surface.py#L167) / [:133](../mod-privesc/surface.py#L133) | Scan nach setuid, setgid und Capabilities in einem Thread; für andere beschreibbare sensible Dateien |
| `fRunDoctor` / `fRequirementChecks` (privesc) | [mod-privesc/doctor.py:275](../mod-privesc/doctor.py#L275) / [:282](../mod-privesc/doctor.py#L282) | Prüfungen der Diagnose (Beschreibungen; Behebungen nur für Pakete und Lesezugriff); Voraussetzung `command_source`: jede lesbare Quelle |
| `Module` / `LineFramer` | [backend/core/module.py:59](../../localSIEM/backend/core/module.py#L59) / [:48](../../localSIEM/backend/core/module.py#L48) | Schnittstelle eines Moduls; eine Zeile pro Einheit |
| `fReadManifest` | [backend/core/registry.py:133](../../localSIEM/backend/core/registry.py#L133) | Prüft `module.json`, liest die Texte |
| `fListManifests` / `fCreateModules` | [backend/core/registry.py:165](../../localSIEM/backend/core/registry.py#L165) / [:229](../../localSIEM/backend/core/registry.py#L229) | Die installierten Module (`/opt/localsiem/modules/*`); Instanzen und Fehler |
| `fRegisterPackage` / `fLoadClass` | [backend/core/registry.py:185](../../localSIEM/backend/core/registry.py#L185) / [:197](../../localSIEM/backend/core/registry.py#L197) | Namespace-Paket `localsiem_modules`; Import und Prüfungen des Einstiegspunkts |
| `fModuleSettings` / `fValidateSettings` | [backend/core/registry.py:250](../../localSIEM/backend/core/registry.py#L250) / [:317](../../localSIEM/backend/core/registry.py#L317) | Standardwerte unter den gespeicherten Werten; Validierung des Gespeicherten |
| `fSaveModule` | [backend/web/api_modules.py:290](../../localSIEM/backend/web/api_modules.py#L290) | `POST /api/admin/modules/{name}` |
| `fGetCatalog` / `fInstallFromCatalog` / `fUninstallModule` | [backend/web/api_modules.py:384](../../localSIEM/backend/web/api_modules.py#L384) / [:395](../../localSIEM/backend/web/api_modules.py#L395) / [:422](../../localSIEM/backend/web/api_modules.py#L422) | `GET /api/admin/module-catalog`; `POST /api/admin/module-catalog/{name}` (installieren oder aktualisieren; eine erste Installation ohne ihre Voraussetzungen wird deaktiviert: `fFirstInstallation`); `DELETE /api/admin/modules/{name}` |
| `fInstall` / `fCatalog` | [backend/core/catalog.py:235](../../localSIEM/backend/core/catalog.py#L235) / [:171](../../localSIEM/backend/core/catalog.py#L171) | Installiert oder aktualisiert ein Modul neben der installierten Kopie und tauscht beide durch Umbenennen aus (`previous`, `access_changed`); die Module des Repositorys mit `installed`, `newer` und ihrer Aktion |
| `fRemove` / `fRootCommand` | [backend/core/catalog.py:302](../../localSIEM/backend/core/catalog.py#L302) / [:372](../../localSIEM/backend/core/catalog.py#L372) | Deinstalliert ein Modul (Umbenennen und Löschen); der Befehl für root (`manage.py setup-modules`) |
| `fCatalogPanel` / `fUpdateNotice` / `fUpdate` | [frontend/assets/modules.js:218](../../localSIEM/frontend/assets/modules.js#L218) / [:417](../../localSIEM/frontend/assets/modules.js#L417) / [:452](../../localSIEM/frontend/assets/modules.js#L452) | Bereich Installierbar (nur die nicht installierten Module, **Installieren** und sein Dialog); Hinweis auf eine neuere Version in einer Zeile von Installiert; **Aktualisieren** (Bestätigung, derselbe `POST`, ein Dialog nur bei `access_changed` oder wenn der Collector nicht geantwortet hat) |

<a id="flows"></a>
## 4. Hauptaufrufpfade

**Start des Collectors → Registry → ApacheModule**

`Collector.mSetup` → `fCreateModules` → `fListManifests` (`/opt/localsiem/modules/*`) → `fReadManifest` (id = Ordner, entry, settings, `core` ≤ `cVersion`, `fReadTexts`) → `fCreateModule` → `fLoadClass` (`fRegisterPackage`, `import localsiem_modules.apache2.module`, Unterklasse von `Module`, `vName == id`) → `ApacheModule(dSettings, vMasker, vStorage, dManifest)` → `mStart` → `mCreateCorrelator` → `Collector.mLoadRules` (`mRulesPath`, `mRuleFunctions`, Überschreibungen `rules.<id>` → `RulesEngine.mLoad`) → `Collector.mDiscover` (`mEnabled` → `mDiscover` → `ApacheConfig.mParse` → `fDiscoverSources`; ein `FileTailer` und `mCreateFramer` pro Quelle) → ausstehende Einträge zurück in den Korrelator → `mPublishDoctor` (`mDoctor` → `fRunDoctor` → Zustand `apache2.doctor`).

**Eine gelesene Zeile → Detektionen**

1. `Collector.mReadSources` → `FileTailer.mPoll` → Framer `mFeed` (`LineFramer` oder `AuditFramer`, dessen `mSafeCommit` die Position vor einem unvollständigen Eintrag hält) → `ApacheModule.mParse` (`AccessParser.mParse`, `fParseErrorLine` oder `fReadConcurrentEntry` + `fParseAuditRecord` und `mObserveAudit`) → Einträge und Positionen in einer Transaktion gespeichert → `Correlator.mAdd`.
2. `Collector.mProcessDue` → `Correlator.mDue(pWatermark=...)` → `ApacheModule.mBuildEvent` (`fSummarize`, ergriffene Aktion, `mAssess`, `mPathFirstSeen` für 2xx `.php`) → `RulesEngine.mEvaluate` (YAML-Regeln; `{function: apache2.new_php}` → `mIsNewPhp`) → `mSaveEvents` → `mDetect` für jede Detektion und `mDetectionFromSignal` für jedes Signal → `Grouper.mAdd`.
3. `Collector.mProcessGroups` → `ApacheModule.mEnrich` (`mGetIpContext`) → `fBuildAlert` → SOC-Warteschlange.

**Der Administrator speichert die Einstellungen → Neuladen des Collectors**

`modules.js fBuildSettings` (Absenden) → `POST /api/admin/modules/apache2` `{settings}` → `fSaveModule` → `fValidateSettings` (422 `invalid_setting:<key>` oder `<key>.<field>`) → `fSaveSettings` (`settings.json`, `modules.apache2`) → `WebContext.mApplySettings` → Socket des Collectors `{"command": "reload"}` → `Collector.mHandleIpc` → `Collector.mCycle` → `mReloadSettings` (`ApacheModule.mReload`, `mLoadRules`, `mDiscover`, `mPublishDoctor`, `mPublishState`). Der Schalter sendet `{enabled}` auf dieselbe Weise (beim Aktivieren: 422 `requirements_missing`, solange eine Voraussetzung des Moduls fehlt), und die Regeltabelle sendet `{rules}` (`fCleanRules` → `rules.<id>`: `enabled`, `severity`, `threshold` oder `first_threshold`, `window`). Antwortet der Socket nicht, bemerkt der Collector die neue `settings.json` trotzdem in seinem nächsten Zyklus.

**Ein Modul über die Weboberfläche installieren** (der einzige Weg, Module zu installieren)

`modules.js fCatalogPanel` (Module › Installierbar) → **Repository prüfen** → `GET /api/admin/module-catalog` (`fGetCatalog` → `fFetchCatalog` → `fDownload` → `fCatalog`: jeder Ordner `mod-<name>/` des Repositorys, mit `installed`, `newer` und `action`) → nur die Elemente mit `installed` null werden aufgelistet → **Voraussetzungen** (`fShowRequirements` → `fRequirementsBody`: die `install_requirements` des Moduls für das System des Servers, `system` der Antwort, als root und mit `sudo`, sowie die Hinweise `install_requirements.*` seiner Locales; nichts wird ausgeführt) → **Installieren** → `POST /api/admin/module-catalog/{name}` (`fInstallFromCatalog` → `fFetchAndInstall` → `InstallLock` → `fDownload` → `fInstall`: `mod-apache2/` → `/opt/localsiem/modules/apache2/`, `previous` null, `access_changed` true) → `WebContext.mReloadModules` → `fFirstInstallation` (eine Voraussetzung fehlt und `modules.<name>.enabled` wurde nie gespeichert: `enabled = false`) → `restart` des Collectors → `fCreateModules` lädt das Modul → der Dialog «<Modul> installiert» zeigt den Befehl für root (`fRootCommand`: `manage.py setup-modules`, Lesezugriff auf die `read_paths`) oder, wenn eine Voraussetzung fehlt, die nicht erfüllten Prüfungen.

**Ein Modul über die Weboberfläche aktualisieren**

Module › Installiert wird geöffnet → `fCheckRepository` → `fFetchCatalog(false)` von `modules.js` (die letzte Antwort von `GET /api/admin/module-catalog`, 600 s lang wiederverwendet; das Installieren, Aktualisieren oder Deinstallieren eines Moduls verwirft sie) → Elemente mit `newer` und `action` `update` oder `incompatible` → `fUpdateNotice` in der Zeile (nur solange die installierte Version die verglichene ist) → **Aktualisieren** → `fUpdate` → Bestätigung → `POST /api/admin/module-catalog/{name}` (dasselbe `fInstallFromCatalog` → `fInstall`: Die neue Kopie ersetzt die installierte, `previous` ist die alte Version, `access_changed` gibt an, ob sich `read_paths` geändert hat; kein `fFirstInstallation`, daher bleiben `enabled` und die Einstellungen erhalten) → `restart` des Collectors → ein Dialog nur bei `access_changed` (der Befehl für root) oder wenn der Collector nicht geantwortet hat.

**Ein Modul über die Weboberfläche deinstallieren**

**Deinstallieren** (Zeile unter Module › Installiert oder Seite des Moduls) → `fUninstallButton` → Bestätigung → `DELETE /api/admin/modules/{name}` (`fUninstallModule` → `fRemove` → `InstallLock` → Umbenennen von `/opt/localsiem/modules/<name>/` in einen Zwischenordner, dort gelöscht) → `WebContext.mReloadModules` → `restart` des Collectors. `modules.<name>` und die Überschreibungen seiner Regeln bleiben in `settings.json`, und der von root gewährte Lesezugriff bleibt bestehen.

**Erste Installation ohne Apache oder ModSecurity → Neu konfigurieren** (localSIEM 2.2.0 oder neuer)

Installation über die Weboberfläche → `fInstall` (erste Installation) → das aus der installierten Kopie erzeugte Modul (Speicher `None`) → `ApacheModule.mRequirements` → `ApacheConfig.mParse` → `fRequirementChecks` (mit Apache: `fRunDoctor` → `apache_config`, `modsecurity`; ohne Apache beide als Fehler) → ein Fehler und `modules.apache2.enabled` nie gespeichert → `modules.apache2.enabled = false` («Aus», Schalter gesperrt, Voraussetzungen auf der Seite). Später, mit installiertem Apache und ModSecurity: **Neu konfigurieren** → `POST /api/admin/modules/apache2/reconfigure` → `mRequirements` → erfüllt → Schalter freigegeben und der Befehl für root (Lesezugriff auf die `read_paths`; apache2 hat keine `setup_option`) → der Administrator aktiviert das Modul → Neuladen des Collectors → `mDiscover` → `mPublishDoctor`.

**Detailansicht der Anfrage und Diagnose über die Weboberfläche**

`GET /api/events/{id}` → `fEvent` → `WebContext.mModule("apache2")` → `mDisplayRecord` → `fAuditDisplay`. **Erneut erkennen und Diagnose ausführen** → `POST /api/admin/modules/apache2/doctor` → Collector `{"command": "doctor"}` → `mDiscover` + `mPublishDoctor`.

**Zustand**

`Collector.mCycle` (alle 60 s) → `mCheckHealth` → `ApacheModule.mHealth` (höchstens alle 300 s; `ApacheConfig.mParse`, `mCountRecentEvents`) → `fHealthDetection` → `mDetect`.

**privesc: ein ausgeführter Befehl → Detektionen**

1. auditd schreibt `SYSCALL`, `EXECVE`, `CWD`, `PATH`, `PROCTITLE`, `EOE` mit einer Seriennummer → `FileTailer.mPoll` → `LineFramer` → `PrivescModule.mParse` → `fParseAuditLine` (Hexadezimalwerte dekodiert, `fMaskCommand`, Rohtext neu aufgebaut) → `Correlator.mAdd` (Schlüssel `audit:<time>:<serial>`, fällig bei `EOE`).
2. `Correlator.mDue` → `PrivescModule.mBuildEvent` → `mAuditEvent` → `mAuditExec` (`suid_escape`, `BPRM_FCAPS`, `root_without_door` aus `SessionTracker.mGet`, `mRememberProcess`) → `mAnalyzeCommand` (`fReconToken` → `SessionTracker.mRecon` → `recon_burst`/`recon_massive`; `cDownloadOnelinerRegex`, `mDownload`/`mRecentDownload`; `fCompileInTemporary`; `mCommand`; Dienstkonto: `fProgramKey` → `mPathFirstSeen` → `new_program`) → `fCleanFields`.
3. `RulesEngine.mEvaluate` (Regeln aus `mod-privesc/rules/`) → `PrivescModule.mDetectionFromSignal` → `Grouper.mAdd` → `Collector.mProcessGroups` → `PrivescModule.mEnrich` (Sitzung: letzte 20 Befehle) → `fBuildAlert` → SOC-Warteschlange.

Mit snoopy kommt derselbe Befehl auch als syslog-Zeile an: `fParseSyslogLine` → `fParseSyslogMessage` → `mSyslogEvent` → `mAnalyzeCommand` (Sitzung `snoopy:<uid>:<sid>`).

**privesc: Sitzungen und Zugänge**

`LOGIN` (auid und ses zugewiesen) oder `USER_LOGIN`/`USER_START` von sshd oder login → `mAuditUser` → `SessionTracker.mStart` (Benutzer, SSH-Adresse). `USER_START`/`USER_CMD` mit dem Ergebnis success von sudo, su, pkexec, doas, run0 oder systemd → `SessionTracker.mDoor`. Ein späteres `EXECVE` dieser Sitzung mit uid und euid 0 → `root_without_door` nur, wenn der Beginn gesehen wurde und es keinen Zugang gab. `mHealth` speichert `SessionTracker.mExport` höchstens jede Minute in `privesc.sessions`; `mStart` lädt es (`mImport`).

**privesc: ein von den Audit-Regeln des Servers aufgezeichneter Systemaufruf**

auditd schreibt `SYSCALL` (mit `arch`, `syscall`, `a0`-`a3`, `success`, `exit` und dem Schlüssel der Regel, die ihn aufgezeichnet hat), `CWD`, `PATH`... → `fParseAuditLine` → `Correlator` → `mAuditEvent` → `mAuditSyscall`: `fSyscallName` → fehlgeschlagenes open/exec/truncate mit `EACCES`/`EPERM` und einer Login-UID → `denied`; `init_module`/`finit_module`/`delete_module` → `kmod`; `ptrace` → `ptrace`; `chmod`/`fchmod`/`fchmodat`/`fchmodat2` mit `S_ISUID`/`S_ISGID` im Modus, nicht auf einem Ordner → `chmod` (`mWriterAllowed`); eine Änderung (ein Aufruf aus `sChangeSyscalls`, ein open mit Schreib-Flags, ein `PATH` mit `CREATE`/`DELETE`) eines Pfades aus `lSensitivePaths` → `file` mit `sensitive_group` (`dKeyHints` nur ohne auflösbaren Pfad) und `mWriterAllowed`; alles andere → `syscall`. `mBuildEvent` merkt sich für die Diagnose den Zeitpunkt jeder Art (`dRuntime["audit_kinds"]`).

**privesc: Scan der Angriffsfläche**

`mHealth` (alle 300 s, fünf Minuten nach dem Start, alle `surface_scan_hours`) → `SurfaceScanner.mStart` (Thread: `os.walk` von `scan_paths`, `os.lstat`, `os.getxattr("security.capability")` → `fCapabilities`) → nächstes `mHealth` → `mSurfaceResult` (`SurfaceScanner.mTake`, abgeglichen mit `privesc.surface`: neue setuid/setgid → `new_setuid*`, neue Capabilities → `new_capabilities`) → `mModuleDetection` → `mDetect`; das Ergebnis wird in `privesc.surface` gespeichert und von `fSurfaceChecks` angezeigt. Stündlich `fCheckSensitiveFiles` → `sensitive_file_writable`.

**privesc: Voraussetzungen und Neu konfigurieren**

`fInstall` (erste Installation) oder **Neu konfigurieren** → `PrivescModule.mRequirements` → `fRequirementChecks(mModuleSettings())` (`fContainer`, `fAuditdPid`, `fAuditLogPath` → `fReadState`; `fSyslogPath` → `fReadState`, außer `syslog_mode` ist `never`; `fSnoopyInstalled`) → eine lesbare Quelle: `command_source` ok (die nicht lesbaren als Warnungen); eine Quelle, die existiert, aber nicht gelesen werden kann: Fehler `audit_log` oder `syslog` mit dem Lesezugriff (`manage.py setup-modules` oder `setfacl`); nichts: Fehler `command_source` mit dem zu installierenden Paket. Das Modul bleibt deaktiviert, solange ein Fehler vorliegt.

<a id="routes"></a>
## 5. Einstiegspunkte

| Einstiegspunkt | Handler | Datei |
|---|---|---|
| `"entry": "module:ApacheModule"` von `module.json` | `ApacheModule` | [mod-apache2/module.py](../mod-apache2/module.py) |
| `mod-apache2/rules/*.yaml` | `RulesEngine` (Kern) | [mod-apache2/rules/](../mod-apache2/rules/) |
| Regelfunktion `apache2.new_php` | `ApacheModule.mIsNewPhp` | [mod-apache2/module.py](../mod-apache2/module.py) |
| Weboberfläche: Module › Installierbar, der einzige Weg, Module zu installieren (`GET /api/admin/module-catalog`, `POST /api/admin/module-catalog/{name}`) | `fGetCatalog`, `fInstallFromCatalog`; Ansicht `fCatalogPanel` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| Weboberfläche: **Aktualisieren** in einer Zeile von Module › Installiert (derselbe `GET`, vom Browser 10 Minuten lang wiederverwendet, und derselbe `POST`) | `fCheckRepository`, `fUpdateNotice`, `fUpdate` → `fInstallFromCatalog` | [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js), [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| Weboberfläche: **Deinstallieren** (`DELETE /api/admin/modules/{name}`) | `fUninstallModule` → `fRemove` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `read_paths` von `module.json` | `manage.py read-paths`: die Ordner, die localSIEM als root für `localsiem` lesbar macht (der Befehl von `fRootCommand`) | [backend/manage.py](../../localSIEM/backend/manage.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `manage.py modules` | `fMain` (`fModules`) | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py doctor [--json]` | `mDiscover`, `mSkipped`, `mDoctor` | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py read-paths` | `read_paths` jedes Manifests | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `/user/dashboard/modules/`; `/admin/dashboard/modules/` (302 auf `installed/`), `/admin/dashboard/modules/installed/`, `/admin/dashboard/modules/installable/` | `fUserTab` / `fAdminTab` / `fAdminModulesSection`; Ansicht `LocalsiemViews.modules` | [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| `/admin/dashboard/modules/installed/apache2/` (die ältere Adresse `/admin/dashboard/modules/apache2/` antwortet mit 301 darauf) | `fAdminModule` (die 301: `fAdminModulesSection`); Ansicht `LocalsiemViews.module` | dieselben Dateien |
| `GET /api/modules` | `fModules` (Zustand für alle angemeldeten Benutzer) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `GET /api/admin/modules/apache2` | `fModule` (Einstellungen, Werte, Quellen, Diagnose, Regeln) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2` | `fSaveModule` (`enabled`, `settings`, `rules`) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/doctor` | `fRunDoctor` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/reconfigure` (**Neu konfigurieren**, localSIEM 2.2.0 oder neuer) | `mRequirements` → `fRequirementChecks` | [mod-apache2/module.py](../mod-apache2/module.py), [mod-apache2/doctor.py](../mod-apache2/doctor.py) |
| `GET /api/events/{id}` | `fEvent` → `mDisplayRecord` | [backend/web/api_search.py](../../localSIEM/backend/web/api_search.py) |
| `"entry": "module:PrivescModule"` von `mod-privesc/module.json` | `PrivescModule` | [mod-privesc/module.py](../mod-privesc/module.py) |
| `mod-privesc/rules/*.yaml` | `RulesEngine` (Kern) | [mod-privesc/rules/](../mod-privesc/rules/) |
| `/admin/dashboard/modules/installed/privesc/`, `GET`/`POST /api/admin/modules/privesc`, `.../privesc/doctor`, `.../privesc/reconfigure` | `fAdminModule`, `fModule`, `fSaveModule`, `fRunDoctor`, `mRequirements` → `fRequirementChecks` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [mod-privesc/doctor.py](../mod-privesc/doctor.py) |
| Audit-Einträge der Regeln des Servers (beliebiger Schlüssel) | `mAuditEvent` → `mAuditExec`, `mAuditUser`, `mAuditSyscall` | [mod-privesc/module.py](../mod-privesc/module.py) |

<a id="impact"></a>
## 6. Auswirkungsanalyse

| Komponente | Was betroffen ist, wenn sie sich ändert |
|---|---|
| `module.json` `id` | Muss dem Ordnernamen ohne `mod-` (dem Namen des installierten Ordners) und dem `vName` entsprechen. Sie ist der Schlüssel der Einstellungen (`modules.<id>`), des Zustands (`<id>.doctor`) und das `module` jedes Ereignisses: Eine Umbenennung verliert die gespeicherten Einstellungen und teilt den Verlauf auf. |
| `module.json` `core` | Wird er über das installierte localSIEM angehoben, wird das Modul nicht mehr geladen (Zustand «Fehler»); im Repository zeigt Installierbar «Erfordert localSIEM X oder neuer», und Installiert zeigt die neuere Version ohne **Aktualisieren**. |
| `module.json` `entry` | Muss auf eine `Module`-Unterklasse verweisen; ein falscher Wert ist ein Ladefehler. |
| `module.json` `default_enabled` | Aktiviert/deaktiviert auf Servern, auf denen der Administrator nie entschieden hat (fehlen bei der ersten Installation seine Voraussetzungen: deaktiviert). |
| `module.json` `read_paths` | Der Lesezugriff, den localSIEM als root gewährt (`manage.py read-paths`): Ein fehlender Ordner bedeutet Berechtigungsfehler in der Diagnose und im Zustand. Eine Änderung in einer neuen Version lässt die Weboberfläche nach **Aktualisieren** den Befehl für root erneut anzeigen (`access_changed`). |
| `module.json` `install_requirements` | Der Dialog Voraussetzungen von Installierbar (`fRequirementsBody` von `modules.js`). Ein falscher Wert (ein anderes System als `debian` und `alpine`, eine leere Liste oder mehr als 20 Befehle, ein Befehl mit einem Shell-Operator oder einem Zeilenumbruch) macht das Modul ungültig (`fCheckInstallRequirements` des Kerns): Es wird weder installiert noch geladen. |
| `module.json` `setup_option` | Nichts: Der Kern ignoriert es (seit apache2 1.3.0 und privesc 1.1.0 hat kein Modul eine). |
| Ordner `mod-<name>/` mit einer `module.json` auf der obersten Ebene des Repositorys | Was der Katalog der Weboberfläche als Modul `<name>` auflistet: Installierbar zeigt die noch nicht installierten (eines, das einen neueren Kern benötigt, als «Erfordert localSIEM X oder neuer», ein ungültiges als «Das Modul des Repositorys ist ungültig»), und eine `version`, die höher als die installierte ist, lässt Installiert **Aktualisieren** anbieten. |
| `module.json` `settings` | Das Formular, die Validierung und die Standardwerte. Ein neuer Standardwert gilt für Server, die diesen Schlüssel nie gespeichert haben. Gespeicherte Werte werden nicht migriert: Ein umbenannter Schlüssel verliert seinen Wert, und ein alter Wert mit einem neuen Typ erreicht das Modul so, wie er gespeichert wurde. |
| `locales/*.json` | Nur die Texte der Weboberfläche; ein fehlender Text fällt auf en-US und dann auf den Schlüssel zurück. |
| `parsers.py` (Dict des Eintrags) | Korrelation (`correlation`, `fields.client_ip`, `fields.path`), die Detailansicht der Anfrage, der Volltextindex (`search`, `raw`), der Zustand der nicht geparsten Zeilen und der Datenschutz. |
| `logformat.py` `dKnownFormats` | Parsing jedes Access-Logs; `localsiem_combined` bleibt für die Server, die es bereits schreiben (die Versionen 1.2.0 und älter des Moduls haben es hinzugefügt): Ändern Sie seine Definition nicht. |
| `correlate.py` | Ein Ereignis pro Anfrage; der Kern ruft `mAdd`, `mDue(pNow, pForce, pWatermark)` und `mPendingCount` auf und speist nach einem Neustart die noch ausstehenden Einträge wieder ein. Ohne `UNIQUE_ID` paart er Einträge anhand ihrer Felder `client_ip`, `method`, `uri`, `status` und `path`: Ein Parser, der sie anders schreibt, bricht die Paarung. Das Warten auf den Audit-Eintrag (`mWaitsForAudit`) benötigt das Feld `modsecurity` der error.log-Zeilen und die Einträge der Quelle `audit`. |
| `modsec.py` (Kategorien, Bezeichnungen, Bereiche) | Regelnamen der Alarme (die Statistiken des SOC gruppieren danach: halten Sie sie stabil), Gruppierungsschlüssel, Suchen mit `category:`. |
| `ApacheModule.mBuildEvent` (Dict des Ereignisses) | Spalten der Ereignistabelle, die von den YAML-Regeln gelesenen Felder (`action`, `status`, `method`, `path`, `crs_matched`, `db_error`...), Suchen und der CSV-Export. |
| `ApacheModule.mAssess` | Was das SOC erreicht und mit welchem Schweregrad; die Grenzen von `GenericAlert` des Kerns (Regel 300, Beschreibung 10 000 Zeichen). |
| `severity.yaml` | Schweregrad jeder Detektion von ModSecurity; der Schweregrad ist Teil des Gruppierungsschlüssels, daher beginnt eine Änderung neue Gruppen. |
| `rules/*.yaml` | Die `id` ist der Schlüssel der Überschreibungen (`rules.<id>`) und der Suchen (`rule:localsiem:<id>`): Halten Sie sie stabil. Die Felder müssen in den Ereignissen existieren; `{function: ...}` benötigt `mRuleFunctions`. |
| `discovery.py` | Welche Logs gelesen werden; `fSourceKey` ist der Schlüssel der gespeicherten Positionen (ein neuer Schlüssel macht die Datei zu einer neuen Quelle, ohne ihre gespeicherte Position); DocumentRoots der Web-Shell-Regel; die Diagnose. |
| `doctor.py` | Die Diagnose der Weboberfläche und von `manage.py` sowie die dem Kunden angezeigten Hinweise. Nur die Prüfungen zu dem, was kein Log ist (ModSecurity, das CRS, `SecRuleEngine`, `mod_unique_id`, Berechtigungen), dürfen einen `fix` enthalten; die Prüfungen zu den Logs beschreiben diese nur. |
| `mRequirements` / `fRequirementChecks` | Ob das Modul aktiviert werden kann, der Zustand «Aus» nach einer ersten Installation ohne Apache oder ModSecurity, die Voraussetzungen, die die Weboberfläche zeigt, und **Neu konfigurieren**. Sie laufen in der Weboberfläche und in `manage.py` ohne Speicher und parsen die Apache-Konfiguration bei jedem Aufruf: Halten Sie sie vom Speicher und von allem Langsamen fern, und halten Sie die IDs `apache_config` und `modsecurity` stabil. |
| privesc: Spalten und Felder der Ereignisse (`mBuildEvent`, `mAnalyzeCommand`) | Die YAML-Regeln prüfen sie nach Namen (`recon_burst`, `suid_escape`, `root_without_door`, `sensitive_group`, `writer_allowed`, `ptrace_attach`, `parent_interpreter`, `account_type`, `real_uid`, `argc_zero`...): Ein umbenanntes Feld deaktiviert stillschweigend die Regeln, die es verwenden. `vhost` ist der Benutzer: Der Gruppierungsschlüssel der Alarme und die Suchen mit `vhost:` hängen davon ab. |
| privesc: `fReconToken` | Was als Aufklärung zählt und wie unterschiedliche Befehle auseinandergehalten werden: Die Änderung eines Tokens ändert, wie schnell eine Sitzung die Schwellenwerte erreicht. |
| privesc: `SessionTracker` und die Zugänge (`sDoors`) | `root_without_door`: Ein Zugang, der in der Liste fehlt, macht legitime root-Sitzungen kritisch; ein zusätzlicher verbirgt Kernel-Exploits. `mExport`/`mImport` ist das Format von `privesc.sessions`. |
| privesc: `parsers.py` | Die Felder der Einträge (`args`, `command`, `kind`, `uid`/`euid` von snoopy), die Maskierung von Passwörtern und der Rohtext der Audit-Einträge; die Formate von snoopy, die es liest (das Modul ändert `snoopy.ini` nie). |
| privesc: Klassifizierung der Audit-Einträge (`lSensitivePaths`, `dSyscallTables`, `sChangeSyscalls`, `dOpenFlagArgument`, `dChmodModeArgument`, `sDeniedSyscalls`, `dKeyHints`) | Was zu `file`, `chmod`, `kmod`, `ptrace` und `denied` wird, und damit die Regeln sensitive-file, persistence-file, monitoring-changed, suid-set, kernel-module, ptrace, denied-burst und sensitive-denied; eine falsche Syscall-Nummer klassifiziert die Einträge dieser Architektur falsch. |
| privesc: `surface.py` | Die Kosten des Scans (Thread, Grenzen) und was die Diagnose und `mSurfaceResult` melden; `privesc.surface` ist seine Referenz. |
| privesc: `mRequirements` / `fRequirementChecks` | Ob das Modul aktiviert werden kann (jede lesbare Quelle), der Zustand «Aus» nach einer ersten Installation, deren Logs `localsiem` noch nicht lesen kann, und **Neu konfigurieren**; ohne Speicher von der Weboberfläche und `manage.py` aufgerufen: Halten Sie es schnell und ohne root. Behalten Sie die IDs `command_source`, `audit_log` und `syslog` bei. |
| Schnittstelle des Kerns (`backend/core/module.py`, `registry.py` von localSIEM) | Jedes Modul: Eine geänderte Signatur eines Hooks, ein neuer erforderlicher Schlüssel im Manifest oder ein neuer Vertrag für Einträge und Ereignisse bricht sie; erhöhen Sie `core` in ihrer `module.json`, wenn sie das neue localSIEM benötigen. |

<a id="extensions"></a>
## 7. Erweiterungspunkte

### Wie man ein neues Modul schreibt

1. **Ordner**: Erstellen Sie `mod-<name>/` im Stammverzeichnis dieses Projekts; `<name>`, der Name des Moduls, entspricht `[a-z][a-z0-9_]{1,31}`. Das Präfix `mod-` gilt nur für den Ordner: `module.json`, die Klasse, die Optionen und die Texte verwenden `<name>`. Keine `__init__.py`.
2. **`module.json`**, zum Beispiel:

   ```json
   {
     "id": "example",
     "version": "1.0.0",
     "core": "2.2.0",
     "entry": "module:ExampleModule",
     "default_enabled": false,
     "read_paths": ["/var/log/example"],
     "install_requirements": {"debian": ["apt-get -y install example"], "alpine": ["apk add example"]},
     "settings": [
       {"key": "log_file", "type": "path", "default": "/var/log/example/example.log"}
     ]
   }
   ```

3. **Texte**: `locales/<language>.json` für jede der 15 Sprachen von localSIEM mit `name`, `summary` sowie der Bezeichnung und Hilfe jeder Einstellung. Die Hinweise zu den Voraussetzungen kommen in `install_requirements` (`note`, für alle Systeme, sowie `debian` und `alpine`) und werden im Dialog Voraussetzungen angezeigt.
4. **Code**: `module.py` mit einer Unterklasse von `Module`, deren `vName` die ID ist. Sie muss `mParse`, `mCreateCorrelator` und `mBuildEvent` implementieren und in der Regel `mDiscover`; die anderen Hooks sind optional (Abschnitt 1). Importieren Sie die eigenen Dateien relativ und den Kern als `backend.core...`. Die beiden Module dieses Repositorys sind vollständige Beispiele ([mod-apache2/module.py](../mod-apache2/module.py), [mod-privesc/module.py](../mod-privesc/module.py)); ein minimales Gerüst:

   ```python
   from backend.core.module import Module


   class OneEventCorrelator:
     # Jeder Eintrag ist ein eigenes Ereignis, ohne Wartezeit.

     def __init__(self):
       self.lPending = []

     def mAdd(self, pRecord: dict, pNow: float | None = None) -> None:
       self.lPending.append({"key": "x", "records": [pRecord], "weak": False, "uid": None})

     def mDue(self, pNow: float | None = None, pForce: bool = False, pWatermark: float | None = None) -> list[dict]:
       lDue = self.lPending
       self.lPending = []
       return lDue

     def mPendingCount(self) -> int:
       return len(self.lPending)


   class ExampleModule(Module):

     vName = "example"

     def mDiscover(self) -> list[dict]:
       vPath = self.mModuleSettings().get("log_file", "")
       return [{"key": "example:log:" + vPath, "path": vPath, "kind": "log", "format": "", "vhost": ""}] if vPath else []

     def mParse(self, pSource: dict, pUnit: str, pReceived: str) -> dict:
       return {
         "time": pReceived, "received": pReceived, "module": "example", "source": pSource["kind"],
         "source_key": pSource["key"], "correlation": None, "parse_status": "ok",
         "fields": {}, "raw": self.vMasker.mMaskText(pUnit)
       }

     def mCreateCorrelator(self):
       return OneEventCorrelator()

     def mBuildEvent(self, pTransaction: dict) -> dict:
       dRecord = pTransaction["records"][0]
       dEvent = {vColumn: None for vColumn in ("vhost", "method", "uri", "path", "query", "status", "bytes", "duration", "ua", "referer", "uid", "category", "phase", "score", "threshold", "engine", "severity")}
       dEvent.update({
         "time": dRecord["time"], "received": dRecord["received"], "host": self.dSettings["host"], "module": "example",
         "sources": [dRecord["source"]], "ip": None, "rules": [], "action": "none", "parse_status": dRecord["parse_status"],
         "correlation": "none", "fields": {}, "record_ids": [dRecord["id"]] if dRecord.get("id") else [],
         "rule_hits": [], "detections": []
       })
       return dEvent
   ```

5. **Ergriffene Aktion**: Legen Sie fest, was «bereits behoben» für den Dienst bedeutet (zum Beispiel eine bereits gesperrte IP), und setzen Sie dafür `action` auf `blocked`; fügen Sie eine Detektion nur zu Ereignissen ohne ergriffene Aktion hinzu.
6. **Regeln**: YAML-Dateien in `mod-<name>/rules/`, zurückgegeben von `mRulesPath`, und die Funktionen, die sie aufrufen, in `mRuleFunctions`.
7. **Voraussetzungen**: Benötigt das Modul Software auf dem Server (so wie apache2 Apache und ModSecurity 2 benötigt), geben Sie aus `mRequirements()` eine Prüfung pro Voraussetzung zurück (das Format von `fCheck`: `status` `ok` oder `error` und in `fix` der Befehl, der sie installiert), und installieren Sie diese Software nie aus dem Modul heraus: Ohne seine Voraussetzungen wird das Modul deaktiviert installiert. Es läuft ohne Speicher, auch in der Weboberfläche und in `manage.py`. Geben Sie außerdem in `install_requirements` von `module.json` die Befehle an, die diese Software unter Debian und unter Alpine installieren (ein Befehl pro Zeile, ohne Shell-Operatoren): Die Weboberfläche zeigt sie unter Module › Installierbar › Voraussetzungen, so wie sie sind und mit vorangestelltem `sudo`, bevor das Modul installiert wird.
8. **Installieren**: Veröffentlichen Sie es in diesem Repository (Branch `main`); es erscheint unter Module › Installierbar in der Weboberfläche von localSIEM, solange es nicht installiert ist, und **Installieren** kopiert den Ordner `mod-<name>/` nach `/opt/localsiem/modules/<name>/` und startet den Collector neu. Der Lesezugriff auf seine `read_paths` erfordert root: Die Weboberfläche zeigt den Befehl (`manage.py setup-modules`). Ein Modul hat keine Einrichtungsoption: Es installiert nie etwas und ändert nie etwas außerhalb von `/opt/localsiem`, schreibt nie in die Logs des Kunden, rotiert oder löscht sie nie und ändert nie ihr Format; schreibt ein Server seine Logs auf seine eigene Weise, passt sich das Modul daran an, und was dem Server fehlt, ist eine Voraussetzung. Um eine neue Version zu veröffentlichen, erhöhen Sie `version`: Module › Installiert zeigt den Hinweis und **Aktualisieren**, das die Einstellungen und den Aktivierungszustand des Moduls beibehält und den Befehl für root nur dann erneut anzeigt, wenn sich `read_paths` geändert hat.
9. **Dokumentation**: Aktualisieren Sie das README, dieses CODE und das MANUAL in den 15 Sprachen.

### Wie man dem Modul apache2 eine Regel hinzufügt

Erstellen Sie eine YAML-Datei in [mod-apache2/rules/](../mod-apache2/rules/) (jeder Schlüssel und Operator ist am Anfang von [backend/core/rules.py](../../localSIEM/backend/core/rules.py) beschrieben): `id`, `name`, `category`, `type`, `severity`, `kind` (`match`, `threshold` oder `sequence`), die Bedingungen (`when` oder `first`/`first_threshold`/`then`), `by`, `window`, `threshold`, `lists`, `description` und `search`. Felder werden zuerst in den Spalten des Ereignisses und dann in `fields` gesucht. Sie erscheint in der Regeltabelle der Seite des Moduls und wird vom Collector geladen, sobald die neue Version des Moduls installiert ist: Erhöhen Sie `version` in `module.json`, veröffentlichen Sie sie und klicken Sie unter Module › Installiert auf **Aktualisieren**.

### Wie man dem Modul apache2 eine Einstellung hinzufügt

Fügen Sie sie mit ihrem Typ und Standardwert zu `settings` von [mod-apache2/module.json](../mod-apache2/module.json) hinzu, fügen Sie ihr `label` und ihre `help` zu den vier Dateien von [mod-apache2/locales/](../mod-apache2/locales/) hinzu und lesen Sie sie mit `self.mModuleSettings().get("<key>")`. Das Formular, die Validierung und das Neuladen stellt der Kern bereit.

### Wie man eine Prüfung der Diagnose hinzufügt oder einen Schweregrad ändert

Eine Prüfung ist ein `fCheck(id, status, title, detail, fix)` in `fRunDoctor` ([mod-apache2/doctor.py](../mod-apache2/doctor.py)); halten Sie die `id` stabil und setzen Sie in `fix` das genaue Konfigurationsfragment oder den genauen Befehl, nur für Voraussetzungen, die keine Logs sind: Eine Prüfung zu den Logs des Kunden beschreibt nur diese und was localSIEM aus ihnen lesen kann oder nicht, ohne `fix`. Die Schweregrade der Detektionen von ModSecurity werden in [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) geändert (`low`, `medium`, `high`, `critical`).

### Wie man dem Modul privesc eine Regel hinzufügt

Erstellen Sie eine YAML-Datei in [mod-privesc/rules/](../mod-privesc/rules/), wie die von Apache. Prüfen Sie die Spalten (`method`, `uri`, `path`, `vhost`, `action`) und die Felder der Ereignisse (`sensitive_group`, `account_type`, `real_uid`, `recon`, `service_account`, `file`...), nie den Schlüssel einer Audit-Regel; fügen Sie `ignored: {not: true}` hinzu, damit die ignorierten Benutzer sie nie auslösen, und `action: none`, wenn nur zählt, was tatsächlich ausgeführt wurde. Benötigt die Bedingung Zustand oder Logik (eine Sequenz derselben Sitzung, eine Prüfung einer Datei), berechnen Sie ein Flag in `PrivescModule.mAnalyzeCommand` (alle Quellen) oder in `mAuditExec`/`mAuditSyscall`/`mSyslogEvent` (eine Quelle) und prüfen Sie es in der Regel.

### Wie man dem Modul privesc einen Aufklärungsbefehl, ein Werkzeug oder einen Exploit hinzufügt

- Aufklärung: Fügen Sie das Programm zu `sReconSimple` hinzu oder einen Zweig zu `fReconToken`, der ein Token pro Art von Frage zurückgibt ([mod-privesc/commands.py](../mod-privesc/commands.py)). Ein Token, das sich mit jedem Argument ändert, bläht die Zählungen auf.
- Werkzeuge und Exploits: Fügen Sie einen regulären Ausdruck zur Liste von [rules/known-tool.yaml](../mod-privesc/rules/known-tool.yaml) oder [rules/exploit.yaml](../mod-privesc/rules/exploit.yaml) hinzu (ohne Beachtung der Groß-/Kleinschreibung, mit der Befehlszeile abgeglichen); der Administrator kann sie auch über die Einstellungen hinzufügen (`rules.<id>.lists`).

### Wie man dem Modul privesc eine Quelle oder eine Art von Audit-Eintrag hinzufügt

- Ein sensibler Pfad: Fügen Sie ihn mit seiner Gruppe zu `lSensitivePaths` von [mod-privesc/module.py](../mod-privesc/module.py) hinzu (oder eine neue Gruppe und eine Regel, die `sensitive_group` prüft). Eine Art von Systemaufruf: Fügen Sie seinen Namen zu den Mengen von `mAuditSyscall` und seine Nummer zu jeder Tabelle von `dSyscallTables` hinzu. Hängen Sie nie vom Schlüssel einer Audit-Regel ab (fügen Sie ihn höchstens zu `dKeyHints` hinzu) und installieren Sie nie Audit-Regeln: Der Server zeichnet auf, was sein Administrator entscheidet, und die Diagnose beschreibt es (`dAuditKinds` von [doctor.py](../mod-privesc/doctor.py)).
- Eine Quelle: Geben Sie sie aus `fDiscoverSources` mit einer neuen `kind` zurück, parsen Sie sie in `mParse` und bauen Sie ihre Ereignisse in `mBuildEvent` mit denselben Spalten und Feldern wie die anderen, damit die Regeln ohne Änderungen funktionieren.
