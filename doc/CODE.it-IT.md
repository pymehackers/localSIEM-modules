# Riferimento del codice di localSIEM-modules

Questo CODE è disponibile anche in:\
[de-DE](CODE.de-DE.md), [en-GB](CODE.en-GB.md), [en-US](CODE.md), [es-AR](CODE.es-AR.md), [es-ES](CODE.es-ES.md), [fr-FR](CODE.fr-FR.md), [he-IL](CODE.he-IL.md), [hi-IN](CODE.hi-IN.md), it-IT, [ja-JP](CODE.ja-JP.md), [ko-KR](CODE.ko-KR.md), [pt-BR](CODE.pt-BR.md), [pt-PT](CODE.pt-PT.md), [ru-RU](CODE.ru-RU.md), [zh-CN](CODE.zh-CN.md)

## Indice

1. [Architettura e decisioni di progettazione](#architecture)
2. [Mappa dei moduli](#modules)
3. [Simboli chiave](#symbols)
4. [Flussi principali (call path)](#flows)
5. [Punti di ingresso](#routes)
6. [Analisi di impatto](#impact)
7. [Punti di estensione](#extensions)

[Installazione](README.it-IT.md) · [Manuale utente](MANUAL.it-IT.md) · [Riferimento del codice di localSIEM](../../localSIEM/doc/CODE.it-IT.md)

<a id="architecture"></a>
## 1. Architettura e decisioni di progettazione

Questo progetto contiene i moduli installabili di localSIEM (progetto fratello `../localSIEM`). Non ha alcun servizio né un installer proprio: i moduli si installano solo dall'interfaccia web di localSIEM, in Moduli › Installabili (si aggiornano e si disinstallano in Moduli › Installati), che scarica questo repository (branch `main`) e copia la cartella di ogni modulo, `mod-<name>/`, in `/opt/localsiem/modules/<name>/`; l'installer di localSIEM installa solo il nucleo, mai un modulo, e localSIEM non ha moduli propri. I processi di localSIEM (collettore, interfaccia web, `manage.py`) lo caricano. Il prefisso `mod-` appartiene solo al nome della cartella in questo repository: il modulo stesso (l'`id` del suo `module.json`, le sue opzioni, le sue impostazioni e la sua cartella installata) mantiene il suo nome senza prefisso. Oggi ci sono due moduli: `apache2` (cartella `mod-apache2/`) e `privesc` (cartella `mod-privesc/`).

### Perché i moduli vivono fuori dal nucleo

Il nucleo di localSIEM ([backend/core/](../../localSIEM/backend/core/)) è generico: archiviazione, ricerca, motore delle regole, raggruppamento, coda del SOC, heartbeat e salute non sanno nulla di Apache. Ciò che significa un servizio (dove si trovano i suoi log, come vengono suddivisi in record e analizzati, come i record diventano un evento, cosa conta come già risolto, le sue regole e i suoi requisiti) vive in un modulo. Tenere i moduli in un progetto proprio significa che:

- un modulo ha una versione (`version`), dichiara il localSIEM minimo di cui ha bisogno (`core`) e si aggiorna, si aggiunge o si disattiva senza una nuova release di localSIEM;
- il nucleo non importa alcun modulo per nome e non ha moduli propri: il registro ([backend/core/registry.py](../../localSIEM/backend/core/registry.py)) esamina solo `/opt/localsiem/modules/` (`LOCALSIEM_MODULES_PATH` nelle copie di sviluppo), dove l'interfaccia web installa i moduli di questo repository;
- un modulo che non riesce a caricarsi non ferma mai gli altri: il suo errore viene elencato nell'interfaccia web (stato «Errore») e da `manage.py modules`;
- un modulo non modifica mai il nucleo: `backend/core/module.py` e `backend/core/registry.py` sono l'intero contratto.

### Il contratto: module.json, locales e una sottoclasse di Module

**`module.json`** (verificato da `fReadManifest`):

| Chiave | Predefinito | Significato | apache2 | privesc |
|---|---|---|---|---|
| `id` | obbligatorio | Nome della cartella del modulo senza il prefisso `mod-` (il nome della cartella installata), `[a-z][a-z0-9_]{1,31}`; anche il `vName` della classe | `apache2` | `privesc` |
| `version` | `"0"` | Versione del modulo, mostrata nell'interfaccia web e da `manage.py modules` | `1.3.2` | `1.1.2` |
| `core` | `"0"` | Versione minima di localSIEM di cui ha bisogno; una superiore al `cVersion` del localSIEM installato significa che il modulo non viene caricato | `2.2.0` | `2.2.0` |
| `entry` | obbligatorio | `"file:Class"`: `file` senza `.py` (`[a-z][a-z0-9_]{0,63}`), `Class` una sottoclasse di `Module` | `module:ApacheModule` | `module:PrivescModule` |
| `default_enabled` | `true` | Se è in funzione finché l'amministratore non decide (`modules.<id>.enabled`) | `true` | `true` |
| `read_paths` | `[]` | Cartelle assolute che localSIEM, come root, permette di leggere all'utente `localsiem` (il comando che l'interfaccia web mostra dopo l'installazione, dopo **Riconfigura** e dopo un aggiornamento che le cambia) | `["/var/log/apache2"]` | `["/var/log/audit"]` |
| `install_requirements` | `{}` | Comandi che installano sul server, come root, il software di cui il modulo ha bisogno, per ogni sistema (`debian`, `alpine`): un comando per riga, senza operatori della shell, perché l'interfaccia web li mostra anche preceduti da `sudo` (`fCheckInstallRequirements` del nucleo). Mostrati in Moduli › Installabili › Requisiti, mai eseguiti | Debian: Apache, ModSecurity 2, il CRS, `a2enmod`, la configurazione consigliata di ModSecurity se non ce n'è una, riavvio; Alpine: Apache | Debian: auditd e rsyslog; Alpine: auditd |
| `setup_option` | — | Non usata da nessun modulo: il nucleo la ignora (il registro la scarta), perché un modulo non modifica mai il server; i file `module.json` di versioni precedenti possono ancora averla | non impostata | non impostata (`--configure-privesc` è stata rimossa nella 1.1.0) |
| `settings` | `[]` | Descrizione di ogni impostazione: l'interfaccia web ne costruisce il form | 6 impostazioni | 13 impostazioni |

Ogni impostazione ha una `key` (`[a-z][a-z0-9_]{1,31}`), un `type`, di solito un `default`, e gli attributi del suo tipo. `fValidateSettings` / `fCleanValue` / `fCleanRecords` verificano ciò che l'amministratore salva:

| Tipo | Attributi | Controllo web | Valori accettati |
|---|---|---|---|
| `boolean` | — | casella di spunta | `true` / `false` |
| `integer` | `min`, `max` | campo numerico | un intero compreso tra `min`..`max` |
| `string` | `max_length` (500) | campo di testo | testo senza caratteri di controllo, senza spazi iniziali e finali, fino a `max_length` |
| `path` | — | campo di testo a spaziatura fissa | vuoto o assoluto (inizia con `/`), fino a 1024 caratteri |
| `choice` | `choices` (obbligatorio), `required` | elenco (con «—» quando non è obbligatorio) | uno dei `choices`, o vuoto |
| `records` | `fields` (obbligatorio: impostazioni degli altri tipi), `max_items` (50) | un blocco per record con Aggiungi e Rimuovi | un elenco fino a `max_items` record; ogni campo viene verificato, i campi `required` non possono essere vuoti e i campi vuoti vengono scartati |

**`locales/<language>.json`** (de-DE, en-GB, en-US, es-AR, es-ES, fr-FR, he-IL, hi-IN, it-IT, ja-JP, ko-KR, pt-BR, pt-PT, ru-RU, zh-CN), letto da `fReadTexts` e mostrato dall'interfaccia web (`modules.js fModuleText`, che ripiega su en-US e poi sulla chiave):

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

Un file di locale mancante o danneggiato fa perdere solo la sua lingua.

**La sottoclasse di `Module`** ([backend/core/module.py](../../localSIEM/backend/core/module.py)). Il registro la crea come `Class(pSettings, pMasker, pStorage, pManifest)`. I suoi hook:

| Hook | Chiamato da | Predefinito | `ApacheModule` | `PrivescModule` |
|---|---|---|---|---|
| `mStart()` | collettore, una volta, con l'archiviazione pronta | niente | salva `apache.first_start` (inizio dei giorni di apprendimento) | salva `privesc.first_start`; carica `privesc.sessions`, `privesc.surface` e `privesc.health` |
| `mEnabled()`, `mModuleSettings()`, `mReload()` | collettore, interfaccia web | da `modules.<id>` sopra i valori predefiniti di `module.json` | ereditato | ereditato; `mReload` svuota anche la cache di `mSettings` |
| `mDiscoveryInterval()` | collettore (il più breve dei moduli attivati, almeno 60 s) | `discovery_interval_seconds` o 3600 | ereditato | ereditato (predefinito 300) |
| `mDiscover()` | collettore (avvio, intervallo, ricarica, richiesta della diagnostica), `manage.py doctor` | `[]` | sorgenti `{key, path, kind, format, vhost, audit_type, storage_dir}` dalla configurazione di Apache e dalle sorgenti manuali | `fDiscoverSources`: il log di audit e syslog |
| `mCreateFramer(pSource)` | collettore, per sorgente | `LineFramer` | `AuditFramer` per il log di audit seriale nativo | ereditato (`LineFramer`) |
| `mParse(pSource, pUnit, pReceived)` | collettore, per unità | obbligatorio | record di `access`, `error` o `audit` | record di `audit` o `syslog` |
| `mCreateCorrelator()` | collettore, all'avvio | obbligatorio | `Correlator` (finestra e correlazione debole dalle impostazioni del nucleo) | `Correlator`: record di audit per numero di serie (EOE o 2 s); righe di syslog subito |
| `mBuildEvent(pTransaction)` | collettore, per transazione scaduta | obbligatorio | evento con `action` e `detections` | evento con i flag che le regole confrontano; nessuna rilevazione propria |
| `mRulesPath()` / `mRuleFunctions()` | collettore, al caricamento delle regole | `None` / `{}` | `rules/` della sua cartella / `{"apache2.new_php": mIsNewPhp}` | `rules/` della sua cartella / `{}` ereditato |
| `mDetectionFromSignal(pEvent, pSignal)` | collettore, per segnale di regola (opzionale: cercato con `hasattr`) | rilevazione generica | rilevazione con i dettagli della richiesta e `{rule: {id, count}}` | rilevazione con utente, comando, programma, sessione, padre, file... |
| `mEnrich(pDetection)` | collettore, con il gruppo, prima di costruire l'avviso | `{}` | contesto dell'IP nell'ultima ora | contesto della sessione: inizio visto, porta, indirizzo SSH, ultimi 20 comandi |
| `mDoctor()` | collettore (stato `<id>.doctor`), `manage.py doctor` | `[]` | `fRunDoctor` | `fRunDoctor` (auditd e ciò che le sue regole hanno registrato, syslog, snoopy, ciò che il modulo vede, file della versione 1.0.0, superficie di attacco) |
| `mHealth(pNow)` | collettore, ogni 60 s, solo moduli attivati | `[]` | ModSecurity non caricato o Off, IP reale del client mancante (al massimo ogni 300 s) | salva le sessioni; risultati della scansione; ogni 300 s: auditd fermato, file sensibili scrivibili (ogni ora), avvia la scansione dei programmi setuid |
| `mSkipped()` | stato del collettore, `manage.py doctor` | `[]` | log tramite pipe, log coperti dal `GlobalLog`, log di accesso senza dati (`format_without_data`) | syslog non letto (auditd in esecuzione, `syslog_mode` mai), log di audit mancante |
| `mSetLowDisk(pLowDisk)` | collettore, livello del disco | niente | smette di salvare header e corpi dell'audit | ereditato |
| `mDisplayRecord(pRecord)` | interfaccia web, scheda della richiesta | `{}` | header e corpo del record di audit salvato (`fAuditDisplay`) | ereditato |
| `mRequirements()` | nucleo, localSIEM 2.2.0 o successivo: prima installazione, avvio e ricarica del collettore, **Riconfigura** nell'interfaccia web, `manage.py modules` e `doctor` | `[]` (nessun requisito) | `apache_config` e `modsecurity` (`fRequirementChecks`) | `command_source`: qualsiasi sorgente che `localsiem` possa leggere, il log di audit (auditd in esecuzione, non in un container) o syslog (con snoopy, se installato); `audit_log` / `syslog` quando una sorgente esiste ma non può essere letta |

Il nucleo non ha più né `mSetupSnippet` né `mApplySetup`: i moduli non hanno opzioni di configurazione e non modificano mai il server.

I record sono dict con `time`, `received`, `module` (l'id: il collettore sceglie il correlatore in base a esso), `source`, `source_key`, `correlation`, `parse_status` (`ok`, `partial`, `unparsed`), `fields` e `raw` (mascherato), più opzionalmente `search` (il testo indicizzato per la ricerca full-text). Gli eventi hanno le colonne della tabella degli eventi (`lEventColumns` in `storage_sqlite.py`) più `record_ids`, `rule_hits` e `detections`. Una rilevazione ha `module`, `vhost`, `ip`, `category`, `severity`, `rule`, `type`, `description`, `search`, `details`, `time` e `uid`.

### Requisiti: un modulo non installa mai ciò che sorveglia

Installare un modulo non installa mai il software che sorveglia: il modulo apache2 non installa né Apache né ModSecurity, e il modulo privesc non installa né auditd, né un demone syslog, né snoopy (il suo requisito, `command_source`, è una qualsiasi sorgente che l'utente `localsiem` possa leggere: il log di audit con auditd in esecuzione fuori da un container, o syslog; `fRequirementChecks` di `mod-privesc/doctor.py`). È il modulo stesso a definire ciò di cui ha bisogno prima di poter essere attivato, in `mRequirements()` (localSIEM 2.2.0 o successivo): un elenco di controlli nel formato della diagnostica, soddisfatti quando nessuno ha lo stato `error`. Il modulo apache2 restituisce `apache_config` (viene trovata una configurazione di Apache: `apache2.conf`, `httpd.conf` o il file dell'impostazione `config_file`) e `modsecurity` (`mod_security2` è caricato; ModSecurity 3 non conta), che `fRequirementChecks` prende dai primi controlli della diagnostica; senza Apache, entrambi sono errori. Ciò che installa quel software è dichiarato in `install_requirements` di `module.json`: l'interfaccia web lo mostra prima di installare il modulo (Moduli › Installabili › Requisiti), per il sistema del server, e non lo esegue mai. Il nucleo:

- installa il modulo disattivato (`modules.<id>.enabled = false`) quando manca un requisito alla sua prima installazione e l'amministratore non ha mai deciso; un aggiornamento non cambia mai `enabled`;
- non permette di attivarlo finché manca un requisito: l'interruttore è bloccato e l'interfaccia web mostra i requisiti con il loro `fix`;
- non disattiva mai di sua iniziativa un modulo attivato che perde un requisito: lo segnalano la sua diagnostica e le sue avvertenze di salute (`mHealth`: «ModSecurity is no longer loaded»), e disattivarlo le metterebbe a tacere;
- verifica di nuovo i requisiti quando il collettore si avvia o si ricarica, e con **Riconfigura** nella pagina del modulo (anche quando è disattivato): se sono soddisfatti, sblocca l'interruttore, l'amministratore attiva il modulo e l'interfaccia web mostra il comando da eseguire come root che consente a `localsiem` di leggere i log creati dopo l'installazione (`read_paths`).

### Caricati come namespace package

Non c'è alcun `__init__.py` da nessuna parte (namespace package impliciti di Python 3.13). `fRegisterPackage` crea il package `localsiem_modules` con la cartella dei moduli come suo `__path__`, e `fLoadClass` importa `localsiem_modules.<id>.<file>`, verifica che la classe sia un `Module` e che il suo `vName` sia uguale all'`id`. Conseguenze per il codice di un modulo:

- i suoi file vengono importati in modo **relativo** (`from .parsers import AccessParser`);
- il nucleo viene importato come **`backend.core...`** (`from backend.core.module import Module`): i processi di localSIEM mettono la cartella di localSIEM in `sys.path`;
- sono disponibili solo la libreria standard e le dipendenze di localSIEM (il suo ambiente virtuale `/opt/localsiem/venv/`, per esempio PyYAML): localSIEM non installa nulla per un modulo.

### Form delle impostazioni costruito dal manifest

Un modulo non ha HTML proprio. L'interfaccia web legge `settings` di `module.json` e i testi di `locales/`, costruisce il form (`modules.js fBuildSettings`, `fRecordsEditor`), convalida ciò che viene salvato con `fValidateSettings` e salva in `settings.json`, sotto `modules.<id>`, solo i valori che l'amministratore ha salvato; anche `enabled` vive lì. Il modulo legge `mModuleSettings()`: i valori predefiniti di `module.json` con sopra i valori salvati. Aggiungere un'impostazione quindi non richiede alcuna modifica nell'interfaccia web né nel nucleo.

Impostazioni del nucleo che il modulo apache2 legge anche da `self.dSettings`: `host`, `correlation_window_seconds` (5), `weak_correlation_seconds` (2), `below_threshold_severity` (`low`) e `health.single_ip_percent` / `health.single_ip_minimum_requests` (90 / 100). `mModuleSettings()` passa anche le chiavi salvate sotto `modules.apache2` che `module.json` non dichiara: `mDiscover` legge in quel modo `document_roots` (`{vhost: folder}`, sopra le DocumentRoot rilevate); si può impostare solo modificando `settings.json`.

### Il principio dell'«azione intrapresa»

Al SOC va solo ciò che nessuno ha ancora risolto. Nel modulo apache2 l'azione intrapresa viene letta dalla sorgente più affidabile: il log di audit (`Action: Intercepted (phase N)` in formato nativo, `audit_data.action.intercepted/phase` in JSON), poi l'error.log (`Access denied with code NNN (phase N)`). Un 403 senza alcuna traccia di ModSecurity non è un blocco (`fields.doubtful_block`).

| Situazione | `action` | Rilevazione (al SOC) |
|---|---|---|
| Intercettata nelle fasi 1-2 (l'applicazione non l'ha mai ricevuta) | `blocked` | nessuna: `mAssess` restituisce `None`; contata nel contesto degli avvisi successivi |
| Intercettata nelle fasi 3-4 | `none` | sì, `blocked_late` (alta), o `success_indicator` con un errore del database |
| Corrispondenze con il motore in `DetectionOnly` | `none` | sì |
| Corrispondenze sotto la soglia di anomalia | `none` | sì, `below_threshold` (bassa) |
| Segnali delle regole YAML | `none` | sì |

Le gravità provengono da `severity.yaml` (`fLoadSeverityTable`; un file mancante o un valore non valido mantiene il valore predefinito incorporato): `crs_not_blocked_2xx` alta, `crs_not_blocked_other` media, `blocked_late` alta, `success_indicator` critica (regola in uscita 950-955 non bloccata, o un errore del database nella stessa richiesta), `below_threshold` bassa (l'impostazione del nucleo `below_threshold_severity` ha la precedenza). «Sopra la soglia» significa che una regola 949xxx ha trovato corrispondenza o che il punteggio indicato da ModSecurity ha raggiunto la soglia; un punteggio calcolato dalle gravità delle regole è solo una stima e non decide. La soglia è quella dei messaggi, altrimenti `anomaly_threshold`, altrimenti quella di `crs-setup.conf`, altrimenti 5.

### Come funziona il modulo apache2

1. **Rilevamento** (`discovery.py`): `ApacheConfig` legge direttamente la configurazione (`Include`, `IncludeOptional`, `Define`, `${VARS}` dell'`envvars` di Debian, `<VirtualHost>`, `<IfModule>` rispetto ai moduli caricati), come utente `localsiem` e senza `apache2ctl`. `fDiscoverSources` trasforma `CustomLog`/`GlobalLog`/`TransferLog`, `ErrorLog` e `SecAuditLog` in sorgenti con la chiave stabile `apache:<kind>:<real path>`. Un `GlobalLog` il cui formato contiene `%v` copre tutti i vhost (gli altri log di accesso vengono saltati); i log tramite pipe e syslog vengono saltati, così come i log di accesso il cui formato non ha alcuna direttiva `%` (Apache scrive così com'è un nome che nessun `LogFormat` definisce: `format_without_data`, a meno che un altro `CustomLog` con dati scriva sullo stesso file; la diagnostica lo indica, senza correzione, dato che il formato dei log non viene mai modificato); le sorgenti manuali vanno per prime e un file viene letto una sola volta.
2. **Suddivisione e analisi** (`parsers.py`, `logformat.py`, `modsec.py`): le righe di accesso vengono analizzate con un'espressione regolare generata dal loro `LogFormat` (si prova per primo l'ultimo formato che ha funzionato); le righe di errore vengono classificate (`modsecurity`, `database`, `php`, `crash`, `apache`); i record di audit vengono letti come JSON (una riga, tagliata prima di `matched_rules`), seriale nativo (`AuditFramer` unisce da `--id-A--` a `--id-Z--`) o concorrente (la riga di indice punta a un file sotto `SecAuditLogStorageDir`). Tutto viene mascherato; ciò che non corrisponde viene conservato come `unparsed`.
3. **Correlazione** (`correlate.py`): i record con lo stesso `UNIQUE_ID` formano una transazione, che attende la finestra di correlazione e il watermark delle sorgenti che stanno recuperando; una riga di accesso senza `UNIQUE_ID` (i formati che Apache scrive per impostazione predefinita) viene abbinata da `mPair`, quando essa o i record della sua richiesta scadono, ai record di ModSecurity che non hanno una riga di accesso: stesso IP del client, ora entro ±2 s (la riga ha secondi interi) e stessi metodo, URI, stato e percorso quando entrambe le parti li conoscono; vince il candidato che coincide in più di essi, poi il più vicino, poi il più vecchio, e l'evento viene marcato come debole. Le righe dell'error.log senza `UNIQUE_ID` si uniscono subito alla transazione più vicina del loro IP. Una transazione con un `UNIQUE_ID` e una riga di ModSecurity dell'error.log, mentre arrivano record di audit (`vAuditSeen`), attende anche il proprio record di audit (`mWaitsForAudit`), al massimo `cAuditWaitSeconds` (120 s) dal suo primo record: ModSecurity scrive le righe delle sue regole mentre la richiesta è in corso e il record di audit quando termina, quindi altrimenti una richiesta lenta diventerebbe due eventi; una volta arrivato il record di audit, la riga di accesso ha altri `cAfterAuditSeconds` (2 s).
4. **Evento** (`ApacheModule.mBuildEvent`): campi presi dall'accesso, poi dall'audit, poi dall'errore; il vhost da `%v` o, in sua assenza, dall'header Host e dalla porta locale del record di audit (`mVhostName`); con una riga di accesso a secondi interi, l'ora del record di audit; `fSummarize` fornisce regole, categorie, punteggio, soglia e intercettazione; l'azione intrapresa e `mAssess` decidono la rilevazione.
5. **Regole, arricchimento, diagnostica e salute**: le regole YAML di `rules/` vengono eseguite su ogni evento (motore del nucleo); `mEnrich` aggiunge il contesto dell'IP; `fRunDoctor` verifica i requisiti e descrive i log, senza modificare nulla; `mHealth` sorveglia ModSecurity e l'IP reale del client. Il modulo non ha opzioni di configurazione: come root, localSIEM dà solo a `localsiem` l'accesso in lettura a `/var/log/apache2`.

### Decisioni di progettazione da conoscere

- **Nessun installer proprio**: i moduli si installano (Moduli › Installabili), si aggiornano (**Aggiorna**, in Moduli › Installati) e si disinstallano (**Disinstalla**) solo dall'interfaccia web di localSIEM, che scarica questo repository e li installa con `backend/core/catalog.py` (estrazione sicura, un'installazione alla volta, sostituzione atomica della cartella). Ciò che richiede root (l'accesso in lettura ai `read_paths`) lo fa localSIEM: dopo l'installazione (e dopo un aggiornamento che cambia `read_paths`), l'interfaccia web mostra il comando da eseguire come root.
- **I log del cliente vengono solo letti**: un modulo non scrive mai nei log dei servizi che sorveglia, né li ruota, tronca, sposta o elimina, e non ne modifica mai il formato; neanche il modulo apache2 modifica mai la configurazione di Apache o di ModSecurity (non ha `setup_option`). Se un server scrive i suoi log in un formato proprio (un `LogFormat` proprio, l'IP del client di `mod_remoteip`), il modulo si adatta: `AccessFormat` costruisce il parser di ogni log di accesso dal suo `LogFormat`, e `fCanPair` / `Correlator.mPair` uniscono le righe senza `UNIQUE_ID`. La diagnostica si limita a descrivere i log e ciò che localSIEM può o non può leggerne: i controlli `log_format`, `log_format_without_data`, `remoteip`, `audit_log` e `sanitise` non hanno `fix`; solo ciò che non è un log (ModSecurity, il CRS, `SecRuleEngine`, `mod_unique_id`, i permessi di lettura di `localsiem`) ne ha uno. `--configure-apache` è stata rimossa nella versione 1.3.0; `localsiem_combined` resta in `dKnownFormats` per i server che lo scrivono già, e l'installer di localSIEM elimina il `localsiem.conf` che scrivevano le versioni precedenti (`--uninstall`, `--reinstall`).
- **La parte K** (`matched_rules`) e **la parte E** (corpo della risposta) del log di audit non vengono mai salvate. Header e corpo restano solo nel record grezzo mascherato; la scheda della richiesta li ricostruisce (`fAuditDisplay`). L'indice full-text riceve un testo ridotto (`search`: riga della richiesta, host, user agent e l'id, il messaggio e i dati di ogni regola).
- **Il testo grezzo viene ricostruito dalle parti mascherate**: il record di audit originale può contenere password e cookie.
- **L'interfaccia web e gli strumenti creano il modulo senza archiviazione** (`pStorage` è `None` in `WebContext.mModule` e in `manage.py`): il costruttore e gli hook che chiamano non devono usare l'archiviazione.
- **Stato nel database degli eventi**: `apache.first_start` (giorni di apprendimento), `apache.health` (ciò che è già stato segnalato, così un riavvio non lo ripete) e `apache2.doctor` (scritto dal collettore). I primi due, come le chiavi delle sorgenti `apache:<kind>:<real path>`, mantengono il nome che il modulo aveva prima di chiamarsi apache2: un server che aveva il modulo `apache` conserva i suoi giorni di apprendimento, la sua memoria della salute e le sue posizioni di lettura (con una nuova chiave di sorgente, ogni log sotto i 5 MiB verrebbe riletto dall'inizio). Le ore della memoria della salute sono nel formato nativo del progetto (`2026-10-29@13-59-59.723`, UTC); uno stato salvato da una versione precedente, con secondi epoch, viene convertito al caricamento.
- **Sicurezza dei percorsi**: `mIsNewPhp` rifiuta `..` e resta dentro la DocumentRoot; `fReadConcurrentEntry` resta dentro `SecAuditLogStorageDir` e legge al massimo 8 MiB; il correlatore mantiene al massimo 50 000 transazioni in sospeso.

### Come funziona il modulo privesc

La domanda non è «qualcuno ha eseguito `whoami`?» (gli amministratori lo fanno ogni giorno) ma «questa sessione sta percorrendo la strada di un'escalation, e ci è arrivata?». Il modulo trasforma due sorgenti in eventi con un unico significato (`vhost` la persona, `method` il tipo, `uri` il comando, `path` il programma o il file, `ip` l'indirizzo SSH, `score` la ricognizione distinta della sessione), calcola dei flag su di essi, e lascia che siano le regole YAML a decidere cosa va al SOC.

1. **Rilevamento** (`discovery.py`): `fDiscoverSources` restituisce il log di audit (`fAuditLogPath`: impostazione, `log_file` di `auditd.conf`, `/var/log/audit/audit.log`; anche quando auditd è in esecuzione e `localsiem` non può ancora leggerlo, così che il nucleo lo segnali) e syslog (`fSyslogPath`) quando lo indica `syslog_mode` (`auto`: auditd non in esecuzione, il suo log non leggibile, o snoopy installato). Raccoglie anche ciò di cui ha bisogno la diagnostica: container (`fContainer`, leggibile senza root: `/run/systemd/container`, `/run/.containerenv`, `/.dockerenv`, `/proc/self/cgroup`, `systemd-detect-virt`), binario e pid di auditd, snoopy, se ogni log può essere letto (`fReadState`: `readable`, `unreadable` o `missing`) e i file lasciati dalla versione 1.0.0 (`fLegacyLeftovers`). `Accounts` rilegge `/etc/passwd`, `/etc/group` e `UID_MIN` quando cambiano, e classifica un uid come `root`, `admin` (membro di `admin_groups`), `user` o `service`.
2. **Analisi** (`parsers.py`): `fParseAuditLine` legge `type=... msg=audit(<time>:<serial>): k=v ...`, la parte in spazio utente `msg='...'`, la parte arricchita dopo `\x1d`, unisce gli argomenti di `EXECVE` (anche quelli divisi in pezzi `aN[i]`), decodifica i valori esadecimali (`proctitle`, `cmd`, `cwd`, `name`, `exe`, `aN`...) e **ricostruisce il testo grezzo dai valori decodificati e mascherati** (l'esadecimale di una password la conserverebbe); `search` riceve il comando decodificato. `fParseSyslogLine` legge timestamp ISO e classici (con o senza il `facility.priority` di busybox) e `fParseSyslogMessage` comprende snoopy (i suoi formati predefiniti della 2.4 e della 2.5, `uid:alice(1000)/root(0)` compreso, e quello impostato dalla versione 1.0.0), sudo, su (util-linux e busybox), pkexec, doas, `pam_unix` e sshd. `fMaskCommand` maschera le password nelle righe di comando prima del mascheratore del nucleo.
3. **Correlazione** (`correlate.py`): i record di audit con lo stesso numero di serie formano una transazione, che scade a `EOE`, subito per i tipi in spazio utente di un solo record (`USER_*`, `CRED_*`, `DAEMON_*`...), o dopo 2 s senza record; al massimo 50 000 in sospeso. Le righe di syslog scadono subito.
4. **Evento** (`PrivescModule.mBuildEvent`): `mAuditEvent` smista per tipo: `EXECVE` → `mAuditExec` (bit setuid del programma dal record `PATH` o da `stat`, `suid_escape` quando l'euid è 0, l'uid reale no e il programma non è setuid, capability ottenute da `BPRM_FCAPS`, `root_without_door`, `parent_interpreter` quando una shell viene eseguita come root avviata da un interprete di un utente diverso da root, il padre dalla memoria dei processi); `USER_*`/`LOGIN` → `mAuditUser` (sessione avviata, indirizzo SSH, porte: `USER_START`/`USER_CMD` di sudo, su, pkexec, doas, run0, systemd; fallimenti); `CONFIG_CHANGE` (`audit_disabled`, `audit_rule_removed` per qualsiasi regola rimossa), `DAEMON_*` (`auditd_stopped_manually` quando il mittente non è il pid 1), `ANOM_ABEND` (`crash_suspicious`); qualsiasi altro `SYSCALL` → `mAuditSyscall`, che lo classifica in base alla sua chiamata di sistema (`fSyscallName`: il nome del formato arricchito, o il numero nella tabella della sua architettura), ai suoi argomenti e ai suoi record `PATH`, mai in base alla chiave della regola: `denied` (apertura, esecuzione o troncamento falliti con `EACCES`/`EPERM` per una persona), `kmod`, `ptrace` (`ptrace_attach` per `PTRACE_ATTACH`/`PTRACE_SEIZE`), `chmod` (modalità con il bit setuid o setgid, non su una cartella, con `writer_allowed`) e `file` (una modifica di un percorso di `lSensitivePaths`, con `sensitive_group` e `writer_allowed`; la chiave, tramite `dKeyHints`, solo quando non si può risolvere alcun percorso). `mSyslogEvent` gestisce snoopy come `exec` (`suid_escape` da `stat`; senza `filename`, il programma dalla prima parola del comando) e sudo, su, pkexec, doas, login e pam. Ogni comando passa per `mAnalyzeCommand`: token di ricognizione (`fReconToken`) e token distinti della sessione nella finestra (`recon_burst`, `recon_massive`, `score`), download eseguiti da una shell (`cDownloadOnelinerRegex`, o un programma di download seguito da una shell con lo stesso padre), `compile_in_tmp`, gli ultimi comandi della sessione e, per gli account di servizio, il programma (`fProgramKey`) confrontato con la sua cronologia (`mPathFirstSeen` del nucleo, dopo `learning_days`: `new_program`). `ignored` marca gli utenti ignorati.
5. **Regole, arricchimento, diagnostica e salute**: le 35 regole YAML di `rules/` decidono ogni rilevazione (`mDetectionFromSignal`); `mEnrich` aggiunge il contesto della sessione; `fRunDoctor` descrive auditd e ciò che le sue regole hanno registrato, syslog, snoopy, ciò che il modulo vede e ciò che non vede, i file della versione 1.0.0 e la superficie di attacco; `mHealth` segnala auditd fermato, i file sensibili scrivibili e il risultato della scansione dei programmi setuid (`SurfaceScanner`, un thread). Il modulo non ha opzioni di configurazione e non modifica nulla sul server.

### Decisioni di progettazione del modulo privesc

- **Due sorgenti, un solo significato.** auditd non può essere evitato da un utente ma non funziona dentro i container (l'audit del kernel non ha namespace); snoopy vede ogni programma nei container ma richiede syslog; il solo syslog fornisce solo sudo, su, pkexec e doas. Nessuna sorgente vede i comandi interni della shell. Le regole confrontano colonne e flag, mai la sorgente, quindi si può aggiungere una sorgente senza toccarle. Lo stesso comando visto due volte genera un solo avviso: il nucleo raggruppa le rilevazioni per modulo, utente, IP, categoria e gravità.
- **Raffiche, non comandi.** La ricognizione è un token per tipo di domanda (`whoami`, `read:/etc/passwd`, `find:-perm:`...), e solo il numero di token distinti di una sessione in una finestra genera un avviso, con una soglia più alta per gli amministratori e una terza per gli script. Le soglie sono impostazioni, non soglie di regole: la regola confronta solo `recon_burst` / `recon_massive`.
- **Il successo è ciò che conta di più.** `suid_escape` (un programma che non è setuid eseguito con euid 0 e un uid reale diverso da 0) e `root_without_door` (root in una sessione di cui si è visto l'inizio e che non è mai passata per sudo, su, pkexec o doas) sono i due segni critici che un'escalation ha funzionato, quasi senza falsi positivi. Una sessione di cui non si è visto l'inizio (sessioni aperte prima del modulo, sessioni dimenticate dopo un giorno di inattività) non viene mai segnalata.
- **Le sessioni sopravvivono ai riavvii.** `SessionTracker` conserva l'inizio, l'indirizzo SSH e la porta di ogni sessione nello stato `privesc.sessions` (salvato al massimo ogni minuto); i token di ricognizione e gli ultimi comandi restano in memoria. Le sessioni inattive da un giorno vengono scartate.
- **Solo ciò che il server ha già.** Il modulo non installa mai nulla né modifica nulla fuori da `/opt/localsiem`: non carica regole di audit, non tocca `auditd.conf` né `snoopy.ini` e non installa alcun hook. La versione 1.0.0 lo faceva (`--configure-privesc`: regole di audit con le chiavi `lsiem_*`, `log_group = adm`, un hook di bash, il formato di snoopy); la versione 1.1.0 l'ha rimossa. I record di audit vengono quindi classificati in base al tipo, alla chiamata di sistema e ai percorsi, così funzionano qualsiasi regole di audit (quelle del server, le regole di esempio STIG, o le regole `lsiem_*` lasciate dalla 1.0.0); la chiave viene conservata in `fields.key` per le ricerche ed è solo un indizio (`dKeyHints`). I numeri delle chiamate di sistema vengono letti per architettura (`dSyscallTables`: x86_64, i386 e la tabella generica di aarch64, riscv64 e loongarch64) quando il log non ha i nomi arricchiti. La diagnostica descrive ciò che le regole del server registrano e ciò che non registrano; il suo `fix` è solo un pacchetto da installare o l'accesso in lettura di `localsiem`.
- **Leggibile significa leggibile.** Il requisito è soddisfatto da una sorgente che esiste e che `localsiem` può aprire (`fReadState`), non da un programma installato: in una prima installazione i log di solito appartengono a root, quindi il modulo resta disattivato fino al comando per root (`manage.py setup-modules`) e a **Riconfigura**.
- **I gestori di pacchetti non sono attaccanti.** Le modifiche di file sensibili e di bit setuid fatte dagli strumenti di account e di pacchetti (`sAllowedWriters`), o da programmi i cui antenati noti sono gestori di pacchetti, impostano `writer_allowed`, e le regole le saltano.
- **La scansione non blocca mai il collettore.** `SurfaceScanner` percorre gli `scan_paths` in un thread proprio, senza uscire dal file system di ognuno, saltando `/proc`, `/sys` e le cartelle dei container, fino a 3 milioni di file o 15 minuti; `mHealth` prende il risultato quando è pronto. La prima scansione è il riferimento; le successive segnalano ciò che è nuovo.
- **L'interfaccia web e gli strumenti creano il modulo senza archiviazione**: `mDiscover`, `mDoctor` e `mRequirements` non la usano mai, e `mAnalyzeCommand` chiama `mPathFirstSeen` solo quando esiste.
- **Stato nel database degli eventi**: `privesc.first_start` (giorni di apprendimento), `privesc.sessions`, `privesc.surface` (il riferimento della scansione e la diagnostica), `privesc.health` (ciò che è già stato segnalato, se auditd era in esecuzione) e `privesc.doctor` (scritto dal collettore). I programmi visti degli account di servizio sono righe di `seen_paths` con il vhost `privesc:<account>`. Le ore di `privesc.health` (la memoria della salute) e di `privesc.sessions` (`last` di ogni sessione) sono nel formato nativo del progetto (`2026-10-29@13-59-59.723`, UTC); uno stato salvato da una versione precedente, con secondi epoch, viene convertito al caricamento.

<a id="modules"></a>
## 2. Mappa dei moduli

| Modulo | Percorso | Responsabilità | Dipende da | Usato da |
|---|---|---|---|---|
| Manifest | [mod-apache2/module.json](../mod-apache2/module.json) | id, versione, nucleo minimo, entry, percorsi di lettura, impostazioni (nessuna opzione di configurazione) | — | registro, interfaccia web, `manage.py` |
| Modulo Apache | [mod-apache2/module.py](../mod-apache2/module.py) | `ApacheModule`: hook, azione intrapresa, gravità, rilevazioni, funzione di regola, arricchimento, salute | correlate, discovery, doctor, modsec, parsers; nucleo `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | collettore, interfaccia web, `manage.py` |
| Rilevamento | [mod-apache2/discovery.py](../mod-apache2/discovery.py) | `ApacheConfig` (parser della configurazione), sorgenti e log saltati, DocumentRoot | logformat (`dKnownFormats`) | module, doctor |
| Diagnostica | [mod-apache2/doctor.py](../mod-apache2/doctor.py) | Controlli dei requisiti; descrive i log (formato, log di audit, mascheramento) senza proporre di modificarli | discovery | module |
| Formati di accesso | [mod-apache2/logformat.py](../mod-apache2/logformat.py) | Da `LogFormat` a espressione regolare, ore in UTC, riga della richiesta | nucleo `timeutil` | parsers, discovery |
| Parser | [mod-apache2/parsers.py](../mod-apache2/parsers.py) | access, error, audit (JSON, nativo, concorrente), `AuditFramer`, `fAuditDisplay` | logformat, modsec; nucleo `masking`, `timeutil` | module |
| ModSecurity | [mod-apache2/modsec.py](../mod-apache2/modsec.py) | Messaggi, categorie, intervalli del CRS, punteggi, intercettazione | — | parsers, module |
| Correlazione | [mod-apache2/correlate.py](../mod-apache2/correlate.py) | `UNIQUE_ID`, abbinamento senza di esso (`mPair`), finestra, watermark | nucleo `timeutil` | module (collettore) |
| Tabella delle gravità | [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) | Gravità delle rilevazioni di ModSecurity | — | module (`fLoadSeverityTable`) |
| Regole | [mod-apache2/rules/](../mod-apache2/rules/) | Sei regole YAML | motore delle regole del nucleo, `mIsNewPhp` | collettore (`RulesEngine`), interfaccia web (`fRules`) |
| Testi | [mod-apache2/locales/](../mod-apache2/locales/) | Nome, riepilogo, etichette e aiuto delle impostazioni, scelte | — | interfaccia web |
| privesc: manifest | [mod-privesc/module.json](../mod-privesc/module.json) | id, versione, nucleo minimo, entry, percorsi di lettura, 13 impostazioni (nessuna opzione di configurazione) | — | registro, interfaccia web, `manage.py` |
| privesc: modulo | [mod-privesc/module.py](../mod-privesc/module.py) | `PrivescModule`: hook, eventi delle due sorgenti, classificazione dei record di audit (percorsi sensibili, chiamate di sistema per architettura), flag, rilevazioni delle regole, arricchimento, salute, risultati della scansione | commands, correlate, discovery, doctor, parsers, surface; nucleo `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | collettore, interfaccia web, `manage.py` |
| privesc: rilevamento | [mod-privesc/discovery.py](../mod-privesc/discovery.py) | Sorgenti, container, auditd, snoopy, syslog, se ogni log può essere letto, file lasciati dalla versione 1.0.0, `Accounts` (utenti, gruppi, tipo di account) | — | module, doctor |
| privesc: parser | [mod-privesc/parsers.py](../mod-privesc/parsers.py) | Record di audit (esadecimale, `msg='...'`, arricchito), righe di syslog (snoopy nei suoi formati abituali, sudo, su, pkexec, doas, pam, sshd), mascheramento delle righe di comando | nucleo `masking`, `timeutil` | module |
| privesc: correlazione | [mod-privesc/correlate.py](../mod-privesc/correlate.py) | Record di audit per numero di serie (EOE, record in spazio utente, 2 s); righe di syslog subito | — | module (collettore) |
| privesc: comandi | [mod-privesc/commands.py](../mod-privesc/commands.py) | Token di ricognizione, programma di un account di servizio, shell, interpreti, programmi di download, porte, compilatori; `SessionTracker` | nucleo `timeutil` | module |
| privesc: superficie di attacco | [mod-privesc/surface.py](../mod-privesc/surface.py) | `SurfaceScanner` (setuid, setgid, capability), GTFOBins, file sensibili scrivibili, gruppi privilegiati | — | module, doctor |
| privesc: diagnostica | [mod-privesc/doctor.py](../mod-privesc/doctor.py) | Descrive auditd, il suo log e ciò che le sue regole hanno registrato, syslog, snoopy, ciò che il modulo vede, i file della versione 1.0.0 e la superficie (correzioni: solo pacchetti e accesso in lettura); requisito `command_source` (qualsiasi sorgente leggibile) | discovery, surface; nucleo `timeutil` | module |
| privesc: regole | [mod-privesc/rules/](../mod-privesc/rules/) | 35 regole YAML | motore delle regole del nucleo | collettore (`RulesEngine`), interfaccia web (`fRules`) |
| privesc: tabella delle gravità | [mod-privesc/severity.yaml](../mod-privesc/severity.yaml) | Gravità delle rilevazioni costruite dal modulo (scansione, file sensibili) | — | module (`fLoadSeverityTable`) |
| privesc: testi | [mod-privesc/locales/](../mod-privesc/locales/) | Nome, riepilogo, etichette e aiuto delle impostazioni, scelte | — | interfaccia web |
| Nucleo: interfaccia | [backend/core/module.py](../../localSIEM/backend/core/module.py) | `Module`, `LineFramer` | registry | moduli |
| Nucleo: registro | [backend/core/registry.py](../../localSIEM/backend/core/registry.py) | Trovare, verificare e caricare i moduli; valori predefiniti e convalida delle impostazioni | `config` | collettore, interfaccia web, `manage.py`, `backend/core/catalog.py` |
| Nucleo: web | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) | Pagine dei Moduli (Installati, Installabili, la pagina di un modulo) e API | registry, catalog, rules | browser |
| Nucleo: catalogo | [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) | Download ed estrazione sicura del repository, elenco con l'azione di ogni modulo (`install`, `update`, `incompatible`, `invalid`...) e `newer`, installazione o aggiornamento atomici (`previous`, `access_changed`), disinstallazione, comando per root: Moduli › Installabili e **Aggiorna** / **Disinstalla** di Moduli › Installati, l'unico modo per installare i moduli | registry | interfaccia web |

<a id="symbols"></a>
## 3. Simboli chiave

| Simbolo | File:riga | Cosa fa |
|---|---|---|
| `ApacheModule` | [mod-apache2/module.py:68](../mod-apache2/module.py#L68) | Il modulo apache2 (`vName = "apache2"`) |
| `fLoadSeverityTable` | [mod-apache2/module.py:54](../mod-apache2/module.py#L54) | `severity.yaml` sopra i valori predefiniti incorporati |
| `ApacheModule.mDiscover` | [mod-apache2/module.py:95](../mod-apache2/module.py#L95) | Analizza la configurazione, sorgenti, log saltati, DocumentRoot |
| `ApacheModule.mThreshold` | [mod-apache2/module.py:105](../mod-apache2/module.py#L105) | Soglia di anomalia: impostazione, CRS, o 5 |
| `ApacheModule.mParse` | [mod-apache2/module.py:136](../mod-apache2/module.py#L136) | Da unità a record in base al tipo di sorgente |
| `ApacheModule.mBuildEvent` | [mod-apache2/module.py:176](../mod-apache2/module.py#L176) | Da transazione a evento: campi, azione intrapresa, punteggi, rilevazione |
| `ApacheModule.mVhostName` | [mod-apache2/module.py:311](../mod-apache2/module.py#L311) | Dall'header Host o dall'hostname di ModSecurity al vhost che ha scelto Apache (ciò che registra `%v`) |
| `ApacheModule.mAssess` | [mod-apache2/module.py:323](../mod-apache2/module.py#L323) | Gravità, nome della regola, descrizione e dettagli di ciò che va al SOC |
| `ApacheModule.mDetectionFromSignal` | [mod-apache2/module.py:385](../mod-apache2/module.py#L385) | Da segnale di una regola YAML a rilevazione |
| `ApacheModule.mIsNewPhp` | [mod-apache2/module.py:414](../mod-apache2/module.py#L414) | Funzione di regola `apache2.new_php` |
| `ApacheModule.mEnrich` | [mod-apache2/module.py:442](../mod-apache2/module.py#L442) | Contesto dell'IP (ultima ora) per l'avviso |
| `ApacheModule.mHealth` | [mod-apache2/module.py:461](../mod-apache2/module.py#L461) | ModSecurity non caricato o Off; IP reale del client mancante |
| `ApacheModule.mDisplayRecord` | [mod-apache2/module.py:538](../mod-apache2/module.py#L538) | Header e corpo per la scheda della richiesta |
| `ApacheModule.mRequirements` | [mod-apache2/module.py:545](../mod-apache2/module.py#L545) | Apache e ModSecurity 2: ciò di cui il modulo ha bisogno prima di poter essere attivato |
| `ApacheConfig` | [mod-apache2/discovery.py:105](../mod-apache2/discovery.py#L105) | Parser della configurazione di Apache |
| `ApacheConfig.mDirective` | [mod-apache2/discovery.py:228](../mod-apache2/discovery.py#L228) | Direttive lette (log, vhost, moduli, ModSecurity) |
| `ApacheConfig.mVhostName` | [mod-apache2/discovery.py:358](../mod-apache2/discovery.py#L358) | Vhost di una richiesta dal suo header Host e dall'indirizzo e porta locali, come lo sceglie Apache |
| `fSourceKey` / `fDiscoverSources` | [mod-apache2/discovery.py:403](../mod-apache2/discovery.py#L403) / [:408](../mod-apache2/discovery.py#L408) | Chiave stabile della sorgente; sorgenti da leggere e quelle saltate |
| `fRunDoctor` | [mod-apache2/doctor.py:46](../mod-apache2/doctor.py#L46) | Controlli dei requisiti `{id, status, title, detail, fix}` |
| `fCanPair` | [mod-apache2/doctor.py:26](../mod-apache2/doctor.py#L26) | Se un formato di accesso può essere unito senza `UNIQUE_ID` (IP del client, ora, riga della richiesta, stato) |
| `fRequirementChecks` | [mod-apache2/doctor.py:174](../mod-apache2/doctor.py#L174) | I controlli `apache_config` e `modsecurity` della diagnostica o, senza Apache, entrambi come errori, con il comando che li installa |
| `AccessFormat` / `dKnownFormats` | [mod-apache2/logformat.py:60](../mod-apache2/logformat.py#L60) / [:15](../mod-apache2/logformat.py#L15) | Da `LogFormat` a espressione regolare; nomi noti |
| `AccessParser` | [mod-apache2/parsers.py:59](../mod-apache2/parsers.py#L59) | Da riga di access.log a record |
| `fParseErrorLine` | [mod-apache2/parsers.py:147](../mod-apache2/parsers.py#L147) | Riga di error.log: ModSecurity, database, PHP, crash |
| `AuditFramer` | [mod-apache2/parsers.py:233](../mod-apache2/parsers.py#L233) | Record nativi su più righe; posizione di commit sicura |
| `fParseAuditRecord` / `fFinishAudit` | [mod-apache2/parsers.py:277](../mod-apache2/parsers.py#L277) / [:426](../mod-apache2/parsers.py#L426) | Record di audit JSON o nativo; mascheramento, testo grezzo e indicizzato |
| `fAuditDisplay` / `fReadConcurrentEntry` | [mod-apache2/parsers.py:495](../mod-apache2/parsers.py#L495) / [:577](../mod-apache2/parsers.py#L577) | Scheda di un record salvato; file di una voce concorrente |
| `fParseMessage` / `fSummarize` | [mod-apache2/modsec.py:52](../mod-apache2/modsec.py#L52) / [:152](../mod-apache2/modsec.py#L152) | Un messaggio di ModSecurity; regole, categorie, punteggio, soglia, intercettazione |
| `Correlator` | [mod-apache2/correlate.py:57](../mod-apache2/correlate.py#L57) | `mAdd` ([:148](../mod-apache2/correlate.py#L148)), `mPair` ([:207](../mod-apache2/correlate.py#L207)), `mDue` ([:248](../mod-apache2/correlate.py#L248)), `mWaitsForAudit` ([:271](../mod-apache2/correlate.py#L271)), `mPendingCount` |
| `PrivescModule` | [mod-privesc/module.py:226](../mod-privesc/module.py#L226) | Il modulo privesc (`vName = "privesc"`) |
| `PrivescModule.mBuildEvent` | [mod-privesc/module.py:341](../mod-privesc/module.py#L341) | Da transazione a evento, per sorgente; `ignored`; campi vuoti scartati (`fCleanFields` mantiene lo 0) |
| `PrivescModule.mAnalyzeCommand` | [mod-privesc/module.py:366](../mod-privesc/module.py#L366) | Ricognizione della sessione, download eseguito da una shell, compilazione in `/tmp`, comandi recenti, nuovo programma di un account di servizio |
| `PrivescModule.mAuditEvent` / `mAuditExec` / `mAuditUser` | [mod-privesc/module.py:427](../mod-privesc/module.py#L427) / [:587](../mod-privesc/module.py#L587) / [:661](../mod-privesc/module.py#L661) | Transazione di audit per tipo; programmi eseguiti (`suid_escape`, `root_without_door`, `parent_interpreter`, capability); accessi, porte e fallimenti |
| `PrivescModule.mAuditSyscall` | [mod-privesc/module.py:509](../mod-privesc/module.py#L509) | Qualsiasi altra chiamata di sistema in base al nome, agli argomenti e ai percorsi: `denied`, `kmod`, `ptrace`, `chmod`, `file` (`sensitive_group`) o `syscall` |
| `fSyscallName` / `fSensitiveGroup` | [mod-privesc/module.py:184](../mod-privesc/module.py#L184) / [:210](../mod-privesc/module.py#L210) | Nome di una chiamata di sistema (nome arricchito, o numero per architettura); gruppo di un percorso sensibile (`lSensitivePaths`) |
| `PrivescModule.mSyslogEvent` | [mod-privesc/module.py:702](../mod-privesc/module.py#L702) | snoopy, sudo, su, pkexec, doas, accessi |
| `PrivescModule.mWriterAllowed` | [mod-privesc/module.py:412](../mod-privesc/module.py#L412) | Chi scrive un file sensibile, o un suo antenato noto, è uno strumento di account o di pacchetti |
| `PrivescModule.mDetectionFromSignal` / `mEnrich` | [mod-privesc/module.py:781](../mod-privesc/module.py#L781) / [:818](../mod-privesc/module.py#L818) | Da segnale di una regola a rilevazione; contesto della sessione per l'avviso |
| `PrivescModule.mHealth` / `mSurfaceResult` | [mod-privesc/module.py:851](../mod-privesc/module.py#L851) / [:903](../mod-privesc/module.py#L903) | Sessioni salvate, auditd fermato, file sensibili, scansione avviata; nuovi programmi setuid e capability |
| `fDiscoverSources` / `fReadState` / `fLegacyLeftovers` | [mod-privesc/discovery.py:291](../mod-privesc/discovery.py#L291) / [:160](../mod-privesc/discovery.py#L160) / [:175](../mod-privesc/discovery.py#L175) | Sorgenti, quelle saltate e informazioni per la diagnostica; se un log può essere letto; file lasciati dalla versione 1.0.0 |
| `fContainer` / `fAuditdPid` | [mod-privesc/discovery.py:54](../mod-privesc/discovery.py#L54) / [:96](../mod-privesc/discovery.py#L96) | Tipo di container (senza root); pid di un auditd in esecuzione |
| `Accounts` | [mod-privesc/discovery.py:190](../mod-privesc/discovery.py#L190) | Nomi degli uid, gruppi, `UID_MIN`, tipo di account (`mAccountType`) |
| `fParseAuditLine` / `fParseSyslogLine` | [mod-privesc/parsers.py:83](../mod-privesc/parsers.py#L83) / [:316](../mod-privesc/parsers.py#L316) | Record delle due sorgenti |
| `fMaskCommand` | [mod-privesc/parsers.py:45](../mod-privesc/parsers.py#L45) | Password delle righe di comando, poi il mascheratore del nucleo |
| `Correlator` (privesc) | [mod-privesc/correlate.py:20](../mod-privesc/correlate.py#L20) | Record di audit per numero di serie; gli altri subito |
| `fReconToken` / `fProgramKey` / `fCommandArgs` | [mod-privesc/commands.py:115](../mod-privesc/commands.py#L115) / [:180](../mod-privesc/commands.py#L180) / [:91](../mod-privesc/commands.py#L91) | Token di ricognizione di un comando; programma di un account di servizio; parole di un comando digitato |
| `SessionTracker` | [mod-privesc/commands.py:202](../mod-privesc/commands.py#L202) | Sessioni (inizio, IP, porta, ricognizione, ultimi comandi), processi, download; `mExport`/`mImport` |
| `SurfaceScanner` / `fCheckSensitiveFiles` | [mod-privesc/surface.py:167](../mod-privesc/surface.py#L167) / [:133](../mod-privesc/surface.py#L133) | Scansione di setuid, setgid e capability in un thread; file sensibili scrivibili da altri |
| `fRunDoctor` / `fRequirementChecks` (privesc) | [mod-privesc/doctor.py:275](../mod-privesc/doctor.py#L275) / [:282](../mod-privesc/doctor.py#L282) | Controlli della diagnostica (descrizioni; correzioni solo per pacchetti e accesso in lettura); requisito `command_source`: qualsiasi sorgente leggibile |
| `Module` / `LineFramer` | [backend/core/module.py:59](../../localSIEM/backend/core/module.py#L59) / [:48](../../localSIEM/backend/core/module.py#L48) | Interfaccia di un modulo; una riga per unità |
| `fReadManifest` | [backend/core/registry.py:133](../../localSIEM/backend/core/registry.py#L133) | Verifica `module.json`, legge i testi |
| `fListManifests` / `fCreateModules` | [backend/core/registry.py:165](../../localSIEM/backend/core/registry.py#L165) / [:229](../../localSIEM/backend/core/registry.py#L229) | I moduli installati (`/opt/localsiem/modules/*`); istanze ed errori |
| `fRegisterPackage` / `fLoadClass` | [backend/core/registry.py:185](../../localSIEM/backend/core/registry.py#L185) / [:197](../../localSIEM/backend/core/registry.py#L197) | Namespace package `localsiem_modules`; importazione e verifiche dell'entry |
| `fModuleSettings` / `fValidateSettings` | [backend/core/registry.py:250](../../localSIEM/backend/core/registry.py#L250) / [:317](../../localSIEM/backend/core/registry.py#L317) | Valori predefiniti sotto i valori salvati; convalida di ciò che viene salvato |
| `fSaveModule` | [backend/web/api_modules.py:290](../../localSIEM/backend/web/api_modules.py#L290) | `POST /api/admin/modules/{name}` |
| `fGetCatalog` / `fInstallFromCatalog` / `fUninstallModule` | [backend/web/api_modules.py:384](../../localSIEM/backend/web/api_modules.py#L384) / [:395](../../localSIEM/backend/web/api_modules.py#L395) / [:422](../../localSIEM/backend/web/api_modules.py#L422) | `GET /api/admin/module-catalog`; `POST /api/admin/module-catalog/{name}` (installa o aggiorna; una prima installazione senza i suoi requisiti viene disattivata: `fFirstInstallation`); `DELETE /api/admin/modules/{name}` |
| `fInstall` / `fCatalog` | [backend/core/catalog.py:235](../../localSIEM/backend/core/catalog.py#L235) / [:171](../../localSIEM/backend/core/catalog.py#L171) | Installa o aggiorna un modulo accanto alla copia installata e le scambia con un rename (`previous`, `access_changed`); i moduli del repository con `installed`, `newer` e la loro azione |
| `fRemove` / `fRootCommand` | [backend/core/catalog.py:302](../../localSIEM/backend/core/catalog.py#L302) / [:372](../../localSIEM/backend/core/catalog.py#L372) | Disinstalla un modulo (rename ed eliminazione); il comando per root (`manage.py setup-modules`) |
| `fCatalogPanel` / `fUpdateNotice` / `fUpdate` | [frontend/assets/modules.js:218](../../localSIEM/frontend/assets/modules.js#L218) / [:417](../../localSIEM/frontend/assets/modules.js#L417) / [:452](../../localSIEM/frontend/assets/modules.js#L452) | Sezione Installabili (solo i moduli non installati, **Installa** e la sua finestra di dialogo); notifica di una versione più recente su una riga di Installati; **Aggiorna** (conferma, lo stesso `POST`, una finestra di dialogo solo con `access_changed` o quando il collettore non ha risposto) |

<a id="flows"></a>
## 4. Flussi principali (call path)

**Avvio del collettore → registro → ApacheModule**

`Collector.mSetup` → `fCreateModules` → `fListManifests` (`/opt/localsiem/modules/*`) → `fReadManifest` (id = cartella, entry, impostazioni, `core` ≤ `cVersion`, `fReadTexts`) → `fCreateModule` → `fLoadClass` (`fRegisterPackage`, `import localsiem_modules.apache2.module`, sottoclasse di `Module`, `vName == id`) → `ApacheModule(dSettings, vMasker, vStorage, dManifest)` → `mStart` → `mCreateCorrelator` → `Collector.mLoadRules` (`mRulesPath`, `mRuleFunctions`, sovrascritture `rules.<id>` → `RulesEngine.mLoad`) → `Collector.mDiscover` (`mEnabled` → `mDiscover` → `ApacheConfig.mParse` → `fDiscoverSources`; un `FileTailer` e `mCreateFramer` per sorgente) → i record in sospeso tornano nel correlatore → `mPublishDoctor` (`mDoctor` → `fRunDoctor` → stato `apache2.doctor`).

**Una riga letta → rilevazioni**

1. `Collector.mReadSources` → `FileTailer.mPoll` → framer `mFeed` (`LineFramer`, o `AuditFramer`, il cui `mSafeCommit` mantiene la posizione prima di un record non terminato) → `ApacheModule.mParse` (`AccessParser.mParse`, `fParseErrorLine`, o `fReadConcurrentEntry` + `fParseAuditRecord` e `mObserveAudit`) → record e posizioni salvati in una sola transazione → `Correlator.mAdd`.
2. `Collector.mProcessDue` → `Correlator.mDue(pWatermark=...)` → `ApacheModule.mBuildEvent` (`fSummarize`, azione intrapresa, `mAssess`, `mPathFirstSeen` per `.php` con 2xx) → `RulesEngine.mEvaluate` (regole YAML; `{function: apache2.new_php}` → `mIsNewPhp`) → `mSaveEvents` → `mDetect` per ogni rilevazione e `mDetectionFromSignal` per ogni segnale → `Grouper.mAdd`.
3. `Collector.mProcessGroups` → `ApacheModule.mEnrich` (`mGetIpContext`) → `fBuildAlert` → coda del SOC.

**L'amministratore salva le impostazioni → ricarica del collettore**

`modules.js fBuildSettings` (invio) → `POST /api/admin/modules/apache2` `{settings}` → `fSaveModule` → `fValidateSettings` (422 `invalid_setting:<key>` o `<key>.<field>`) → `fSaveSettings` (`settings.json`, `modules.apache2`) → `WebContext.mApplySettings` → socket del collettore `{"command": "reload"}` → `Collector.mHandleIpc` → `Collector.mCycle` → `mReloadSettings` (`ApacheModule.mReload`, `mLoadRules`, `mDiscover`, `mPublishDoctor`, `mPublishState`). L'interruttore invia `{enabled}` allo stesso modo (per attivarlo: 422 `requirements_missing` finché manca un requisito del modulo) e la tabella delle regole invia `{rules}` (`fCleanRules` → `rules.<id>`: `enabled`, `severity`, `threshold` o `first_threshold`, `window`). Se il socket non risponde, il collettore si accorge comunque del nuovo `settings.json` al suo ciclo successivo.

**Installare un modulo dall'interfaccia web** (l'unico modo per installare i moduli)

`modules.js fCatalogPanel` (Moduli › Installabili) → **Controlla il repository** → `GET /api/admin/module-catalog` (`fGetCatalog` → `fFetchCatalog` → `fDownload` → `fCatalog`: ogni cartella `mod-<name>/` del repository, con `installed`, `newer` e `action`) → vengono elencati solo gli elementi con `installed` null → **Requisiti** (`fShowRequirements` → `fRequirementsBody`: gli `install_requirements` del modulo per il sistema del server, `system` della risposta, come root e con `sudo`, e le note `install_requirements.*` dei suoi locales; non viene eseguito nulla) → **Installa** → `POST /api/admin/module-catalog/{name}` (`fInstallFromCatalog` → `fFetchAndInstall` → `InstallLock` → `fDownload` → `fInstall`: `mod-apache2/` → `/opt/localsiem/modules/apache2/`, `previous` null, `access_changed` true) → `WebContext.mReloadModules` → `fFirstInstallation` (un requisito mancante e `modules.<name>.enabled` mai salvato: `enabled = false`) → `restart` del collettore → `fCreateModules` carica il modulo → la finestra di dialogo «<module> installato» mostra il comando per root (`fRootCommand`: `manage.py setup-modules`, accesso in lettura ai `read_paths`) o, se manca un requisito, i controlli non soddisfatti.

**Aggiornare un modulo dall'interfaccia web**

Si apre Moduli › Installati → `fCheckRepository` → `fFetchCatalog(false)` di `modules.js` (l'ultima risposta di `GET /api/admin/module-catalog`, riutilizzata per 600 s; installare, aggiornare o disinstallare un modulo la dimentica) → elementi con `newer` e `action` `update` o `incompatible` → `fUpdateNotice` sulla riga (solo finché la versione installata è quella confrontata) → **Aggiorna** → `fUpdate` → conferma → `POST /api/admin/module-catalog/{name}` (lo stesso `fInstallFromCatalog` → `fInstall`: la nuova copia sostituisce quella installata, `previous` è la versione vecchia, `access_changed` indica se `read_paths` è cambiato; nessun `fFirstInstallation`, quindi `enabled` e le impostazioni restano) → `restart` del collettore → una finestra di dialogo solo se `access_changed` (il comando per root) o se il collettore non ha risposto.

**Disinstallare un modulo dall'interfaccia web**

**Disinstalla** (riga di Moduli › Installati o pagina del modulo) → `fUninstallButton` → conferma → `DELETE /api/admin/modules/{name}` (`fUninstallModule` → `fRemove` → `InstallLock` → rename di `/opt/localsiem/modules/<name>/` in una cartella di staging, dove viene eliminata) → `WebContext.mReloadModules` → `restart` del collettore. `modules.<name>` e le sovrascritture delle sue regole restano in `settings.json`, e l'accesso in lettura dato da root resta.

**Prima installazione senza Apache o ModSecurity → Riconfigura** (localSIEM 2.2.0 o successivo)

Installazione nell'interfaccia web → `fInstall` (prima installazione) → il modulo creato dalla copia installata (archiviazione `None`) → `ApacheModule.mRequirements` → `ApacheConfig.mParse` → `fRequirementChecks` (con Apache: `fRunDoctor` → `apache_config`, `modsecurity`; senza, entrambi come errori) → un errore e `modules.apache2.enabled` mai salvato → `modules.apache2.enabled = false` («Disattivato», interruttore bloccato, requisiti nella pagina). Più tardi, con Apache e ModSecurity installati: **Riconfigura** → `POST /api/admin/modules/apache2/reconfigure` → `mRequirements` → soddisfatti → interruttore sbloccato e il comando per root (accesso in lettura ai `read_paths`; apache2 non ha `setup_option`) → l'amministratore attiva il modulo → ricarica del collettore → `mDiscover` → `mPublishDoctor`.

**Scheda della richiesta e diagnostica dall'interfaccia web**

`GET /api/events/{id}` → `fEvent` → `WebContext.mModule("apache2")` → `mDisplayRecord` → `fAuditDisplay`. **Rileva di nuovo ed esegui la diagnostica** → `POST /api/admin/modules/apache2/doctor` → collettore `{"command": "doctor"}` → `mDiscover` + `mPublishDoctor`.

**Salute**

`Collector.mCycle` (ogni 60 s) → `mCheckHealth` → `ApacheModule.mHealth` (al massimo ogni 300 s; `ApacheConfig.mParse`, `mCountRecentEvents`) → `fHealthDetection` → `mDetect`.

**privesc: un comando eseguito → rilevazioni**

1. auditd scrive `SYSCALL`, `EXECVE`, `CWD`, `PATH`, `PROCTITLE`, `EOE` con un numero di serie → `FileTailer.mPoll` → `LineFramer` → `PrivescModule.mParse` → `fParseAuditLine` (esadecimale decodificato, `fMaskCommand`, testo grezzo ricostruito) → `Correlator.mAdd` (chiave `audit:<time>:<serial>`, scade a `EOE`).
2. `Correlator.mDue` → `PrivescModule.mBuildEvent` → `mAuditEvent` → `mAuditExec` (`suid_escape`, `BPRM_FCAPS`, `root_without_door` da `SessionTracker.mGet`, `mRememberProcess`) → `mAnalyzeCommand` (`fReconToken` → `SessionTracker.mRecon` → `recon_burst`/`recon_massive`; `cDownloadOnelinerRegex`, `mDownload`/`mRecentDownload`; `fCompileInTemporary`; `mCommand`; account di servizio: `fProgramKey` → `mPathFirstSeen` → `new_program`) → `fCleanFields`.
3. `RulesEngine.mEvaluate` (regole di `mod-privesc/rules/`) → `PrivescModule.mDetectionFromSignal` → `Grouper.mAdd` → `Collector.mProcessGroups` → `PrivescModule.mEnrich` (sessione: ultimi 20 comandi) → `fBuildAlert` → coda del SOC.

Con snoopy, lo stesso comando arriva anche come riga di syslog: `fParseSyslogLine` → `fParseSyslogMessage` → `mSyslogEvent` → `mAnalyzeCommand` (sessione `snoopy:<uid>:<sid>`).

**privesc: sessioni e porte**

`LOGIN` (auid e ses assegnati) o `USER_LOGIN`/`USER_START` di sshd o di login → `mAuditUser` → `SessionTracker.mStart` (utente, indirizzo SSH). `USER_START`/`USER_CMD` con risultato success di sudo, su, pkexec, doas, run0 o systemd → `SessionTracker.mDoor`. Un `EXECVE` successivo di quella sessione con uid ed euid 0 → `root_without_door` solo se l'inizio è stato visto e non c'è stata alcuna porta. `mHealth` salva `SessionTracker.mExport` in `privesc.sessions` al massimo ogni minuto; `mStart` lo carica (`mImport`).

**privesc: una chiamata di sistema registrata dalle regole di audit del server**

auditd scrive `SYSCALL` (con `arch`, `syscall`, `a0`-`a3`, `success`, `exit` e la chiave della regola che l'ha registrata, qualunque sia), `CWD`, `PATH`... → `fParseAuditLine` → `Correlator` → `mAuditEvent` → `mAuditSyscall`: `fSyscallName` → open/exec/truncate fallito con `EACCES`/`EPERM` e un uid di login → `denied`; `init_module`/`finit_module`/`delete_module` → `kmod`; `ptrace` → `ptrace`; `chmod`/`fchmod`/`fchmodat`/`fchmodat2` con `S_ISUID`/`S_ISGID` nella modalità, non su una cartella → `chmod` (`mWriterAllowed`); una modifica (una chiamata di `sChangeSyscalls`, un'apertura con flag di scrittura, un `PATH` con `CREATE`/`DELETE`) di un percorso di `lSensitivePaths` → `file` con `sensitive_group` (`dKeyHints` solo senza un percorso risolvibile) e `mWriterAllowed`; qualsiasi altra cosa → `syscall`. `mBuildEvent` ricorda l'ora di ogni tipo (`dRuntime["audit_kinds"]`) per la diagnostica.

**privesc: scansione della superficie di attacco**

`mHealth` (ogni 300 s, cinque minuti dopo l'avvio, ogni `surface_scan_hours`) → `SurfaceScanner.mStart` (thread: `os.walk` di `scan_paths`, `os.lstat`, `os.getxattr("security.capability")` → `fCapabilities`) → `mHealth` successivo → `mSurfaceResult` (`SurfaceScanner.mTake`, confrontato con `privesc.surface`: nuovi setuid/setgid → `new_setuid*`, nuove capability → `new_capabilities`) → `mModuleDetection` → `mDetect`; il risultato viene salvato in `privesc.surface` e mostrato da `fSurfaceChecks`. Ogni ora `fCheckSensitiveFiles` → `sensitive_file_writable`.

**privesc: requisiti e Riconfigura**

`fInstall` (prima installazione) o **Riconfigura** → `PrivescModule.mRequirements` → `fRequirementChecks(mModuleSettings())` (`fContainer`, `fAuditdPid`, `fAuditLogPath` → `fReadState`; `fSyslogPath` → `fReadState` a meno che `syslog_mode` non sia `never`; `fSnoopyInstalled`) → una sorgente leggibile: `command_source` ok (quelle illeggibili come avvertenze); una sorgente che esiste ma non può essere letta: errore `audit_log` o `syslog` con l'accesso in lettura (`manage.py setup-modules` o `setfacl`); nulla: errore `command_source` con il pacchetto da installare. Il modulo resta disattivato finché c'è un errore.

<a id="routes"></a>
## 5. Punti di ingresso

| Punto di ingresso | Handler | File |
|---|---|---|
| `"entry": "module:ApacheModule"` di `module.json` | `ApacheModule` | [mod-apache2/module.py](../mod-apache2/module.py) |
| `mod-apache2/rules/*.yaml` | `RulesEngine` (nucleo) | [mod-apache2/rules/](../mod-apache2/rules/) |
| Funzione di regola `apache2.new_php` | `ApacheModule.mIsNewPhp` | [mod-apache2/module.py](../mod-apache2/module.py) |
| Web: Moduli › Installabili, l'unico modo per installare i moduli (`GET /api/admin/module-catalog`, `POST /api/admin/module-catalog/{name}`) | `fGetCatalog`, `fInstallFromCatalog`; vista `fCatalogPanel` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| Web: **Aggiorna** su una riga di Moduli › Installati (lo stesso `GET`, riutilizzato dal browser per 10 minuti, e lo stesso `POST`) | `fCheckRepository`, `fUpdateNotice`, `fUpdate` → `fInstallFromCatalog` | [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js), [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| Web: **Disinstalla** (`DELETE /api/admin/modules/{name}`) | `fUninstallModule` → `fRemove` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `read_paths` di `module.json` | `manage.py read-paths`: le cartelle che localSIEM, come root, permette di leggere a `localsiem` (il comando di `fRootCommand`) | [backend/manage.py](../../localSIEM/backend/manage.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `manage.py modules` | `fMain` (`fModules`) | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py doctor [--json]` | `mDiscover`, `mSkipped`, `mDoctor` | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py read-paths` | `read_paths` di ogni manifest | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `/user/dashboard/modules/`; `/admin/dashboard/modules/` (302 verso `installed/`), `/admin/dashboard/modules/installed/`, `/admin/dashboard/modules/installable/` | `fUserTab` / `fAdminTab` / `fAdminModulesSection`; vista `LocalsiemViews.modules` | [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| `/admin/dashboard/modules/installed/apache2/` (il vecchio `/admin/dashboard/modules/apache2/` risponde con un 301 verso di esso) | `fAdminModule` (il 301: `fAdminModulesSection`); vista `LocalsiemViews.module` | stessi file |
| `GET /api/modules` | `fModules` (stato per chiunque abbia effettuato l'accesso) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `GET /api/admin/modules/apache2` | `fModule` (impostazioni, valori, sorgenti, diagnostica, regole) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2` | `fSaveModule` (`enabled`, `settings`, `rules`) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/doctor` | `fRunDoctor` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/reconfigure` (**Riconfigura**, localSIEM 2.2.0 o successivo) | `mRequirements` → `fRequirementChecks` | [mod-apache2/module.py](../mod-apache2/module.py), [mod-apache2/doctor.py](../mod-apache2/doctor.py) |
| `GET /api/events/{id}` | `fEvent` → `mDisplayRecord` | [backend/web/api_search.py](../../localSIEM/backend/web/api_search.py) |
| `"entry": "module:PrivescModule"` di `mod-privesc/module.json` | `PrivescModule` | [mod-privesc/module.py](../mod-privesc/module.py) |
| `mod-privesc/rules/*.yaml` | `RulesEngine` (nucleo) | [mod-privesc/rules/](../mod-privesc/rules/) |
| `/admin/dashboard/modules/installed/privesc/`, `GET`/`POST /api/admin/modules/privesc`, `.../privesc/doctor`, `.../privesc/reconfigure` | `fAdminModule`, `fModule`, `fSaveModule`, `fRunDoctor`, `mRequirements` → `fRequirementChecks` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [mod-privesc/doctor.py](../mod-privesc/doctor.py) |
| Record di audit delle regole del server (qualsiasi chiave) | `mAuditEvent` → `mAuditExec`, `mAuditUser`, `mAuditSyscall` | [mod-privesc/module.py](../mod-privesc/module.py) |

<a id="impact"></a>
## 6. Analisi di impatto

| Componente | Cosa viene influenzato se cambia |
|---|---|
| `module.json` `id` | Deve essere uguale al nome della cartella senza `mod-` (il nome della cartella installata) e a `vName`. È la chiave delle impostazioni (`modules.<id>`), dello stato (`<id>.doctor`) e il `module` di ogni evento: rinominarlo fa perdere le impostazioni salvate e divide la cronologia. |
| `module.json` `core` | Alzarlo sopra il localSIEM installato impedisce il caricamento del modulo (stato «Errore»); nel repository, Installabili mostra «Richiede localSIEM X o successivo» e Installati mostra la versione più recente senza **Aggiorna**. |
| `module.json` `entry` | Deve puntare a una sottoclasse di `Module`; un valore errato è un errore di caricamento. |
| `module.json` `default_enabled` | Attivato/disattivato nei server in cui l'amministratore non ha mai deciso (se alla prima installazione mancano i suoi requisiti, disattivato). |
| `module.json` `read_paths` | L'accesso in lettura che localSIEM dà come root (`manage.py read-paths`): una cartella mancante significa errori di permessi nella diagnostica e nello stato. Una modifica in una nuova versione fa sì che l'interfaccia web mostri di nuovo il comando per root dopo **Aggiorna** (`access_changed`). |
| `module.json` `install_requirements` | La finestra di dialogo Requisiti di Installabili (`fRequirementsBody` di `modules.js`). Uno errato (un sistema diverso da `debian` e `alpine`, un elenco vuoto o più di 20 comandi, un comando con un operatore della shell o un a capo) rende il modulo non valido (`fCheckInstallRequirements` del nucleo): non viene né installato né caricato. |
| `module.json` `setup_option` | Niente: il nucleo la ignora (nessun modulo ne ha una da apache2 1.3.0 e privesc 1.1.0). |
| Cartelle `mod-<name>/` con un `module.json` al primo livello del repository | Ciò che elenca il catalogo dell'interfaccia web, come modulo `<name>`: Installabili mostra quelli non ancora installati (uno che richiede un nucleo più recente come «Richiede localSIEM X o successivo», uno non valido come «Il modulo del repository non è valido»), e una `version` superiore a quella installata fa sì che Installati proponga **Aggiorna**. |
| `module.json` `settings` | Il form, la convalida e i valori predefiniti. Un nuovo valore predefinito si applica ai server che non hanno mai salvato quella chiave. I valori salvati non vengono migrati: una chiave rinominata perde il suo valore e un vecchio valore con un nuovo tipo arriva al modulo così come è stato salvato. |
| `locales/*.json` | Solo i testi dell'interfaccia web; un testo mancante ripiega su en-US, poi sulla chiave. |
| `parsers.py` (dict del record) | La correlazione (`correlation`, `fields.client_ip`, `fields.path`), la scheda della richiesta, l'indice full-text (`search`, `raw`), la salute delle righe non analizzate e la privacy. |
| `logformat.py` `dKnownFormats` | L'analisi di ogni log di accesso; `localsiem_combined` resta per i server che lo scrivono già (lo aggiungevano le versioni 1.2.0 e precedenti del modulo): non cambiarne la definizione. |
| `correlate.py` | Un evento per richiesta; il nucleo chiama `mAdd`, `mDue(pNow, pForce, pWatermark)` e `mPendingCount`, e reinserisce i record ancora in sospeso dopo un riavvio. Senza `UNIQUE_ID` abbina i record in base ai loro campi `client_ip`, `method`, `uri`, `status` e `path`: un parser che li scrive in modo diverso rompe l'abbinamento. L'attesa del record di audit (`mWaitsForAudit`) richiede il campo `modsecurity` delle righe dell'error.log e i record della sorgente `audit`. |
| `modsec.py` (categorie, etichette, intervalli) | I nomi delle regole degli avvisi (le statistiche del SOC raggruppano in base a essi: mantienili stabili), le chiavi di raggruppamento, le ricerche `category:`. |
| `ApacheModule.mBuildEvent` (dict dell'evento) | Le colonne della tabella degli eventi, i campi letti dalle regole YAML (`action`, `status`, `method`, `path`, `crs_matched`, `db_error`...), le ricerche e l'esportazione CSV. |
| `ApacheModule.mAssess` | Ciò che arriva al SOC e la sua gravità; i limiti di `GenericAlert` del nucleo (regola 300, descrizione 10 000 caratteri). |
| `severity.yaml` | La gravità di ogni rilevazione di ModSecurity; la gravità fa parte della chiave di raggruppamento, quindi una modifica avvia nuovi gruppi. |
| `rules/*.yaml` | L'`id` è la chiave delle sovrascritture (`rules.<id>`) e delle ricerche (`rule:localsiem:<id>`): mantienilo stabile. I campi devono esistere negli eventi; `{function: ...}` richiede `mRuleFunctions`. |
| `discovery.py` | Quali log vengono letti; `fSourceKey` è la chiave delle posizioni salvate (una nuova chiave fa del file una nuova sorgente, senza la sua posizione salvata); le DocumentRoot della regola delle web shell; la diagnostica. |
| `doctor.py` | La diagnostica dell'interfaccia web e di `manage.py` e i suggerimenti mostrati al cliente. Solo i controlli su ciò che non è un log (ModSecurity, il CRS, `SecRuleEngine`, `mod_unique_id`, permessi) possono avere un `fix`; i controlli sui log si limitano a descriverli. |
| `mRequirements` / `fRequirementChecks` | Se il modulo può essere attivato, lo stato «Disattivato» dopo una prima installazione senza Apache o ModSecurity, i requisiti che mostra l'interfaccia web e **Riconfigura**. Vengono eseguiti nell'interfaccia web e in `manage.py` senza archiviazione e analizzano la configurazione di Apache a ogni chiamata: tienili lontani dall'archiviazione e da qualsiasi cosa lenta, e mantieni stabili gli id `apache_config` e `modsecurity`. |
| privesc: colonne e campi degli eventi (`mBuildEvent`, `mAnalyzeCommand`) | Le regole YAML li confrontano per nome (`recon_burst`, `suid_escape`, `root_without_door`, `sensitive_group`, `writer_allowed`, `ptrace_attach`, `parent_interpreter`, `account_type`, `real_uid`, `argc_zero`...): un campo rinominato disattiva silenziosamente le regole che lo usano. `vhost` è l'utente: ne dipendono la chiave di raggruppamento degli avvisi e le ricerche `vhost:`. |
| privesc: `fReconToken` | Cosa conta come ricognizione e come si distinguono i comandi distinti: cambiare un token cambia la velocità con cui una sessione raggiunge le soglie. |
| privesc: `SessionTracker` e le porte (`sDoors`) | `root_without_door`: una porta mancante dall'elenco rende critiche le sessioni di root legittime; una in più nasconde gli exploit del kernel. `mExport`/`mImport` è il formato di `privesc.sessions`. |
| privesc: `parsers.py` | I campi dei record (`args`, `command`, `kind`, `uid`/`euid` di snoopy), il mascheramento delle password e il testo grezzo dei record di audit; i formati di snoopy che legge (il modulo non modifica mai `snoopy.ini`). |
| privesc: classificazione dei record di audit (`lSensitivePaths`, `dSyscallTables`, `sChangeSyscalls`, `dOpenFlagArgument`, `dChmodModeArgument`, `sDeniedSyscalls`, `dKeyHints`) | Cosa diventa `file`, `chmod`, `kmod`, `ptrace` e `denied`, e quindi le regole sensitive-file, persistence-file, monitoring-changed, suid-set, kernel-module, ptrace, denied-burst e sensitive-denied; un numero di syscall errato classifica male i record di quell'architettura. |
| privesc: `surface.py` | Il costo della scansione (thread, limiti) e ciò che segnalano la diagnostica e `mSurfaceResult`; `privesc.surface` è il suo riferimento. |
| privesc: `mRequirements` / `fRequirementChecks` | Se il modulo può essere attivato (qualsiasi sorgente leggibile), lo stato «Disattivato» dopo una prima installazione i cui log `localsiem` non può ancora leggere, e **Riconfigura**; chiamati senza archiviazione dall'interfaccia web e da `manage.py`: mantienili veloci e senza root. Mantieni gli id `command_source`, `audit_log` e `syslog`. |
| Interfaccia del nucleo (`backend/core/module.py`, `registry.py` di localSIEM) | Ogni modulo: una firma di hook cambiata, una nuova chiave obbligatoria del manifest o un nuovo contratto di record ed eventi li rompe; alza `core` nel loro `module.json` quando richiedono il nuovo localSIEM. |

<a id="extensions"></a>
## 7. Punti di estensione

### Come scrivere un nuovo modulo

1. **Cartella**: crea `mod-<name>/` nella radice di questo progetto; `<name>`, il nome del modulo, corrisponde a `[a-z][a-z0-9_]{1,31}`. Il prefisso `mod-` è solo per la cartella: `module.json`, la classe, le opzioni e i testi usano `<name>`. Nessun `__init__.py`.
2. **`module.json`**, per esempio:

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

3. **Testi**: `locales/<language>.json` per ognuna delle 15 lingue di localSIEM con `name`, `summary` e l'etichetta e l'aiuto di ogni impostazione. Le note sui requisiti vanno in `install_requirements` (`note`, per ogni sistema, e `debian` e `alpine`), mostrate nella finestra di dialogo Requisiti.
4. **Codice**: `module.py` con una sottoclasse di `Module` il cui `vName` è l'id. Deve implementare `mParse`, `mCreateCorrelator` e `mBuildEvent`, e di solito `mDiscover`; gli altri hook sono opzionali (sezione 1). Importa i suoi file in modo relativo e il nucleo come `backend.core...`. I due moduli di questo repository sono esempi completi ([mod-apache2/module.py](../mod-apache2/module.py), [mod-privesc/module.py](../mod-privesc/module.py)); uno schema minimo:

   ```python
   from backend.core.module import Module


   class OneEventCorrelator:
     # Ogni record è un evento a sé, senza attese.

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

5. **Azione intrapresa**: decidi cosa significa «già risolto» per il servizio (per esempio, un IP già bannato) e imposta `action` a `blocked` in quel caso; aggiungi una rilevazione solo agli eventi senza un'azione intrapresa.
6. **Regole**: file YAML in `mod-<name>/rules/`, restituiti da `mRulesPath`, e le funzioni che chiamano in `mRuleFunctions`.
7. **Requisiti**: se il modulo ha bisogno di software sul server (come apache2 ha bisogno di Apache e ModSecurity 2), restituisci da `mRequirements()` un controllo per requisito (il formato di `fCheck`: `status` `ok` o `error`, e in `fix` il comando che lo installa) e non installare mai quel software dal modulo: senza i suoi requisiti il modulo viene installato disattivato. Viene eseguito senza archiviazione, anche nell'interfaccia web e in `manage.py`. Dichiara anche, in `install_requirements` di `module.json`, i comandi che installano quel software su Debian e su Alpine (un comando per riga, senza operatori della shell): l'interfaccia web li mostra in Moduli › Installabili › Requisiti, così come sono e preceduti da `sudo`, prima che il modulo venga installato.
8. **Installazione**: pubblicalo in questo repository (branch `main`); compare in Moduli › Installabili dell'interfaccia web di localSIEM finché non è installato, e **Installa** copia la cartella `mod-<name>/` in `/opt/localsiem/modules/<name>/` e riavvia il collettore. L'accesso in lettura ai suoi `read_paths` richiede root: l'interfaccia web mostra il comando (`manage.py setup-modules`). Un modulo non ha opzioni di configurazione: non installa mai nulla né modifica nulla fuori da `/opt/localsiem`, e non scrive mai nei log del cliente, né li ruota o li elimina, né ne modifica il formato; se un server scrive i suoi log a modo suo, il modulo vi si adatta, e ciò che manca al server è un requisito. Per pubblicare una nuova versione, alza `version`: Moduli › Installati mostra la notifica e **Aggiorna**, che mantiene le impostazioni e lo stato attivato/disattivato del modulo e mostra di nuovo il comando per root solo se `read_paths` è cambiato.
9. **Documentazione**: aggiorna il README, questo CODE e il MANUAL nelle 15 lingue.

### Come aggiungere una regola al modulo apache2

Crea un file YAML in [mod-apache2/rules/](../mod-apache2/rules/) (ogni chiave e operatore è descritto all'inizio di [backend/core/rules.py](../../localSIEM/backend/core/rules.py)): `id`, `name`, `category`, `type`, `severity`, `kind` (`match`, `threshold` o `sequence`), le condizioni (`when`, o `first`/`first_threshold`/`then`), `by`, `window`, `threshold`, `lists`, `description` e `search`. I campi vengono cercati prima nelle colonne dell'evento e poi in `fields`. Compare nella tabella delle regole della pagina del modulo e viene caricata dal collettore una volta installata la nuova versione del modulo: alza `version` in `module.json`, pubblicalo e premi **Aggiorna** in Moduli › Installati.

### Come aggiungere un'impostazione al modulo apache2

Aggiungila a `settings` di [mod-apache2/module.json](../mod-apache2/module.json) con il suo tipo e il suo valore predefinito, aggiungi la sua `label` e il suo `help` ai quattro file di [mod-apache2/locales/](../mod-apache2/locales/), e leggila con `self.mModuleSettings().get("<key>")`. Il form, la convalida e la ricarica li fornisce il nucleo.

### Come aggiungere un controllo della diagnostica o cambiare una gravità

Un controllo è un `fCheck(id, status, title, detail, fix)` in `fRunDoctor` ([mod-apache2/doctor.py](../mod-apache2/doctor.py)); mantieni stabile l'`id` e metti in `fix` il frammento o il comando esatto, solo per i requisiti che non sono log: un controllo sui log del cliente si limita a descriverli e a dire cosa localSIEM può o non può leggerne, senza `fix`. Le gravità delle rilevazioni di ModSecurity si cambiano in [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) (`low`, `medium`, `high`, `critical`).

### Come aggiungere una regola al modulo privesc

Crea un file YAML in [mod-privesc/rules/](../mod-privesc/rules/), come quelli di Apache. Confronta le colonne (`method`, `uri`, `path`, `vhost`, `action`) e i campi degli eventi (`sensitive_group`, `account_type`, `real_uid`, `recon`, `service_account`, `file`...), mai la chiave di una regola di audit; aggiungi `ignored: {not: true}` perché gli utenti ignorati non la facciano mai scattare, e `action: none` quando conta solo ciò che è stato realmente eseguito. Se la condizione richiede stato o logica (una sequenza della stessa sessione, un controllo di un file), calcola un flag in `PrivescModule.mAnalyzeCommand` (ogni sorgente) o in `mAuditExec`/`mAuditSyscall`/`mSyslogEvent` (una sorgente) e confrontalo dalla regola.

### Come aggiungere un comando di ricognizione, uno strumento o un exploit al modulo privesc

- Ricognizione: aggiungi il programma a `sReconSimple`, o un ramo a `fReconToken` che restituisca un token per tipo di domanda ([mod-privesc/commands.py](../mod-privesc/commands.py)). Un token che cambia con ogni argomento gonfia i conteggi.
- Strumenti ed exploit: aggiungi un'espressione regolare all'elenco di [rules/known-tool.yaml](../mod-privesc/rules/known-tool.yaml) o di [rules/exploit.yaml](../mod-privesc/rules/exploit.yaml) (senza distinzione tra maiuscole e minuscole, confrontata con la riga di comando); l'amministratore può aggiungerle anche dalle impostazioni (`rules.<id>.lists`).

### Come aggiungere una sorgente o un tipo di record di audit al modulo privesc

- Un percorso sensibile: aggiungilo a `lSensitivePaths` di [mod-privesc/module.py](../mod-privesc/module.py) con il suo gruppo (o un nuovo gruppo e una regola che confronti `sensitive_group`). Un tipo di chiamata di sistema: aggiungi il suo nome agli insiemi di `mAuditSyscall` e il suo numero a ogni tabella di `dSyscallTables`. Non dipendere mai dalla chiave di una regola di audit (al massimo aggiungila a `dKeyHints`) e non installare mai regole di audit: il server registra ciò che decide il suo amministratore, e la diagnostica lo descrive (`dAuditKinds` di [doctor.py](../mod-privesc/doctor.py)).
- Una sorgente: restituiscila da `fDiscoverSources` con un nuovo `kind`, analizzala in `mParse` e costruiscine gli eventi in `mBuildEvent` con le stesse colonne e gli stessi campi delle altre, così le regole funzionano senza modifiche.
