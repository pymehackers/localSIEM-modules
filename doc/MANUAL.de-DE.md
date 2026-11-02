# Benutzerhandbuch von localSIEM-modules

Dieses MANUAL ist auch in folgenden Sprachen verfügbar:\
de-DE, [en-GB](MANUAL.en-GB.md), [en-US](MANUAL.md), [es-AR](MANUAL.es-AR.md), [es-ES](MANUAL.es-ES.md), [fr-FR](MANUAL.fr-FR.md), [he-IL](MANUAL.he-IL.md), [hi-IN](MANUAL.hi-IN.md), [it-IT](MANUAL.it-IT.md), [ja-JP](MANUAL.ja-JP.md), [ko-KR](MANUAL.ko-KR.md), [pt-BR](MANUAL.pt-BR.md), [pt-PT](MANUAL.pt-PT.md), [ru-RU](MANUAL.ru-RU.md), [zh-CN](MANUAL.zh-CN.md)

[Installation](README.de-DE.md) · [Code-Referenz](CODE.de-DE.md) · [Handbuch von localSIEM](../../localSIEM/doc/MANUAL.de-DE.md)

## Inhalt

1. [Was die Module sind](#what)
2. [Die Module installieren und aktualisieren](#installation)
3. [Die Seite Module](#modules-page)
4. [Die Seite des Apache-Moduls](#apache-page)
5. [Einstellungen des Apache-Moduls](#settings)
6. [Was das Apache-Modul an das SOC sendet](#soc)
7. [Voraussetzungen von Apache und ModSecurity: die Diagnose](#doctor)
8. [Die Logs des Kunden werden nie angetastet](#client-logs)
9. [Regeln des Apache-Moduls](#rules)
10. [Zustandswarnungen des Apache-Moduls](#health)
11. [Das Modul zur Rechteausweitung](#privesc)
12. [Einstellungen des Moduls zur Rechteausweitung](#privesc-settings)
13. [Was das Modul zur Rechteausweitung an das SOC sendet: seine Regeln](#privesc-rules)
14. [Voraussetzungen des Moduls zur Rechteausweitung: die Diagnose](#privesc-doctor)
15. [Server, die von Version 1.0.0 des Moduls zur Rechteausweitung aktualisiert wurden](#privesc-legacy)
16. [Angriffsfläche und Zustandswarnungen des Moduls zur Rechteausweitung](#privesc-health)
17. [Kommandozeile](#cli)

<a id="what"></a>
## 1. Was die Module sind

localSIEM besteht aus einem **Kern** und **Modulen**. Der Kern speichert die Ereignisse, durchsucht sie, wendet die Regeln an, gruppiert die Alarme, sendet sie an das SOC und überwacht seinen eigenen Zustand. Jedes Modul fügt einen Dienst des Servers hinzu: Es findet dessen Logs, liest sie, wandelt sie in Ereignisse um, entscheidet, was bereits behoben ist, bringt seine eigenen Regeln mit und prüft die Voraussetzungen dieses Dienstes.

Die Module dieses Projekts werden in `/opt/localsiem/modules/<name>/` installiert. Derzeit gibt es zwei: **apache2** («Apache + ModSecurity», Abschnitte 4 bis 10) und **privesc** («Rechteausweitung», Abschnitte 11 bis 16). localSIEM hat keine eigenen Module: Die Seite Module listet nur die aus diesem Repository installierten Module auf.

<a id="installation"></a>
## 2. Die Module installieren und aktualisieren

Zuerst muss localSIEM installiert werden; sein Installationsprogramm installiert nur den Kern, nie ein Modul. Die Module dieses Projekts werden **ausschließlich über die Weboberfläche von localSIEM** installiert: Dieses Projekt hat kein eigenes Installationsprogramm. Die Weboberfläche lädt sie aus dem Repository `https://github.com/PYMEHackers/localSIEM-modules` (Branch `main`) herunter. Die Module benötigen localSIEM 2.2.0 oder neuer.

**Installieren.** Öffnen Sie als Administrator Module › **Installierbar** (Abschnitt 3), klicken Sie auf **Repository prüfen**, sehen Sie sich **Voraussetzungen** an (was das Modul auf dem Server benötigt, und die Befehle, die es installieren und vor der Installation des Moduls auszuführen sind) und klicken Sie dann beim Modul auf **Installieren**. Danach geht localSIEM wie folgt vor:

1. Es lädt das Repository herunter und entpackt es sicher (nichts außerhalb seines Ordners, Größenbeschränkungen);
2. Es kopiert den Ordner des Moduls (`mod-<name>/` im Repository) nach `/opt/localsiem/modules/<name>/`, ohne `tests/` (und ohne Python-Caches); ein erneut installiertes Modul erhält die Einstellungen zurück, die es hatte;
3. Es startet den Collector neu, der das Modul innerhalb weniger Sekunden lädt;
4. Es nimmt das Modul aus der Liste und öffnet den Dialog «<Modul> installiert» mit dem Befehl, der auf dem Server als root auszuführen ist (`manage.py setup-modules`), und einer Schaltfläche **Kopieren**: Er gibt dem Benutzer `localsiem` Lesezugriff auf die Ordner, die in `read_paths` seiner `module.json` aufgeführt sind (`/var/log/apache2` für das Modul apache2, `/var/log/audit` für das Modul privesc), auch auf die Dateien der nächsten Rotationen, und startet localSIEM neu. Dieser Lesezugriff ist alles, was ein Modul braucht: Module haben keine Einrichtungsoptionen und ändern nie den Server (Abschnitte 8 und 11). Bis der Befehl ausgeführt wurde, kann das Modul «Fehler» anzeigen: Seine Logs können noch nicht gelesen werden. Der Dialog wird mit «Schließen» oder mit «Installierte Module anzeigen» geschlossen, das Installiert öffnet.

**Aktualisieren.** Wenn Module › **Installiert** geöffnet wird, prüft die Weboberfläche das Repository, und ein Modul, für das es dort eine neuere Version gibt, zeigt einen Hinweis mit **Aktualisieren** (Abschnitt 3). Nach Ihrer Bestätigung lädt localSIEM die neue Version herunter und setzt sie an die Stelle der installierten (Schritte 1 bis 3), behält ihre Einstellungen bei und lässt das Modul aktiviert oder deaktiviert, wie es war. Der Befehl für root wird nur dann erneut angezeigt, wenn die neue Version andere Logs liest (`read_paths`); andernfalls ist nichts auszuführen. Eine Aktualisierung von localSIEM behält die installierten Module und ihren Lesezugriff bei.

**Neu installieren.** Die Weboberfläche installiert ein Modul weder neu noch installiert sie eine ältere Version davon: Um ein Modul neu zu installieren, klicken Sie auf **Deinstallieren** (Abschnitt 3) und installieren Sie es erneut über **Installierbar**; seine Einstellungen bleiben erhalten.

**Die Installation eines Moduls installiert nie die Software, die es überwacht.** Das Modul apache2 installiert weder Apache noch ModSecurity, und das Modul privesc installiert weder auditd noch einen syslog-Daemon noch snoopy. Fehlt dem Server bei der ersten Installation, was das Modul benötigt (Apache und ModSecurity für apache2; für privesc eine Quelle, die `localsiem` lesen kann, Abschnitt 14), wird das Modul **deaktiviert** installiert: Der Dialog listet anstelle des Befehls auf, was fehlt, und das Modul kann erst aktiviert werden, wenn **Neu konfigurieren** es findet (Abschnitt 4). Eine Aktualisierung lässt das Modul aktiviert oder deaktiviert, wie es war.

<a id="modules-page"></a>
## 3. Die Seite Module

Administratoren öffnen **Administration › Module**, die zwei Bereiche hat, jeder unter seiner eigenen Adresse: **Installiert** (`/admin/dashboard/modules/installed/`), der standardmäßig geöffnet wird (`/admin/dashboard/modules/` führt dorthin), und **Installierbar** (`/admin/dashboard/modules/installable/`). Analysten sehen **Module** in ihrem Dashboard (`/user/dashboard/modules/`): nur die Liste der installierten Module, schreibgeschützt, ohne Bereiche.

**Installiert** zeigt eine Zeile pro installiertem Modul über die gesamte Breite: seinen Namen, seine ID, seine Version, eine Zustandsanzeige, seine Zusammenfassung und darunter die Gründe für diesen Zustand. Die Liste aktualisiert sich alle 10 Sekunden von selbst. Ist kein Modul installiert, erscheint «Installieren Sie Module über die Registerkarte Installierbar.» (für Analysten: «Keine Module installiert. Ein Administrator installiert sie unter Module › Installierbar.»).

| Zustand | Bedeutung |
|---|---|
| **Aktiv und funktionsfähig** | Aktiviert, vom Collector geladen und liest seine Quellen. Warnungen der Diagnose werden als Hinweise aufgeführt, ändern aber den Zustand nicht. |
| **Aktiv, mit Warnungen** | Aktiviert, aber es wurden keine Logs zum Lesen gefunden, eine Quelle existiert noch nicht, oder das Modul wurde nach dem Start des Collectors installiert (starten Sie den Dienst `localsiem` neu). |
| **Fehler** | Das Modul wird nicht geladen (der Fehler wird angezeigt), seine Diagnose meldet einen Fehler, oder eine Quelle kann nicht gelesen werden (Berechtigungen des Benutzers `localsiem`). |
| **Aus** | Deaktiviert oder ohne seine Voraussetzungen installiert (für apache2: Apache oder ModSecurity fehlt; für privesc: `localsiem` kann weder das Log von auditd noch syslog lesen), wie sein Grund angibt. |
| **Änderung wird übernommen…** | Gerade aktiviert oder deaktiviert: Der Collector übernimmt die Änderung. |
| **Unbekannt** | Der Collector (Dienst `localsiem`) läuft nicht, daher wird nichts gelesen. |

Wenn das Modul nicht deaktiviert ist, zeigt die Zeile außerdem: **Gelesene Quellen** (gelesen / gefunden), **Zeilen (1 h)**, **Letzte Daten**, **Ereignisse (24 h)**, **Blockiert (24 h)** und die Zähler der **Diagnose** («n OK · n Warnungen · n Fehler»).

Administratoren erhalten in jeder Zeile außerdem:

- **Den Schalter** jedes Moduls. Das Deaktivieren eines Moduls verlangt eine Bestätigung: localSIEM liest seine Logs nicht mehr und sendet seine Alarme nicht mehr, bis es wieder aktiviert wird; bereits Gespeichertes bleibt erhalten. Das Aktivieren startet das Lesen sofort. Solange eine Voraussetzung des Moduls fehlt, ist der Schalter gesperrt («Aus: Voraussetzungen fehlen»): **Neu konfigurieren** (Abschnitt 4) gibt ihn frei, sobald es sie findet.
- **Konfigurieren**, das die Seite des Moduls öffnet, `/admin/dashboard/modules/installed/<name>/` (Abschnitt 4); die ältere Adresse `/admin/dashboard/modules/<name>/` führt dorthin.
- **Deinstallieren**, auch bei einem Modul, das nicht geladen wird (und auf der Seite des Moduls). Nach Ihrer Bestätigung löscht localSIEM `/opt/localsiem/modules/<name>/` und startet den Collector ohne das Modul neu: Es liest seine Logs nicht mehr und sendet seine Alarme nicht mehr. Die bereits gespeicherten Ereignisse können weiterhin durchsucht werden, und seine Einstellungen bleiben erhalten, falls Sie es erneut installieren. Der Lesezugriff auf seine Logs, den root `localsiem` gegeben hat, wird nicht entzogen.
- **Aktualisieren**, wenn das Repository eine neuere Version des Moduls hat. Jedes Mal, wenn Installiert geöffnet wird, prüft die Weboberfläche das Repository («Repository wird auf neuere Versionen geprüft…»; der Browser verwendet die Antwort 10 Minuten lang wieder), und eine Zeile, deren Modul eine neuere Version hat, zeigt «Das Repository hat Version X (installiert ist Y).» mit der Schaltfläche **Aktualisieren**. Nach Ihrer Bestätigung installiert localSIEM die neue Version (Abschnitt 2), behält ihre Einstellungen bei, lässt das Modul aktiviert oder deaktiviert, wie es war, und startet den Collector neu; ein Dialog zeigt den Befehl für root nur dann, wenn die neue Version andere Logs liest. Erfordert die neue Version ein neueres localSIEM, lautet der Hinweis «Das Repository hat Version X, diese erfordert jedoch localSIEM Z oder neuer: Aktualisieren Sie localSIEM, um sie zu installieren.» und hat keine Schaltfläche.

**Installierbar** (nur für Administratoren) enthält die Karte «Installierbare Module». **Repository prüfen** lädt das Repository herunter und listet die Module auf, die auf diesem Server noch nicht installiert sind, jedes mit Namen, ID, Version und Zusammenfassung und einer Schaltfläche oder einem Hinweis:

| Schaltfläche oder Hinweis | Bedeutung |
|---|---|
| **Voraussetzungen** | Zeigt, was das Modul auf dem Server benötigt, und die Befehle, die es installieren, als root und mit sudo (siehe unten) |
| **Installieren** | Installiert das Modul (Abschnitt 2) |
| «Erfordert localSIEM X oder neuer» | Es kann nicht installiert werden: Aktualisieren Sie zuerst localSIEM |
| «Das Modul des Repositorys ist ungültig» | Es kann nicht installiert werden |

Bereits installierte Module erscheinen hier nie: Sie werden über Installiert aktualisiert. Sind alle Module des Repositorys installiert, zeigt die Karte «Alle Module des Repositorys sind bereits installiert.». Nach der Installation zeigt der Dialog «<Modul> installiert» den Befehl, der als root auszuführen ist, damit `localsiem` die Logs des Moduls lesen kann (Abschnitt 2), mit einer Schaltfläche **Kopieren**; bis er ausgeführt wurde, kann das Modul «Fehler» anzeigen: Seine Logs können noch nicht gelesen werden. Fehlt dem Server, was das Modul benötigt, listet der Dialog stattdessen auf, was fehlt, mit dem Hinweis, das Modul unter Installiert zu öffnen (**Konfigurieren**) und auf **Neu konfigurieren** zu klicken, sobald es vorhanden ist.

**Voraussetzungen** öffnet «<Modul>: Voraussetzungen»: was das Modul auf dem Server benötigt, und die Befehle, die es auf dem System dieses Servers installieren («Dieser Server: …»), wie vom Modul angegeben (`install_requirements` seiner `module.json`), zweimal, jeweils mit **Kopieren**: **Als root** und **Mit sudo** (dieselben Befehle mit vorangestelltem `sudo`). Führen Sie sie auf dem Server aus, bevor Sie das Modul installieren: Dessen Installation installiert diese Software nie, und localSIEM führt sie nie aus. Für das Modul apache2 unter Debian: `apt-get -y update`, `apt-get -y install apache2 libapache2-mod-security2 modsecurity-crs`, `a2enmod security2 unique_id`, `cp --update=none /etc/modsecurity/modsecurity.conf-recommended /etc/modsecurity/modsecurity.conf` (erstellt die Konfiguration von ModSecurity, DetectionOnly, nur, wenn keine vorhanden ist) und `systemctl restart apache2`; unter Alpine nur Apache (`apk add apache2`, dann `rc-update` und `rc-service`, um es zu starten), weil Alpine kein ModSecurity-2-Paket hat: Solange ModSecurity nicht aus dem Quellcode kompiliert und geladen ist, bleibt das Modul deaktiviert. Für das Modul privesc: `apt-get -y install auditd rsyslog` unter Debian und `apk add audit` mit beim Booten gestartetem auditd unter Alpine; eine einzige lesbare Quelle genügt, und in einem Container kann auditd nicht laufen.

<a id="apache-page"></a>
## 4. Die Seite des Apache-Moduls

`/admin/dashboard/modules/installed/apache2/` (nur für Administratoren; die ältere Adresse `/admin/dashboard/modules/apache2/` führt dorthin) hat fünf Teile:

1. **Kopfbereich**: Name, ID, Version, der Installationspfad (`/opt/localsiem/modules/apache2`), der Schalter, der Zustand mit seinen Gründen und die Kennzahlen aus Abschnitt 3. **Zurück zu den installierten Modulen** kehrt zu Installiert zurück; **Erneut erkennen und Diagnose ausführen** liest die Apache-Konfiguration sofort erneut und aktualisiert die Diagnose; **Neu konfigurieren** sucht erneut nach Apache und ModSecurity (siehe unten); **Deinstallieren** deinstalliert das Modul (Abschnitt 3) und kehrt zu Installiert zurück.
2. **Einstellungen**: das Formular aus Abschnitt 5. **Einstellungen speichern** prüft jeden Wert und gibt, wenn einer falsch ist, an, welcher («Ungültiger Wert: …»).
3. **Quellen**: jedes gelesene Log, mit **Art** (`access`, `error`, `audit`), **Pfad**, **Vhost**, **Zeilen (1 h)**, **Nicht geparst (1 h)**, **Letzte Daten** (zum Beispiel `2026/10/29@13:59:59.723`) und **Zustand** (Fehler, wenn es nicht gelesen werden kann, Warnung, wenn es noch nicht existiert). Darunter die gefundenen, aber nicht gelesenen Logs mit dem Grund: «Log über Pipe, nicht unterstützt», «abgedeckt durch ein GlobalLog, das alle vhosts schreibt» oder «sein Format enthält keine Daten: Jede Zeile ist derselbe Text (ein nicht definierter LogFormat-Kurzname)».
4. **Diagnose**: die Prüfungen aus Abschnitt 7 mit dem Zeitpunkt ihrer Ausführung. Zu jeder fehlenden Voraussetzung (ModSecurity, das CRS, `SecRuleEngine`, `mod_unique_id`, der Lesezugriff von `localsiem`) gehören das Konfigurationsfragment oder der Befehl, der sie behebt, und eine Schaltfläche **Kopieren**. Die Prüfungen zu den Logs beschreiben nur diese und was localSIEM aus ihnen lesen kann, ohne Behebung: Die Logs des Kunden werden nie geändert (Abschnitt 8).
5. **Regeln**: die Regeln aus Abschnitt 9, jede mit **Aktiv**, **Regel** (Name, ID und Kategorie), **Schweregrad**, **Schwellenwert** und **Zeitfenster (s)**, sowie **Regeln speichern**.

**Voraussetzungen und Neu konfigurieren.** Solange Apache oder ModSecurity fehlt, ist das Modul deaktiviert, und der Kopfbereich listet auf, was fehlt, mit dem Befehl, der es installiert. **Neu konfigurieren** (auch bei deaktiviertem Modul) sucht mit den gespeicherten Einstellungen erneut danach; liegt Apache an einem nicht standardmäßigen Ort, legen Sie zuerst die **Apache-Konfigurationsdatei** fest (Abschnitt 5). Werden beide gefunden, gibt es den Schalter frei —das Modul zu aktivieren ist Ihre Entscheidung— und zeigt den Befehl, der als root auszuführen ist, damit `localsiem` die Apache-Logs lesen kann, die nach der Installation des Moduls erstellt wurden. Ein aktiviertes Modul, das Apache oder ModSecurity verliert, bleibt aktiviert: Die Diagnose und die Zustandswarnungen (Abschnitt 10) melden es.

**Jede Änderung wird sofort übernommen, ohne etwas neu zu starten**: Die Weboberfläche speichert sie und benachrichtigt den Collector, der seine Einstellungen neu lädt, die Quellen erneut erkennt und die Diagnose ausführt. Antwortet der Collector nicht, weist die Weboberfläche darauf hin, und die Änderung wird beim Start des Collectors übernommen.

<a id="settings"></a>
## 5. Einstellungen des Apache-Moduls

| Einstellung | Standard | Funktion |
|---|---|---|
| **Nur die Quellen unten** | aus | Die Logs nicht aus der Apache-Konfiguration erkennen: nur die manuell hinzugefügten Quellen lesen. |
| **Manuell hinzugefügte Quellen** | keine | Logs, die zusätzlich zu den erkannten gelesen werden (oder stattdessen, mit der Option oben). Bis zu 50. |
| **Apache-Konfigurationsdatei** | leer | Leer: wird automatisch gefunden (`/etc/apache2/apache2.conf` unter Debian, `/etc/apache2/httpd.conf` unter Alpine; `/etc/httpd/conf/httpd.conf` wird ebenfalls erkannt). Ein absoluter Pfad verwendet stattdessen diese Datei, sofern sie existiert. |
| **Erkennungsintervall (Sekunden)** | 3600 | Wie oft die Apache-Konfiguration erneut gelesen wird, um neue vhosts und Logs zu finden (60 bis 86400). |
| **Blockierungsschwellenwert von ModSecurity** | 0 | 0: wird aus der CRS-Konfiguration gelesen (`tx.inbound_anomaly_score_threshold` in `crs-setup.conf`), 5, falls er dort nicht vorhanden ist. Dient dazu, einen Treffer oberhalb des Blockierungsschwellenwerts von einem darunter zu unterscheiden, wenn die Meldungen von ModSecurity den Schwellenwert nicht selbst angeben (0 bis 1000). |
| **Lerntage für neue PHP-Dateien** | 3 | In den ersten Tagen nach dem ersten Start des Moduls wird eine nie zuvor gesehene PHP-Datei von der Regel `apache-webshell` nicht als neu gemeldet (0 bis 365). Eine Datei, die am letzten Tag in ihrem DocumentRoot erstellt oder geändert wurde, gilt immer als neu. |

Jede **manuell hinzugefügte Quelle** hat diese Felder (* Pflichtfeld):

| Feld | Verwendung |
|---|---|
| **Art** * | `access.log`, `error.log` oder `Audit-Log von ModSecurity` |
| **Pfad** * | Absoluter Pfad der Datei |
| **Vhost** | Vhost der Zeilen, für Logs, deren Zeilen ihn nicht angeben |
| **LogFormat** | Für Access-Logs: ein Kurzname (`localsiem_combined`, `combined`, `vhost_combined`, `common`, `combinedio` oder einer, der in der Apache-Konfiguration definiert ist) oder das Format selbst. Leer: Die üblichen Formate werden ausprobiert. |
| **Typ des Audit-Logs** | `Seriell (eine Datei)` oder `Parallel (eine Datei pro Anfrage)` |
| **Audit-Speicherordner** | Für den parallelen Typ: der Ordner von `SecAuditLogStorageDir` |

Eine Datei wird nur einmal gelesen, auch wenn sie sowohl erkannt als auch manuell hinzugefügt wurde. Eine Quelle, die erscheint, während localSIEM läuft, wird von ihrem Anfang an gelesen, wenn sie 5 MB oder kleiner ist, andernfalls ab ihrem Ende.

Zwei Einstellungen unter **Administration › Einstellungen** von localSIEM wirken sich ebenfalls auf dieses Modul aus: das **Korrelationsfenster** (5 Sekunden: wie lange auf die drei Einträge einer Anfrage gewartet wird) und der **Schweregrad unterhalb des Blockierungsschwellenwerts** (`low`). Eine Anfrage, die ModSecurity markiert hat, wartet außerdem bis zu 2 Minuten auf ihren Audit-Eintrag, den ModSecurity schreibt, wenn die Anfrage endet: So wird eine langsame Anfrage nicht in zwei Ereignisse aufgeteilt.

<a id="soc"></a>
## 6. Was das Apache-Modul an das SOC sendet

Für jede Anfrage führt das Modul die Access-Zeile, die Error-Zeilen und den Audit-Eintrag mit derselben `UNIQUE_ID` zusammen. Die Access-Logs, die Apache standardmäßig schreibt (`combined`, `vhost_combined`, `common`), haben keine `UNIQUE_ID`: Dann wird jede Access-Zeile mit dem Audit-Eintrag und den Error-Zeilen ihrer eigenen Anfrage anhand von Client-IP, Methode, URI, Status und Uhrzeit (±2 Sekunden) zusammengeführt, auch wenn sich dieselbe Anfrage in derselben Sekunde wiederholt, und das Ereignis wird als «schwache Korrelation» markiert. Der vhost stammt aus `%v` oder, falls das Format ihn nicht enthält, aus dem Host-Header und dem Port des Audit-Eintrags, ausgewählt auf dieselbe Weise, wie Apache ihn auswählt; die Uhrzeit übernimmt die Mikrosekunden des Audit-Eintrags. Dann entscheidet es, ob bereits etwas dagegen unternommen wurde («ergriffene Aktion»), wobei es zuerst das Audit-Log liest (`Action: Intercepted (phase N)`) und dann das error.log (`Access denied with code NNN (phase N)`). Ein 403 ohne jede Spur von ModSecurity wird nicht als Blockierung gewertet: Es wird als zweifelhaft markiert.

| Situation | Geht an das SOC? |
|---|---|
| Von ModSecurity in den Phasen 1-2 blockiert (die Anwendung hat die Anfrage nie erhalten) | **Nein.** Sie bleibt durchsuchbar in localSIEM (`action:blocked`) und wird im Kontext des nächsten Alarms dieser IP mitgezählt. |
| In den Phasen 3-4 blockiert (die Anwendung hatte sie bereits ausgeführt) | Ja |
| Regeltreffer mit der Engine in `DetectionOnly` | Ja |
| Regeltreffer unterhalb des Blockierungsschwellenwerts | Ja |
| Signale der Regeln aus Abschnitt 9 | Ja |

Schweregrad der Alarme, die durch Treffer von ModSecurity ausgelöst werden (Datei `severity.yaml` des Moduls):

| Situation | Schweregrad |
|---|---|
| Nicht blockierte Treffer, Antwort 3xx, 4xx oder 5xx | Mittel |
| Nicht blockierte Treffer, Antwort 2xx | Hoch |
| In den Phasen 3-4 blockiert | Hoch |
| Anzeichen eines Erfolgs: Eine ausgehende Regel (950-955) hat angeschlagen und nichts wurde blockiert, oder auf die Anfrage folgte ein Datenbankfehler | Kritisch |
| Unterhalb des Blockierungsschwellenwerts (oft ein Fehlalarm der Anwendung selbst) | Niedrig (der Schweregrad unterhalb des Blockierungsschwellenwerts unter Administration › Einstellungen) |

Jeder Alarm hat einen festen Namen (zum Beispiel «Apache/ModSecurity: SQL injection not blocked (CRS 942)»), eine Beschreibung, die mit der Abfrage endet, die in die Suche von localSIEM einzufügen ist (zum Beispiel `ip:203.0.113.7 category:sqli`), und Details: vhost, Client-IP, Methode, URI (maskiert), Antwort, User-Agent und die Daten von ModSecurity (Engine, Aktion, Phase, Anomalie-Score, Schwellenwert, Regeln und übereinstimmende Daten). Beim Versand enthält der Alarm außerdem den Kontext der IP: Anfragen und blockierte Anfragen der letzten Stunde, die Regeln, die sie blockiert haben, und den Zeitpunkt, zu dem sie zum ersten Mal gesehen wurde.

Passwörter, Cookies, `Authorization`-Header und Token werden maskiert, bevor etwas gespeichert wird, auch innerhalb der Anfragekörper, und Anfragekörper gelangen nie zum SOC. Der Antwortkörper (Teil E) und der vollständige Text der ausgeführten Regeln (Teil K) des Audit-Logs werden nie aufbewahrt.

<a id="doctor"></a>
## 7. Voraussetzungen von Apache und ModSecurity: die Diagnose

Die Diagnose des Moduls apache2 liest die Apache-Konfiguration (ohne sie zu ändern) und prüft jede Voraussetzung. Sie wird ausgeführt, wenn der Collector startet, nach jeder Änderung der Einstellungen, bei jeder Erkennung, mit **Erneut erkennen und Diagnose ausführen** und mit `manage.py doctor` (Abschnitt 17), jedoch nur, solange das Modul aktiviert ist: Solange es deaktiviert ist, weil Apache oder ModSecurity fehlt, zeigt die Seite des Moduls stattdessen diese Voraussetzungen (Abschnitt 4). Status: OK, Warnung (funktioniert mit Einschränkungen), Fehler (muss behoben werden) und Info (nur in bestimmten Situationen relevant).

| Prüfung | In Ordnung, wenn | Andernfalls |
|---|---|---|
| Apache-Konfiguration | `apache2.conf` oder `httpd.conf` (oder die konfigurierte Datei) wird gefunden und gelesen | Fehler: Fügen Sie die Quellen manuell hinzu (Abschnitt 5). Teile, die nicht gelesen werden können, werden als Warnungen aufgeführt. |
| ModSecurity | `mod_security2` (ModSecurity 2) ist geladen | Fehler. Debian: `apt-get install libapache2-mod-security2 modsecurity-crs && a2enmod security2`. Alpine hat kein Paket: Kompilieren Sie mod_security2 2.9 aus dem Quellcode. ModSecurity 3 (libmodsecurity) wird nicht unterstützt. |
| OWASP CRS | Die CRS-Dateien sind eingebunden (die Diagnose zeigt, wie viele, und den Anomalie-Schwellenwert) | Fehler: `apt-get install modsecurity-crs`, oder binden Sie `crs-setup.conf` und `rules/*.conf` nach ModSecurity ein |
| SecRuleEngine | `On` (Anfragen über dem Schwellenwert werden in Phase 2 blockiert und bleiben in localSIEM) oder `DetectionOnly` (nichts wird blockiert: Jeder Treffer geht an das SOC) | Fehler bei `Off`; Warnung, wenn es außer in einigen vhosts `Off` ist, wenn es fehlt (ModSecurity verwendet dann standardmäßig `Off`) oder wenn einige vhosts es auf `Off` setzen |
| mod_unique_id | Geladen: ModSecurity funktioniert, und die drei Quellen einer Anfrage werden über `UNIQUE_ID` zusammengeführt | Fehler, wenn ModSecurity geladen ist: ModSecurity 2 prüft ohne es nichts (Alpine lädt es nicht); andernfalls Warnung (schwache Korrelation). Debian: `a2enmod unique_id`; Alpine: `LoadModule unique_id_module modules/mod_unique_id.so` |
| Format des Access-Logs | Die Access-Logs enthalten Client-IP, Uhrzeit, Anfragezeile und Status, wie die Formate, die Apache standardmäßig schreibt (OK, «Access logs in the format Apache writes»): Jede Zeile wird mit den Einträgen von ModSecurity zu ihrer Anfrage anhand von Client-IP, Methode, URI, Status und Uhrzeit zusammengeführt. Mit Millisekunden, vhost und `UNIQUE_ID` im Format (zum Beispiel `localsiem_combined`, auf den Servern, die es bereits schreiben) werden sie über `UNIQUE_ID` zusammengeführt (OK, «Access log with milliseconds, vhost, duration and UNIQUE_ID») | Info, ohne Behebung, wenn einem Access-Log eines der vier fehlt: localSIEM liest es so, wie es ist, kann seine Zeilen aber nicht mit den Einträgen von ModSecurity zusammenführen (diese Anfragen sind im Audit-Log zu sehen); Info, wenn kein Access-Log gelesen wird (die Anfragen sind im Error-Log und im Audit-Log zu sehen). Das Format der Logs ist Sache des Kunden (Abschnitt 8) |
| mod_remoteip | Mit `RemoteIPHeader` geladen | Info, ohne Behebung: Steht die Website hinter einem Proxy oder einem Load Balancer, enthalten die Logs die IP des Proxys, ebenso die Alarme und die Regeln nach IP |
| Audit-Log | `SecAuditEngine RelevantOnly` (oder `On`) mit einem `SecAuditLog` | Warnung, wenn es deaktiviert ist: localSIEM entscheidet nur anhand von error.log, und die Detailansicht der Anfrage enthält keine Header und keine Regelliste. Ist es aktiviert, beschreiben seine Hinweise es nur: paralleler Typ (eine Datei pro Transaktion; ModSecurity erstellt sie meist mit Modus 600, und localSIEM liest sie, wenn `localsiem` es kann), natives Format (wird so gelesen, wie es ist), Teil E protokolliert (geht nie an das SOC), Teil H fehlt (die ergriffene Aktion kann nicht aus dem Audit-Log gelesen werden; der einzige Hinweis, der die Prüfung zu einer Warnung macht). Keine Behebung: Das Audit-Log konfiguriert der Kunde (Abschnitt 8) |
| Maskierung an der Quelle | Es gibt eine `sanitise`-Aktion | Info, ohne Behebung («The audit log on disk is not masked»): Die von ModSecurity geschriebene Datei kann Passwörter und Cookies enthalten; localSIEM maskiert sie vor dem Speichern, und sie gehen nie an das SOC |
| Berechtigungen | `localsiem` kann jede Quelle lesen | Fehler. Debian: `usermod -aG adm localsiem`; Alpine: die angezeigten `setfacl`-Befehle. Eine Quelle, die noch nicht existiert, ist nur eine Info. |
| Logs über Pipe | — | Warnung: `\|/usr/bin/rotatelogs ...` und syslog können nicht gelesen werden; schreiben Sie das Log zusätzlich in eine Datei, oder fügen Sie die Quelle manuell hinzu |
| Access-Log ohne Daten | — | Warnung: Ein `CustomLog` verwendet ein Format, das kein `LogFormat` definiert (oder ein `LogFormat` ohne jede `%`-Direktive), daher schreibt Apache in jede Zeile denselben Text, ohne Client-IP, Uhrzeit oder Anfrage. localSIEM liest dieses Log nicht und sieht die Anfragen seines vhosts in dessen Error-Log und im Audit-Log von ModSecurity. Das Format der Logs des Servers wird nie geändert. |
| Engine als Off gesehen | — | Fehler: Die Audit-Einträge melden die Engine als deaktiviert |
| ModSecurity-Version | — | Info: die aus dem Audit-Log gelesene Version |

Wenn die Konfiguration ein `GlobalLog` enthält, dessen Format `%v` hat (es schreibt alle vhosts), werden die anderen Access-Logs nicht gelesen: Sie würden nur dessen Zeilen wiederholen. Die Diagnose schlägt nie vor, das Format der Logs oder die Einstellungen des Audit-Logs zu ändern (Abschnitt 8).

<a id="client-logs"></a>
## 8. Die Logs des Kunden werden nie angetastet

Das Modul apache2 **liest** die Logs von Apache und ModSecurity nur: Es schreibt nie hinein, rotiert, kürzt, verschiebt oder löscht sie nie und ändert nie ihr Format oder die Konfiguration von Apache oder ModSecurity, die sie schreibt. Schreibt ein Server seine Logs in einem eigenen Format (zum Beispiel mit einem eigenen `LogFormat` oder mit der Client-IP, die `mod_remoteip` liefert), passt sich das Modul daran an: Es liest jedes Access-Log mit dem Format, das sein `CustomLog` verwendet. Die Diagnose (Abschnitt 7) beschreibt nur die Logs und was localSIEM aus ihnen lesen kann oder nicht, ohne vorzuschlagen, sie zu ändern; eine Behebung nennt sie nur für das, was kein Log ist: ModSecurity, das CRS, `SecRuleEngine`, `mod_unique_id` und den Lesezugriff des Benutzers `localsiem`. Das Einzige, was für dieses Modul als root ausgeführt wird, ist dieser Lesezugriff (`manage.py setup-modules`, Abschnitt 2).

Die Versionen 1.2.0 und älter des Moduls hatten die Einrichtungsoption `--configure-apache`, die in Version 1.3.0 entfernt wurde. Server, auf denen sie angewendet wurde, behalten die Datei, die sie geschrieben hat, `/etc/apache2/conf-available/localsiem.conf` (Debian) oder `/etc/apache2/conf.d/localsiem.conf` (Alpine), mit dem Format `localsiem_combined` und seinem `GlobalLog` (`localsiem_access.log`), Einstellungen des Audit-Logs und einer `SecAction`, die sensible Werte maskiert. Solange diese Datei vorhanden ist, liest das Modul diese Logs wie alle anderen. Um das rückgängig zu machen, löschen Sie diese Datei (Debian: `a2disconf localsiem`) und laden Sie Apache neu. Unter Alpine hat diese Datei außerdem `mod_unique_id` und `mod_logio` geladen: Laden Sie `mod_unique_id` an anderer Stelle in der Apache-Konfiguration, bevor Sie sie löschen, denn ModSecurity 2 prüft ohne es nichts (Abschnitt 7). Das Installationsprogramm von localSIEM löscht diese Datei mit `--uninstall` oder `--reinstall` (laden Sie unter Alpine zuerst `mod_unique_id` an anderer Stelle) und lässt die Logs (`localsiem_access.log`, `modsec_audit.log`) dort, wo sie sind.

<a id="rules"></a>
## 9. Regeln des Apache-Moduls

Die Regeln werden bei jedem Ereignis ausgewertet. Ein Signal einer Regel geht immer an das SOC. Auf der Seite des Moduls kann jede Regel deaktiviert und ihr Schweregrad, ihr Schwellenwert (1 bis 100000) und ihr Zeitfenster (1 bis 86400 Sekunden) geändert werden; Schwellenwert und Zeitfenster gelten nur für Schwellenwert- und Sequenzregeln. Ihre Ereignisse lassen sich mit `rule:localsiem:<id>` finden.

| Regel | Art | Schweregrad | Wann | Schwellenwert / Zeitfenster |
|---|---|---|---|---|
| `apache-bruteforce` «Brute-Force-Angriff auf eine Anmeldeseite» | Schwellenwert | Mittel | Nicht blockierte POST-Anfragen von einer IP an eine Anmeldeseite eines vhosts (`/wp-login.php`, `/xmlrpc.php`, `/administrator/index.php`, `/user/login`, `/login`, `/admin/login`, `/login.php`, `/admin.php`, `/signin`, `/auth/login`, `/phpmyadmin/index.php`) | 20 in 300 s |
| `apache-login-after-bruteforce` «erfolgreiche Anmeldung nach einem Brute-Force-Angriff» | Sequenz | Hoch | Mindestens 10 fehlgeschlagene Anmeldungen (POST mit Antwort 200, 401 oder 403) an einer Anmeldeseite, danach eine mit Antwort 302 oder 303 (WordPress antwortet auf eine fehlgeschlagene Anmeldung mit 200 und auf eine erfolgreiche mit 302) | 10, innerhalb von 1800 s |
| `apache-enumeration` «Enumeration (Häufung von 404-Antworten)» | Schwellenwert | Mittel | Nicht blockierte 404-Antworten an eine IP von einem vhost | 30 in 60 s |
| `apache-sensitive-file` «ausgelieferte sensible Datei» | Treffer | Hoch | Eine 2xx-Antwort auf eine Datei, die nicht öffentlich sein sollte: `.env`, `.git/`, `.svn/`, `.hg/`, `.htaccess`, `.htpasswd`, Dumps und Backups (`.sql`, `.sql.gz`, `.bak`, `.old`, `.orig`, `.swp`, `.save`, `.backup`, `.dump`, Namen, die auf `~` enden), `phpinfo`, `info.php`, `server-status`, `server-info`, Kopien von `wp-config.php` und `config.php`/`config.inc`, `.DS_Store`, private SSH-Schlüssel, `composer.json`/`composer.lock`, `.aws/`, `backup.zip`/`.tar`/`.tar.gz`/`.tgz`/`.rar` | — |
| `apache-webshell` «mögliche Web-Shell (POST an eine neue PHP-Datei)» | Treffer | Kritisch | Ein mit 2xx beantworteter POST an eine PHP-Datei, die am letzten Tag in ihrem DocumentRoot erstellt oder geändert oder in der letzten Stunde zum ersten Mal gesehen wurde (nach den Lerntagen) | — |
| `apache-db-error-after-attack` «Datenbankfehler nach einer verdächtigen Anfrage» | Sequenz | Kritisch | Eine Anfrage, die CRS-Regeln ausgelöst hat, und von derselben IP ein Datenbankfehler (SQL oder PDO) im error.log | 1, innerhalb von 30 s |

<a id="health"></a>
## 10. Zustandswarnungen des Apache-Moduls

Neben den Zustandswarnungen von localSIEM selbst prüft das Modul höchstens alle 5 Minuten Folgendes und sendet es an das SOC:

| Warnung | Schweregrad | Was zu tun ist |
|---|---|---|
| ModSecurity ist nicht mehr geladen | Hoch | Es war geladen und ist es nicht mehr: Anfragen werden nicht geprüft. Wenn das niemand absichtlich getan hat, hat möglicherweise jemand den Schutz abgeschaltet. |
| Engine von ModSecurity auf Off gesetzt | Hoch | `SecRuleEngine` wurde auf `Off` geändert, oder das Audit-Log meldet die Engine als deaktiviert. Prüfen Sie die Apache-Konfiguration und ihre jüngsten Änderungen. |
| Echte Client-IP fehlt (mod_remoteip) | Mittel | In der letzten Stunde kamen mindestens 90 % von mindestens 100 Anfragen von einer einzigen privaten oder lokalen Adresse: Die Website steht wahrscheinlich hinter einem Proxy, und Apache protokolliert die IP des Proxys, sodass die Regeln nach IP für diese Anfragen nicht funktionieren. Wird höchstens einmal pro Tag gesendet. |

Was bereits gemeldet wurde, bleibt über Neustarts hinweg gespeichert, sodass eine Aktualisierung es nicht erneut sendet. Wegen dieser Warnungen wird ein aktiviertes Modul nie von selbst deaktiviert, wenn Apache oder ModSecurity verschwindet.

<a id="privesc"></a>
## 11. Das Modul zur Rechteausweitung

Das Modul **privesc** («Rechteausweitung») überwacht, was Personen und Dienste auf dem Server ausführen, und meldet die Schritte einer Rechteausweitung zu root: Aufklärung, die Suche nach setuid-Programmen, Enumerationswerkzeuge wie linpeas, bekannte Exploits, Reverse Shells, ohne sudo oder su erlangte root-Rechte, zurückgelassene Hintertüren und die Versuche, die Überwachung blind zu machen. Außerdem überprüft es die Angriffsfläche des Servers: setuid-Programme, Capabilities und für andere beschreibbare sensible Dateien (Abschnitt 16).

Es liest nur, was der Server bereits hat: Es installiert nie etwas, lädt nie Audit-Regeln und ändert nie die Konfiguration von auditd, snoopy oder den Shells. Es liest bis zu zwei Quellen:

| Quelle | Was es sieht | Wo es funktioniert |
|---|---|---|
| **auditd** (`/var/log/audit/audit.log`) | sudo, su, pkexec und SSH-Anmeldungen (PAM) sowie alles, was die Audit-Regeln des Servers aufzeichnen (siehe unten) | Physische Server und virtuelle Maschinen, solange auditd läuft. **Nicht innerhalb eines Containers** (LXC, podman, systemd-nspawn, Docker): Das Audit des Kernels ist nicht in Namespaces aufgeteilt, daher läuft auditd nur auf dem Host. |
| **syslog** (`/var/log/auth.log`, `/var/log/secure` oder `/var/log/messages`) | sudo, su, pkexec, doas, SSH-Anmeldungen und, wenn **snoopy** installiert ist, jedes ausgeführte Programm | Überall, auch in Containern. Wird gelesen, wenn auditd nicht läuft, sein Log nicht gelesen werden kann oder snoopy installiert ist (Einstellung **syslog lesen**). Es braucht einen syslog-Daemon, der eine Datei schreibt: Das Journal von systemd allein wird nicht gelesen. |

Was auditd zeigt, hängt von den Audit-Regeln ab, die der Server lädt und über die sein Administrator entscheidet; das Modul verwendet sie so, wie sie sind, unabhängig von ihren Schlüsseln, und ordnet jeden Eintrag nach seiner Art, seinem Systemaufruf und seinen Dateien ein:

| Das Modul sieht | Wenn die Audit-Regeln des Servers Folgendes aufzeichnen |
|---|---|
| Jedes ausgeführte Programm (auch aus Skripten, Web-Shells und Exploits), setuid-Programme, von ihnen geerbte root-Rechte, erlangte Capabilities | `execve` |
| Änderungen an Konten, sudoers, PAM, preload, SSH, cron, Diensten und `/etc/audit` | Überwachungen (`-w ... -p wa`) dieser Dateien oder der Systemaufrufe, die sie ändern |
| Gesetzte setuid- oder setgid-Bits | `chmod`, `fchmod`, `fchmodat` |
| Geladene oder entfernte Kernelmodule | `init_module`, `finit_module`, `delete_module` |
| Mit ptrace angehängte Prozesse | `ptrace` |
| Einer Person verweigerte Dateien | `open`, `openat`, `execve`..., die mit `EACCES` oder `EPERM` fehlschlagen |
| Entfernte Audit-Regeln, abgeschaltetes Audit, gestopptes auditd, abstürzende Programme | Immer (der Kernel und auditd melden sie) |

Auf einem physischen Server oder einer virtuellen Maschine ist auditd die Quelle, die ein Benutzer nicht umgehen kann; die Diagnose gibt an, was die Audit-Regeln des Servers bisher aufgezeichnet haben (Abschnitt 14). In einem Container ist snoopy die einzige Möglichkeit, jedes ausgeführte Programm zu sehen.

Die Builtins der Shell (`pwd`, `cd`, `unset HISTFILE`, `history -c`) führen nie ein Programm aus, daher sieht sie keine Quelle, außer innerhalb einer Befehlszeile wie `bash -c '...'`. Ein einzelnes `whoami` ist nie ein Alarm: Das Modul zählt die **unterschiedlichen** Aufklärungsbefehle jeder Sitzung innerhalb eines Zeitfensters, und nur eine Häufung davon ist einer (Abschnitt 13).

Was jedes Ereignis des Moduls enthält und wie man danach sucht:

| Spalte | Enthält | Beispielsuche |
|---|---|---|
| `vhost` | Die Person: der Anmeldebenutzer (er bleibt über sudo und su hinweg derselbe) | `module:privesc vhost:alice` |
| `method` | Art des Ereignisses: `exec` (ausgeführtes Programm, auditd oder snoopy), `sudo`, `su`, `pkexec`, `doas`, `login`, `pam`, `file` (geänderte sensible Datei), `chmod` (setuid-Bit), `kmod`, `ptrace`, `denied` (verweigerte Datei), `audit_config`, `auditd`, `crash`, `syscall` (ein anderer Systemaufruf, den die Audit-Regeln des Servers aufzeichnen) | `module:privesc method:sudo` |
| `uri` | Die Befehlszeile (Passwörter maskiert) | `module:privesc uri:*linpeas*` |
| `path` | Das ausgeführte Programm oder die geänderte Datei | `module:privesc path:/tmp/*` |
| `ip` | Die SSH-Adresse der Sitzung, sofern bekannt | `module:privesc ip:203.0.113.7` |
| `score` | Unterschiedliche Aufklärungsbefehle der Sitzung im Zeitfenster | `module:privesc score:>=8` |
| `action` | `blocked`, wenn das System selbst es verhindert hat: ein Programm, das nicht ausgeführt werden konnte, verweigertes sudo oder su, eine verweigerte Datei | `module:privesc action:blocked` |
| `source` | `audit` oder `syslog` | `module:privesc source:syslog` |

Regeln zu Versuchen (wiederholte sudo-Fehlschläge, viele verweigerte Dateien) zählen die blockierten Ereignisse trotzdem; die anderen berücksichtigen nur, was tatsächlich ausgeführt wurde.

Die Seite des Moduls, `/admin/dashboard/modules/installed/privesc/`, hat dieselben Teile wie die Seite des Apache-Moduls (Abschnitt 4): Kopfbereich (mit **Erneut erkennen und Diagnose ausführen**, **Neu konfigurieren** und **Deinstallieren**), Einstellungen (Abschnitt 12), Quellen (`audit`, `syslog`; sowie die nicht gelesenen mit dem Grund), Diagnose (Abschnitt 14) und Regeln (Abschnitt 13).

<a id="privesc-settings"></a>
## 12. Einstellungen des Moduls zur Rechteausweitung

| Einstellung | Standard | Funktion |
|---|---|---|
| **Audit-Log** | leer | Leer: `log_file` aus `/etc/audit/auditd.conf` oder `/var/log/audit/audit.log`. |
| **syslog lesen** | Automatisch | Automatisch: nur wenn auditd nicht läuft, sein Log nicht gelesen werden kann oder snoopy installiert ist. Immer oder Nie. |
| **syslog-Datei** | leer | Leer: `/var/log/auth.log`, `/var/log/secure` oder `/var/log/messages`, die erste, die existiert. |
| **Ignorierte Benutzer** | leer | Durch Kommas getrennt. Ihre Befehle werden gespeichert und sind durchsuchbar, lösen aber nie einen Alarm aus: Automatisierungskonten (ansible, Backups). Der Benutzer `localsiem` wird immer ignoriert. |
| **Administratorgruppen** | `sudo,wheel,admin` | Durch Kommas getrennt. Ihre Mitglieder (und root) erhalten den höheren Aufklärungsschwellenwert und dürfen ihre sudo-Rechte ohne Alarm auflisten. |
| **Aufklärungsfenster (Sekunden)** | 120 | Zeitfenster, in dem die unterschiedlichen Aufklärungsbefehle einer Sitzung gezählt werden (10 bis 3600). |
| **Aufklärungsschwellenwert** | 8 | Anzahl unterschiedlicher Aufklärungsbefehle im Zeitfenster, die eine Häufung bilden, für Benutzer und Dienstkonten (2 bis 500). |
| **Aufklärungsschwellenwert für Administratoren** | 20 | Dasselbe für root und die Administratoren, die diese Befehle im Rahmen ihrer Arbeit ausführen (2 bis 500). |
| **Schwellenwert für automatisierte Enumeration** | 40 | Anzahl unterschiedlicher Aufklärungsbefehle im Zeitfenster, die nur ein Skript ausführt (ähnlich wie linpeas), für alle (5 bis 1000). |
| **Lerntage der Dienstkonten** | 3 | In den ersten Tagen nach dem ersten Start des Moduls werden die Programme, die jedes Dienstkonto ausführt (`www-data` führt `sh -c sendmail` aus), ohne Alarme gelernt (0 bis 365). |
| **Stunden zwischen Scans nach setuid-Programmen** | 24 | Wie oft nach setuid- und setgid-Programmen sowie Datei-Capabilities gesucht wird (Abschnitt 16). 0: nie (0 bis 168). |
| **Gescannte Ordner** | `/usr,/bin,/sbin,/lib,/lib64,/opt,/home,/srv,/tmp,/var/tmp,/dev/shm,/var/www,/etc` | Durch Kommas getrennt; jeder Ordner wird durchlaufen, ohne sein Dateisystem zu verlassen. Die Ordner von Containern sowie `/proc` und `/sys` werden immer übersprungen. |
| **Erkennungsintervall (Sekunden)** | 300 | Wie oft nach dem Audit-Log, syslog und dem Zustand von auditd gesucht wird (60 bis 86400). Das kürzeste Intervall der aktivierten Module gilt für alle. |

Was als Aufklärung zählt: `whoami`, `id`, `groups`, `uname`, `hostname`, `w`, `who`, `last`, `ps`, `ss`, `netstat`, `ip`, `ifconfig`, `env`, `pwd`, `history`, `getcap`, `lsmod`, `dmesg`, `mount` und Ähnliches; `sudo -l`, `crontab -l`, `systemctl list-*`, die Paketlisten; `which`, `locate`, `command -v`; `docker ps` und Ähnliches; jedes unterschiedliche `find`; das Lesen von `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`, `/etc/*-release`, `/proc/version`, `/root/...`, Verläufen, SSH-Schlüsseln und `.env`-Dateien; das Auflisten von `/root`, `/home`, `/opt`, `/tmp`, den cron-Ordnern...; `grep -r password`; und `<program> --version`. Jeder unterschiedliche Befehl einer Sitzung zählt innerhalb des Zeitfensters einmal.

<a id="privesc-rules"></a>
## 13. Was das Modul zur Rechteausweitung an das SOC sendet: seine Regeln

Jeder Alarm des Moduls stammt aus einer seiner Regeln (sie funktionieren gleich, unabhängig davon, welche Quelle den Befehl gesehen hat), außer denen aus Abschnitt 16. Wie bei Apache kann jede Regel auf der Seite des Moduls deaktiviert und ihr Schweregrad, ihr Schwellenwert und ihr Zeitfenster geändert werden; ihre Ereignisse lassen sich mit `rule:localsiem:<id>` finden. Für die Benutzer unter **Ignorierte Benutzer** wird keine ausgelöst. Die mit «auditd» markierten Regeln benötigen die Audit-Einträge aus Abschnitt 11.

| Regel | Art | Schweregrad | Wann | Schwellenwert / Zeitfenster |
|---|---|---|---|---|
| `privesc-recon-burst` «Häufung von Aufklärungsbefehlen» | Treffer | Mittel | Die Sitzung hat den Aufklärungsschwellenwert erreicht (Abschnitt 12) | — |
| `privesc-enumeration` «automatisierte Enumeration (ähnlich wie linpeas)» | Treffer | Hoch | Die Sitzung hat den Schwellenwert für automatisierte Enumeration erreicht, auch mit einem umbenannten Skript | — |
| `privesc-suid-hunt` «Suche nach setuid-Programmen oder Capabilities» | Treffer | Hoch | `find ... -perm -4000` (oder `-u=s`, `/6000`, `-2000`...), `getcap -r`, `find -writable` | — |
| `privesc-sudo-list` «von einem Nicht-Administrator aufgelistete sudo-Rechte» | Treffer | Mittel | `sudo -l` durch einen Benutzer oder ein Dienstkonto, der bzw. das kein Administrator ist | — |
| `privesc-known-tool` «bekanntes Enumerationswerkzeug» | Treffer | Hoch | linpeas, LinEnum, lse.sh, linux-exploit-suggester, les.sh, pspy, unix-privesc-check, linuxprivchecker, traitor, BeRoot, GTFONow, PEASS, deepce, CDK, sudo_killer, suid3num, mimipenguin, LaZagne, pwncat, searchsploit | — |
| `privesc-exploit` «bekannter Exploit» | Treffer | Kritisch | PwnKit, DirtyPipe, Dirty COW, Baron Samedit (`sudoedit -s '\'`), Looney Tunables (`GLIBC_TUNABLES`), GameOver(lay), nf_tables (CVE-2024-1086), CVE-2023-22809 (`EDITOR=... -- /...`), polkit CVE-2021-3560 (`dbus-send ... CreateUser`), `LD_PRELOAD` mit sudo, ein nach einer CVE benanntes Skript, Programme mit den Namen `exploit`, `getroot`, `rootme` | — |
| `privesc-pwnkit` «PwnKit (pkexec ohne Argumente ausgeführt)» | Treffer | Kritisch | `pkexec` mit null Argumenten ausgeführt (auditd) | — |
| `privesc-pwnkit-log` «pkexec meldet einen PwnKit-Versuch» | Treffer | Kritisch | pkexec protokolliert `GCONV_PATH`, «suspicious content» oder «was not found the /etc/shells» (syslog) | — |
| `privesc-suid-escape` «von einem setuid-Programm geerbte root-Rechte» | Treffer | Kritisch | Ein Programm, das nicht setuid ist, läuft mit der effektiven UID von root und der realen UID eines Benutzers: Ein setuid-Programm wurde missbraucht (GTFOBins). Mount-Hilfsprogramme, D-Bus, polkit und X sind ausgenommen. | — |
| `privesc-root-without-door` «root ohne sudo, su oder pkexec» | Treffer | Kritisch | Eine Sitzung einer Person, deren Beginn gesehen wurde, führt Programme als root aus, ohne über sudo, su, pkexec oder doas gegangen zu sein (Kernel-Exploits) (auditd) | — |
| `privesc-root-shell-interpreter` «von einem Interpreter gestartete root-Shell» | Treffer | Hoch | Eine Shell läuft als root, gestartet von python, perl, ruby, awk, gdb..., das ein gewöhnlicher Benutzer ausgeführt hat (als dessen Kind oder im selben Prozess) (auditd) | — |
| `privesc-file-capabilities` «Programm hat root-Capabilities aus seiner Datei erhalten» | Treffer | Hoch | Ein Benutzer hat ein Programm ausgeführt, dessen Datei ihm `cap_setuid`, `cap_dac_override`, `cap_sys_admin`... verleiht (auditd) | — |
| `privesc-tmp-exec` «aus einem für alle beschreibbaren Ordner ausgeführtes Programm» | Treffer | Hoch | Ein Programm in `/tmp`, `/var/tmp`, `/dev/shm` oder `/run/user/<uid>` | — |
| `privesc-compile-tmp` «in einem temporären Ordner kompiliertes Programm» | Treffer | Hoch | `gcc`, `cc`, `clang`, `make`... in einem temporären Ordner oder auf Dateien darin | — |
| `privesc-download-shell` «von einer Shell ausgeführtes heruntergeladenes Skript» | Treffer | Hoch | `curl ... \| sh`, `bash -c "$(curl ...)"`, `bash <(wget ...)` oder ein Downloader, gefolgt von einer Shell in derselben Pipeline | — |
| `privesc-reverse-shell` «Reverse Shell» | Treffer | Hoch | `/dev/tcp/`, `nc -e`, `ncat --exec`, `socat exec:`, `mkfifo ... \| nc`, Sockets von python/perl/php/ruby/lua/node, `openssl s_client ... \| sh`, `awk /inet/tcp` | — |
| `privesc-tty-upgrade` «Shell zu einem vollständigen Terminal aufgewertet» | Treffer | Hoch | `pty.spawn`, `script ... /dev/null`, `stty raw -echo`, `socat ... pty`, `expect ... spawn sh` | — |
| `privesc-service-recon` «Dienstkonto hat Aufklärungsbefehle ausgeführt» | Treffer | Hoch | `www-data`, `mysql` und andere Dienstkonten führen `whoami`, `id`, `uname`... aus (eine Web-Shell) | — |
| `privesc-service-new-program` «Dienstkonto hat ein Programm ausgeführt, das es nie zuvor ausgeführt hat» | Treffer | Hoch | Nach den Lerntagen führt ein Dienstkonto eine Shell, einen Interpreter oder ein Werkzeug aus, das es nie ausgeführt hat (`sh -c id`, wo es nur `sh -c sendmail` ausgeführt hat) | — |
| `privesc-container-escape` «Container verwendet, um als root auf den Host zuzugreifen» | Treffer | Hoch | Jemand, der nicht root ist, führt `docker run -v /:/...`, `--privileged`, `--pid=host`, `nsenter -t 1`, `lxc config set ... security.privileged true`, `lxc config device add ... source=/`, `debugfs /dev/...` aus | — |
| `privesc-auth-failures` «wiederholte sudo- oder su-Fehlschläge» | Schwellenwert | Mittel | Fehlgeschlagenes sudo, su, pkexec oder doas eines Benutzers | 3 in 600 s |
| `privesc-sensitive-file` «Konto-, sudo-, PAM- oder preload-Datei geändert» | Treffer | Hoch | `/etc/passwd`, `shadow`, `group`, `gshadow`, `sudoers`, `sudoers.d`, `doas.conf`, `doas.d`, `ld.so.preload`, `ld.so.conf`, `ld.so.conf.d`, `pam.d`, `security` geändert von einem Programm, das kein Paket- oder Kontowerkzeug ist (auditd) | — |
| `privesc-persistence-file` «SSH-, cron- oder Dienstdatei geändert» | Treffer | Mittel | `/root/.ssh`, `sshd_config`, `sshd_config.d`, cron-Dateien, `/etc/systemd/system`, `/etc/init.d`, `rc.local`, `/etc/local.d` geändert (auditd) | — |
| `privesc-monitoring-changed` «Konfiguration von auditd geändert» | Treffer | Mittel | `/etc/audit` geändert von einem Programm, das kein Paketwerkzeug ist (auditd) | — |
| `privesc-suid-set` «setuid- oder setgid-Bit auf einer Datei gesetzt» | Treffer | Hoch | `chmod u+s`/`g+s` auf einer Datei (nicht einem Ordner) außerhalb des Paketmanagers (auditd) | — |
| `privesc-setcap` «Datei-Capabilities gesetzt» | Treffer | Hoch | `setcap ... cap_...` | — |
| `privesc-kernel-module` «Kernelmodul aus einer Sitzung geladen» | Treffer | Hoch | Ein Modul, das aus der Sitzung einer Person geladen oder entfernt wurde (auditd) | — |
| `privesc-ptrace` «Prozess mit ptrace angehängt» | Treffer | Mittel | `PTRACE_ATTACH` oder `PTRACE_SEIZE` (auditd) | — |
| `privesc-denied-burst` «viele verweigerte Dateien (Enumeration)» | Schwellenwert | Mittel | Einem Benutzer verweigerte Dateien (`EACCES`, `EPERM`) (auditd) | 30 in 60 s |
| `privesc-sensitive-denied` «Versuch, die Passwort-Hashes oder Dateien von root zu lesen» | Treffer | Mittel | `/etc/shadow`, `/etc/gshadow`, `/etc/sudoers`, `/etc/sudoers.d/` oder `/root` einem Benutzer verweigert (auditd) | — |
| `privesc-history-tampering` «Shell-Verlauf gelöscht oder abgeschaltet» | Treffer | Mittel | `ln -s /dev/null ~/.bash_history`, `rm .bash_history`...; `unset HISTFILE`, `HISTFILE=/dev/null`, `HISTSIZE=0`, `history -c`, `set +o history` nur innerhalb einer Befehlszeile (`bash -c`), da Builtins kein Programm ausführen | — |
| `privesc-audit-stop-command` «Befehl zum Abschalten von auditd» | Treffer | Kritisch | `auditctl -e 0`, `auditctl -D`, `auditctl -a never`, `systemctl stop/disable/mask auditd`, `service auditd stop`, `pkill auditd`, Löschen von `/var/log/audit` oder `/etc/audit` | — |
| `privesc-audit-disabled` «Auditing abgeschaltet» | Treffer | Kritisch | Der Kernel meldet `audit_enabled=0` (auditd) | — |
| `privesc-auditd-stopped` «auditd von einem Prozess gestoppt» | Treffer | Hoch | auditd wurde auf Anforderung eines anderen Prozesses als init gestoppt (ein Herunterfahren des Servers wird nicht gemeldet) | — |
| `privesc-crash` «setuid- oder temporäres Programm abgestürzt» | Treffer | Mittel | Ein setuid-Programm oder eines in einem temporären Ordner ist abgestürzt (auditd `ANOM_ABEND`): oft ein fehlgeschlagener Exploit | — |

Jeder Alarm hat einen festen Namen, eine Beschreibung, die mit der Abfrage endet, die in die Suche von localSIEM einzufügen ist, und Details: Benutzer, Kontoart (`root`, `admin`, `user`, `service`), realer und effektiver Benutzer, Befehl, Programm, Ordner, Terminal, Sitzung, Quelle (`auditd`, `snoopy`, `syslog`), Client-IP und, sofern zutreffend, das übergeordnete Programm, der Interpreter, die geänderte Datei und ihre Gruppe, die gezählten Aufklärungsbefehle, die Capabilities, der gesetzte Modus, die ptrace-Anforderung und der Fehler einer verweigerten Datei. Beim Versand enthält der Alarm außerdem den Kontext der Sitzung: ob ihr Beginn gesehen wurde, ob sie über sudo oder su gegangen ist, ihre SSH-Adresse und ihre **letzten 20 Befehle**, sodass der Analyst ohne Suche liest, was zu dem Alarm geführt hat.

Derselbe Befehl kann von mehr als einer Quelle gesehen werden (auditd und snoopy): Die Alarme werden nach Modul, Benutzer, IP, Kategorie und Schweregrad gruppiert, sodass daraus trotzdem ein einziger Alarm wird. Passwörter in Befehlszeilen (`mysql -p...`, `sshpass -p`, `curl -u user:pass`, `PASSWORD=...`, URLs mit einem Passwort) werden maskiert, bevor etwas gespeichert wird, auch in der hexadezimalen Darstellung der Audit-Einträge.

<a id="privesc-doctor"></a>
## 14. Voraussetzungen des Moduls zur Rechteausweitung: die Diagnose

**Voraussetzungen.** Das Modul benötigt eine Quelle, die der Benutzer `localsiem` lesen kann (die Datei existiert und `localsiem` kann sie öffnen): das Log von **auditd** (auditd läuft, außerhalb eines Containers) oder die Datei von **syslog** mit sudo, su, pkexec und doas (`/var/log/auth.log`, `/var/log/secure` oder `/var/log/messages` oder die Einstellung **syslog-Datei**, sofern **syslog lesen** nicht auf Nie steht), in die **snoopy**, falls installiert, außerdem jedes ausgeführte Programm schreibt. Eine davon genügt. Existiert eine Quelle, kann `localsiem` sie aber nicht lesen, gibt die Voraussetzung dies an, mit dem Befehl, der Lesezugriff gewährt (für das Audit-Log der Befehl der Seite Module, `manage.py setup-modules`; für syslog `setfacl -m g:localsiem:r <file>`). Ist keine davon vorhanden, gibt sie an, was zu installieren ist: auditd (Debian: `apt-get install auditd`; Alpine: `apk add audit && rc-update add auditd && rc-service auditd start`), ein syslog-Daemon (Debian: `apt-get install rsyslog`; Alpine: `apk add rsyslog && rc-update add rsyslog && rc-service rsyslog start`) oder snoopy. Bis dahin bleibt das Modul deaktiviert; **Neu konfigurieren** prüft erneut. Es installiert nichts von selbst. Bei einer Erstinstallation gehören die Logs meist root: Führen Sie den Befehl aus, den die Weboberfläche anzeigt, und klicken Sie dann auf **Neu konfigurieren**.

Die Diagnose läuft wie die von Apache (Abschnitt 7). Sie beschreibt nur, was das Modul mit dem, was der Server hat, sieht und was es nicht sehen kann; ihre Behebungen beschränken sich auf die zu installierenden Pakete und den Lesezugriff von `localsiem`. Sie schlägt nie vor, die Audit-Regeln, `auditd.conf` (außer `log_group`, siehe unten), `snoopy.ini`, die Shells oder irgendeine andere Konfiguration zu ändern:

| Prüfung | In Ordnung, wenn | Andernfalls |
|---|---|---|
| auditd | auditd läuft | Warnung, wenn es nicht installiert ist (Debian: `apt-get install auditd`; Alpine: `apk add audit && rc-update add auditd && rc-service auditd start`); Warnung ohne Behebung, wenn es installiert, aber gestoppt ist (ob es läuft, entscheidet der Administrator). Info innerhalb eines Containers: auditd kann dort nicht laufen. |
| Audit-Log | `localsiem` kann es lesen | Fehler, mit dem Befehl der Seite Module; Warnung, wenn auditd läuft und sein Log nicht dort liegt, wo das Modul danach sucht (Einstellung **Audit-Log**) |
| Gruppe des Audit-Logs | Das Audit-Log gehört nicht zur Gruppe `root` | Warnung, wenn doch (`log_group = root` in `auditd.conf`): Jedes Log, das auditd beim Rotieren erstellt, hat Modus 600, ist nur für root lesbar, und localSIEM hört auf zu lesen. Die Behebung ist die Zeile `log_group = adm` für `/etc/audit/auditd.conf` (danach auditd neu starten): Die neuen Logs werden mit Modus 640 erstellt. |
| Einträge der Audit-Regeln | Ausgeführte Programme (`EXECVE`) wurden gelesen | Warnung, wenn auditd schreibt, aber keiner seiner Einträge ein ausgeführtes Programm ist: Die Audit-Regeln des Servers zeichnen `execve` nicht auf, daher werden die Befehle von Skripten, Web-Shells und Exploits über auditd nicht gesehen. Info mit dem, was die Regeln bisher sonst aufgezeichnet haben (Änderungen sensibler Dateien, setuid-Bits, Kernelmodule, ptrace, verweigerte Dateien), und was noch nicht |
| syslog | Die syslog-Datei wird gelesen | Fehler, wenn sie nicht gelesen werden kann (`setfacl -m g:localsiem:r <file>`); Warnung, wenn es weder ein verwendbares Audit-Log noch eine syslog-Datei gibt (Debian: `apt-get install rsyslog`; Alpine: `apk add rsyslog && rc-update add rsyslog && rc-service rsyslog start`) |
| snoopy | Installiert, und seine Zeilen werden gelesen | Warnung ohne auditd: Die Befehle von Skripten und Web-Shells werden nicht gesehen (Debian: `apt-get install snoopy`; Alpine hat kein Paket: Es wird aus dem Quellcode kompiliert). Warnung, wenn es installiert ist, syslog aber nicht gelesen wird. Info, wenn seine Zeilen keine effektive UID enthalten (`message_format` von `snoopy.ini`): Von einem setuid-Programm geerbte root-Rechte werden über snoopy nicht gesehen |
| Was das Modul sieht | — | Info: auditd (und was seine Regeln aufzeichnen), snoopy (jedes ausgeführte Programm) oder, als Warnung, nur sudo, su, pkexec und doas (syslog ohne snoopy: Die meisten Regeln können nicht auslösen); Fehler, wenn es nichts lesen kann. Außerdem erinnert sie daran, dass die Builtins der Shell nie gesehen werden |
| Dateien der Version 1.0.0 | — | Info ohne Behebung, wenn die Dateien gefunden werden, die `--configure-privesc` hinterlassen hat (Abschnitt 15) |
| setuid-Programme und Capabilities | — | Info: der letzte Scan (Abschnitt 16). Warnung ohne Behebung mit den setuid-Programmen, die eine root-Shell liefern (GTFOBins), und mit den Programmen, deren Capabilities praktisch root entsprechen |
| Sensible Dateien | Keine ist für jemand anderen als root beschreibbar | Fehler ohne Behebung für jede einzelne (`/etc/passwd`, `sudoers`, cron, `/etc/profile.d`, die Ordner im `PATH` von root, `docker.sock`...) |
| Privilegierte Gruppen | — | Warnung ohne Behebung mit den Mitgliedern von `docker`, `lxd`, `incus-admin`, `disk` und `libvirt`: Sie sind praktisch root |

<a id="privesc-legacy"></a>
## 15. Server, die von Version 1.0.0 des Moduls zur Rechteausweitung aktualisiert wurden

Version 1.0.0 des Moduls hatte die Einrichtungsoption `--configure-privesc` und einen Bash-Hook; Version 1.1.0 hat beide entfernt, weil ein Modul nie etwas außerhalb von `/opt/localsiem` installiert oder ändert. Server, auf denen sie angewendet wurde, behalten, was sie geschrieben hat, und localSIEM verwendet es weder, noch löscht es es:

- `/etc/audit/rules.d/90-localsiem-privesc.rules`: ihre Audit-Regeln (Schlüssel `lsiem_*`). Solange sie geladen sind, liest das Modul ihre Einträge wie die jeder anderen Regel des Servers.
- `/etc/localsiem-privesc/` (der Hook), `/etc/profile.d/localsiem-privesc.sh` und die Zeile nach «localSIEM privesc: command hook» in `/etc/bash.bashrc` (Debian) oder `/etc/bash/bashrc` (Alpine): Solange sie vorhanden sind, schreibt jede interaktive Bash ihre Befehle weiterhin in `/var/log/localsiem-privesc/`, das niemand liest.
- `/var/log/localsiem-privesc/`: die Befehlsdateien jedes Benutzers.
- `log_group = adm` in `/etc/audit/auditd.conf`, `/root/.ssh` (leer erstellt) und das `message_format` von `/etc/snoopy.ini`: Sie können bleiben (`log_group = adm` hält die rotierten Audit-Logs lesbar, Abschnitt 14, und das Modul liest dieses Format von snoopy ebenso wie dessen Standardformate).

Die Diagnose listet diejenigen auf, die sie sehen kann (Prüfung «Files of version 1.0.0 of the module»). Um sie zu entfernen, als root: Löschen Sie die Regeldatei und laden Sie die Regeln erneut (`augenrules --load`); löschen Sie `/etc/profile.d/localsiem-privesc.sh`, `/etc/localsiem-privesc/` und die Zeile in der bashrc; und löschen Sie `/var/log/localsiem-privesc/`, wenn Sie die darin enthaltenen Befehle nicht behalten möchten.

<a id="privesc-health"></a>
## 16. Angriffsfläche und Zustandswarnungen des Moduls zur Rechteausweitung

Neben seinen Regeln betrachtet das Modul den Server selbst und sendet an das SOC:

| Warnung | Schweregrad | Wann |
|---|---|---|
| Neues setuid- oder setgid-Programm | Hoch | Ein Scan findet ein setuid- oder setgid-Programm, das der vorherige Scan nicht hatte (der erste Scan dient nur als Referenz). Ein Angreifer, der root geworden ist, hinterlässt oft eine setuid-Shell; auch eine Paketaktualisierung kann eines hinzufügen. |
| Neues setuid-Programm in einem beschreibbaren Ordner | Kritisch | Dasselbe, in `/tmp`, `/var/tmp`, `/dev/shm`, `/home`, `/srv` oder `/var/www` |
| Neues setuid-Programm aus GTFOBins | Kritisch | Dasselbe, für ein Programm, das als setuid eine root-Shell liefert (`bash`, `find`, `python`, `vim`, `less`, `cp`...) |
| Neue Capabilities | Hoch | Ein Programm hat Capabilities erhalten, die praktisch root entsprechen (`cap_setuid`, `cap_dac_override`, `cap_sys_admin`...) |
| Sensible Datei, die für jemand anderen als root beschreibbar ist | Kritisch | Wird stündlich geprüft: `/etc/passwd`, `/etc/shadow` (auch, ob sie für alle lesbar ist), `sudoers`, cron, `/etc/profile.d`, PAM, Dienste, `ld.so.preload`, die Ordner im `PATH` von root, `docker.sock`... Wird einmal pro Datei und Problem gemeldet. |
| auditd gestoppt (Zustand von localSIEM) | Hoch | auditd lief und läuft nicht mehr (außerhalb von Containern) |

Der Scan läuft im Hintergrund, höchstens alle **Stunden zwischen Scans nach setuid-Programmen** (der erste fünf Minuten nach dem Start des Collectors), durch die Ordner unter **Gescannte Ordner**, als Benutzer `localsiem` (was er nicht lesen kann, wird übersprungen), und bricht nach 3 Millionen Dateien oder 15 Minuten ab. Sein Ergebnis wird mit den gefundenen GTFOBins und Capabilities in der Diagnose angezeigt. Die Schweregrade dieser Warnungen stehen in `severity.yaml` des Moduls. Was bereits gemeldet wurde, bleibt über Neustarts hinweg gespeichert.

<a id="cli"></a>
## 17. Kommandozeile

Als root, `/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py <command>`:

| Befehl | Verwendung |
|---|---|
| `modules` | Installierte Module: ID, Version, aktiviert, deaktiviert oder nicht geladen, und Ordner, mit den fehlenden Voraussetzungen, falls vorhanden; sowie die Module, die nicht geladen werden konnten, mit dem Fehler |
| `doctor` | Für jedes aktivierte Modul: jede Prüfung (`✓`, `!`, `✗`, `·`) mit dem Fragment, das sie behebt, und die gefundenen Quellen; für ein Modul, das wegen einer fehlenden Voraussetzung deaktiviert ist, seine Voraussetzungen. `--json` liefert dasselbe als JSON. |
| `read-paths` | Ordner, die die Module lesen und auf die localSIEM als root Lesezugriff gewährt |
| `setup-modules [--no-restart]` | Als root: der Befehl, den die Weboberfläche anzeigt; Lesezugriff auf die Ordner der Module (`read_paths`) und ein Neustart von localSIEM (`--no-restart`: ohne Neustart). Module haben keine Einrichtungsoptionen |

Führen Sie die Diagnose als Benutzer `localsiem` aus, um seine tatsächlichen Berechtigungen zu sehen:

```bash
runuser -u localsiem -- /opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor   # Debian
su -s /bin/sh localsiem -c "/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor"   # Alpine
```
