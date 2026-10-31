# localSIEM-modules user manual

This MANUAL is also available in:\
en-GB, [en-US](MANUAL.md), [es-AR](MANUAL.es-AR.md), [es-ES](MANUAL.es-ES.md)

[Installation](README.en-GB.md) · [Code reference](CODE.en-GB.md) · [localSIEM manual](../../localSIEM/doc/MANUAL.en-GB.md)

## Contents

1. [What the modules are](#what)
2. [Installing and updating the modules](#installation)
3. [The Modules page](#modules-page)
4. [The page of the Apache module](#apache-page)
5. [Settings of the Apache module](#settings)
6. [What the Apache module sends to the SOC](#soc)
7. [Apache and ModSecurity requirements: the doctor](#doctor)
8. [Applying the requirements: --configure-apache](#configure-apache)
9. [Rules of the Apache module](#rules)
10. [Health warnings of the Apache module](#health)
11. [The privilege escalation module](#privesc)
12. [Settings of the privilege escalation module](#privesc-settings)
13. [What the privilege escalation module sends to the SOC: its rules](#privesc-rules)
14. [Requirements of the privilege escalation module: the doctor](#privesc-doctor)
15. [Applying the requirements: --configure-privesc](#configure-privesc)
16. [Attack surface and health warnings of the privilege escalation module](#privesc-health)
17. [Command line](#cli)

<a id="what"></a>
## 1. What the modules are

localSIEM is made of a **core** and **modules**. The core stores the events, searches them, runs the rules, groups the alerts, sends them to the SOC and watches its own health. Each module adds one service of the server: it finds its logs, reads them, turns them into events, decides what is already resolved, brings its own rules and checks the requirements of that service.

The modules of this project are installed in `/opt/localsiem/modules/<name>/`. Today there are two: **apache2** («Apache + ModSecurity», sections 4 to 10) and **privesc** («Privilege escalation», sections 11 to 16). localSIEM has no modules of its own: the Modules page only lists the modules installed from this repository.

<a id="installation"></a>
## 2. Installing and updating the modules

localSIEM must be installed first; its installer installs the core only, never a module. The modules of this project are installed **only from the localSIEM web**: this project has no installer of its own. The web downloads them from the repository `https://github.com/PYMEHackers/localSIEM-modules` (branch `main`).

**Installing.** As an administrator, open Modules › **Installable** (section 3), press **Check the repository** and then **Install** on the module. localSIEM then:

1. downloads the repository and unpacks it safely (nothing out of its folder, size limits);
2. copies the folder of the module (`mod-<name>/` in the repository) to `/opt/localsiem/modules/<name>/`, without `tests/` (and without Python caches); a module installed again gets back the settings it had;
3. restarts the collector, which loads the module within a few seconds;
4. takes the module out of the list and opens the dialogue «<module> installed» with the command to run as root on the server (`manage.py setup-modules`) and a **Copy** button: it gives the `localsiem` user read access to the folders listed in `read_paths` of its `module.json` (`/var/log/apache2` for the apache2 module, `/var/log/audit` for the privesc module), also to the files of the next rotations, and, if you add the setup option of the module to it, it also applies the requirements of the module: `--configure-apache` (section 8) or `--configure-privesc` (section 15). Until it is run the module may show «Error»: its logs cannot be read yet. The dialogue closes with «Close» or with «See the installed modules», which opens Installed.

**Updating.** When Modules › **Installed** opens, the web checks the repository, and a module with a newer version there shows a notice with **Update** (section 3). After you confirm, localSIEM downloads the new version and puts it in place of the installed one (steps 1 to 3), keeps its settings and leaves the module on or off as it was. The command for root is shown again only if the new version reads other logs (`read_paths`) or has another setup option; otherwise there is nothing to run. An update of localSIEM keeps the modules installed and their read access.

**Reinstalling.** The web neither reinstalls a module nor installs an older version of it: to reinstall a module, press **Uninstall** (section 3) and install it again from **Installable**; its settings are kept.

**Installing a module never installs the software it watches.** The apache2 module installs neither Apache nor ModSecurity, and the privesc module installs neither auditd, bash nor snoopy. If, on its first installation, the server lacks what the module needs (Apache and ModSecurity for apache2; at least one of auditd, bash and snoopy for privesc), the module is installed **turned off**: the dialogue lists what is missing instead of the command, and the module cannot be turned on until **Reconfigure** finds them (section 4). An update keeps the module on or off as it was.

<a id="modules-page"></a>
## 3. The Modules page

Administrators open **Administration › Modules**, which has two sections, each at its own address: **Installed** (`/admin/dashboard/modules/installed/`), which opens by default (`/admin/dashboard/modules/` goes there), and **Installable** (`/admin/dashboard/modules/installable/`). Analysts see **Modules** in their dashboard (`/user/dashboard/modules/`): only the list of the installed modules, read-only, without sections.

**Installed** shows one row per installed module, the whole width: its name, its id, its version, a state pill, its summary and, below it, the reasons of that state. The list refreshes itself every 10 seconds. With no module installed it says «Install modules from the Installable tab.» (to analysts: «No modules installed. An administrator installs them in Modules › Installable.»).

| State | Meaning |
|---|---|
| **On and working** | On, loaded by the collector and reading its sources. Doctor warnings are listed as notes but do not change the state. |
| **On, with warnings** | On, but no logs were found to read, a source does not exist yet, or the module was installed after the collector started (restart the `localsiem` service). |
| **Error** | The module does not load (the error is shown), its doctor reports an error, or a source cannot be read (permissions of the `localsiem` user). |
| **Off** | Turned off, or installed without its requirements (for apache2: Apache or ModSecurity is missing; for privesc: neither auditd, bash nor snoopy), as its reason says. |
| **Applying the change…** | Just turned on or off: the collector is applying it. |
| **Unknown** | The collector (service `localsiem`) is not running, so nothing is being read. |

When the module is not off, the row also shows: **Sources being read** (read / found), **Lines (1 h)**, **Last data**, **Events (24 h)**, **Blocked (24 h)** and the **Doctor** counts («n OK · n warnings · n errors»).

Administrators also get, on each row:

- **The switch** of each module. Turning a module off asks for confirmation: localSIEM stops reading its logs and sending its alerts until it is turned on again; what is already stored stays. Turning it on starts reading at once. While a requirement of the module is missing, the switch is locked («Off: requirements missing»): **Reconfigure** (section 4) unlocks it once it finds them.
- **Configure**, which opens the page of the module, `/admin/dashboard/modules/installed/<name>/` (section 4); the older address `/admin/dashboard/modules/<name>/` takes you there.
- **Uninstall**, also on a module that does not load (and on the page of the module). After you confirm, localSIEM deletes `/opt/localsiem/modules/<name>/` and restarts the collector without it: it stops reading its logs and sending its alerts. The events already stored can still be searched, and its settings stay, in case you install it again. The read access that root gave `localsiem` to its logs is not taken back.
- **Update**, when the repository has a newer version of the module. Each time Installed opens, the web checks the repository («Checking the repository for newer versions…»; the browser reuses the answer for 10 minutes), and a row whose module has a newer version shows «The repository has version X (the installed one is Y).» with the button **Update**. After you confirm, localSIEM installs the new version (section 2), keeps its settings, leaves the module on or off as it was and restarts the collector; a dialogue shows the command for root only if the new version reads other logs or has another setup option. If the new version needs a newer localSIEM, the notice says «The repository has version X, but it needs localSIEM Z or newer: update localSIEM to install it.» and has no button.

**Installable** (administrators only) has the card «Installable modules». **Check the repository** downloads the repository and lists the modules that are not installed on this server yet, each one with its name, id, version and summary and a button or a note:

| Button or note | Meaning |
|---|---|
| **Install** | Installs the module (section 2) |
| «Needs localSIEM X or newer» | It cannot be installed: update localSIEM first |
| «The module of the repository is not valid» | It cannot be installed |

The modules already installed never appear here: they are updated from Installed. If every module of the repository is installed, the card says «Every module of the repository is already installed.». After installing, the dialogue «<module> installed» shows the command to run as root so that `localsiem` can read the logs of the module (section 2), with a **Copy** button and the hint to add the setup option of the module (`--configure-apache` for apache2, `--configure-privesc` for privesc); until it is run the module may show «Error»: its logs cannot be read yet. If the server lacks what the module needs, the dialogue lists what is missing instead, with the hint to open the module in Installed (**Configure**) and press **Reconfigure** once it is there.

<a id="apache-page"></a>
## 4. The page of the Apache module

`/admin/dashboard/modules/installed/apache2/` (administrators only; the older `/admin/dashboard/modules/apache2/` takes you there) has five parts:

1. **Header**: name, id, version, the installed path (`/opt/localsiem/modules/apache2`), the switch, the state with its reasons and the figures of section 3. **Back to the installed modules** returns to Installed; **Discover again and run the doctor** reads the Apache configuration again at once and refreshes the doctor; **Reconfigure** looks for Apache and ModSecurity again (below); **Uninstall** uninstalls the module (section 3) and returns to Installed.
2. **Settings**: the form of section 5. **Save the settings** checks every value and, if one is wrong, says which one («Invalid value: …»).
3. **Sources**: every log being read, with **Kind** (`access`, `error`, `audit`), **Path**, **Vhost**, **Lines (1 h)**, **Not parsed (1 h)**, **Last data** (for example `2026/10/29@13:59:59.723`) and **State** (error if it cannot be read, warning if it does not exist yet). Below, the logs found but not read, with the reason: «piped log, not supported», «covered by the localsiem_combined GlobalLog» or «its format has no data: every line is the same text (a LogFormat nickname that is not defined)».
4. **Doctor**: the checks of section 7, with the time they ran. Each missing requirement comes with the snippet that fixes it and a **Copy** button. Above them, the command for root that applies the requirements for you (`manage.py setup-modules --configure-apache`, section 8), also with a **Copy** button.
5. **Rules**: the rules of section 9, each with **On**, **Rule** (name, id and category), **Severity**, **Threshold** and **Window (s)**, and **Save the rules**.

**Requirements and Reconfigure.** While Apache or ModSecurity is missing, the module is off and the header lists what is missing, with the command that installs it. **Reconfigure** (also when the module is off) looks for them again with the saved settings; if Apache is in a non-standard place, set **Apache configuration file** first (section 5). When both are found, it unlocks the switch —turning the module on is your decision— and shows the command to run as root so that `localsiem` can read the Apache logs created after the module was installed; add `--configure-apache` to also apply the requirements of section 8. A module that is on and loses Apache or ModSecurity stays on: the doctor and the health warnings (section 10) report it.

**Every change applies at once, without restarting anything**: the web saves it and tells the collector, which reloads its settings, discovers the sources again and runs the doctor. If the collector does not answer, the web says so and the change is applied when the collector starts.

<a id="settings"></a>
## 5. Settings of the Apache module

| Setting | Default | What it does |
|---|---|---|
| **Only the sources below** | off | Do not discover the logs from the Apache configuration: read only the sources added by hand. |
| **Sources added by hand** | none | Logs to read besides the discovered ones (or instead of them, with the option above). Up to 50. |
| **Apache configuration file** | empty | Empty: found automatically (`/etc/apache2/apache2.conf` on Debian, `/etc/apache2/httpd.conf` on Alpine; `/etc/httpd/conf/httpd.conf` is also recognised). An absolute path uses that file instead, if it exists. |
| **Discovery interval (seconds)** | 3600 | How often the Apache configuration is read again to find new vhosts and logs (60 to 86400). |
| **Blocking threshold of ModSecurity** | 0 | 0: read from the CRS configuration (`tx.inbound_anomaly_score_threshold` in `crs-setup.conf`), 5 if it is not there. Used to tell a match above the blocking threshold from one below it when the ModSecurity messages do not state the threshold themselves (0 to 1000). |
| **Learning days for new PHP files** | 3 | During the first days after the module first started, a PHP file never seen before is not reported as new by the rule `apache-webshell` (0 to 365). A file created or modified in its DocumentRoot in the last day always counts as new. |

Each **source added by hand** has these fields (* required):

| Field | Use |
|---|---|
| **Kind** * | `access.log`, `error.log` or `ModSecurity audit log` |
| **Path** * | Absolute path of the file |
| **Vhost** | Vhost of the lines, for logs whose lines do not say it |
| **LogFormat** | For access logs: a nickname (`localsiem_combined`, `combined`, `vhost_combined`, `common`, `combinedio`, or one defined in the Apache configuration) or the format itself. Empty: the usual formats are tried. |
| **Audit log type** | `Serial (one file)` or `Concurrent (one file per request)` |
| **Audit storage folder** | For the concurrent type: the folder of `SecAuditLogStorageDir` |

A file is read only once, even if it is both discovered and added by hand. A source that appears while localSIEM is running is read from its beginning if it is 5 MB or smaller, and from its end otherwise.

Two settings of **Administration › Settings** of localSIEM also act on this module: the **correlation window** (5 seconds: how long the three records of a request are awaited) and the **severity below the threshold** (`low`).

<a id="soc"></a>
## 6. What the Apache module sends to the SOC

For every request the module joins the access line, the error lines and the audit record with the same `UNIQUE_ID`. The access logs Apache writes by default (`combined`, `vhost_combined`, `common`) have no `UNIQUE_ID`: then each access line is joined to the audit record and the error lines of its own request by client IP, method, URI, status and time (±2 seconds), even when the same request repeats in the same second, and the event is marked as «weak correlation». The vhost comes from `%v` or, if the format lacks it, from the Host header and port of the audit record, chosen the way Apache chooses it; the time takes the microseconds of the audit record. Then it decides whether something has already been done about it («action taken»), reading the audit log first (`Action: Intercepted (phase N)`), then error.log (`Access denied with code NNN (phase N)`). A 403 without any trace of ModSecurity is not taken as a block: it is marked as doubtful.

| Situation | Goes to the SOC? |
|---|---|
| Blocked by ModSecurity in phases 1-2 (the application never received it) | **No.** It stays in localSIEM, searchable (`action:blocked`), and is counted in the context of the next alert of that IP. |
| Blocked in phases 3-4 (the application had already run it) | Yes |
| Rule matches with the engine in `DetectionOnly` | Yes |
| Rule matches below the blocking threshold | Yes |
| Signals of the rules of section 9 | Yes |

Severity of the alerts raised by ModSecurity matches (file `severity.yaml` of the module):

| Situation | Severity |
|---|---|
| Matches not blocked, answer 3xx, 4xx or 5xx | medium |
| Matches not blocked, answer 2xx | high |
| Blocked in phases 3-4 | high |
| Signs of success: an outbound rule (950-955) matched and nothing was blocked, or a database error followed the request | critical |
| Below the blocking threshold (often a false positive of the application itself) | low (the severity below the threshold of Administration › Settings) |

Each alert has a stable name (for example «Apache/ModSecurity: SQL injection not blocked (CRS 942)»), a description that ends with the query to paste in the localSIEM search (for example `ip:203.0.113.7 category:sqli`), and details: vhost, client IP, method, URI (masked), answer, user agent and the ModSecurity data (engine, action, phase, anomaly score, threshold, rules and matched data). When it leaves, the alert also carries the context of the IP: requests and blocked requests of the last hour, the rules that blocked it and the first time it was seen.

Passwords, cookies, `Authorization` headers and tokens are masked before anything is stored, also inside the request bodies, and request bodies never travel to the SOC. The response body (part E) and the full text of the rules run (part K) of the audit log are never kept.

<a id="doctor"></a>
## 7. Apache and ModSecurity requirements: the doctor

The doctor of the apache2 module reads the Apache configuration (without changing it) and checks each requirement. It runs when the collector starts, after every change of settings, at every discovery, with **Discover again and run the doctor** and with `manage.py doctor` (section 17), only while the module is on: while it is off because Apache or ModSecurity is missing, the page of the module shows those requirements instead (section 4). Statuses: OK, warning (it works with limits), error (must be fixed) and info (only matters in some situations).

| Check | Fine when | If not |
|---|---|---|
| Apache configuration | `apache2.conf` or `httpd.conf` (or the configured file) is found and read | Error: add the sources by hand (section 5). Parts that cannot be read are listed as warnings. |
| ModSecurity | `mod_security2` (ModSecurity 2) is loaded | Error. Debian: `apt-get install libapache2-mod-security2 modsecurity-crs && a2enmod security2`. Alpine has no package: build mod_security2 2.9 from source. ModSecurity 3 (libmodsecurity) is not supported. |
| OWASP CRS | The CRS files are included (the doctor shows how many and the anomaly threshold) | Error: `apt-get install modsecurity-crs`, or include `crs-setup.conf` and `rules/*.conf` after ModSecurity |
| SecRuleEngine | `On` (requests over the threshold are blocked in phase 2 and stay in localSIEM) or `DetectionOnly` (nothing is blocked: every match goes to the SOC) | Error if `Off`; warning if it is `Off` except in some vhosts, if it is missing (ModSecurity then defaults to `Off`) or if some vhosts set it `Off` |
| mod_unique_id | Loaded: ModSecurity works and the three sources of a request are joined by `UNIQUE_ID` | Error if ModSecurity is loaded: ModSecurity 2 inspects nothing without it (Alpine does not load it); otherwise warning (weak correlation). Debian: `a2enmod unique_id`; Alpine: `LoadModule unique_id_module modules/mod_unique_id.so` |
| Access log format | The access logs have client IP, time, request line and status, as the formats Apache writes by default do (OK, «Access logs in the format Apache writes»); with milliseconds, vhost, duration and `UNIQUE_ID` (`localsiem_combined`) they are joined by `UNIQUE_ID` | Warning if a format lacks any of the four, with the `localsiem_combined` format and its `GlobalLog` |
| mod_remoteip | Loaded with `RemoteIPHeader` | Info: only needed behind a proxy or a load balancer; without it every request seems to come from the proxy and the rules by IP do not work |
| Audit log | `SecAuditEngine RelevantOnly` (or `On`) with a `SecAuditLog` | Warning if it is off. Notes: concurrent type (works, but its files are usually mode 600 and unreadable: Serial is recommended), native format (JSON is recommended), part E logged (bulky and sensitive), part H missing (the action taken cannot be read from the audit log) |
| Masking at the source | A `sanitise` action exists | Warning, with the `SecAction` that masks passwords, tokens and cookies in the audit log on disk |
| Permissions | `localsiem` can read every source | Error. Debian: `usermod -aG adm localsiem`; Alpine: the `setfacl` commands shown. A source that does not exist yet is only info. |
| Piped logs | — | Warning: `\|/usr/bin/rotatelogs ...` and syslog cannot be read; write the log to a file too, or add the source by hand |
| Access log without data | — | Warning: a `CustomLog` uses a format that no `LogFormat` defines (or a `LogFormat` without any `%` directive), so Apache writes that same text on every line, without the client IP, the time or the request. localSIEM does not read that log and sees the requests of its vhost in its error log and in the ModSecurity audit log. The format of the logs of the server is never changed. |
| Engine seen Off | — | Error: the audit records report the engine as disabled |
| ModSecurity version | — | Info: the version read from the audit log |

The optional access log, for milliseconds, duration and joining by `UNIQUE_ID` (`GlobalLog` writes it for every vhost without touching their own logs):

```apache
LogFormat "%a %l %u [%{%d/%b/%Y:%H:%M:%S}t.%{msec_frac}t %{%z}t] \"%r\" %>s %O \"%{Referer}i\" \"%{User-Agent}i\" %v %D %{UNIQUE_ID}e" localsiem_combined
GlobalLog ${APACHE_LOG_DIR}/localsiem_access.log localsiem_combined
```

When a `GlobalLog` whose format has `%v` exists, the other access logs are not read (they would only repeat its lines). The recommended audit log:

```apache
SecAuditEngine RelevantOnly
SecAuditLogRelevantStatus "^(?:5|4(?!04))"
SecAuditLogType Serial
SecAuditLogFormat JSON
SecAuditLogParts ABIJFHKZ
SecAuditLog /var/log/apache2/modsec_audit.log
```

<a id="configure-apache"></a>
## 8. Applying the requirements: --configure-apache

The module never changes the Apache configuration by itself. `--configure-apache` asks it to apply the requirements, as root: with the command the web shows after installing the module (section 2) or with `manage.py apply-setup -- --configure-apache` (section 17):

1. It writes one file of its own: `/etc/apache2/conf-available/localsiem.conf` (Debian, enabled with `a2enconf localsiem`) or `/etc/apache2/conf.d/localsiem.conf` (Alpine). It holds the `localsiem_combined` format with its `GlobalLog`, the audit log settings above and the `SecAction` that masks sensitive values (id 77001).
2. It enables `mod_unique_id` (Debian: `a2enmod unique_id`; Alpine: a `LoadModule` inside the file). On Alpine the file also loads `mod_logio`, which the `%O` of the format needs and Alpine does not load by default (Debian has it built in).
3. It creates `localsiem_access.log` and `modsec_audit.log` in `/var/log/apache2` if they do not exist yet (group `adm` on Debian), before Apache creates them with its own mode, so the read access localSIEM gives covers them.
4. It runs `apache2ctl configtest` (Debian) or `httpd -t` (Alpine). If it passes, it reloads Apache (`systemctl reload apache2` or `rc-service apache2 reload`), never restarts it. If this ModSecurity does not accept `SecAuditLogFormat JSON`, it tries again with the native format. If it fails, it **undoes everything** and Apache keeps its previous configuration.

It does not install ModSecurity or the CRS, and it does not change `SecRuleEngine`: those stay the decision of the client. To see the file before applying it: `manage.py configure-apache` (section 17). To undo it later, delete that file (Debian: `a2disconf localsiem`) and reload Apache.

<a id="rules"></a>
## 9. Rules of the Apache module

The rules are evaluated on every event. A signal of a rule always goes to the SOC. In the page of the module each rule can be turned off, and its severity, threshold (1 to 100000) and window (1 to 86400 seconds) changed; the threshold and the window only apply to threshold and sequence rules. Its events can be found with `rule:localsiem:<id>`.

| Rule | Kind | Severity | When | Threshold / window |
|---|---|---|---|---|
| `apache-bruteforce` «brute force against a login page» | threshold | medium | POST requests not blocked from one IP to a login page of one vhost (`/wp-login.php`, `/xmlrpc.php`, `/administrator/index.php`, `/user/login`, `/login`, `/admin/login`, `/login.php`, `/admin.php`, `/signin`, `/auth/login`, `/phpmyadmin/index.php`) | 20 in 300 s |
| `apache-login-after-bruteforce` «successful login after a brute force» | sequence | high | At least 10 failed logins (POST answered 200, 401 or 403) to a login page, then one answered 302 or 303 (WordPress answers 200 to a failed login and 302 to a good one) | 10, within 1800 s |
| `apache-enumeration` «enumeration (burst of 404 answers)» | threshold | medium | 404 answers not blocked to one IP from one vhost | 30 in 60 s |
| `apache-sensitive-file` «sensitive file served» | match | high | A 2xx answer for a file that should not be public: `.env`, `.git/`, `.svn/`, `.hg/`, `.htaccess`, `.htpasswd`, dumps and backups (`.sql`, `.sql.gz`, `.bak`, `.old`, `.orig`, `.swp`, `.save`, `.backup`, `.dump`, names ending in `~`), `phpinfo`, `info.php`, `server-status`, `server-info`, copies of `wp-config.php` and `config.php`/`config.inc`, `.DS_Store`, private SSH keys, `composer.json`/`composer.lock`, `.aws/`, `backup.zip`/`.tar`/`.tar.gz`/`.tgz`/`.rar` | — |
| `apache-webshell` «possible web shell (POST to a new PHP file)» | match | critical | A POST answered 2xx to a PHP file created or modified in its DocumentRoot in the last day, or seen for the first time in the last hour (after the learning days) | — |
| `apache-db-error-after-attack` «database error after a suspicious request» | sequence | critical | A request that matched CRS rules and, from the same IP, a database error (SQL or PDO) in error.log | 1, within 30 s |

<a id="health"></a>
## 10. Health warnings of the Apache module

Besides the health warnings of localSIEM itself, the module checks every 5 minutes, at most, and sends to the SOC:

| Warning | Severity | What to do |
|---|---|---|
| ModSecurity is no longer loaded | high | It was loaded and is not any more: requests are not inspected. If nobody did it on purpose, someone may have turned the protection off. |
| ModSecurity engine turned Off | high | `SecRuleEngine` changed to `Off`, or the audit log reports the engine as disabled. Check the Apache configuration and its recent changes. |
| Real client IP missing (mod_remoteip) | medium | In the last hour, at least 90 % of at least 100 requests came from one private or local address: the web is probably behind a proxy. Configure `mod_remoteip`. Sent at most once a day. |

What was already reported is remembered across restarts, so an update does not send it again. Because of these warnings, a module that is on is never turned off by itself when Apache or ModSecurity disappears.

<a id="privesc"></a>
## 11. The privilege escalation module

The **privesc** module («Privilege escalation») watches what people and services run on the server and reports the steps of an escalation to root: reconnaissance, the search for setuid programs, enumeration tools such as linpeas, known exploits, reverse shells, root gained without sudo or su, the back doors left behind and the attempts to blind the monitoring. It also reviews the attack surface of the server: setuid programs, capabilities and sensitive files writable by others (section 16).

It reads up to three sources, depending on what the server has:

| Source | What it sees | Where it works |
|---|---|---|
| **auditd** (`/var/log/audit/audit.log`) | Every program run by a person (also from scripts and exploits), setuid programs, shells and tools run by service accounts (a web shell), sudo, su, pkexec and SSH logins, changes of sensitive files, setuid bits set, kernel modules, ptrace, files refused, auditing turned off | Bare metal and virtual machines. **Not inside a container** (LXC, podman, systemd-nspawn, Docker): the audit of the kernel is not namespaced, so auditd only runs on the host. |
| **bash hook** (`/var/log/localsiem-privesc/<uid>.log`) | Every command typed in an interactive bash, builtins included (`pwd`, `cd`, `unset HISTFILE`, `trap`), with its folder, terminal and SSH address | Everywhere, containers included. A user can avoid it (`bash --norc`, `trap - DEBUG`), and doing so is reported. It does not see the shells of busybox (`ash`, the default of Alpine) nor scripts. |
| **syslog** (`/var/log/auth.log`, `/var/log/secure` or `/var/log/messages`) | sudo, su, pkexec, doas, SSH logins and, if **snoopy** is installed, every program run | Read when auditd is not running (containers) or snoopy is installed (setting **Read syslog**). It needs a syslog daemon that writes a file: the journal of systemd alone is not read. |

On a bare-metal server or a virtual machine, install **auditd**: it is the source a user cannot avoid. In a container, run auditd with these rules on the host and, inside, rely on the hook and on snoopy.

A note about `pwd`, `cd` and the other builtins of the shell: they never run a program, so auditd and snoopy do not see them; only the hook does. A single `whoami` or `pwd` is never an alert: the module counts the **distinct** reconnaissance commands of each session within a window, and only a burst of them is (section 13).

What each event of the module holds, and how to search it:

| Column | Holds | Example search |
|---|---|---|
| `vhost` | The person: the login user (it stays the same through sudo and su); for the hook, the owner of the file | `module:privesc vhost:alice` |
| `method` | Kind of event: `exec` (program run, auditd or snoopy), `command` (hook), `shell` (an interactive bash starts), `sudo`, `su`, `pkexec`, `doas`, `login`, `pam`, `file` (sensitive file changed), `chmod` (setuid bit), `kmod`, `ptrace`, `denied` (file refused), `audit_config`, `auditd`, `crash` | `module:privesc method:sudo` |
| `uri` | The command line (passwords masked) | `module:privesc uri:*linpeas*` |
| `path` | The program run, or the file changed | `module:privesc path:/tmp/*` |
| `ip` | The SSH address of the session, when it is known | `module:privesc ip:203.0.113.7` |
| `score` | Distinct reconnaissance commands of the session in the window | `module:privesc score:>=8` |
| `action` | `blocked` when the system itself stopped it: a program that could not run, sudo or su refused, a file refused | `module:privesc action:blocked` |
| `source` | `audit`, `hook` or `syslog` | `module:privesc source:hook` |

Rules about attempts (repeated sudo failures, many files refused) count the blocked events anyway; the others only look at what really ran.

The page of the module, `/admin/dashboard/modules/installed/privesc/`, has the same parts as the page of the Apache module (section 4): header (with **Discover again and run the doctor**, **Reconfigure** and **Uninstall**), settings (section 12), sources (`audit`, `hook` with one file per user, `syslog`; and the ones not read, with the reason), doctor (section 14) and rules (section 13).

<a id="privesc-settings"></a>
## 12. Settings of the privilege escalation module

| Setting | Default | What it does |
|---|---|---|
| **Audit log** | empty | Empty: `log_file` of `/etc/audit/auditd.conf`, or `/var/log/audit/audit.log`. |
| **Read syslog** | Automatic | Automatic: only when auditd is not running or snoopy is installed. Always, or Never. |
| **Syslog file** | empty | Empty: `/var/log/auth.log`, `/var/log/secure` or `/var/log/messages`, the first one that exists. |
| **Ignored users** | empty | Comma separated. Their commands are stored and searchable but never raise an alert: automation accounts (ansible, backups). The user `localsiem` is always ignored. |
| **Administrator groups** | `sudo,wheel,admin` | Comma separated. Their members (and root) get the higher reconnaissance threshold and may list their sudo rights without an alert. |
| **Reconnaissance window (seconds)** | 120 | Window in which the distinct reconnaissance commands of a session are counted (10 to 3600). |
| **Reconnaissance threshold** | 8 | Distinct reconnaissance commands in the window that make a burst, for users and service accounts (2 to 500). |
| **Reconnaissance threshold for administrators** | 20 | The same for root and the administrators, who run them as part of their job (2 to 500). |
| **Automated enumeration threshold** | 40 | Distinct reconnaissance commands in the window that only a script runs (linpeas-like), for everybody (5 to 1000). |
| **Learning days of the service accounts** | 3 | During the first days after the module first started, the programs each service account runs (`www-data` running `sh -c sendmail`) are learnt without alerts (0 to 365). |
| **Hours between scans of setuid programs** | 24 | How often the setuid and setgid programs and the file capabilities are searched (section 16). 0: never (0 to 168). |
| **Folders scanned** | `/usr,/bin,/sbin,/lib,/lib64,/opt,/home,/srv,/tmp,/var/tmp,/dev/shm,/var/www,/etc` | Comma separated; each one is walked without leaving its file system. The folders of containers and of `/proc` and `/sys` are always skipped. |
| **Discovery interval (seconds)** | 300 | How often the files of the hook of new users, syslog and the state of auditd are looked for (60 to 86400). The shortest interval of the modules that are on applies to all of them. |

What counts as reconnaissance: `whoami`, `id`, `groups`, `uname`, `hostname`, `w`, `who`, `last`, `ps`, `ss`, `netstat`, `ip`, `ifconfig`, `env`, `pwd`, `history`, `getcap`, `lsmod`, `dmesg`, `mount` and similar; `sudo -l`, `crontab -l`, `systemctl list-*`, the package lists; `which`, `locate`, `command -v`; `docker ps` and similar; every different `find`; reading `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`, `/etc/*-release`, `/proc/version`, `/root/...`, histories, SSH keys and `.env` files; listing `/root`, `/home`, `/opt`, `/tmp`, the cron folders...; `grep -r password`; and `<program> --version`. Each different command of a session counts once within the window.

<a id="privesc-rules"></a>
## 13. What the privilege escalation module sends to the SOC: its rules

Every alert of the module comes from one of its rules (they work the same whatever source saw the command), except the ones of section 16. As for Apache, each rule can be turned off and its severity, threshold and window changed in the page of the module; its events can be found with `rule:localsiem:<id>`. None fires for the **Ignored users**.

| Rule | Kind | Severity | When | Threshold / window |
|---|---|---|---|---|
| `privesc-recon-burst` «reconnaissance burst» | match | medium | The session reached the reconnaissance threshold (section 12) | — |
| `privesc-enumeration` «automated enumeration (linpeas-like)» | match | high | The session reached the automated enumeration threshold, even with a renamed script | — |
| `privesc-suid-hunt` «search for setuid programs or capabilities» | match | high | `find ... -perm -4000` (or `-u=s`, `/6000`, `-2000`...), `getcap -r`, `find -writable` | — |
| `privesc-sudo-list` «sudo rights listed by a non-administrator» | match | medium | `sudo -l` by a user or service account that is not an administrator | — |
| `privesc-known-tool` «known enumeration tool» | match | high | linpeas, LinEnum, lse.sh, linux-exploit-suggester, les.sh, pspy, unix-privesc-check, linuxprivchecker, traitor, BeRoot, GTFONow, PEASS, deepce, CDK, sudo_killer, suid3num, mimipenguin, LaZagne, pwncat, searchsploit | — |
| `privesc-exploit` «known exploit» | match | critical | PwnKit, DirtyPipe, Dirty COW, Baron Samedit (`sudoedit -s '\'`), Looney Tunables (`GLIBC_TUNABLES`), GameOver(lay), nf_tables (CVE-2024-1086), CVE-2023-22809 (`EDITOR=... -- /...`), polkit CVE-2021-3560 (`dbus-send ... CreateUser`), `LD_PRELOAD` with sudo, a script named after a CVE, programs named `exploit`, `getroot`, `rootme` | — |
| `privesc-pwnkit` «PwnKit (pkexec run without arguments)» | match | critical | `pkexec` run with zero arguments (auditd) | — |
| `privesc-pwnkit-log` «pkexec reports a PwnKit attempt» | match | critical | pkexec logs `GCONV_PATH`, «suspicious content» or «was not found the /etc/shells» (syslog) | — |
| `privesc-suid-escape` «root inherited from a setuid program» | match | critical | A program that is not setuid runs with the effective uid of root and the real uid of a user: a setuid program was abused (GTFOBins). Mount helpers, D-Bus, polkit and X are excepted. | — |
| `privesc-root-without-door` «root without sudo, su or pkexec» | match | critical | auditd: a session of a person whose start was seen runs programs as root without having gone through sudo, su, pkexec or doas (kernel exploits). Hook: a root bash started by a program of an ordinary user that is not su, sudo, sshd, login... | — |
| `privesc-root-shell-interpreter` «root shell started by an interpreter» | match | high | Hook: a root bash whose parent is python, perl, ruby, awk, gdb... | — |
| `privesc-file-capabilities` «program gained root capabilities from its file» | match | high | A user ran a program whose file gives it `cap_setuid`, `cap_dac_override`, `cap_sys_admin`... (auditd) | — |
| `privesc-tmp-exec` «program run from a world-writable folder» | match | high | A program in `/tmp`, `/var/tmp`, `/dev/shm` or `/run/user/<uid>` | — |
| `privesc-compile-tmp` «program compiled in a temporary folder» | match | high | `gcc`, `cc`, `clang`, `make`... in or on files of a temporary folder | — |
| `privesc-download-shell` «downloaded script run by a shell» | match | high | `curl ... \| sh`, `bash -c "$(curl ...)"`, `bash <(wget ...)`, or a downloader followed by a shell in the same pipeline | — |
| `privesc-reverse-shell` «reverse shell» | match | high | `/dev/tcp/`, `nc -e`, `ncat --exec`, `socat exec:`, `mkfifo ... \| nc`, python/perl/php/ruby/lua/node sockets, `openssl s_client ... \| sh`, `awk /inet/tcp` | — |
| `privesc-tty-upgrade` «shell upgraded to a full terminal» | match | high | `pty.spawn`, `script ... /dev/null`, `stty raw -echo`, `socat ... pty`, `expect ... spawn sh` | — |
| `privesc-service-recon` «service account ran reconnaissance commands» | match | high | `www-data`, `mysql` and other service accounts running `whoami`, `id`, `uname`... (a web shell) | — |
| `privesc-service-new-program` «service account ran a program it never ran before» | match | high | After the learning days, a service account runs a shell, interpreter or tool it never ran (`sh -c id` where it only ran `sh -c sendmail`) | — |
| `privesc-container-escape` «container used to reach the host as root» | match | high | Someone who is not root runs `docker run -v /:/...`, `--privileged`, `--pid=host`, `nsenter -t 1`, `lxc config set ... security.privileged true`, `lxc config device add ... source=/`, `debugfs /dev/...` | — |
| `privesc-auth-failures` «repeated sudo or su failures» | threshold | medium | Failed sudo, su, pkexec or doas of one user | 3 in 600 s |
| `privesc-sensitive-file` «account, sudo, PAM or preload file changed» | match | high | `/etc/passwd`, `shadow`, `group`, `gshadow`, `sudoers`, `sudoers.d`, `doas.conf`, `ld.so.preload`, `ld.so.conf`, `pam.d`, `security` changed by a program that is not a package or account tool (auditd) | — |
| `privesc-persistence-file` «SSH, cron or service file changed» | match | medium | `/root/.ssh`, `sshd_config`, cron files, `/etc/systemd/system`, `/etc/init.d`, `rc.local`, `/etc/local.d` changed (auditd) | — |
| `privesc-monitoring-changed` «auditd configuration or command hook changed» | match | medium | `/etc/audit`, the hook or the bashrc changed (expected while `--configure-privesc` runs) | — |
| `privesc-suid-set` «setuid or setgid bit set on a file» | match | high | `chmod u+s`/`g+s` outside the package manager (auditd) | — |
| `privesc-setcap` «file capabilities set» | match | high | `setcap ... cap_...` | — |
| `privesc-kernel-module` «kernel module loaded from a session» | match | high | A module loaded or removed from the session of a person (auditd) | — |
| `privesc-ptrace` «process attached with ptrace» | match | medium | `PTRACE_ATTACH` or `PTRACE_SEIZE` by a person (auditd) | — |
| `privesc-denied-burst` «many files refused (enumeration)» | threshold | medium | Files refused (`EACCES`, `EPERM`) to one user (auditd) | 30 in 60 s |
| `privesc-sensitive-denied` «attempt to read the password hashes or files of root» | match | medium | `/etc/shadow`, `/etc/gshadow`, `/etc/sudoers`, `/etc/sudoers.d/` or `/root` refused to a user (auditd) | — |
| `privesc-history-tampering` «shell history erased or turned off» | match | medium | `unset HISTFILE`, `HISTFILE=/dev/null`, `HISTSIZE=0`, `history -c`, `set +o history`, `ln -s /dev/null ~/.bash_history`, `rm .bash_history`... | — |
| `privesc-hook-disabled` «command hook of localSIEM avoided» | match | high | `trap - DEBUG`, `unset ...LocalsiemPrivesc...`, `bash --norc`/`--noprofile`, `env -i bash` | — |
| `privesc-hook-forged` «forged line in the command file of a user» | match | medium | A line of a hook file claims another uid than the owner of the file | — |
| `privesc-audit-stop-command` «command to turn auditd off» | match | critical | `auditctl -e 0`, `auditctl -D`, `auditctl -a never`, `systemctl stop/disable/mask auditd`, `service auditd stop`, `pkill auditd`, erasing `/var/log/audit` or `/etc/audit` | — |
| `privesc-audit-disabled` «auditing turned off» | match | critical | The kernel reports `audit_enabled=0` (auditd) | — |
| `privesc-auditd-stopped` «auditd stopped by a process» | match | high | auditd stopped at the request of a process other than init (a shutdown of the server is not reported) | — |
| `privesc-crash` «setuid or temporary program crashed» | match | medium | A setuid program, or one in a temporary folder, crashed (auditd `ANOM_ABEND`): often a failed exploit | — |

Each alert has a stable name, a description that ends with the query to paste in the localSIEM search, and details: user, kind of account (`root`, `admin`, `user`, `service`), real and effective user, command, program, folder, terminal, session, source (`auditd`, `hook`, `snoopy`, `syslog`), client IP and, when they apply, the parent program, the file changed, the reconnaissance commands counted, the capabilities and the mode set. When it leaves, the alert also carries the context of the session: whether its start was seen, whether it went through sudo or su, its SSH address and its **last 20 commands**, so the analyst reads what led to the alert without searching.

The same command can be seen by more than one source (the hook and auditd): the alerts are grouped by module, user, IP, category and severity, so it still makes one alert. Passwords in command lines (`mysql -p...`, `sshpass -p`, `curl -u user:pass`, `PASSWORD=...`, URLs with a password) are masked before anything is stored, also in the hexadecimal of the audit records.

<a id="privesc-doctor"></a>
## 14. Requirements of the privilege escalation module: the doctor

**Requirements.** The module needs one way to see the commands: **auditd** (outside a container), **bash** (for its hook) or **snoopy**. With none of them it is installed turned off, with the command that installs one; **Reconfigure** checks again. It installs none of them by itself.

The doctor runs like the one of Apache (section 7):

| Check | Fine when | If not |
|---|---|---|
| auditd | auditd is running | Warning if it is not installed (Debian: `apt-get install auditd`; Alpine: `apk add audit && rc-update add auditd && rc-service auditd start`); error if it is installed but stopped (`systemctl enable --now auditd`). Info inside a container: auditd is not available, run it on the host. |
| Audit rules | `/etc/audit/rules.d/90-localsiem-privesc.rules` of this version is installed | Warning, with the command of section 15 |
| Records of the rules | Records with a key `lsiem_*` are being read (the time of the last one) | Warning if auditd writes but none carries a localSIEM key: the rules are not loaded |
| Audit log | `localsiem` can read it | Error, with the command of section 15 |
| Group of the audit log | auditd creates its logs for the group `adm` | Warning: after a rotation the new log may not be readable; `--configure-privesc` sets `log_group = adm` |
| bash | — | Info if bash is not installed: the hook only works in bash |
| bash hook | Installed and the same as this version of the module | Warning if missing or outdated (apply section 15 again after updating the module) |
| Folder of the hook | `/var/log/localsiem-privesc` is `root:localsiem` with mode `3753` | Error, with the command of section 15 |
| Files of the hook | Each `<uid>.log` belongs to its user and can be read | Error if one belongs to another user (someone took it); warning if its user made it unreadable |
| syslog | The syslog file is read | Error if it cannot be read (`setfacl -m g:localsiem:r <file>`); warning if there is neither auditd nor a syslog file (Debian: `apt-get install rsyslog`; Alpine: `rc-update add syslog boot && rc-service syslog start`) |
| snoopy | Installed | Warning without auditd: the commands of scripts and web shells are not seen (Debian: `apt-get install snoopy`; Alpine: build it from source) |
| Setuid programs and capabilities | — | Info: the last scan (section 16). Warning with the setuid programs that give a root shell (GTFOBins) and with the programs whose capabilities are root in practice |
| Sensitive files | None writable by someone other than root | Error for each one (`/etc/passwd`, `sudoers`, cron, `/etc/profile.d`, the folders of the `PATH` of root, `docker.sock`...), with the `chown`/`chmod` that fixes it |
| Privileged groups | — | Warning with the members of `docker`, `lxd`, `incus-admin`, `disk` and `libvirt`: they are root in practice |

<a id="configure-privesc"></a>
## 15. Applying the requirements: --configure-privesc

The module never changes the system by itself. `--configure-privesc` applies its requirements, as root: with the command the web shows after installing the module or after **Reconfigure** (section 2), or with `manage.py apply-setup -- --configure-privesc` (section 17). It installs no software, and running it again is safe:

1. **auditd** (if installed, and not in a container): it writes `/etc/audit/rules.d/90-localsiem-privesc.rules` and loads it with `augenrules --load`. The rules audit every program run by a person (login uid 1000 or more) and the programs run with the effective uid of root by someone else; the shells, interpreters and tools (`sh`, `bash`, `python3`, `perl`, `php`, `curl`, `wget`, `nc`, `id`, `whoami`...) run by service accounts; `chmod` with the setuid or setgid bit; kernel modules; `ptrace`; files refused to people; and the changes of accounts, sudoers, PAM, preload, SSH, cron, services, `/etc/audit` and the hook. On 64-bit x86 they cover 32-bit programs too (if the kernel refuses them, they are loaded without them). If auditd does not accept the rules, the previous file comes back. If the rules are immutable (`-e 2`), they load at the next reboot. It also sets `log_group = adm` in `auditd.conf`, so the logs auditd creates when it rotates them stay readable by `localsiem` (and, on Alpine, adds `localsiem` to `adm`), and creates `/root/.ssh` (empty, 700) so that a key added later is seen.
2. **bash hook**: it copies `/etc/localsiem-privesc/hook.bash`, writes `/etc/profile.d/localsiem-privesc.sh` and adds one line to `/etc/bash.bashrc` (Debian) or `/etc/bash/bashrc` (Alpine). It creates `/var/log/localsiem-privesc` (`root:localsiem`, mode `3753`: every user can create their own file there, nobody can list the folder nor delete the files of the others) and a file `<uid>.log` (mode 640) for root and each person. A file that belongs to the wrong user is moved aside (`<uid>.log.wrong-owner-<date>`) and a good one is created. The hook writes at most 30 commands per second per shell and never runs a program for each command.
3. **snoopy** (if installed): it sets `message_format` in `/etc/snoopy.ini` so that each line carries the login, the uid and the effective uid, the pid and the parent.

To see the rules before applying them: `manage.py doctor` lists what is missing; the rules are in `/etc/audit/rules.d/90-localsiem-privesc.rules` once applied. To undo it: delete that file and run `augenrules --load`; delete `/etc/profile.d/localsiem-privesc.sh`, `/etc/localsiem-privesc/` and the line of the bashrc that follows «localSIEM privesc: command hook»; and delete `/var/log/localsiem-privesc` if you do not want to keep the commands.

<a id="privesc-health"></a>
## 16. Attack surface and health warnings of the privilege escalation module

Besides its rules, the module looks at the server itself and sends to the SOC:

| Warning | Severity | When |
|---|---|---|
| New setuid or setgid program | high | A scan finds a setuid or setgid program that the previous scan did not have (the first scan is only the reference). An attacker who became root often leaves a setuid shell behind; a package update can also add one. |
| New setuid program in a writable folder | critical | The same, in `/tmp`, `/var/tmp`, `/dev/shm`, `/home`, `/srv` or `/var/www` |
| New setuid program of GTFOBins | critical | The same, for a program that gives a root shell when setuid (`bash`, `find`, `python`, `vim`, `less`, `cp`...) |
| New capabilities | high | A program got capabilities that are root in practice (`cap_setuid`, `cap_dac_override`, `cap_sys_admin`...) |
| Sensitive file writable by someone other than root | critical | Checked every hour: `/etc/passwd`, `/etc/shadow` (also readable by everybody), `sudoers`, cron, `/etc/profile.d`, PAM, services, `ld.so.preload`, the folders of the `PATH` of root, `docker.sock`... Reported once per file and problem. |
| The command file of a user was taken by another user | high | A `<uid>.log` of the hook belongs to another user or is not a file |
| auditd stopped (health of localSIEM) | high | auditd was running and is not any more (outside containers) |

The scan runs in the background, at most every **Hours between scans of setuid programs** (the first one five minutes after the collector starts), through the **Folders scanned**, as the `localsiem` user (what it cannot read is skipped), and stops after 3 million files or 15 minutes. Its result, with the GTFOBins and capabilities found, is shown in the doctor. The severities of these warnings are in `severity.yaml` of the module. What was already reported is remembered across restarts.

<a id="cli"></a>
## 17. Command line

As root, `/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py <command>`:

| Command | Use |
|---|---|
| `modules` | Installed modules: id, version, enabled, disabled or not loaded, and folder, with the requirements it lacks, if any; and the modules that could not be loaded, with the error |
| `doctor` | For every enabled module: each check (`[ OK ]`, `[WARN]`, `[FAIL]`, `[INFO]`) with the snippet that fixes it, and the sources found; for a module off because a requirement is missing, its requirements. `--json` gives the same as JSON. |
| `configure-apache` | Prints the file that `--configure-apache` would write |
| `read-paths` | Folders the modules read, to which localSIEM gives read access as root |
| `apply-setup -- OPTION` | As root: applies the setup option of an installed module (`--configure-apache`, section 8; `--configure-privesc`, section 15) |
| `setup-modules [OPTION...]` | As root: the command the web shows; read access to the folders of the modules, the setup options added (for example `--configure-privesc`) and a restart of localSIEM |

Run the doctor as the `localsiem` user to see its real permissions:

```bash
runuser -u localsiem -- /opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor   # Debian
su -s /bin/sh localsiem -c "/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor"   # Alpine
```
