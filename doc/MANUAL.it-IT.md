# Manuale utente di localSIEM-modules

Questo MANUALE è disponibile anche in:\
[de-DE](MANUAL.de-DE.md), [en-GB](MANUAL.en-GB.md), [en-US](MANUAL.md), [es-AR](MANUAL.es-AR.md), [es-ES](MANUAL.es-ES.md), [fr-FR](MANUAL.fr-FR.md), [he-IL](MANUAL.he-IL.md), [hi-IN](MANUAL.hi-IN.md), it-IT, [ja-JP](MANUAL.ja-JP.md), [ko-KR](MANUAL.ko-KR.md), [pt-BR](MANUAL.pt-BR.md), [pt-PT](MANUAL.pt-PT.md), [ru-RU](MANUAL.ru-RU.md), [zh-CN](MANUAL.zh-CN.md)

[Installazione](README.it-IT.md) · [Riferimento del codice](CODE.it-IT.md) · [Manuale di localSIEM](../../localSIEM/doc/MANUAL.it-IT.md)

## Indice

1. [Cosa sono i moduli](#what)
2. [Installare e aggiornare i moduli](#installation)
3. [La pagina dei Moduli](#modules-page)
4. [La pagina del modulo Apache](#apache-page)
5. [Impostazioni del modulo Apache](#settings)
6. [Cosa invia al SOC il modulo Apache](#soc)
7. [Requisiti di Apache e ModSecurity: la diagnostica](#doctor)
8. [I log del cliente non vengono mai toccati](#client-logs)
9. [Regole del modulo Apache](#rules)
10. [Avvertenze di salute del modulo Apache](#health)
11. [Il modulo di escalation dei privilegi](#privesc)
12. [Impostazioni del modulo di escalation dei privilegi](#privesc-settings)
13. [Cosa invia al SOC il modulo di escalation dei privilegi: le sue regole](#privesc-rules)
14. [Requisiti del modulo di escalation dei privilegi: la diagnostica](#privesc-doctor)
15. [Server aggiornati dalla versione 1.0.0 del modulo di escalation dei privilegi](#privesc-legacy)
16. [Superficie di attacco e avvertenze di salute del modulo di escalation dei privilegi](#privesc-health)
17. [Riga di comando](#cli)

<a id="what"></a>
## 1. Cosa sono i moduli

localSIEM è composto da un **nucleo** e da **moduli**. Il nucleo salva gli eventi, li ricerca, esegue le regole, raggruppa gli avvisi, li invia al SOC e sorveglia la propria salute. Ogni modulo aggiunge un servizio del server: ne trova i log, li legge, li trasforma in eventi, decide cosa è già risolto, porta le sue regole e verifica i requisiti di quel servizio.

I moduli di questo progetto si installano in `/opt/localsiem/modules/<name>/`. Oggi ce ne sono due: **apache2** («Apache + ModSecurity», sezioni da 4 a 10) e **privesc** («Escalation dei privilegi», sezioni da 11 a 16). localSIEM non ha moduli propri: la pagina dei Moduli elenca solo i moduli installati da questo repository.

<a id="installation"></a>
## 2. Installare e aggiornare i moduli

Prima bisogna installare localSIEM; il suo installer installa solo il nucleo, mai un modulo. I moduli di questo progetto si installano **solo dall'interfaccia web di localSIEM**: questo progetto non ha un installer proprio. L'interfaccia web li scarica dal repository `https://github.com/PYMEHackers/localSIEM-modules` (branch `main`). I moduli richiedono localSIEM 2.2.0 o successivo.

**Installare.** Come amministratore, apri Moduli › **Installabili** (sezione 3), premi **Controlla il repository**, guarda **Requisiti** (ciò di cui il modulo ha bisogno sul server e i comandi che lo installano, da eseguire prima di installarlo) e poi premi **Installa** sul modulo. A quel punto localSIEM:

1. scarica il repository e lo estrae in modo sicuro (niente fuori dalla sua cartella, limiti di dimensione);
2. copia la cartella del modulo (`mod-<name>/` nel repository) in `/opt/localsiem/modules/<name>/`, senza `tests/` (e senza le cache di Python); un modulo installato di nuovo recupera le impostazioni che aveva;
3. riavvia il collettore, che carica il modulo entro pochi secondi;
4. toglie il modulo dall'elenco e apre la finestra di dialogo «<module> installato» con il comando da eseguire come root sul server (`manage.py setup-modules`) e un pulsante **Copia**: dà all'utente `localsiem` l'accesso in lettura alle cartelle elencate in `read_paths` del suo `module.json` (`/var/log/apache2` per il modulo apache2, `/var/log/audit` per il modulo privesc), anche ai file delle prossime rotazioni, e riavvia localSIEM. Quell'accesso in lettura è tutto ciò che serve a un modulo: i moduli non hanno opzioni di configurazione e non modificano mai il server (sezioni 8 e 11). Finché non viene eseguito, il modulo può mostrare «Errore»: i suoi log non si possono ancora leggere. La finestra di dialogo si chiude con «Chiudi» o con «Vedi i moduli installati», che apre Installati.

**Aggiornare.** Quando si apre Moduli › **Installati**, l'interfaccia web controlla il repository, e un modulo che lì ha una versione più recente mostra una notifica con **Aggiorna** (sezione 3). Dopo la tua conferma, localSIEM scarica la nuova versione e la mette al posto di quella installata (passi da 1 a 3), ne mantiene le impostazioni e lascia il modulo attivato o disattivato com'era. Il comando per root viene mostrato di nuovo solo se la nuova versione legge altri log (`read_paths`); altrimenti non c'è nulla da eseguire. Un aggiornamento di localSIEM mantiene i moduli installati e il loro accesso in lettura.

**Reinstallare.** L'interfaccia web non reinstalla un modulo né ne installa una versione precedente: per reinstallare un modulo, premi **Disinstalla** (sezione 3) e installalo di nuovo da **Installabili**; le sue impostazioni vengono mantenute.

**Installare un modulo non installa mai il software che sorveglia.** Il modulo apache2 non installa né Apache né ModSecurity, e il modulo privesc non installa né auditd, né un demone syslog, né snoopy. Se, alla sua prima installazione, al server manca ciò che serve al modulo (Apache e ModSecurity per apache2; per privesc, una sorgente che `localsiem` possa leggere, sezione 14), il modulo viene installato **disattivato**: la finestra di dialogo elenca ciò che manca al posto del comando, e il modulo non si può attivare finché **Riconfigura** non lo trova (sezione 4). Un aggiornamento lascia il modulo attivato o disattivato com'era.

<a id="modules-page"></a>
## 3. La pagina dei Moduli

Gli amministratori aprono **Amministrazione › Moduli**, che ha due sezioni, ognuna al proprio indirizzo: **Installati** (`/admin/dashboard/modules/installed/`), che si apre per impostazione predefinita (`/admin/dashboard/modules/` porta lì), e **Installabili** (`/admin/dashboard/modules/installable/`). Gli analisti vedono **Moduli** nella loro dashboard (`/user/dashboard/modules/`): solo l'elenco dei moduli installati, in sola lettura, senza sezioni.

**Installati** mostra una riga per ogni modulo installato, a tutta larghezza: il suo nome, il suo id, la sua versione, un'etichetta di stato, il suo riepilogo e, sotto, i motivi di quello stato. L'elenco si aggiorna da solo ogni 10 secondi. Senza moduli installati indica «Installa i moduli dalla scheda Installabili.» (agli analisti: «Nessun modulo installato. Li installa un amministratore in Moduli › Installabili.»).

| Stato | Significato |
|---|---|
| **Attivo e funzionante** | Attivato, caricato dal collettore e in lettura delle sue sorgenti. Le avvertenze della diagnostica vengono elencate come note ma non cambiano lo stato. |
| **Attivo, con avvertenze** | Attivato, ma non sono stati trovati log da leggere, una sorgente non esiste ancora, oppure il modulo è stato installato dopo l'avvio del collettore (riavvia il servizio `localsiem`). |
| **Errore** | Il modulo non si carica (viene mostrato l'errore), la sua diagnostica segnala un errore, oppure una sorgente non può essere letta (permessi dell'utente `localsiem`). |
| **Disattivato** | Disattivato, oppure installato senza i suoi requisiti (per apache2: manca Apache o ModSecurity; per privesc: `localsiem` non può leggere né il log di auditd né syslog), come indica il suo motivo. |
| **Applicazione della modifica…** | Appena attivato o disattivato: il collettore sta applicando la modifica. |
| **Sconosciuto** | Il collettore (servizio `localsiem`) non è in esecuzione, quindi non si sta leggendo nulla. |

Quando il modulo non è disattivato, la riga mostra anche: **Sorgenti in lettura** (lette / trovate), **Righe (1 h)**, **Ultimi dati**, **Eventi (24 h)**, **Bloccati (24 h)** e i conteggi della **Diagnostica** («n OK · n avvertenze · n errori»).

Gli amministratori hanno inoltre, su ogni riga:

- **L'interruttore** di ogni modulo. Disattivare un modulo chiede una conferma: localSIEM smette di leggerne i log e di inviarne gli avvisi finché non viene riattivato; ciò che è già salvato resta. Attivarlo avvia subito la lettura. Finché manca un requisito del modulo, l'interruttore è bloccato («Disattivato: requisiti mancanti»): **Riconfigura** (sezione 4) lo sblocca non appena li trova.
- **Configura**, che apre la pagina del modulo, `/admin/dashboard/modules/installed/<name>/` (sezione 4); il vecchio indirizzo `/admin/dashboard/modules/<name>/` ti porta lì.
- **Disinstalla**, anche su un modulo che non si carica (e nella pagina del modulo). Dopo la tua conferma, localSIEM elimina `/opt/localsiem/modules/<name>/` e riavvia il collettore senza di esso: smette di leggerne i log e di inviarne gli avvisi. Gli eventi già salvati restano ricercabili, e le sue impostazioni restano, nel caso tu lo installi di nuovo. L'accesso in lettura ai suoi log che root ha dato a `localsiem` non viene revocato.
- **Aggiorna**, quando il repository ha una versione più recente del modulo. Ogni volta che si apre Installati, l'interfaccia web controlla il repository («Ricerca di versioni più recenti nel repository…»; il browser riutilizza la risposta per 10 minuti), e una riga il cui modulo ha una versione più recente mostra «Il repository ha la versione X (quella installata è la Y).» con il pulsante **Aggiorna**. Dopo la tua conferma, localSIEM installa la nuova versione (sezione 2), ne mantiene le impostazioni, lascia il modulo attivato o disattivato com'era e riavvia il collettore; una finestra di dialogo mostra il comando per root solo se la nuova versione legge altri log. Se la nuova versione richiede un localSIEM più recente, la notifica indica «Il repository ha la versione X, ma richiede localSIEM Z o successivo: aggiorna localSIEM per installarla.» e non ha alcun pulsante.

**Installabili** (solo amministratori) contiene la scheda «Moduli installabili». **Controlla il repository** scarica il repository ed elenca i moduli non ancora installati su questo server, ognuno con il suo nome, id, versione e riepilogo e un pulsante o una nota:

| Pulsante o nota | Significato |
|---|---|
| **Requisiti** | Mostra ciò di cui il modulo ha bisogno sul server e i comandi che lo installano, come root e con sudo (vedi sotto) |
| **Installa** | Installa il modulo (sezione 2) |
| «Richiede localSIEM X o successivo» | Non si può installare: aggiorna prima localSIEM |
| «Il modulo del repository non è valido» | Non si può installare |

I moduli già installati non compaiono mai qui: si aggiornano da Installati. Se tutti i moduli del repository sono installati, la scheda indica «Tutti i moduli del repository sono già installati.». Dopo l'installazione, la finestra di dialogo «<module> installato» mostra il comando da eseguire come root perché `localsiem` possa leggere i log del modulo (sezione 2), con un pulsante **Copia**; finché non viene eseguito, il modulo può mostrare «Errore»: i suoi log non si possono ancora leggere. Se al server manca ciò che serve al modulo, la finestra di dialogo elenca invece ciò che manca, con il suggerimento di aprire il modulo in Installati (**Configura**) e premere **Riconfigura** quando è presente.

**Requisiti** apre «<module>: requisiti»: ciò di cui il modulo ha bisogno sul server e i comandi che lo installano sul sistema di questo server («Questo server: …»), dichiarati dal modulo (`install_requirements` del suo `module.json`), due volte, ognuna con **Copia**: **Come root** e **Con sudo** (gli stessi comandi preceduti da `sudo`). Eseguili sul server prima di installare il modulo: installarlo non installa mai quel software, e localSIEM non li esegue mai. Per il modulo apache2, su Debian: `apt-get -y update`, `apt-get -y install apache2 libapache2-mod-security2 modsecurity-crs`, `a2enmod security2 unique_id`, `cp --update=none /etc/modsecurity/modsecurity.conf-recommended /etc/modsecurity/modsecurity.conf` (crea la configurazione di ModSecurity, DetectionOnly, solo quando non ce n'è una) e `systemctl restart apache2`; su Alpine, solo Apache (`apk add apache2`, poi `rc-update` e `rc-service` per avviarlo), perché Alpine non ha un pacchetto di ModSecurity 2: finché ModSecurity non viene compilato dai sorgenti e caricato, il modulo resta disattivato. Per il modulo privesc: `apt-get -y install auditd rsyslog` su Debian, e `apk add audit` con auditd avviato al boot su Alpine; basta una qualsiasi sorgente leggibile, e in un container auditd non può funzionare.

<a id="apache-page"></a>
## 4. La pagina del modulo Apache

`/admin/dashboard/modules/installed/apache2/` (solo amministratori; il vecchio `/admin/dashboard/modules/apache2/` ti porta lì) ha cinque parti:

1. **Intestazione**: nome, id, versione, il percorso di installazione (`/opt/localsiem/modules/apache2`), l'interruttore, lo stato con i suoi motivi e i numeri della sezione 3. **Torna ai moduli installati** riporta a Installati; **Rileva di nuovo ed esegui la diagnostica** rilegge subito la configurazione di Apache e aggiorna la diagnostica; **Riconfigura** cerca di nuovo Apache e ModSecurity (vedi sotto); **Disinstalla** disinstalla il modulo (sezione 3) e riporta a Installati.
2. **Impostazioni**: il form della sezione 5. **Salva le impostazioni** verifica ogni valore e, se uno è errato, indica quale («Valore non valido: …»).
3. **Sorgenti**: ogni log in lettura, con **Tipo** (`access`, `error`, `audit`), **Percorso**, **Vhost**, **Righe (1 h)**, **Non analizzate (1 h)**, **Ultimi dati** (per esempio `2026/10/29@13:59:59.723`) e **Stato** (errore se non può essere letto, avvertenza se non esiste ancora). Sotto, i log trovati ma non letti, con il motivo: «log tramite pipe, non supportato», «coperto da un GlobalLog che scrive tutti i vhost» o «il suo formato non contiene dati: ogni riga è lo stesso testo (un nome di LogFormat non definito)».
4. **Diagnostica**: i controlli della sezione 7, con l'ora in cui sono stati eseguiti. Ogni requisito mancante (ModSecurity, il CRS, `SecRuleEngine`, `mod_unique_id`, l'accesso in lettura di `localsiem`) è accompagnato dal frammento o dal comando che lo risolve e da un pulsante **Copia**. I controlli sui log si limitano a descriverli e a dire cosa localSIEM può leggerne, senza correzione: i log del cliente non vengono mai modificati (sezione 8).
5. **Regole**: le regole della sezione 9, ognuna con **Attiva**, **Regola** (nome, id e categoria), **Gravità**, **Soglia** e **Finestra (s)**, e **Salva le regole**.

**Requisiti e Riconfigura.** Finché manca Apache o ModSecurity, il modulo è disattivato e l'intestazione elenca ciò che manca, con il comando che lo installa. **Riconfigura** (anche quando il modulo è disattivato) li cerca di nuovo con le impostazioni salvate; se Apache si trova in un percorso non standard, imposta prima **File di configurazione di Apache** (sezione 5). Quando li trova entrambi, sblocca l'interruttore —attivare il modulo è una tua decisione— e mostra il comando da eseguire come root perché `localsiem` possa leggere i log di Apache creati dopo l'installazione del modulo. Un modulo attivato che perde Apache o ModSecurity resta attivato: lo segnalano la diagnostica e le avvertenze di salute (sezione 10).

**Ogni modifica si applica subito, senza riavviare nulla**: l'interfaccia web la salva e la comunica al collettore, che ricarica le sue impostazioni, rileva di nuovo le sorgenti ed esegue la diagnostica. Se il collettore non risponde, l'interfaccia web lo indica e la modifica viene applicata all'avvio del collettore.

<a id="settings"></a>
## 5. Impostazioni del modulo Apache

| Impostazione | Predefinito | Cosa fa |
|---|---|---|
| **Solo le sorgenti qui sotto** | disattivato | Non rilevare i log dalla configurazione di Apache: leggere solo le sorgenti aggiunte a mano. |
| **Sorgenti aggiunte a mano** | nessuna | Log da leggere oltre a quelli rilevati (o al loro posto, con l'opzione qui sopra). Fino a 50. |
| **File di configurazione di Apache** | vuoto | Vuoto: viene individuato automaticamente (`/etc/apache2/apache2.conf` su Debian, `/etc/apache2/httpd.conf` su Alpine; viene riconosciuto anche `/etc/httpd/conf/httpd.conf`). Un percorso assoluto usa invece quel file, se esiste. |
| **Intervallo di rilevamento (secondi)** | 3600 | Ogni quanto si rilegge la configurazione di Apache per trovare nuovi vhost e log (da 60 a 86400). |
| **Soglia di blocco di ModSecurity** | 0 | 0: letta dalla configurazione del CRS (`tx.inbound_anomaly_score_threshold` in `crs-setup.conf`), 5 se non è presente. Serve a distinguere una corrispondenza sopra la soglia di blocco da una sotto quando i messaggi di ModSecurity non indicano essi stessi la soglia (da 0 a 1000). |
| **Giorni di apprendimento per i nuovi file PHP** | 3 | Durante i primi giorni dopo il primo avvio del modulo, un file PHP mai visto prima non viene segnalato come nuovo dalla regola `apache-webshell` (da 0 a 365). Un file creato o modificato nella sua DocumentRoot nell'ultimo giorno conta sempre come nuovo. |

Ogni **sorgente aggiunta a mano** ha questi campi (* obbligatorio):

| Campo | Uso |
|---|---|
| **Tipo** * | `access.log`, `error.log` o `Log di audit di ModSecurity` |
| **Percorso** * | Percorso assoluto del file |
| **Vhost** | Vhost delle righe, per i log le cui righe non lo indicano |
| **LogFormat** | Per i log di accesso: un nome (`localsiem_combined`, `combined`, `vhost_combined`, `common`, `combinedio`, o uno definito nella configurazione di Apache) o il formato stesso. Vuoto: si provano i formati abituali. |
| **Tipo di log di audit** | `Seriale (un solo file)` o `Concorrente (un file per richiesta)` |
| **Cartella di archiviazione dell'audit** | Per il tipo concorrente: la cartella di `SecAuditLogStorageDir` |

Un file viene letto una sola volta, anche se è sia rilevato sia aggiunto a mano. Una sorgente che compare mentre localSIEM è in esecuzione viene letta dal suo inizio se è di 5 MB o meno, e dalla sua fine altrimenti.

Anche due impostazioni di **Amministrazione › Impostazioni** di localSIEM agiscono su questo modulo: la **finestra di correlazione** (5 secondi: quanto si attendono i tre record di una richiesta) e la **gravità sotto la soglia di blocco** (`low`). Una richiesta segnalata da ModSecurity attende anche il suo record di audit, che ModSecurity scrive quando la richiesta termina, fino a 2 minuti: così una richiesta lenta non viene divisa in due eventi.

<a id="soc"></a>
## 6. Cosa invia al SOC il modulo Apache

Per ogni richiesta il modulo unisce la riga di accesso, le righe di errore e il record di audit con lo stesso `UNIQUE_ID`. I log di accesso che Apache scrive per impostazione predefinita (`combined`, `vhost_combined`, `common`) non hanno `UNIQUE_ID`: in quel caso ogni riga di accesso viene unita al record di audit e alle righe di errore della sua stessa richiesta tramite IP del client, metodo, URI, stato e ora (±2 secondi), anche quando la stessa richiesta si ripete nello stesso secondo, e l'evento viene marcato come «correlazione debole». Il vhost proviene da `%v` o, se il formato non lo contiene, dall'header Host e dalla porta del record di audit, scelto nello stesso modo in cui lo sceglie Apache; l'ora prende i microsecondi del record di audit. Poi decide se è già stato fatto qualcosa al riguardo («azione intrapresa»), leggendo prima il log di audit (`Action: Intercepted (phase N)`), poi l'error.log (`Access denied with code NNN (phase N)`). Un 403 senza alcuna traccia di ModSecurity non viene considerato un blocco: viene marcato come dubbio.

| Situazione | Va al SOC? |
|---|---|
| Bloccata da ModSecurity nelle fasi 1-2 (l'applicazione non l'ha mai ricevuta) | **No.** Resta in localSIEM, ricercabile (`action:blocked`), e viene contata nel contesto del prossimo avviso di quell'IP. |
| Bloccata nelle fasi 3-4 (l'applicazione l'aveva già eseguita) | Sì |
| Corrispondenze di regole con il motore in `DetectionOnly` | Sì |
| Corrispondenze di regole sotto la soglia di blocco | Sì |
| Segnali delle regole della sezione 9 | Sì |

Gravità degli avvisi generati dalle corrispondenze di ModSecurity (file `severity.yaml` del modulo):

| Situazione | Gravità |
|---|---|
| Corrispondenze non bloccate, risposta 3xx, 4xx o 5xx | media |
| Corrispondenze non bloccate, risposta 2xx | alta |
| Bloccata nelle fasi 3-4 | alta |
| Segni di successo: una regola in uscita (950-955) ha trovato corrispondenza e non è stato bloccato nulla, oppure un errore del database è seguito alla richiesta | critica |
| Sotto la soglia di blocco (spesso un falso positivo dell'applicazione stessa) | bassa (la gravità sotto la soglia di blocco di Amministrazione › Impostazioni) |

Ogni avviso ha un nome stabile (per esempio «Apache/ModSecurity: SQL injection not blocked (CRS 942)»), una descrizione che termina con la query da incollare nella ricerca di localSIEM (per esempio `ip:203.0.113.7 category:sqli`), e dei dettagli: vhost, IP del client, metodo, URI (mascherato), risposta, user agent e i dati di ModSecurity (motore, azione, fase, punteggio di anomalia, soglia, regole e dati corrispondenti). Quando parte, l'avviso porta anche il contesto dell'IP: richieste e richieste bloccate dell'ultima ora, le regole che l'hanno bloccata e la prima volta in cui è stato visto.

Password, cookie, header `Authorization` e token vengono mascherati prima che venga salvato qualsiasi cosa, anche dentro i corpi delle richieste, e i corpi delle richieste non viaggiano mai verso il SOC. Il corpo della risposta (parte E) e il testo completo delle regole eseguite (parte K) del log di audit non vengono mai conservati.

<a id="doctor"></a>
## 7. Requisiti di Apache e ModSecurity: la diagnostica

La diagnostica del modulo apache2 legge la configurazione di Apache (senza modificarla) e verifica ogni requisito. Viene eseguita all'avvio del collettore, dopo ogni modifica delle impostazioni, a ogni rilevamento, con **Rileva di nuovo ed esegui la diagnostica** e con `manage.py doctor` (sezione 17), solo mentre il modulo è attivato: mentre è disattivato perché manca Apache o ModSecurity, la pagina del modulo mostra invece quei requisiti (sezione 4). Stati: OK, avvertenza (funziona con dei limiti), errore (va corretto) e info (conta solo in alcune situazioni).

| Controllo | Corretto quando | Altrimenti |
|---|---|---|
| Configurazione di Apache | `apache2.conf` o `httpd.conf` (o il file configurato) viene trovato e letto | Errore: aggiungi le sorgenti a mano (sezione 5). Le parti che non si possono leggere vengono elencate come avvertenze. |
| ModSecurity | `mod_security2` (ModSecurity 2) è caricato | Errore. Debian: `apt-get install libapache2-mod-security2 modsecurity-crs && a2enmod security2`. Alpine non ha un pacchetto: compila mod_security2 2.9 dai sorgenti. ModSecurity 3 (libmodsecurity) non è supportato. |
| OWASP CRS | I file del CRS sono inclusi (la diagnostica mostra quanti e la soglia di anomalia) | Errore: `apt-get install modsecurity-crs`, oppure includi `crs-setup.conf` e `rules/*.conf` dopo ModSecurity |
| SecRuleEngine | `On` (le richieste sopra la soglia vengono bloccate nella fase 2 e restano in localSIEM) o `DetectionOnly` (non viene bloccato nulla: ogni corrispondenza va al SOC) | Errore se `Off`; avvertenza se è `Off` tranne in alcuni vhost, se manca (in quel caso ModSecurity usa `Off` per impostazione predefinita) o se alcuni vhost lo impostano a `Off` |
| mod_unique_id | Caricato: ModSecurity funziona e le tre sorgenti di una richiesta vengono unite tramite `UNIQUE_ID` | Errore se ModSecurity è caricato: senza di esso ModSecurity 2 non ispeziona nulla (Alpine non lo carica); altrimenti avvertenza (correlazione debole). Debian: `a2enmod unique_id`; Alpine: `LoadModule unique_id_module modules/mod_unique_id.so` |
| Formato del log di accesso | I log di accesso hanno IP del client, ora, riga della richiesta e stato, come i formati che Apache scrive per impostazione predefinita (OK, «Access logs in the format Apache writes»): ogni riga viene unita ai record di ModSecurity della sua richiesta tramite IP del client, metodo, URI, stato e ora. Con millisecondi, vhost e `UNIQUE_ID` nel formato (per esempio `localsiem_combined`, sui server che lo scrivono già), vengono uniti tramite `UNIQUE_ID` (OK, «Access log with milliseconds, vhost, duration and UNIQUE_ID») | Info, senza correzione, se a un log di accesso manca uno dei quattro: localSIEM lo legge così com'è, ma non può unirne le righe ai record di ModSecurity (quelle richieste si vedono nel log di audit); info se non viene letto alcun log di accesso (le richieste si vedono nel log degli errori e nel log di audit). Il formato dei log è quello del cliente (sezione 8) |
| mod_remoteip | Caricato con `RemoteIPHeader` | Info, senza correzione: se il sito web è dietro un proxy o un bilanciatore di carico, i log contengono l'IP del proxy, e così gli avvisi e le regole per IP |
| Log di audit | `SecAuditEngine RelevantOnly` (o `On`) con un `SecAuditLog` | Avvertenza se è disattivato: localSIEM decide solo dall'error.log, e la scheda della richiesta non ha header né elenco delle regole. Quando è attivato, le sue note si limitano a descriverlo: tipo concorrente (un file per transazione; ModSecurity di solito li crea con modalità 600, e localSIEM li legge se `localsiem` può farlo), formato nativo (letto così com'è), parte E registrata (non va mai al SOC), parte H mancante (l'azione intrapresa non si può leggere dal log di audit; l'unica nota che rende il controllo un'avvertenza). Nessuna correzione: il log di audit lo configura il cliente (sezione 8) |
| Mascheramento alla sorgente | Esiste un'azione `sanitise` | Info, senza correzione («The audit log on disk is not masked»): il file scritto da ModSecurity può contenere password e cookie; localSIEM li maschera prima di salvarli, e non vanno mai al SOC |
| Permessi | `localsiem` può leggere ogni sorgente | Errore. Debian: `usermod -aG adm localsiem`; Alpine: i comandi `setfacl` mostrati. Una sorgente che non esiste ancora è solo info. |
| Log tramite pipe | — | Avvertenza: `\|/usr/bin/rotatelogs ...` e syslog non si possono leggere; scrivi il log anche su un file, o aggiungi la sorgente a mano |
| Log di accesso senza dati | — | Avvertenza: un `CustomLog` usa un formato che nessun `LogFormat` definisce (o un `LogFormat` senza alcuna direttiva `%`), quindi Apache scrive lo stesso testo su ogni riga, senza l'IP del client, l'ora o la richiesta. localSIEM non legge quel log e vede le richieste del suo vhost nel suo log degli errori e nel log di audit di ModSecurity. Il formato dei log del server non viene mai modificato. |
| Motore visto Off | — | Errore: i record di audit riportano il motore come disattivato |
| Versione di ModSecurity | — | Info: la versione letta dal log di audit |

Quando la configurazione ha un `GlobalLog` il cui formato contiene `%v` (scrive tutti i vhost), gli altri log di accesso non vengono letti: ripeterebbero solo le sue righe. La diagnostica non propone mai di modificare il formato dei log né le impostazioni del log di audit (sezione 8).

<a id="client-logs"></a>
## 8. I log del cliente non vengono mai toccati

Il modulo apache2 si limita a **leggere** i log di Apache e di ModSecurity: non ci scrive mai, né li ruota, tronca, sposta o elimina, e non ne modifica mai il formato né la configurazione di Apache o di ModSecurity che li scrive. Se un server scrive i suoi log in un formato proprio (per esempio, un `LogFormat` proprio, o l'IP del client fornito da `mod_remoteip`), il modulo vi si adatta: legge ogni log di accesso con il formato che usa il suo `CustomLog`. La diagnostica (sezione 7) si limita a descrivere i log e ciò che localSIEM può o non può leggerne, senza proporre di modificarli; fornisce una correzione solo per ciò che non è un log: ModSecurity, il CRS, `SecRuleEngine`, `mod_unique_id` e l'accesso in lettura dell'utente `localsiem`. L'unica cosa che si fa come root per questo modulo è quell'accesso in lettura (`manage.py setup-modules`, sezione 2).

Le versioni 1.2.0 e precedenti del modulo avevano l'opzione di configurazione `--configure-apache`, rimossa nella versione 1.3.0. I server in cui è stata applicata conservano il file che ha scritto, `/etc/apache2/conf-available/localsiem.conf` (Debian) o `/etc/apache2/conf.d/localsiem.conf` (Alpine), con il formato `localsiem_combined` e il suo `GlobalLog` (`localsiem_access.log`), le impostazioni del log di audit e una `SecAction` che maschera i valori sensibili. Finché quel file è presente, il modulo legge quei log come qualsiasi altro. Per annullarlo, elimina quel file (Debian: `a2disconf localsiem`) e ricarica Apache. Su Alpine quel file caricava anche `mod_unique_id` e `mod_logio`: carica `mod_unique_id` altrove nella configurazione di Apache prima di eliminarlo, perché senza di esso ModSecurity 2 non ispeziona nulla (sezione 7). L'installer di localSIEM elimina quel file con `--uninstall` o `--reinstall` (su Alpine, carica prima `mod_unique_id` altrove), e lascia i log (`localsiem_access.log`, `modsec_audit.log`) dove sono.

<a id="rules"></a>
## 9. Regole del modulo Apache

Le regole vengono valutate su ogni evento. Un segnale di una regola va sempre al SOC. Nella pagina del modulo ogni regola si può disattivare, e se ne possono cambiare la gravità, la soglia (da 1 a 100000) e la finestra (da 1 a 86400 secondi); la soglia e la finestra si applicano solo alle regole di soglia e di sequenza. I suoi eventi si trovano con `rule:localsiem:<id>`.

| Regola | Tipo | Gravità | Quando | Soglia / finestra |
|---|---|---|---|---|
| `apache-bruteforce` «brute force against a login page» | soglia | media | Richieste POST non bloccate da un IP verso una pagina di accesso di un vhost (`/wp-login.php`, `/xmlrpc.php`, `/administrator/index.php`, `/user/login`, `/login`, `/admin/login`, `/login.php`, `/admin.php`, `/signin`, `/auth/login`, `/phpmyadmin/index.php`) | 20 in 300 s |
| `apache-login-after-bruteforce` «successful login after a brute force» | sequenza | alta | Almeno 10 accessi falliti (POST con risposta 200, 401 o 403) a una pagina di accesso, poi uno con risposta 302 o 303 (WordPress risponde 200 a un accesso fallito e 302 a uno riuscito) | 10, entro 1800 s |
| `apache-enumeration` «enumeration (burst of 404 answers)» | soglia | media | Risposte 404 non bloccate a un IP da un vhost | 30 in 60 s |
| `apache-sensitive-file` «sensitive file served» | corrispondenza | alta | Una risposta 2xx per un file che non dovrebbe essere pubblico: `.env`, `.git/`, `.svn/`, `.hg/`, `.htaccess`, `.htpasswd`, dump e backup (`.sql`, `.sql.gz`, `.bak`, `.old`, `.orig`, `.swp`, `.save`, `.backup`, `.dump`, nomi che terminano con `~`), `phpinfo`, `info.php`, `server-status`, `server-info`, copie di `wp-config.php` e `config.php`/`config.inc`, `.DS_Store`, chiavi SSH private, `composer.json`/`composer.lock`, `.aws/`, `backup.zip`/`.tar`/`.tar.gz`/`.tgz`/`.rar` | — |
| `apache-webshell` «possible web shell (POST to a new PHP file)» | corrispondenza | critica | Un POST con risposta 2xx a un file PHP creato o modificato nella sua DocumentRoot nell'ultimo giorno, o visto per la prima volta nell'ultima ora (dopo i giorni di apprendimento) | — |
| `apache-db-error-after-attack` «database error after a suspicious request» | sequenza | critica | Una richiesta che ha trovato corrispondenza con regole del CRS e, dallo stesso IP, un errore del database (SQL o PDO) nell'error.log | 1, entro 30 s |

<a id="health"></a>
## 10. Avvertenze di salute del modulo Apache

Oltre alle avvertenze di salute di localSIEM stesso, il modulo controlla al massimo ogni 5 minuti, e invia al SOC:

| Avvertenza | Gravità | Cosa fare |
|---|---|---|
| ModSecurity non è più caricato | alta | Era caricato e non lo è più: le richieste non vengono ispezionate. Se nessuno l'ha fatto di proposito, qualcuno potrebbe aver disattivato la protezione. |
| Motore di ModSecurity impostato a Off | alta | `SecRuleEngine` è passato a `Off`, oppure il log di audit riporta il motore come disattivato. Controlla la configurazione di Apache e le sue modifiche recenti. |
| Manca l'IP reale del client (mod_remoteip) | media | Nell'ultima ora, almeno il 90 % di almeno 100 richieste è arrivato da un unico indirizzo privato o locale: probabilmente il sito web è dietro un proxy e Apache registra l'IP del proxy, quindi le regole per IP non funzionano per queste richieste. Inviata al massimo una volta al giorno. |

Ciò che è già stato segnalato viene ricordato anche dopo i riavvii, quindi un aggiornamento non lo invia di nuovo. Grazie a queste avvertenze, un modulo attivato non si disattiva mai da solo quando Apache o ModSecurity scompaiono.

<a id="privesc"></a>
## 11. Il modulo di escalation dei privilegi

Il modulo **privesc** («Escalation dei privilegi») sorveglia ciò che persone e servizi eseguono sul server e segnala i passi di un'escalation verso root: la ricognizione, la ricerca di programmi setuid, gli strumenti di enumerazione come linpeas, gli exploit noti, le reverse shell, root ottenuto senza sudo né su, le backdoor lasciate e i tentativi di accecare il monitoraggio. Esamina inoltre la superficie di attacco del server: programmi setuid, capability e file sensibili scrivibili da altri (sezione 16).

Legge solo ciò che il server ha già: non installa mai nulla, non carica mai regole di audit e non modifica mai la configurazione di auditd, di snoopy né delle shell. Legge fino a due sorgenti:

| Sorgente | Cosa vede | Dove funziona |
|---|---|---|
| **auditd** (`/var/log/audit/audit.log`) | sudo, su, pkexec e gli accessi SSH (PAM) e tutto ciò che registrano le regole di audit del server (vedi sotto) | Server fisici e macchine virtuali, finché auditd è in esecuzione. **Non dentro un container** (LXC, podman, systemd-nspawn, Docker): l'audit del kernel non ha namespace, quindi auditd funziona solo sull'host. |
| **syslog** (`/var/log/auth.log`, `/var/log/secure` o `/var/log/messages`) | sudo, su, pkexec, doas, gli accessi SSH e, se **snoopy** è installato, ogni programma eseguito | Ovunque, container compresi. Viene letto quando auditd non è in esecuzione, il suo log non può essere letto o snoopy è installato (impostazione **Leggi syslog**). Richiede un demone syslog che scriva su un file: il solo journal di systemd non viene letto. |

Ciò che mostra auditd dipende dalle regole di audit che il server carica, che sono una decisione del suo amministratore; il modulo le usa così come sono, qualunque siano le loro chiavi, e classifica ogni record in base al tipo, alla chiamata di sistema e ai file:

| Il modulo vede | Quando le regole di audit del server registrano |
|---|---|
| Ogni programma eseguito (anche da script, web shell ed exploit), programmi setuid, root ereditato da essi, capability ottenute | `execve` |
| Modifiche di account, sudoers, PAM, preload, SSH, cron, servizi e `/etc/audit` | Sorveglianze (`-w ... -p wa`) su quei file o le chiamate di sistema che li modificano |
| Bit setuid o setgid impostati | `chmod`, `fchmod`, `fchmodat` |
| Moduli del kernel caricati o rimossi | `init_module`, `finit_module`, `delete_module` |
| Processi agganciati con ptrace | `ptrace` |
| File negati a una persona | `open`, `openat`, `execve`... che falliscono con `EACCES` o `EPERM` |
| Regole di audit rimosse, audit disattivato, auditd fermato, programmi che vanno in crash | Sempre (li segnalano il kernel e auditd) |

Su un server fisico o una macchina virtuale, auditd è la sorgente che un utente non può evitare; la diagnostica indica ciò che le regole di audit del server hanno registrato finora (sezione 14). In un container, snoopy è l'unico modo per vedere ogni programma eseguito.

I comandi interni della shell (`pwd`, `cd`, `unset HISTFILE`, `history -c`) non eseguono mai un programma, quindi nessuna sorgente li vede, tranne dentro una riga di comando come `bash -c '...'`. Un singolo `whoami` non è mai un avviso: il modulo conta i comandi di ricognizione **distinti** di ogni sessione all'interno di una finestra, e solo una loro raffica lo è (sezione 13).

Cosa contiene ogni evento del modulo, e come cercarlo:

| Colonna | Contiene | Ricerca di esempio |
|---|---|---|
| `vhost` | La persona: l'utente dell'accesso (resta lo stesso attraverso sudo e su) | `module:privesc vhost:alice` |
| `method` | Tipo di evento: `exec` (programma eseguito, auditd o snoopy), `sudo`, `su`, `pkexec`, `doas`, `login`, `pam`, `file` (file sensibile modificato), `chmod` (bit setuid), `kmod`, `ptrace`, `denied` (file negato), `audit_config`, `auditd`, `crash`, `syscall` (un'altra chiamata di sistema registrata dalle regole di audit del server) | `module:privesc method:sudo` |
| `uri` | La riga di comando (password mascherate) | `module:privesc uri:*linpeas*` |
| `path` | Il programma eseguito, o il file modificato | `module:privesc path:/tmp/*` |
| `ip` | L'indirizzo SSH della sessione, quando è noto | `module:privesc ip:203.0.113.7` |
| `score` | Comandi di ricognizione distinti della sessione nella finestra | `module:privesc score:>=8` |
| `action` | `blocked` quando è stato il sistema stesso a fermarlo: un programma che non è riuscito a eseguirsi, sudo o su rifiutati, un file negato | `module:privesc action:blocked` |
| `source` | `audit` o `syslog` | `module:privesc source:syslog` |

Le regole sui tentativi (fallimenti ripetuti di sudo, molti file negati) contano comunque gli eventi bloccati; le altre guardano solo ciò che è stato realmente eseguito.

La pagina del modulo, `/admin/dashboard/modules/installed/privesc/`, ha le stesse parti della pagina del modulo Apache (sezione 4): intestazione (con **Rileva di nuovo ed esegui la diagnostica**, **Riconfigura** e **Disinstalla**), impostazioni (sezione 12), sorgenti (`audit`, `syslog`; e quelle non lette, con il motivo), diagnostica (sezione 14) e regole (sezione 13).

<a id="privesc-settings"></a>
## 12. Impostazioni del modulo di escalation dei privilegi

| Impostazione | Predefinito | Cosa fa |
|---|---|---|
| **Log di audit** | vuoto | Vuoto: `log_file` di `/etc/audit/auditd.conf`, oppure `/var/log/audit/audit.log`. |
| **Leggi syslog** | Automatico | Automatico: solo quando auditd non è in esecuzione, il suo log non può essere letto o snoopy è installato. Sempre, o Mai. |
| **File di syslog** | vuoto | Vuoto: `/var/log/auth.log`, `/var/log/secure` o `/var/log/messages`, il primo che esiste. |
| **Utenti ignorati** | vuoto | Separati da virgole. I loro comandi vengono salvati e sono ricercabili, ma non generano mai avvisi: account di automazione (ansible, backup). L'utente `localsiem` viene sempre ignorato. |
| **Gruppi di amministratori** | `sudo,wheel,admin` | Separati da virgole. I loro membri (e root) hanno la soglia di ricognizione più alta e possono elencare i propri permessi sudo senza generare avvisi. |
| **Finestra di ricognizione (secondi)** | 120 | Finestra in cui si contano i comandi di ricognizione distinti di una sessione (da 10 a 3600). |
| **Soglia di ricognizione** | 8 | Comandi di ricognizione distinti nella finestra che costituiscono una raffica, per utenti e account di servizio (da 2 a 500). |
| **Soglia di ricognizione per gli amministratori** | 20 | Lo stesso per root e per gli amministratori, che li eseguono come parte del loro lavoro (da 2 a 500). |
| **Soglia di enumerazione automatica** | 40 | Comandi di ricognizione distinti nella finestra che solo uno script esegue (tipo linpeas), per tutti (da 5 a 1000). |
| **Giorni di apprendimento degli account di servizio** | 3 | Durante i primi giorni dopo il primo avvio del modulo, i programmi eseguiti da ogni account di servizio (`www-data` che esegue `sh -c sendmail`) vengono appresi senza avvisi (da 0 a 365). |
| **Ore tra le scansioni dei programmi setuid** | 24 | Ogni quanto si cercano i programmi setuid e setgid e le capability dei file (sezione 16). 0: mai (da 0 a 168). |
| **Cartelle analizzate** | `/usr,/bin,/sbin,/lib,/lib64,/opt,/home,/srv,/tmp,/var/tmp,/dev/shm,/var/www,/etc` | Separate da virgole; ognuna viene percorsa senza uscire dal suo file system. Le cartelle dei container e di `/proc` e `/sys` vengono sempre saltate. |
| **Intervallo di rilevamento (secondi)** | 300 | Ogni quanto si cercano il log di audit, syslog e lo stato di auditd (da 60 a 86400). Si applica a tutti i moduli attivati l'intervallo più breve tra i loro. |

Cosa conta come ricognizione: `whoami`, `id`, `groups`, `uname`, `hostname`, `w`, `who`, `last`, `ps`, `ss`, `netstat`, `ip`, `ifconfig`, `env`, `pwd`, `history`, `getcap`, `lsmod`, `dmesg`, `mount` e simili; `sudo -l`, `crontab -l`, `systemctl list-*`, gli elenchi dei pacchetti; `which`, `locate`, `command -v`; `docker ps` e simili; ogni `find` diverso; la lettura di `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`, `/etc/*-release`, `/proc/version`, `/root/...`, cronologie, chiavi SSH e file `.env`; l'elenco di `/root`, `/home`, `/opt`, `/tmp`, le cartelle di cron...; `grep -r password`; e `<program> --version`. Ogni comando diverso di una sessione conta una volta all'interno della finestra.

<a id="privesc-rules"></a>
## 13. Cosa invia al SOC il modulo di escalation dei privilegi: le sue regole

Ogni avviso del modulo proviene da una delle sue regole (funzionano allo stesso modo qualunque sia la sorgente che ha visto il comando), tranne quelli della sezione 16. Come per Apache, nella pagina del modulo ogni regola si può disattivare e se ne possono cambiare la gravità, la soglia e la finestra; i suoi eventi si trovano con `rule:localsiem:<id>`. Nessuna scatta per gli **Utenti ignorati**. Le regole marcate «auditd» richiedono i record di audit della sezione 11.

| Regola | Tipo | Gravità | Quando | Soglia / finestra |
|---|---|---|---|---|
| `privesc-recon-burst` «reconnaissance burst» | corrispondenza | media | La sessione ha raggiunto la soglia di ricognizione (sezione 12) | — |
| `privesc-enumeration` «automated enumeration (linpeas-like)» | corrispondenza | alta | La sessione ha raggiunto la soglia di enumerazione automatica, anche con uno script rinominato | — |
| `privesc-suid-hunt` «search for setuid programs or capabilities» | corrispondenza | alta | `find ... -perm -4000` (o `-u=s`, `/6000`, `-2000`...), `getcap -r`, `find -writable` | — |
| `privesc-sudo-list` «sudo rights listed by a non-administrator» | corrispondenza | media | `sudo -l` da parte di un utente o di un account di servizio che non è amministratore | — |
| `privesc-known-tool` «known enumeration tool» | corrispondenza | alta | linpeas, LinEnum, lse.sh, linux-exploit-suggester, les.sh, pspy, unix-privesc-check, linuxprivchecker, traitor, BeRoot, GTFONow, PEASS, deepce, CDK, sudo_killer, suid3num, mimipenguin, LaZagne, pwncat, searchsploit | — |
| `privesc-exploit` «known exploit» | corrispondenza | critica | PwnKit, DirtyPipe, Dirty COW, Baron Samedit (`sudoedit -s '\'`), Looney Tunables (`GLIBC_TUNABLES`), GameOver(lay), nf_tables (CVE-2024-1086), CVE-2023-22809 (`EDITOR=... -- /...`), polkit CVE-2021-3560 (`dbus-send ... CreateUser`), `LD_PRELOAD` con sudo, uno script con il nome di una CVE, programmi chiamati `exploit`, `getroot`, `rootme` | — |
| `privesc-pwnkit` «PwnKit (pkexec run without arguments)» | corrispondenza | critica | `pkexec` eseguito con zero argomenti (auditd) | — |
| `privesc-pwnkit-log` «pkexec reports a PwnKit attempt» | corrispondenza | critica | pkexec registra `GCONV_PATH`, «suspicious content» o «was not found the /etc/shells» (syslog) | — |
| `privesc-suid-escape` «root inherited from a setuid program» | corrispondenza | critica | Un programma che non è setuid viene eseguito con l'uid effettivo di root e l'uid reale di un utente: è stato abusato un programma setuid (GTFOBins). Sono esclusi gli helper di mount, D-Bus, polkit e X. | — |
| `privesc-root-without-door` «root without sudo, su or pkexec» | corrispondenza | critica | Una sessione di una persona di cui si è visto l'inizio esegue programmi come root senza essere passata per sudo, su, pkexec o doas (exploit del kernel) (auditd) | — |
| `privesc-root-shell-interpreter` «root shell started by an interpreter» | corrispondenza | alta | Una shell viene eseguita come root, avviata da python, perl, ruby, awk, gdb... che un utente normale stava eseguendo (un suo figlio, o lo stesso processo) (auditd) | — |
| `privesc-file-capabilities` «program gained root capabilities from its file» | corrispondenza | alta | Un utente ha eseguito un programma il cui file gli dà `cap_setuid`, `cap_dac_override`, `cap_sys_admin`... (auditd) | — |
| `privesc-tmp-exec` «program run from a world-writable folder» | corrispondenza | alta | Un programma in `/tmp`, `/var/tmp`, `/dev/shm` o `/run/user/<uid>` | — |
| `privesc-compile-tmp` «program compiled in a temporary folder» | corrispondenza | alta | `gcc`, `cc`, `clang`, `make`... in una cartella temporanea o su suoi file | — |
| `privesc-download-shell` «downloaded script run by a shell» | corrispondenza | alta | `curl ... \| sh`, `bash -c "$(curl ...)"`, `bash <(wget ...)`, o un programma di download seguito da una shell nella stessa pipeline | — |
| `privesc-reverse-shell` «reverse shell» | corrispondenza | alta | `/dev/tcp/`, `nc -e`, `ncat --exec`, `socat exec:`, `mkfifo ... \| nc`, socket di python/perl/php/ruby/lua/node, `openssl s_client ... \| sh`, `awk /inet/tcp` | — |
| `privesc-tty-upgrade` «shell upgraded to a full terminal» | corrispondenza | alta | `pty.spawn`, `script ... /dev/null`, `stty raw -echo`, `socat ... pty`, `expect ... spawn sh` | — |
| `privesc-service-recon` «service account ran reconnaissance commands» | corrispondenza | alta | `www-data`, `mysql` e altri account di servizio che eseguono `whoami`, `id`, `uname`... (una web shell) | — |
| `privesc-service-new-program` «service account ran a program it never ran before» | corrispondenza | alta | Dopo i giorni di apprendimento, un account di servizio esegue una shell, un interprete o uno strumento che non aveva mai eseguito (`sh -c id` dove eseguiva solo `sh -c sendmail`) | — |
| `privesc-container-escape` «container used to reach the host as root» | corrispondenza | alta | Qualcuno che non è root esegue `docker run -v /:/...`, `--privileged`, `--pid=host`, `nsenter -t 1`, `lxc config set ... security.privileged true`, `lxc config device add ... source=/`, `debugfs /dev/...` | — |
| `privesc-auth-failures` «repeated sudo or su failures» | soglia | media | sudo, su, pkexec o doas falliti di un utente | 3 in 600 s |
| `privesc-sensitive-file` «account, sudo, PAM or preload file changed» | corrispondenza | alta | `/etc/passwd`, `shadow`, `group`, `gshadow`, `sudoers`, `sudoers.d`, `doas.conf`, `doas.d`, `ld.so.preload`, `ld.so.conf`, `ld.so.conf.d`, `pam.d`, `security` modificati da un programma che non è uno strumento di pacchetti o di account (auditd) | — |
| `privesc-persistence-file` «SSH, cron or service file changed» | corrispondenza | media | `/root/.ssh`, `sshd_config`, `sshd_config.d`, file di cron, `/etc/systemd/system`, `/etc/init.d`, `rc.local`, `/etc/local.d` modificati (auditd) | — |
| `privesc-monitoring-changed` «auditd configuration changed» | corrispondenza | media | `/etc/audit` modificato da un programma che non è uno strumento di pacchetti (auditd) | — |
| `privesc-suid-set` «setuid or setgid bit set on a file» | corrispondenza | alta | `chmod u+s`/`g+s` su un file (non una cartella) al di fuori del gestore di pacchetti (auditd) | — |
| `privesc-setcap` «file capabilities set» | corrispondenza | alta | `setcap ... cap_...` | — |
| `privesc-kernel-module` «kernel module loaded from a session» | corrispondenza | alta | Un modulo caricato o rimosso dalla sessione di una persona (auditd) | — |
| `privesc-ptrace` «process attached with ptrace» | corrispondenza | media | `PTRACE_ATTACH` o `PTRACE_SEIZE` (auditd) | — |
| `privesc-denied-burst` «many files refused (enumeration)» | soglia | media | File negati (`EACCES`, `EPERM`) a un utente (auditd) | 30 in 60 s |
| `privesc-sensitive-denied` «attempt to read the password hashes or files of root» | corrispondenza | media | `/etc/shadow`, `/etc/gshadow`, `/etc/sudoers`, `/etc/sudoers.d/` o `/root` negati a un utente (auditd) | — |
| `privesc-history-tampering` «shell history erased or turned off» | corrispondenza | media | `ln -s /dev/null ~/.bash_history`, `rm .bash_history`...; `unset HISTFILE`, `HISTFILE=/dev/null`, `HISTSIZE=0`, `history -c`, `set +o history` solo dentro una riga di comando (`bash -c`), dato che i comandi interni non eseguono alcun programma | — |
| `privesc-audit-stop-command` «command to turn auditd off» | corrispondenza | critica | `auditctl -e 0`, `auditctl -D`, `auditctl -a never`, `systemctl stop/disable/mask auditd`, `service auditd stop`, `pkill auditd`, la cancellazione di `/var/log/audit` o di `/etc/audit` | — |
| `privesc-audit-disabled` «auditing turned off» | corrispondenza | critica | Il kernel riporta `audit_enabled=0` (auditd) | — |
| `privesc-auditd-stopped` «auditd stopped by a process» | corrispondenza | alta | auditd fermato su richiesta di un processo diverso da init (uno spegnimento del server non viene segnalato) | — |
| `privesc-crash` «setuid or temporary program crashed» | corrispondenza | media | Un programma setuid, o uno in una cartella temporanea, è andato in crash (auditd `ANOM_ABEND`): spesso un exploit fallito | — |

Ogni avviso ha un nome stabile, una descrizione che termina con la query da incollare nella ricerca di localSIEM, e dei dettagli: utente, tipo di account (`root`, `admin`, `user`, `service`), utente reale ed effettivo, comando, programma, cartella, terminale, sessione, sorgente (`auditd`, `snoopy`, `syslog`), IP del client e, quando si applicano, il programma padre, l'interprete, il file modificato e il suo gruppo, i comandi di ricognizione contati, le capability, la modalità impostata, la richiesta ptrace e l'errore di un file negato. Quando parte, l'avviso porta anche il contesto della sessione: se se ne è visto l'inizio, se è passata per sudo o su, il suo indirizzo SSH e i suoi **ultimi 20 comandi**, così l'analista legge cosa ha portato all'avviso senza dover cercare.

Lo stesso comando può essere visto da più di una sorgente (auditd e snoopy): gli avvisi vengono raggruppati per modulo, utente, IP, categoria e gravità, quindi genera comunque un solo avviso. Le password nelle righe di comando (`mysql -p...`, `sshpass -p`, `curl -u user:pass`, `PASSWORD=...`, URL con una password) vengono mascherate prima che venga salvato qualsiasi cosa, anche nell'esadecimale dei record di audit.

<a id="privesc-doctor"></a>
## 14. Requisiti del modulo di escalation dei privilegi: la diagnostica

**Requisiti.** Il modulo ha bisogno di una sorgente che l'utente `localsiem` possa leggere (il file esiste e `localsiem` può aprirlo): il log di **auditd** (auditd in esecuzione, fuori da un container) o il file di **syslog** con sudo, su, pkexec e doas (`/var/log/auth.log`, `/var/log/secure` o `/var/log/messages`, oppure l'impostazione **File di syslog**, a meno che **Leggi syslog** non sia Mai), dove **snoopy**, se è installato, scrive anche ogni programma eseguito. Ne basta una qualsiasi. Quando una sorgente esiste ma `localsiem` non può leggerla, il requisito lo indica, con il comando che dà l'accesso in lettura (per il log di audit, il comando della pagina dei Moduli, `manage.py setup-modules`; per syslog, `setfacl -m g:localsiem:r <file>`). Se non ce n'è nessuna, indica cosa installare: auditd (Debian: `apt-get install auditd`; Alpine: `apk add audit && rc-update add auditd && rc-service auditd start`), un demone syslog (Debian: `apt-get install rsyslog`; Alpine: `apk add rsyslog && rc-update add rsyslog && rc-service rsyslog start`) o snoopy. Fino ad allora il modulo resta disattivato; **Riconfigura** verifica di nuovo. Non installa nulla di sua iniziativa. In una prima installazione i log di solito appartengono a root: esegui il comando che mostra l'interfaccia web, poi premi **Riconfigura**.

La diagnostica funziona come quella di Apache (sezione 7). Si limita a descrivere ciò che il modulo vede con ciò che il server ha e ciò che non può vedere; le sue correzioni sono solo i pacchetti da installare e l'accesso in lettura di `localsiem`. Non propone mai di modificare le regole di audit, `auditd.conf` (tranne `log_group`, vedi sotto), `snoopy.ini`, le shell o qualsiasi altra configurazione:

| Controllo | Corretto quando | Altrimenti |
|---|---|---|
| auditd | auditd è in esecuzione | Avvertenza se non è installato (Debian: `apt-get install auditd`; Alpine: `apk add audit && rc-update add auditd && rc-service auditd start`); avvertenza, senza correzione, se è installato ma fermo (se debba funzionare lo decide l'amministratore). Info dentro un container: lì auditd non può funzionare. |
| Log di audit | `localsiem` può leggerlo | Errore, con il comando della pagina dei Moduli; avvertenza se auditd è in esecuzione e il suo log non si trova dove il modulo lo cerca (impostazione **Log di audit**) |
| Gruppo del log di audit | Il log di audit non appartiene al gruppo `root` | Avvertenza se vi appartiene (`log_group = root` in `auditd.conf`): ogni log che auditd crea quando ruota ha modalità 600, è leggibile solo da root e localSIEM smette di leggere. La correzione è la riga `log_group = adm` per `/etc/audit/auditd.conf` (poi riavvia auditd): i nuovi log vengono creati con modalità 640. |
| Record delle regole di audit | Sono stati letti programmi eseguiti (`EXECVE`) | Avvertenza se auditd scrive ma nessuno dei suoi record è un programma eseguito: le regole di audit del server non registrano `execve`, quindi i comandi di script, web shell ed exploit non si vedono tramite auditd. Info con cos'altro le regole hanno registrato finora (modifiche di file sensibili, bit setuid, moduli del kernel, ptrace, file negati) e cosa non ancora |
| syslog | Il file di syslog viene letto | Errore se non può essere letto (`setfacl -m g:localsiem:r <file>`); avvertenza se non c'è né un log di audit utilizzabile né un file di syslog (Debian: `apt-get install rsyslog`; Alpine: `apk add rsyslog && rc-update add rsyslog && rc-service rsyslog start`) |
| snoopy | Installato, e le sue righe vengono lette | Avvertenza senza auditd: i comandi degli script e delle web shell non si vedono (Debian: `apt-get install snoopy`; Alpine non ha un pacchetto: va compilato dai sorgenti). Avvertenza se è installato ma syslog non viene letto. Info se le sue righe non hanno uid effettivo (`message_format` di `snoopy.ini`): root ereditato da un programma setuid non si vede tramite snoopy |
| Ciò che il modulo vede | — | Info: auditd (e ciò che registrano le sue regole), snoopy (ogni programma eseguito) o, come avvertenza, solo sudo, su, pkexec e doas (syslog senza snoopy: la maggior parte delle regole non può scattare); errore se non può leggere nulla. Ricorda anche che i comandi interni della shell non si vedono mai |
| File della versione 1.0.0 | — | Info, senza correzione, se vengono trovati i file lasciati da `--configure-privesc` (sezione 15) |
| Programmi setuid e capability | — | Info: l'ultima scansione (sezione 16). Avvertenza, senza correzione, con i programmi setuid che danno una shell di root (GTFOBins) e con i programmi le cui capability sono in pratica root |
| File sensibili | Nessuno scrivibile da qualcuno diverso da root | Errore, senza correzione, per ognuno (`/etc/passwd`, `sudoers`, cron, `/etc/profile.d`, le cartelle del `PATH` di root, `docker.sock`...) |
| Gruppi privilegiati | — | Avvertenza, senza correzione, con i membri di `docker`, `lxd`, `incus-admin`, `disk` e `libvirt`: in pratica sono root |

<a id="privesc-legacy"></a>
## 15. Server aggiornati dalla versione 1.0.0 del modulo di escalation dei privilegi

La versione 1.0.0 del modulo aveva l'opzione di configurazione `--configure-privesc` e un hook di bash; la versione 1.1.0 li ha rimossi entrambi, perché un modulo non installa né modifica mai nulla fuori da `/opt/localsiem`. I server in cui è stata applicata conservano ciò che ha scritto, e localSIEM non lo usa né lo elimina:

- `/etc/audit/rules.d/90-localsiem-privesc.rules`: le sue regole di audit (chiavi `lsiem_*`). Finché sono caricate, il modulo legge i loro record come quelli di qualsiasi altra regola del server.
- `/etc/localsiem-privesc/` (l'hook), `/etc/profile.d/localsiem-privesc.sh` e la riga che segue «localSIEM privesc: command hook» in `/etc/bash.bashrc` (Debian) o `/etc/bash/bashrc` (Alpine): finché sono presenti, ogni bash interattiva continua a scrivere i suoi comandi in `/var/log/localsiem-privesc/`, che nessuno legge.
- `/var/log/localsiem-privesc/`: i file di comandi di ogni utente.
- `log_group = adm` in `/etc/audit/auditd.conf`, `/root/.ssh` (creata vuota) e il `message_format` di `/etc/snoopy.ini`: possono restare (`log_group = adm` mantiene leggibili i log di audit ruotati, sezione 14, e il modulo legge quel formato di snoopy così come quelli predefiniti).

La diagnostica elenca quelli che riesce a vedere (controllo «Files of version 1.0.0 of the module»). Per rimuoverli, come root: elimina il file delle regole e ricarica le regole (`augenrules --load`); elimina `/etc/profile.d/localsiem-privesc.sh`, `/etc/localsiem-privesc/` e la riga del bashrc; ed elimina `/var/log/localsiem-privesc/` se non vuoi conservare i comandi che contiene.

<a id="privesc-health"></a>
## 16. Superficie di attacco e avvertenze di salute del modulo di escalation dei privilegi

Oltre alle sue regole, il modulo esamina il server stesso e invia al SOC:

| Avvertenza | Gravità | Quando |
|---|---|---|
| Nuovo programma setuid o setgid | alta | Una scansione trova un programma setuid o setgid che la scansione precedente non aveva (la prima scansione serve solo da riferimento). Un attaccante diventato root lascia spesso una shell setuid; anche un aggiornamento dei pacchetti può aggiungerne uno. |
| Nuovo programma setuid in una cartella scrivibile | critica | Lo stesso, in `/tmp`, `/var/tmp`, `/dev/shm`, `/home`, `/srv` o `/var/www` |
| Nuovo programma setuid di GTFOBins | critica | Lo stesso, per un programma che dà una shell di root quando è setuid (`bash`, `find`, `python`, `vim`, `less`, `cp`...) |
| Nuove capability | alta | Un programma ha ottenuto capability che sono in pratica root (`cap_setuid`, `cap_dac_override`, `cap_sys_admin`...) |
| File sensibile scrivibile da qualcuno diverso da root | critica | Controllato ogni ora: `/etc/passwd`, `/etc/shadow` (anche leggibile da tutti), `sudoers`, cron, `/etc/profile.d`, PAM, servizi, `ld.so.preload`, le cartelle del `PATH` di root, `docker.sock`... Segnalato una volta per file e problema. |
| auditd fermato (salute di localSIEM) | alta | auditd era in esecuzione e non lo è più (fuori dai container) |

La scansione viene eseguita in background, al massimo ogni **Ore tra le scansioni dei programmi setuid** (la prima cinque minuti dopo l'avvio del collettore), attraverso le **Cartelle analizzate**, come utente `localsiem` (ciò che non può leggere viene saltato), e si ferma dopo 3 milioni di file o 15 minuti. Il suo risultato, con i GTFOBins e le capability trovati, viene mostrato nella diagnostica. Le gravità di queste avvertenze sono in `severity.yaml` del modulo. Ciò che è già stato segnalato viene ricordato anche dopo i riavvii.

<a id="cli"></a>
## 17. Riga di comando

Come root, `/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py <command>`:

| Comando | Uso |
|---|---|
| `modules` | Moduli installati: id, versione, attivato, disattivato o non caricato, e cartella, con i requisiti che gli mancano, se ce ne sono; e i moduli che non è stato possibile caricare, con l'errore |
| `doctor` | Per ogni modulo attivato: ogni controllo (`✓`, `!`, `✗`, `·`) con il frammento che lo risolve, e le sorgenti trovate; per un modulo disattivato perché manca un requisito, i suoi requisiti. `--json` fornisce lo stesso in JSON. |
| `read-paths` | Cartelle che i moduli leggono, a cui localSIEM dà l'accesso in lettura come root |
| `setup-modules [--no-restart]` | Come root: il comando che mostra l'interfaccia web; accesso in lettura alle cartelle dei moduli (`read_paths`) e un riavvio di localSIEM (`--no-restart`: senza riavvio). I moduli non hanno opzioni di configurazione |

Esegui la diagnostica come utente `localsiem` per vederne i permessi reali:

```bash
runuser -u localsiem -- /opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor   # Debian
su -s /bin/sh localsiem -c "/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor"   # Alpine
```
