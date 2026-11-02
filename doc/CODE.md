# localSIEM-modules code reference

This CODE is also available in:\
[de-DE](CODE.de-DE.md), [en-GB](CODE.en-GB.md), en-US, [es-AR](CODE.es-AR.md), [es-ES](CODE.es-ES.md), [fr-FR](CODE.fr-FR.md), [he-IL](CODE.he-IL.md), [hi-IN](CODE.hi-IN.md), [it-IT](CODE.it-IT.md), [ja-JP](CODE.ja-JP.md), [ko-KR](CODE.ko-KR.md), [pt-BR](CODE.pt-BR.md), [pt-PT](CODE.pt-PT.md), [ru-RU](CODE.ru-RU.md), [zh-CN](CODE.zh-CN.md)

## Index

1. [Architecture and design decisions](#architecture)
2. [Module map](#modules)
3. [Key symbols](#symbols)
4. [Main call paths](#flows)
5. [Entry points](#routes)
6. [Impact analysis](#impact)
7. [Extension points](#extensions)

[Installation](../README.md) · [User manual](MANUAL.md) · [localSIEM code reference](../../localSIEM/doc/CODE.md)

<a id="architecture"></a>
## 1. Architecture and design decisions

This project holds the installable modules of localSIEM (sibling project `../localSIEM`). It has no service and no installer of its own: modules are installed only from the localSIEM web, in Modules › Installable (they are updated and uninstalled in Modules › Installed), which downloads this repository (branch `main`) and copies each module folder, `mod-<name>/`, to `/opt/localsiem/modules/<name>/`; the installer of localSIEM installs the core only, never a module, and localSIEM has no modules of its own. The localSIEM processes (collector, web, `manage.py`) load it. The `mod-` prefix belongs only to the name of the folder in this repository: the module itself (the `id` of its `module.json`, its options, its settings and its installed folder) keeps its name without it. Today there are two modules: `apache2` (folder `mod-apache2/`) and `privesc` (folder `mod-privesc/`).

### Why the modules live outside the core

The core of localSIEM ([backend/core/](../../localSIEM/backend/core/)) is generic: storage, search, rules engine, grouping, SOC queue, heartbeat and health know nothing about Apache. What a service means (where its logs are, how they are framed and parsed, how records become one event, what counts as already resolved, its rules and its requirements) lives in a module. Keeping the modules in their own project means that:

- a module is versioned (`version`), declares the lowest localSIEM it needs (`core`) and is updated, added or turned off without a new localSIEM release;
- the core imports no module by name and has no module of its own: the registry ([backend/core/registry.py](../../localSIEM/backend/core/registry.py)) only scans `/opt/localsiem/modules/` (`LOCALSIEM_MODULES_PATH` in development copies), where the web installs the modules of this repository;
- a module that fails to load never stops the others: its error is listed in the web (state «Error») and by `manage.py modules`;
- a module never modifies the core: `backend/core/module.py` and `backend/core/registry.py` are the whole contract.

### The contract: module.json, locales and a Module subclass

**`module.json`** (checked by `fReadManifest`):

| Key | Default | Meaning | apache2 | privesc |
|---|---|---|---|---|
| `id` | required | Name of the module folder without the `mod-` prefix (the name of the installed folder), `[a-z][a-z0-9_]{1,31}`; also the `vName` of the class | `apache2` | `privesc` |
| `version` | `"0"` | Version of the module, shown in the web and by `manage.py modules` | `1.3.2` | `1.1.2` |
| `core` | `"0"` | Lowest localSIEM version it needs; a higher one than the `cVersion` of the installed localSIEM means the module is not loaded | `2.2.0` | `2.2.0` |
| `entry` | required | `"file:Class"`: `file` without `.py` (`[a-z][a-z0-9_]{0,63}`), `Class` a subclass of `Module` | `module:ApacheModule` | `module:PrivescModule` |
| `default_enabled` | `true` | Whether it runs until the administrator decides (`modules.<id>.enabled`) | `true` | `true` |
| `read_paths` | `[]` | Absolute folders that localSIEM, as root, lets the `localsiem` user read (the command the web shows after installing, after **Reconfigure** and after an update that changes them) | `["/var/log/apache2"]` | `["/var/log/audit"]` |
| `install_requirements` | `{}` | Commands that install on the server, as root, the software the module needs, for each system (`debian`, `alpine`): one command per line, without shell operators, because the web also shows them with `sudo` in front (`fCheckInstallRequirements` of the core). Shown in Modules › Installable › Requirements, never run | Debian: Apache, ModSecurity 2, the CRS, `a2enmod`, the recommended ModSecurity configuration if there is none, restart; Alpine: Apache | Debian: auditd and rsyslog; Alpine: auditd |
| `setup_option` | — | Not used by any module: the core ignores it (the registry drops it), because a module never changes the server; `module.json` files of older versions may still have it | not set | not set (`--configure-privesc` was removed in 1.1.0) |
| `settings` | `[]` | Description of each setting: the web builds its form from it | 6 settings | 13 settings |

Each setting has a `key` (`[a-z][a-z0-9_]{1,31}`), a `type`, usually a `default`, and the attributes of its type. `fValidateSettings` / `fCleanValue` / `fCleanRecords` check what the administrator saves:

| Type | Attributes | Web control | Accepted values |
|---|---|---|---|
| `boolean` | — | checkbox | `true` / `false` |
| `integer` | `min`, `max` | number field | an integer within `min`..`max` |
| `string` | `max_length` (500) | text field | text without control characters, trimmed, up to `max_length` |
| `path` | — | monospace text field | empty or absolute (starts with `/`), up to 1024 characters |
| `choice` | `choices` (required), `required` | list (with «—» when not required) | one of `choices`, or empty |
| `records` | `fields` (required: settings of the other types), `max_items` (50) | one block per record with Add and Remove | a list of up to `max_items` records; each field is checked, `required` fields cannot be empty and empty fields are dropped |

**`locales/<language>.json`** (de-DE, en-GB, en-US, es-AR, es-ES, fr-FR, he-IL, hi-IN, it-IT, ja-JP, ko-KR, pt-BR, pt-PT, ru-RU, zh-CN), read by `fReadTexts` and shown by the web (`modules.js fModuleText`, which falls back to en-US and then to the key):

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

A missing or broken locale file only loses its language.

**The `Module` subclass** ([backend/core/module.py](../../localSIEM/backend/core/module.py)). The registry creates it as `Class(pSettings, pMasker, pStorage, pManifest)`. Its hooks:

| Hook | Called by | Default | `ApacheModule` | `PrivescModule` |
|---|---|---|---|---|
| `mStart()` | collector, once, with the storage ready | nothing | saves `apache.first_start` (start of the learning days) | saves `privesc.first_start`; loads `privesc.sessions`, `privesc.surface` and `privesc.health` |
| `mEnabled()`, `mModuleSettings()`, `mReload()` | collector, web | from `modules.<id>` over the defaults of `module.json` | inherited | inherited; `mReload` also empties the cache of `mSettings` |
| `mDiscoveryInterval()` | collector (shortest of the enabled modules, at least 60 s) | `discovery_interval_seconds` or 3600 | inherited | inherited (default 300) |
| `mDiscover()` | collector (start, interval, reload, doctor request), `manage.py doctor` | `[]` | sources `{key, path, kind, format, vhost, audit_type, storage_dir}` from the Apache configuration and the manual sources | `fDiscoverSources`: the audit log and syslog |
| `mCreateFramer(pSource)` | collector, per source | `LineFramer` | `AuditFramer` for the native serial audit log | inherited (`LineFramer`) |
| `mParse(pSource, pUnit, pReceived)` | collector, per unit | required | record of `access`, `error` or `audit` | record of `audit` or `syslog` |
| `mCreateCorrelator()` | collector, at start | required | `Correlator` (window and weak correlation from the core settings) | `Correlator`: audit records by serial (EOE or 2 s); syslog lines at once |
| `mBuildEvent(pTransaction)` | collector, per due transaction | required | event with `action` and `detections` | event with the flags the rules match; no detections of its own |
| `mRulesPath()` / `mRuleFunctions()` | collector, when loading the rules | `None` / `{}` | `rules/` of its folder / `{"apache2.new_php": mIsNewPhp}` | `rules/` of its folder / inherited `{}` |
| `mDetectionFromSignal(pEvent, pSignal)` | collector, per rule signal (optional: looked up with `hasattr`) | generic detection | detection with request details and `{rule: {id, count}}` | detection with user, command, program, session, parent, file... |
| `mEnrich(pDetection)` | collector, with the group, before building the alert | `{}` | context of the IP in the last hour | context of the session: start seen, door, SSH address, last 20 commands |
| `mDoctor()` | collector (state `<id>.doctor`), `manage.py doctor` | `[]` | `fRunDoctor` | `fRunDoctor` (auditd and what its rules recorded, syslog, snoopy, what the module sees, files of version 1.0.0, attack surface) |
| `mHealth(pNow)` | collector, every 60 s, enabled modules only | `[]` | ModSecurity unloaded or Off, real client IP missing (at most every 300 s) | saves the sessions; scan results; every 300 s: auditd stopped, sensitive files writable (hourly), starts the scan of setuid programs |
| `mSkipped()` | collector state, `manage.py doctor` | `[]` | piped logs, logs covered by the `GlobalLog`, access logs without data (`format_without_data`) | syslog not read (auditd running, `syslog_mode` never), audit log missing |
| `mSetLowDisk(pLowDisk)` | collector, disk level | nothing | stops storing audit headers and bodies | inherited |
| `mDisplayRecord(pRecord)` | web, request card | `{}` | headers and body of the stored audit record (`fAuditDisplay`) | inherited |
| `mRequirements()` | core, localSIEM 2.2.0 or newer: first installation, collector start and reload, **Reconfigure** in the web, `manage.py modules` and `doctor` | `[]` (no requirements) | `apache_config` and `modsecurity` (`fRequirementChecks`) | `command_source`: any source `localsiem` can read, the audit log (auditd running, not in a container) or syslog (with snoopy, if installed); `audit_log` / `syslog` when a source exists but cannot be read |

The core has no `mSetupSnippet` nor `mApplySetup` any more: modules have no setup options and never change the server.

Records are dicts with `time`, `received`, `module` (the id: the collector picks the correlator by it), `source`, `source_key`, `correlation`, `parse_status` (`ok`, `partial`, `unparsed`), `fields` and `raw` (masked), plus optionally `search` (the text indexed for full-text search). Events have the columns of the events table (`lEventColumns` in `storage_sqlite.py`) plus `record_ids`, `rule_hits` and `detections`. A detection has `module`, `vhost`, `ip`, `category`, `severity`, `rule`, `type`, `description`, `search`, `details`, `time` and `uid`.

### Requirements: a module never installs what it watches

Installing a module never installs the software it watches: the apache2 module installs neither Apache nor ModSecurity, and the privesc module installs neither auditd, a syslog daemon nor snoopy (its requirement, `command_source`, is any source the `localsiem` user can read: the audit log with auditd running outside a container, or syslog; `fRequirementChecks` of `mod-privesc/doctor.py`). The module itself defines what it needs before it can be turned on, in `mRequirements()` (localSIEM 2.2.0 or newer): a list of checks in the format of the doctor, met when none has the status `error`. The apache2 module returns `apache_config` (an Apache configuration is found: `apache2.conf`, `httpd.conf` or the file of the setting `config_file`) and `modsecurity` (`mod_security2` is loaded; ModSecurity 3 does not count), which `fRequirementChecks` takes from the first checks of the doctor; without Apache, both are errors. What installs that software is declared in `install_requirements` of `module.json`: the web shows it before installing the module (Modules › Installable › Requirements), for the system of the server, and never runs it. The core:

- installs the module turned off (`modules.<id>.enabled = false`) when a requirement is missing on its first installation and the administrator never decided; an update never changes `enabled`;
- does not let it be turned on while a requirement is missing: the switch is locked and the web shows the requirements with their `fix`;
- never turns off by itself a module that is on and loses a requirement: its doctor and its health warnings (`mHealth`: «ModSecurity is no longer loaded») report it, and turning it off would silence them;
- checks the requirements again when the collector starts or reloads, and with **Reconfigure** on the page of the module (also when it is off): if they are met, it unlocks the switch, the administrator turns the module on, and the web shows the command to run as root that lets `localsiem` read the logs created after the installation (`read_paths`).

### Loaded as a namespace package

There is no `__init__.py` anywhere (Python 3.13 implicit namespace packages). `fRegisterPackage` creates the package `localsiem_modules` with the modules folder as its `__path__`, and `fLoadClass` imports `localsiem_modules.<id>.<file>`, checks that the class is a `Module` and that its `vName` equals the `id`. Consequences for the code of a module:

- its own files are imported **relatively** (`from .parsers import AccessParser`);
- the core is imported as **`backend.core...`** (`from backend.core.module import Module`): the localSIEM processes put the localSIEM folder on `sys.path`;
- only the standard library and the dependencies of localSIEM (its virtual environment `/opt/localsiem/venv/`, for example PyYAML) are available: localSIEM installs nothing for a module.

### Settings form built from the manifest

A module has no HTML of its own. The web reads `settings` of `module.json` and the texts of `locales/`, builds the form (`modules.js fBuildSettings`, `fRecordsEditor`), validates what is saved with `fValidateSettings` and stores only the values the administrator saved in `settings.json` under `modules.<id>`; `enabled` lives there too. The module reads `mModuleSettings()`: the defaults of `module.json` with the saved values over them. Adding a setting therefore needs no change in the web or in the core.

Settings of the core that the apache2 module also reads from `self.dSettings`: `host`, `correlation_window_seconds` (5), `weak_correlation_seconds` (2), `below_threshold_severity` (`low`) and `health.single_ip_percent` / `health.single_ip_minimum_requests` (90 / 100). `mModuleSettings()` also passes keys saved under `modules.apache2` that `module.json` does not declare: `mDiscover` reads `document_roots` (`{vhost: folder}`, over the DocumentRoots discovered) that way; it can only be set by editing `settings.json`.

### The «action taken» principle

Only what nobody has resolved yet goes to the SOC. In the apache2 module the action taken is read from the most reliable source: the audit log (`Action: Intercepted (phase N)` in native format, `audit_data.action.intercepted/phase` in JSON), then error.log (`Access denied with code NNN (phase N)`). A 403 without any trace of ModSecurity is not a block (`fields.doubtful_block`).

| Situation | `action` | Detection (to the SOC) |
|---|---|---|
| Intercepted in phases 1-2 (the application never got it) | `blocked` | none: `mAssess` returns `None`; counted in the context of later alerts |
| Intercepted in phases 3-4 | `none` | yes, `blocked_late` (high), or `success_indicator` with a database error |
| Matches with the engine in `DetectionOnly` | `none` | yes |
| Matches below the anomaly threshold | `none` | yes, `below_threshold` (low) |
| Signals of the YAML rules | `none` | yes |

Severities come from `severity.yaml` (`fLoadSeverityTable`; a missing file or an invalid value keeps the built-in default): `crs_not_blocked_2xx` high, `crs_not_blocked_other` medium, `blocked_late` high, `success_indicator` critical (outbound rule 950-955 not blocked, or a database error in the same request), `below_threshold` low (the core setting `below_threshold_severity` takes precedence). «Above the threshold» means a 949xxx rule matched or the score stated by ModSecurity reached the threshold; a score computed from the rule severities is only an estimate and does not decide. The threshold is the one in the messages, else `anomaly_threshold`, else the one of `crs-setup.conf`, else 5.

### How the apache2 module works

1. **Discovery** (`discovery.py`): `ApacheConfig` reads the configuration directly (`Include`, `IncludeOptional`, `Define`, `${VARS}` of Debian's `envvars`, `<VirtualHost>`, `<IfModule>` against the loaded modules), as the `localsiem` user and without `apache2ctl`. `fDiscoverSources` turns `CustomLog`/`GlobalLog`/`TransferLog`, `ErrorLog` and `SecAuditLog` into sources with the stable key `apache:<kind>:<real path>`. A `GlobalLog` whose format has `%v` covers every vhost (the other access logs are skipped); piped logs and syslog are skipped, and so are the access logs whose format has no `%` directive (Apache writes a nickname that no `LogFormat` defines as it is: `format_without_data`, unless another `CustomLog` with data writes to the same file; the doctor says so, without a fix, since the format of the logs is never changed); manual sources go first and a file is read once.
2. **Framing and parsing** (`parsers.py`, `logformat.py`, `modsec.py`): access lines are parsed with a regular expression generated from their `LogFormat` (the last format that worked is tried first); error lines are classified (`modsecurity`, `database`, `php`, `crash`, `apache`); audit records are read as JSON (one line, cut before `matched_rules`), native serial (`AuditFramer` joins `--id-A--` to `--id-Z--`) or concurrent (the index line points to a file under `SecAuditLogStorageDir`). Everything is masked; what does not fit is kept as `unparsed`.
3. **Correlation** (`correlate.py`): records with the same `UNIQUE_ID` form one transaction, which waits the correlation window and the watermark of the sources that are catching up; an access line without `UNIQUE_ID` (the formats Apache writes by default) is paired by `mPair`, when it or the records of its request are due, with the ModSecurity records that have no access line: same client IP, time within ±2 s (the line has whole seconds) and the same method, URI, status and path when both sides know them; the candidate that agrees in more of them wins, then the nearest, then the oldest, and the event is marked weak. error.log lines without `UNIQUE_ID` join at once the nearest transaction of their IP. A transaction with a `UNIQUE_ID` and a ModSecurity line of error.log, while audit records arrive (`vAuditSeen`), also waits for its own audit record (`mWaitsForAudit`), at most `cAuditWaitSeconds` (120 s) from its first record: ModSecurity writes the lines of its rules while the request runs and the audit record when it ends, so a slow request would otherwise become two events; once the audit record arrives, the access line has `cAfterAuditSeconds` (2 s) more.
4. **Event** (`ApacheModule.mBuildEvent`): fields picked from access, then audit, then error; the vhost from `%v` or, without it, from the Host header and local port of the audit record (`mVhostName`); with an access line of whole seconds, the time of the audit record; `fSummarize` gives rules, categories, score, threshold and interception; the action taken and `mAssess` decide the detection.
5. **Rules, enrichment, doctor and health**: the YAML rules of `rules/` run on every event (core engine); `mEnrich` adds the context of the IP; `fRunDoctor` checks the requirements and describes the logs, without changing anything; `mHealth` watches ModSecurity and the real client IP. The module has no setup option: as root, localSIEM only gives `localsiem` read access to `/var/log/apache2`.

### Design decisions worth knowing

- **No installer of its own**: the modules are installed (Modules › Installable), updated (**Update**, in Modules › Installed) and uninstalled (**Uninstall**) only from the localSIEM web, which downloads this repository and installs them with `backend/core/catalog.py` (safe unpacking, one installation at a time, atomic swap of the folder). What needs root (read access to the `read_paths`) is done by localSIEM: after installing (and after an update that changes `read_paths`), the web shows the command to run as root.
- **The logs of the client are only read**: a module never writes in the logs of the services it watches, nor rotates, truncates, moves or deletes them, and never changes their format; the apache2 module never changes the Apache or ModSecurity configuration either (it has no `setup_option`). If a server writes its logs in a format of its own (a `LogFormat` of its own, the client IP of `mod_remoteip`), the module adapts: `AccessFormat` builds the parser of each access log from its `LogFormat`, and `fCanPair` / `Correlator.mPair` join the lines without `UNIQUE_ID`. The doctor only describes the logs and what localSIEM can or cannot read from them: the checks `log_format`, `log_format_without_data`, `remoteip`, `audit_log` and `sanitise` have no `fix`; only what is not a log (ModSecurity, the CRS, `SecRuleEngine`, `mod_unique_id`, the read permissions of `localsiem`) comes with one. `--configure-apache` was removed in version 1.3.0; `localsiem_combined` stays in `dKnownFormats` for the servers that already write it, and the installer of localSIEM deletes the `localsiem.conf` that older versions wrote (`--uninstall`, `--reinstall`).
- **Part K** (`matched_rules`) and **part E** (response body) of the audit log are never stored. Headers and body stay only in the masked raw record; the request card rebuilds them (`fAuditDisplay`). The full-text index gets a reduced text (`search`: request line, host, user agent and the id, message and data of each rule).
- **The raw text is rebuilt from the masked parts**: the original audit record may hold passwords and cookies.
- **The web and the tools create the module without storage** (`pStorage` is `None` in `WebContext.mModule` and `manage.py`): the constructor and the hooks they call must not use the storage.
- **State in the events database**: `apache.first_start` (learning days), `apache.health` (what was already reported, so a restart does not repeat it) and `apache2.doctor` (written by the collector). The first two, like the source keys `apache:<kind>:<real path>`, keep the name the module had before it was called apache2: a server that had the `apache` module keeps its learning days, its health memory and its read positions (with a new source key, every log under 5 MiB would be read again from the start). The times of the health memory are in the native format of the project (`2026-10-29@13-59-59.723`, UTC); a state saved by an older version, with epoch seconds, is converted when loaded.
- **Safety of the paths**: `mIsNewPhp` refuses `..` and stays inside the DocumentRoot; `fReadConcurrentEntry` stays inside `SecAuditLogStorageDir` and reads at most 8 MiB; the correlator keeps at most 50 000 pending transactions.

### How the privesc module works

The question is not «did someone run `whoami`?» (administrators do it every day) but «is this session walking the path of an escalation, and did it get there?». The module turns two sources into events with one meaning (`vhost` the person, `method` the kind, `uri` the command, `path` the program or file, `ip` the SSH address, `score` the distinct reconnaissance of the session), computes flags on them, and lets YAML rules decide what goes to the SOC.

1. **Discovery** (`discovery.py`): `fDiscoverSources` returns the audit log (`fAuditLogPath`: setting, `log_file` of `auditd.conf`, `/var/log/audit/audit.log`; also when auditd runs and `localsiem` cannot read it yet, so that the core reports it) and syslog (`fSyslogPath`) when `syslog_mode` says so (`auto`: auditd not running, its log not readable, or snoopy installed). It also gathers what the doctor needs: container (`fContainer`, readable without root: `/run/systemd/container`, `/run/.containerenv`, `/.dockerenv`, `/proc/self/cgroup`, `systemd-detect-virt`), auditd binary and pid, snoopy, whether each log can be read (`fReadState`: `readable`, `unreadable` or `missing`) and the files that version 1.0.0 left (`fLegacyLeftovers`). `Accounts` reads `/etc/passwd`, `/etc/group` and `UID_MIN` again when they change, and classifies a uid as `root`, `admin` (member of `admin_groups`), `user` or `service`.
2. **Parsing** (`parsers.py`): `fParseAuditLine` reads `type=... msg=audit(<time>:<serial>): k=v ...`, the user-space part `msg='...'`, the enriched part after `\x1d`, joins the arguments of `EXECVE` (also the ones split in `aN[i]` pieces), decodes the hexadecimal values (`proctitle`, `cmd`, `cwd`, `name`, `exe`, `aN`...) and **rebuilds the raw text from the decoded and masked values** (the hexadecimal of a password would keep it); `search` gets the decoded command. `fParseSyslogLine` reads ISO and classic timestamps (with or without the `facility.priority` of busybox) and `fParseSyslogMessage` understands snoopy (its default formats of 2.4 and 2.5, `uid:alice(1000)/root(0)` included, and the one version 1.0.0 set), sudo, su (util-linux and busybox), pkexec, doas, `pam_unix` and sshd. `fMaskCommand` masks passwords in command lines before the masker of the core.
3. **Correlation** (`correlate.py`): audit records with the same serial form one transaction, due at `EOE`, at once for one-record user-space types (`USER_*`, `CRED_*`, `DAEMON_*`...), or after 2 s without records; at most 50 000 pending. Syslog lines are due at once.
4. **Event** (`PrivescModule.mBuildEvent`): `mAuditEvent` splits by type: `EXECVE` → `mAuditExec` (setuid bit of the program from the `PATH` record or `stat`, `suid_escape` when euid is 0, the real uid is not and the program is not setuid, capabilities gained from `BPRM_FCAPS`, `root_without_door`, `parent_interpreter` when a shell runs as root started by an interpreter of a user other than root, the parent from the process memory); `USER_*`/`LOGIN` → `mAuditUser` (session started, SSH address, doors: `USER_START`/`USER_CMD` of sudo, su, pkexec, doas, run0, systemd; failures); `CONFIG_CHANGE` (`audit_disabled`, `audit_rule_removed` for any rule removed), `DAEMON_*` (`auditd_stopped_manually` when the sender is not pid 1), `ANOM_ABEND` (`crash_suspicious`); any other `SYSCALL` → `mAuditSyscall`, which classifies it by its system call (`fSyscallName`: the name of the enriched format, or the number in the table of its architecture), its arguments and its `PATH` records, never by the key of the rule: `denied` (open, exec or truncate failed with `EACCES`/`EPERM` for a person), `kmod`, `ptrace` (`ptrace_attach` for `PTRACE_ATTACH`/`PTRACE_SEIZE`), `chmod` (mode with the setuid or setgid bit, not on a folder, with `writer_allowed`) and `file` (a change of a path of `lSensitivePaths`, with `sensitive_group` and `writer_allowed`; the key, through `dKeyHints`, only when no path can be resolved). `mSyslogEvent` handles snoopy as `exec` (`suid_escape` from `stat`; without `filename`, the program from the first word of the command) and sudo, su, pkexec, doas, login and pam. Every command goes through `mAnalyzeCommand`: reconnaissance token (`fReconToken`) and distinct tokens of the session in the window (`recon_burst`, `recon_massive`, `score`), downloads run by a shell (`cDownloadOnelinerRegex`, or a downloader followed by a shell with the same parent), `compile_in_tmp`, the last commands of the session and, for service accounts, the program (`fProgramKey`) against its history (`mPathFirstSeen` of the core, after `learning_days`: `new_program`). `ignored` marks the ignored users.
5. **Rules, enrichment, doctor and health**: the 35 YAML rules of `rules/` decide every detection (`mDetectionFromSignal`); `mEnrich` adds the context of the session; `fRunDoctor` describes auditd and what its rules recorded, syslog, snoopy, what the module sees and what it cannot, the files of version 1.0.0 and the attack surface; `mHealth` reports auditd stopped, the sensitive files writable and the result of the scan of setuid programs (`SurfaceScanner`, a thread). The module has no setup option and changes nothing on the server.

### Design decisions of the privesc module

- **Two sources, one meaning.** auditd cannot be avoided by a user but does not run inside containers (the audit of the kernel is not namespaced); snoopy sees every program in containers but needs syslog; syslog alone only gives sudo, su, pkexec and doas. No source sees the builtins of the shell. The rules match columns and flags, never the source, so a source can be added without touching them. The same command seen twice makes one alert: the core groups detections by module, user, IP, category and severity.
- **Bursts, not commands.** Reconnaissance is a token per kind of question (`whoami`, `read:/etc/passwd`, `find:-perm:`...), and only the number of distinct tokens of a session in a window raises an alert, with a higher threshold for administrators and a third one for scripts. The thresholds are settings, not rule thresholds: the rule only matches `recon_burst` / `recon_massive`.
- **Success is what matters most.** `suid_escape` (a program that is not setuid running with euid 0 and a real uid that is not 0) and `root_without_door` (root in a session whose start was seen and that never went through sudo, su, pkexec or doas) are the two critical signs that an escalation worked, almost without false positives. A session whose start was not seen (sessions open before the module, sessions forgotten after a day of inactivity) is never flagged.
- **Sessions survive restarts.** `SessionTracker` keeps the start, the SSH address and the door of each session in the state `privesc.sessions` (saved at most every minute); the reconnaissance tokens and the last commands stay in memory. Sessions idle for a day are dropped.
- **Only what the server already has.** The module never installs anything nor changes anything outside `/opt/localsiem`: it loads no audit rules, does not touch `auditd.conf` nor `snoopy.ini` and installs no hook. Version 1.0.0 did (`--configure-privesc`: audit rules with the keys `lsiem_*`, `log_group = adm`, a bash hook, the format of snoopy); version 1.1.0 removed it. The audit records are therefore classified by their type, their system call and their paths, so any audit rules work (those of the server, the STIG sample rules, or the `lsiem_*` rules that 1.0.0 left); the key is kept in `fields.key` for the searches and is only a hint (`dKeyHints`). The numbers of the system calls are read per architecture (`dSyscallTables`: x86_64, i386 and the generic table of aarch64, riscv64 and loongarch64) when the log has no enriched names. The doctor describes what the rules of the server record and what they do not; its `fix` is only a package to install or the read access of `localsiem`.
- **Readable means readable.** The requirement is met by a source that exists and that `localsiem` can open (`fReadState`), not by a program being installed: on a first installation the logs usually belong to root, so the module stays off until the command for root (`manage.py setup-modules`) and **Reconfigure**.
- **Package managers are not attackers.** Changes of sensitive files and setuid bits made by the account and package tools (`sAllowedWriters`), or by programs whose known ancestors are package managers, set `writer_allowed`, and the rules skip them.
- **The scan never blocks the collector.** `SurfaceScanner` walks the `scan_paths` in a thread of its own, without leaving the file system of each one, skipping `/proc`, `/sys` and the folders of containers, up to 3 million files or 15 minutes; `mHealth` takes the result when it is ready. The first scan is the reference; later ones report what is new.
- **The web and the tools create the module without storage**: `mDiscover`, `mDoctor` and `mRequirements` never use it, and `mAnalyzeCommand` only calls `mPathFirstSeen` when it exists.
- **State in the events database**: `privesc.first_start` (learning days), `privesc.sessions`, `privesc.surface` (the reference of the scan and the doctor), `privesc.health` (what was already reported, whether auditd was running) and `privesc.doctor` (written by the collector). The seen programs of the service accounts are rows of `seen_paths` with the vhost `privesc:<account>`. The times of `privesc.health` (the health memory) and of `privesc.sessions` (`last` of each session) are in the native format of the project (`2026-10-29@13-59-59.723`, UTC); a state saved by an older version, with epoch seconds, is converted when loaded.

<a id="modules"></a>
## 2. Module map

| Module | Path | Responsibility | Depends on | Used by |
|---|---|---|---|---|
| Manifest | [mod-apache2/module.json](../mod-apache2/module.json) | id, version, minimum core, entry, read paths, settings (no setup option) | — | registry, web, `manage.py` |
| Apache module | [mod-apache2/module.py](../mod-apache2/module.py) | `ApacheModule`: hooks, action taken, severity, detections, rule function, enrichment, health | correlate, discovery, doctor, modsec, parsers; core `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | collector, web, `manage.py` |
| Discovery | [mod-apache2/discovery.py](../mod-apache2/discovery.py) | `ApacheConfig` (configuration parser), sources and skipped logs, DocumentRoots | logformat (`dKnownFormats`) | module, doctor |
| Doctor | [mod-apache2/doctor.py](../mod-apache2/doctor.py) | Requirement checks; describes the logs (format, audit log, masking) without proposing to change them | discovery | module |
| Access formats | [mod-apache2/logformat.py](../mod-apache2/logformat.py) | `LogFormat` to regular expression, times to UTC, request line | core `timeutil` | parsers, discovery |
| Parsers | [mod-apache2/parsers.py](../mod-apache2/parsers.py) | access, error, audit (JSON, native, concurrent), `AuditFramer`, `fAuditDisplay` | logformat, modsec; core `masking`, `timeutil` | module |
| ModSecurity | [mod-apache2/modsec.py](../mod-apache2/modsec.py) | Messages, categories, CRS ranges, scores, interception | — | parsers, module |
| Correlation | [mod-apache2/correlate.py](../mod-apache2/correlate.py) | `UNIQUE_ID`, pairing without it (`mPair`), window, watermark | core `timeutil` | module (collector) |
| Severity table | [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) | Severities of the ModSecurity detections | — | module (`fLoadSeverityTable`) |
| Rules | [mod-apache2/rules/](../mod-apache2/rules/) | Six YAML rules | core rules engine, `mIsNewPhp` | collector (`RulesEngine`), web (`fRules`) |
| Texts | [mod-apache2/locales/](../mod-apache2/locales/) | Name, summary, labels and help of the settings, choices | — | web |
| privesc: manifest | [mod-privesc/module.json](../mod-privesc/module.json) | id, version, minimum core, entry, read paths, 13 settings (no setup option) | — | registry, web, `manage.py` |
| privesc: module | [mod-privesc/module.py](../mod-privesc/module.py) | `PrivescModule`: hooks, events of the two sources, classification of the audit records (sensitive paths, system calls per architecture), flags, detections of the rules, enrichment, health, scan results | commands, correlate, discovery, doctor, parsers, surface; core `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | collector, web, `manage.py` |
| privesc: discovery | [mod-privesc/discovery.py](../mod-privesc/discovery.py) | Sources, container, auditd, snoopy, syslog, whether each log can be read, files left by version 1.0.0, `Accounts` (users, groups, kind of account) | — | module, doctor |
| privesc: parsers | [mod-privesc/parsers.py](../mod-privesc/parsers.py) | Audit records (hexadecimal, `msg='...'`, enriched), syslog lines (snoopy in its usual formats, sudo, su, pkexec, doas, pam, sshd), masking of command lines | core `masking`, `timeutil` | module |
| privesc: correlation | [mod-privesc/correlate.py](../mod-privesc/correlate.py) | Audit records by serial (EOE, user-space records, 2 s); syslog lines at once | — | module (collector) |
| privesc: commands | [mod-privesc/commands.py](../mod-privesc/commands.py) | Reconnaissance tokens, program of a service account, shells, interpreters, downloaders, doors, compilers; `SessionTracker` | core `timeutil` | module |
| privesc: attack surface | [mod-privesc/surface.py](../mod-privesc/surface.py) | `SurfaceScanner` (setuid, setgid, capabilities), GTFOBins, sensitive files writable, privileged groups | — | module, doctor |
| privesc: doctor | [mod-privesc/doctor.py](../mod-privesc/doctor.py) | Describes auditd, its log and what its rules recorded, syslog, snoopy, what the module sees, the files of version 1.0.0 and the surface (fixes: only packages and read access); requirement `command_source` (any readable source) | discovery, surface; core `timeutil` | module |
| privesc: rules | [mod-privesc/rules/](../mod-privesc/rules/) | 35 YAML rules | core rules engine | collector (`RulesEngine`), web (`fRules`) |
| privesc: severity table | [mod-privesc/severity.yaml](../mod-privesc/severity.yaml) | Severities of the detections built by the module (scan, sensitive files) | — | module (`fLoadSeverityTable`) |
| privesc: texts | [mod-privesc/locales/](../mod-privesc/locales/) | Name, summary, labels and help of the settings, choices | — | web |
| Core: interface | [backend/core/module.py](../../localSIEM/backend/core/module.py) | `Module`, `LineFramer` | registry | modules |
| Core: registry | [backend/core/registry.py](../../localSIEM/backend/core/registry.py) | Find, check and load modules; defaults and validation of settings | `config` | collector, web, `manage.py`, `backend/core/catalog.py` |
| Core: web | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) | Modules pages (Installed, Installable, the page of one module) and API | registry, catalog, rules | browsers |
| Core: catalog | [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) | Download and safe unpacking of the repository, list with the action of each module (`install`, `update`, `incompatible`, `invalid`...) and `newer`, atomic installation or update (`previous`, `access_changed`), uninstallation, command for root: Modules › Installable and **Update** / **Uninstall** of Modules › Installed, the only way to install modules | registry | web |

<a id="symbols"></a>
## 3. Key symbols

| Symbol | File:line | What it does |
|---|---|---|
| `ApacheModule` | [mod-apache2/module.py:68](../mod-apache2/module.py#L68) | The apache2 module (`vName = "apache2"`) |
| `fLoadSeverityTable` | [mod-apache2/module.py:54](../mod-apache2/module.py#L54) | `severity.yaml` over the built-in defaults |
| `ApacheModule.mDiscover` | [mod-apache2/module.py:95](../mod-apache2/module.py#L95) | Parses the configuration, sources, skipped logs, DocumentRoots |
| `ApacheModule.mThreshold` | [mod-apache2/module.py:105](../mod-apache2/module.py#L105) | Anomaly threshold: setting, CRS, or 5 |
| `ApacheModule.mParse` | [mod-apache2/module.py:136](../mod-apache2/module.py#L136) | Unit to record by kind of source |
| `ApacheModule.mBuildEvent` | [mod-apache2/module.py:176](../mod-apache2/module.py#L176) | Transaction to event: fields, action taken, scores, detection |
| `ApacheModule.mVhostName` | [mod-apache2/module.py:311](../mod-apache2/module.py#L311) | Host header or ModSecurity hostname to the vhost Apache chose (what `%v` logs) |
| `ApacheModule.mAssess` | [mod-apache2/module.py:323](../mod-apache2/module.py#L323) | Severity, rule name, description and details of what goes to the SOC |
| `ApacheModule.mDetectionFromSignal` | [mod-apache2/module.py:385](../mod-apache2/module.py#L385) | Signal of a YAML rule to detection |
| `ApacheModule.mIsNewPhp` | [mod-apache2/module.py:414](../mod-apache2/module.py#L414) | Rule function `apache2.new_php` |
| `ApacheModule.mEnrich` | [mod-apache2/module.py:442](../mod-apache2/module.py#L442) | Context of the IP (last hour) for the alert |
| `ApacheModule.mHealth` | [mod-apache2/module.py:461](../mod-apache2/module.py#L461) | ModSecurity unloaded or Off; real client IP missing |
| `ApacheModule.mDisplayRecord` | [mod-apache2/module.py:538](../mod-apache2/module.py#L538) | Headers and body for the request card |
| `ApacheModule.mRequirements` | [mod-apache2/module.py:545](../mod-apache2/module.py#L545) | Apache and ModSecurity 2: what the module needs before it can be turned on |
| `ApacheConfig` | [mod-apache2/discovery.py:105](../mod-apache2/discovery.py#L105) | Parser of the Apache configuration |
| `ApacheConfig.mDirective` | [mod-apache2/discovery.py:228](../mod-apache2/discovery.py#L228) | Directives read (logs, vhosts, modules, ModSecurity) |
| `ApacheConfig.mVhostName` | [mod-apache2/discovery.py:358](../mod-apache2/discovery.py#L358) | Vhost of a request from its Host header and local address and port, as Apache chooses it |
| `fSourceKey` / `fDiscoverSources` | [mod-apache2/discovery.py:403](../mod-apache2/discovery.py#L403) / [:408](../mod-apache2/discovery.py#L408) | Stable source key; sources to read and skipped ones |
| `fRunDoctor` | [mod-apache2/doctor.py:46](../mod-apache2/doctor.py#L46) | Requirement checks `{id, status, title, detail, fix}` |
| `fCanPair` | [mod-apache2/doctor.py:26](../mod-apache2/doctor.py#L26) | Whether an access format can be joined without `UNIQUE_ID` (client IP, time, request line, status) |
| `fRequirementChecks` | [mod-apache2/doctor.py:174](../mod-apache2/doctor.py#L174) | The checks `apache_config` and `modsecurity` of the doctor or, without Apache, both as errors, with the command that installs them |
| `AccessFormat` / `dKnownFormats` | [mod-apache2/logformat.py:60](../mod-apache2/logformat.py#L60) / [:15](../mod-apache2/logformat.py#L15) | `LogFormat` to regular expression; known nicknames |
| `AccessParser` | [mod-apache2/parsers.py:59](../mod-apache2/parsers.py#L59) | access.log line to record |
| `fParseErrorLine` | [mod-apache2/parsers.py:147](../mod-apache2/parsers.py#L147) | error.log line: ModSecurity, database, PHP, crash |
| `AuditFramer` | [mod-apache2/parsers.py:233](../mod-apache2/parsers.py#L233) | Native records across lines; safe commit position |
| `fParseAuditRecord` / `fFinishAudit` | [mod-apache2/parsers.py:277](../mod-apache2/parsers.py#L277) / [:426](../mod-apache2/parsers.py#L426) | JSON or native audit record; masking, raw and indexed text |
| `fAuditDisplay` / `fReadConcurrentEntry` | [mod-apache2/parsers.py:495](../mod-apache2/parsers.py#L495) / [:577](../mod-apache2/parsers.py#L577) | Card of a stored record; file of a concurrent entry |
| `fParseMessage` / `fSummarize` | [mod-apache2/modsec.py:52](../mod-apache2/modsec.py#L52) / [:152](../mod-apache2/modsec.py#L152) | One ModSecurity message; rules, categories, score, threshold, interception |
| `Correlator` | [mod-apache2/correlate.py:57](../mod-apache2/correlate.py#L57) | `mAdd` ([:148](../mod-apache2/correlate.py#L148)), `mPair` ([:207](../mod-apache2/correlate.py#L207)), `mDue` ([:248](../mod-apache2/correlate.py#L248)), `mWaitsForAudit` ([:271](../mod-apache2/correlate.py#L271)), `mPendingCount` |
| `PrivescModule` | [mod-privesc/module.py:226](../mod-privesc/module.py#L226) | The privesc module (`vName = "privesc"`) |
| `PrivescModule.mBuildEvent` | [mod-privesc/module.py:341](../mod-privesc/module.py#L341) | Transaction to event, by source; `ignored`; empty fields dropped (`fCleanFields` keeps 0) |
| `PrivescModule.mAnalyzeCommand` | [mod-privesc/module.py:366](../mod-privesc/module.py#L366) | Reconnaissance of the session, download run by a shell, compile in `/tmp`, recent commands, new program of a service account |
| `PrivescModule.mAuditEvent` / `mAuditExec` / `mAuditUser` | [mod-privesc/module.py:427](../mod-privesc/module.py#L427) / [:587](../mod-privesc/module.py#L587) / [:661](../mod-privesc/module.py#L661) | Audit transaction by type; programs run (`suid_escape`, `root_without_door`, `parent_interpreter`, capabilities); logins, doors and failures |
| `PrivescModule.mAuditSyscall` | [mod-privesc/module.py:509](../mod-privesc/module.py#L509) | Any other system call by its name, arguments and paths: `denied`, `kmod`, `ptrace`, `chmod`, `file` (`sensitive_group`) or `syscall` |
| `fSyscallName` / `fSensitiveGroup` | [mod-privesc/module.py:184](../mod-privesc/module.py#L184) / [:210](../mod-privesc/module.py#L210) | Name of a system call (enriched name, or number by architecture); group of a sensitive path (`lSensitivePaths`) |
| `PrivescModule.mSyslogEvent` | [mod-privesc/module.py:702](../mod-privesc/module.py#L702) | snoopy, sudo, su, pkexec, doas, logins |
| `PrivescModule.mWriterAllowed` | [mod-privesc/module.py:412](../mod-privesc/module.py#L412) | The writer of a sensitive file, or a known ancestor, is an account or package tool |
| `PrivescModule.mDetectionFromSignal` / `mEnrich` | [mod-privesc/module.py:781](../mod-privesc/module.py#L781) / [:818](../mod-privesc/module.py#L818) | Signal of a rule to detection; context of the session for the alert |
| `PrivescModule.mHealth` / `mSurfaceResult` | [mod-privesc/module.py:851](../mod-privesc/module.py#L851) / [:903](../mod-privesc/module.py#L903) | Sessions saved, auditd stopped, sensitive files, scan started; new setuid programs and capabilities |
| `fDiscoverSources` / `fReadState` / `fLegacyLeftovers` | [mod-privesc/discovery.py:291](../mod-privesc/discovery.py#L291) / [:160](../mod-privesc/discovery.py#L160) / [:175](../mod-privesc/discovery.py#L175) | Sources, skipped ones and information for the doctor; whether a log can be read; files left by version 1.0.0 |
| `fContainer` / `fAuditdPid` | [mod-privesc/discovery.py:54](../mod-privesc/discovery.py#L54) / [:96](../mod-privesc/discovery.py#L96) | Kind of container (without root); pid of a running auditd |
| `Accounts` | [mod-privesc/discovery.py:190](../mod-privesc/discovery.py#L190) | Names of uids, groups, `UID_MIN`, kind of account (`mAccountType`) |
| `fParseAuditLine` / `fParseSyslogLine` | [mod-privesc/parsers.py:83](../mod-privesc/parsers.py#L83) / [:316](../mod-privesc/parsers.py#L316) | Records of the two sources |
| `fMaskCommand` | [mod-privesc/parsers.py:45](../mod-privesc/parsers.py#L45) | Passwords of command lines, then the masker of the core |
| `Correlator` (privesc) | [mod-privesc/correlate.py:20](../mod-privesc/correlate.py#L20) | Audit records by serial; the others at once |
| `fReconToken` / `fProgramKey` / `fCommandArgs` | [mod-privesc/commands.py:115](../mod-privesc/commands.py#L115) / [:180](../mod-privesc/commands.py#L180) / [:91](../mod-privesc/commands.py#L91) | Reconnaissance token of a command; program of a service account; words of a typed command |
| `SessionTracker` | [mod-privesc/commands.py:202](../mod-privesc/commands.py#L202) | Sessions (start, IP, door, reconnaissance, last commands), processes, downloads; `mExport`/`mImport` |
| `SurfaceScanner` / `fCheckSensitiveFiles` | [mod-privesc/surface.py:167](../mod-privesc/surface.py#L167) / [:133](../mod-privesc/surface.py#L133) | Scan of setuid, setgid and capabilities in a thread; sensitive files writable by others |
| `fRunDoctor` / `fRequirementChecks` (privesc) | [mod-privesc/doctor.py:275](../mod-privesc/doctor.py#L275) / [:282](../mod-privesc/doctor.py#L282) | Checks of the doctor (descriptions; fixes only for packages and read access); requirement `command_source`: any readable source |
| `Module` / `LineFramer` | [backend/core/module.py:59](../../localSIEM/backend/core/module.py#L59) / [:48](../../localSIEM/backend/core/module.py#L48) | Interface of a module; one line per unit |
| `fReadManifest` | [backend/core/registry.py:133](../../localSIEM/backend/core/registry.py#L133) | Checks `module.json`, reads the texts |
| `fListManifests` / `fCreateModules` | [backend/core/registry.py:165](../../localSIEM/backend/core/registry.py#L165) / [:229](../../localSIEM/backend/core/registry.py#L229) | The installed modules (`/opt/localsiem/modules/*`); instances and errors |
| `fRegisterPackage` / `fLoadClass` | [backend/core/registry.py:185](../../localSIEM/backend/core/registry.py#L185) / [:197](../../localSIEM/backend/core/registry.py#L197) | Namespace package `localsiem_modules`; import and checks of the entry |
| `fModuleSettings` / `fValidateSettings` | [backend/core/registry.py:250](../../localSIEM/backend/core/registry.py#L250) / [:317](../../localSIEM/backend/core/registry.py#L317) | Defaults under the saved values; validation of what is saved |
| `fSaveModule` | [backend/web/api_modules.py:290](../../localSIEM/backend/web/api_modules.py#L290) | `POST /api/admin/modules/{name}` |
| `fGetCatalog` / `fInstallFromCatalog` / `fUninstallModule` | [backend/web/api_modules.py:384](../../localSIEM/backend/web/api_modules.py#L384) / [:395](../../localSIEM/backend/web/api_modules.py#L395) / [:422](../../localSIEM/backend/web/api_modules.py#L422) | `GET /api/admin/module-catalog`; `POST /api/admin/module-catalog/{name}` (install or update; a first installation without its requirements is turned off: `fFirstInstallation`); `DELETE /api/admin/modules/{name}` |
| `fInstall` / `fCatalog` | [backend/core/catalog.py:235](../../localSIEM/backend/core/catalog.py#L235) / [:171](../../localSIEM/backend/core/catalog.py#L171) | Installs or updates a module next to the installed copy and swaps them with a rename (`previous`, `access_changed`); the modules of the repository with `installed`, `newer` and their action |
| `fRemove` / `fRootCommand` | [backend/core/catalog.py:302](../../localSIEM/backend/core/catalog.py#L302) / [:372](../../localSIEM/backend/core/catalog.py#L372) | Uninstalls a module (rename and delete); the command for root (`manage.py setup-modules`) |
| `fCatalogPanel` / `fUpdateNotice` / `fUpdate` | [frontend/assets/modules.js:218](../../localSIEM/frontend/assets/modules.js#L218) / [:417](../../localSIEM/frontend/assets/modules.js#L417) / [:452](../../localSIEM/frontend/assets/modules.js#L452) | Section Installable (only the modules not installed, **Install** and its dialog); notice of a newer version on a row of Installed; **Update** (confirmation, the same `POST`, a dialog only with `access_changed` or when the collector did not answer) |

<a id="flows"></a>
## 4. Main call paths

**Collector start → registry → ApacheModule**

`Collector.mSetup` → `fCreateModules` → `fListManifests` (`/opt/localsiem/modules/*`) → `fReadManifest` (id = folder, entry, settings, `core` ≤ `cVersion`, `fReadTexts`) → `fCreateModule` → `fLoadClass` (`fRegisterPackage`, `import localsiem_modules.apache2.module`, subclass of `Module`, `vName == id`) → `ApacheModule(dSettings, vMasker, vStorage, dManifest)` → `mStart` → `mCreateCorrelator` → `Collector.mLoadRules` (`mRulesPath`, `mRuleFunctions`, overrides `rules.<id>` → `RulesEngine.mLoad`) → `Collector.mDiscover` (`mEnabled` → `mDiscover` → `ApacheConfig.mParse` → `fDiscoverSources`; a `FileTailer` and `mCreateFramer` per source) → pending records back into the correlator → `mPublishDoctor` (`mDoctor` → `fRunDoctor` → state `apache2.doctor`).

**A line read → detections**

1. `Collector.mReadSources` → `FileTailer.mPoll` → framer `mFeed` (`LineFramer`, or `AuditFramer` whose `mSafeCommit` keeps the position before an unfinished record) → `ApacheModule.mParse` (`AccessParser.mParse`, `fParseErrorLine`, or `fReadConcurrentEntry` + `fParseAuditRecord` and `mObserveAudit`) → records and positions stored in one transaction → `Correlator.mAdd`.
2. `Collector.mProcessDue` → `Correlator.mDue(pWatermark=...)` → `ApacheModule.mBuildEvent` (`fSummarize`, action taken, `mAssess`, `mPathFirstSeen` for 2xx `.php`) → `RulesEngine.mEvaluate` (YAML rules; `{function: apache2.new_php}` → `mIsNewPhp`) → `mSaveEvents` → `mDetect` for each detection and `mDetectionFromSignal` for each signal → `Grouper.mAdd`.
3. `Collector.mProcessGroups` → `ApacheModule.mEnrich` (`mGetIpContext`) → `fBuildAlert` → SOC queue.

**Administrator saves the settings → collector reload**

`modules.js fBuildSettings` (submit) → `POST /api/admin/modules/apache2` `{settings}` → `fSaveModule` → `fValidateSettings` (422 `invalid_setting:<key>` or `<key>.<field>`) → `fSaveSettings` (`settings.json`, `modules.apache2`) → `WebContext.mApplySettings` → collector socket `{"command": "reload"}` → `Collector.mHandleIpc` → `Collector.mCycle` → `mReloadSettings` (`ApacheModule.mReload`, `mLoadRules`, `mDiscover`, `mPublishDoctor`, `mPublishState`). The switch sends `{enabled}` the same way (turning it on: 422 `requirements_missing` while a requirement of the module is missing) and the rules table sends `{rules}` (`fCleanRules` → `rules.<id>`: `enabled`, `severity`, `threshold` or `first_threshold`, `window`). If the socket does not answer, the collector still notices the new `settings.json` on its next cycle.

**Installing a module from the web** (the only way to install modules)

`modules.js fCatalogPanel` (Modules › Installable) → **Check the repository** → `GET /api/admin/module-catalog` (`fGetCatalog` → `fFetchCatalog` → `fDownload` → `fCatalog`: each folder `mod-<name>/` of the repository, with `installed`, `newer` and `action`) → only the items with `installed` null are listed → **Requirements** (`fShowRequirements` → `fRequirementsBody`: the `install_requirements` of the module for the system of the server, `system` of the answer, as root and with `sudo`, and the notes `install_requirements.*` of its locales; nothing is run) → **Install** → `POST /api/admin/module-catalog/{name}` (`fInstallFromCatalog` → `fFetchAndInstall` → `InstallLock` → `fDownload` → `fInstall`: `mod-apache2/` → `/opt/localsiem/modules/apache2/`, `previous` null, `access_changed` true) → `WebContext.mReloadModules` → `fFirstInstallation` (a requirement missing and `modules.<name>.enabled` never saved: `enabled = false`) → collector `restart` → `fCreateModules` loads the module → the dialog «<module> installed» shows the command for root (`fRootCommand`: `manage.py setup-modules`, read access to the `read_paths`) or, if a requirement is missing, the checks not met.

**Updating a module from the web**

Modules › Installed opens → `fCheckRepository` → `fFetchCatalog(false)` of `modules.js` (the last answer of `GET /api/admin/module-catalog`, reused for 600 s; installing, updating or uninstalling a module forgets it) → items with `newer` and `action` `update` or `incompatible` → `fUpdateNotice` on the row (only while the installed version is the one compared) → **Update** → `fUpdate` → confirmation → `POST /api/admin/module-catalog/{name}` (the same `fInstallFromCatalog` → `fInstall`: the new copy replaces the installed one, `previous` is the old version, `access_changed` tells whether `read_paths` changed; no `fFirstInstallation`, so `enabled` and the settings stay) → collector `restart` → a dialog only if `access_changed` (the command for root) or the collector did not answer.

**Uninstalling a module from the web**

**Uninstall** (row of Modules › Installed or page of the module) → `fUninstallButton` → confirmation → `DELETE /api/admin/modules/{name}` (`fUninstallModule` → `fRemove` → `InstallLock` → rename of `/opt/localsiem/modules/<name>/` into a staging folder, deleted there) → `WebContext.mReloadModules` → collector `restart`. `modules.<name>` and the overrides of its rules stay in `settings.json`, and the read access given by root stays.

**First installation without Apache or ModSecurity → Reconfigure** (localSIEM 2.2.0 or newer)

Install in the web → `fInstall` (first installation) → the module created from the installed copy (storage `None`) → `ApacheModule.mRequirements` → `ApacheConfig.mParse` → `fRequirementChecks` (with Apache: `fRunDoctor` → `apache_config`, `modsecurity`; without it, both as errors) → an error and `modules.apache2.enabled` never saved → `modules.apache2.enabled = false` («Off», switch locked, requirements on the page). Later, with Apache and ModSecurity installed: **Reconfigure** → `POST /api/admin/modules/apache2/reconfigure` → `mRequirements` → met → switch unlocked and the root command (read access to the `read_paths`; apache2 has no `setup_option`) → the administrator turns the module on → collector reload → `mDiscover` → `mPublishDoctor`.

**Request card and doctor from the web**

`GET /api/events/{id}` → `fEvent` → `WebContext.mModule("apache2")` → `mDisplayRecord` → `fAuditDisplay`. **Discover again and run the doctor** → `POST /api/admin/modules/apache2/doctor` → collector `{"command": "doctor"}` → `mDiscover` + `mPublishDoctor`.

**Health**

`Collector.mCycle` (every 60 s) → `mCheckHealth` → `ApacheModule.mHealth` (every 300 s at most; `ApacheConfig.mParse`, `mCountRecentEvents`) → `fHealthDetection` → `mDetect`.

**privesc: a command run → detections**

1. auditd writes `SYSCALL`, `EXECVE`, `CWD`, `PATH`, `PROCTITLE`, `EOE` with one serial → `FileTailer.mPoll` → `LineFramer` → `PrivescModule.mParse` → `fParseAuditLine` (hexadecimal decoded, `fMaskCommand`, raw rebuilt) → `Correlator.mAdd` (key `audit:<time>:<serial>`, due at `EOE`).
2. `Correlator.mDue` → `PrivescModule.mBuildEvent` → `mAuditEvent` → `mAuditExec` (`suid_escape`, `BPRM_FCAPS`, `root_without_door` from `SessionTracker.mGet`, `mRememberProcess`) → `mAnalyzeCommand` (`fReconToken` → `SessionTracker.mRecon` → `recon_burst`/`recon_massive`; `cDownloadOnelinerRegex`, `mDownload`/`mRecentDownload`; `fCompileInTemporary`; `mCommand`; service account: `fProgramKey` → `mPathFirstSeen` → `new_program`) → `fCleanFields`.
3. `RulesEngine.mEvaluate` (rules of `mod-privesc/rules/`) → `PrivescModule.mDetectionFromSignal` → `Grouper.mAdd` → `Collector.mProcessGroups` → `PrivescModule.mEnrich` (session: last 20 commands) → `fBuildAlert` → SOC queue.

With snoopy, the same command also arrives as a syslog line: `fParseSyslogLine` → `fParseSyslogMessage` → `mSyslogEvent` → `mAnalyzeCommand` (session `snoopy:<uid>:<sid>`).

**privesc: sessions and doors**

`LOGIN` (auid and ses assigned) or `USER_LOGIN`/`USER_START` of sshd or login → `mAuditUser` → `SessionTracker.mStart` (user, SSH address). `USER_START`/`USER_CMD` with result success of sudo, su, pkexec, doas, run0 or systemd → `SessionTracker.mDoor`. A later `EXECVE` of that session with uid and euid 0 → `root_without_door` only if the start was seen and there was no door. `mHealth` saves `SessionTracker.mExport` in `privesc.sessions` at most every minute; `mStart` loads it (`mImport`).

**privesc: a system call recorded by the audit rules of the server**

auditd writes `SYSCALL` (with `arch`, `syscall`, `a0`-`a3`, `success`, `exit` and the key of whatever rule recorded it), `CWD`, `PATH`... → `fParseAuditLine` → `Correlator` → `mAuditEvent` → `mAuditSyscall`: `fSyscallName` → failed open/exec/truncate with `EACCES`/`EPERM` and a login uid → `denied`; `init_module`/`finit_module`/`delete_module` → `kmod`; `ptrace` → `ptrace`; `chmod`/`fchmod`/`fchmodat`/`fchmodat2` with `S_ISUID`/`S_ISGID` in the mode, not on a folder → `chmod` (`mWriterAllowed`); a change (a call of `sChangeSyscalls`, an open with write flags, a `PATH` with `CREATE`/`DELETE`) of a path of `lSensitivePaths` → `file` with `sensitive_group` (`dKeyHints` only without a resolvable path) and `mWriterAllowed`; anything else → `syscall`. `mBuildEvent` remembers the time of each kind (`dRuntime["audit_kinds"]`) for the doctor.

**privesc: scan of the attack surface**

`mHealth` (every 300 s, five minutes after the start, every `surface_scan_hours`) → `SurfaceScanner.mStart` (thread: `os.walk` of `scan_paths`, `os.lstat`, `os.getxattr("security.capability")` → `fCapabilities`) → next `mHealth` → `mSurfaceResult` (`SurfaceScanner.mTake`, against `privesc.surface`: new setuid/setgid → `new_setuid*`, new capabilities → `new_capabilities`) → `mModuleDetection` → `mDetect`; the result is saved in `privesc.surface` and shown by `fSurfaceChecks`. Every hour `fCheckSensitiveFiles` → `sensitive_file_writable`.

**privesc: requirements and Reconfigure**

`fInstall` (first installation) or **Reconfigure** → `PrivescModule.mRequirements` → `fRequirementChecks(mModuleSettings())` (`fContainer`, `fAuditdPid`, `fAuditLogPath` → `fReadState`; `fSyslogPath` → `fReadState` unless `syslog_mode` is `never`; `fSnoopyInstalled`) → a readable source: `command_source` ok (the unreadable ones as warnings); a source that exists but cannot be read: `audit_log` or `syslog` error with the read access (`manage.py setup-modules` or `setfacl`); nothing: `command_source` error with the package to install. The module stays off while there is an error.

<a id="routes"></a>
## 5. Entry points

| Entry point | Handler | File |
|---|---|---|
| `"entry": "module:ApacheModule"` of `module.json` | `ApacheModule` | [mod-apache2/module.py](../mod-apache2/module.py) |
| `mod-apache2/rules/*.yaml` | `RulesEngine` (core) | [mod-apache2/rules/](../mod-apache2/rules/) |
| Rule function `apache2.new_php` | `ApacheModule.mIsNewPhp` | [mod-apache2/module.py](../mod-apache2/module.py) |
| Web: Modules › Installable, the only way to install modules (`GET /api/admin/module-catalog`, `POST /api/admin/module-catalog/{name}`) | `fGetCatalog`, `fInstallFromCatalog`; view `fCatalogPanel` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| Web: **Update** on a row of Modules › Installed (the same `GET`, reused for 10 minutes by the browser, and the same `POST`) | `fCheckRepository`, `fUpdateNotice`, `fUpdate` → `fInstallFromCatalog` | [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js), [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| Web: **Uninstall** (`DELETE /api/admin/modules/{name}`) | `fUninstallModule` → `fRemove` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `read_paths` of `module.json` | `manage.py read-paths`: the folders localSIEM lets `localsiem` read, as root (the command of `fRootCommand`) | [backend/manage.py](../../localSIEM/backend/manage.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `manage.py modules` | `fMain` (`fModules`) | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py doctor [--json]` | `mDiscover`, `mSkipped`, `mDoctor` | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py read-paths` | `read_paths` of every manifest | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `/user/dashboard/modules/`; `/admin/dashboard/modules/` (302 to `installed/`), `/admin/dashboard/modules/installed/`, `/admin/dashboard/modules/installable/` | `fUserTab` / `fAdminTab` / `fAdminModulesSection`; view `LocalsiemViews.modules` | [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| `/admin/dashboard/modules/installed/apache2/` (the older `/admin/dashboard/modules/apache2/` answers 301 to it) | `fAdminModule` (the 301: `fAdminModulesSection`); view `LocalsiemViews.module` | same files |
| `GET /api/modules` | `fModules` (state for everybody signed in) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `GET /api/admin/modules/apache2` | `fModule` (settings, values, sources, doctor, rules) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2` | `fSaveModule` (`enabled`, `settings`, `rules`) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/doctor` | `fRunDoctor` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/reconfigure` (**Reconfigure**, localSIEM 2.2.0 or newer) | `mRequirements` → `fRequirementChecks` | [mod-apache2/module.py](../mod-apache2/module.py), [mod-apache2/doctor.py](../mod-apache2/doctor.py) |
| `GET /api/events/{id}` | `fEvent` → `mDisplayRecord` | [backend/web/api_search.py](../../localSIEM/backend/web/api_search.py) |
| `"entry": "module:PrivescModule"` of `mod-privesc/module.json` | `PrivescModule` | [mod-privesc/module.py](../mod-privesc/module.py) |
| `mod-privesc/rules/*.yaml` | `RulesEngine` (core) | [mod-privesc/rules/](../mod-privesc/rules/) |
| `/admin/dashboard/modules/installed/privesc/`, `GET`/`POST /api/admin/modules/privesc`, `.../privesc/doctor`, `.../privesc/reconfigure` | `fAdminModule`, `fModule`, `fSaveModule`, `fRunDoctor`, `mRequirements` → `fRequirementChecks` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [mod-privesc/doctor.py](../mod-privesc/doctor.py) |
| Audit records of the rules of the server (any key) | `mAuditEvent` → `mAuditExec`, `mAuditUser`, `mAuditSyscall` | [mod-privesc/module.py](../mod-privesc/module.py) |

<a id="impact"></a>
## 6. Impact analysis

| Component | What is affected if it changes |
|---|---|
| `module.json` `id` | Must equal the folder name without `mod-` (the name of the installed folder) and `vName`. It is the key of the settings (`modules.<id>`), of the state (`<id>.doctor`) and the `module` of every event: a rename loses the saved settings and splits the history. |
| `module.json` `core` | Raising it above the installed localSIEM stops the module from loading (state «Error»); in the repository, Installable shows «Needs localSIEM X or newer» and Installed shows the newer version without **Update**. |
| `module.json` `entry` | Must point to a `Module` subclass; a wrong value is a load error. |
| `module.json` `default_enabled` | On/off of servers where the administrator never decided (if its requirements are missing on the first installation, off). |
| `module.json` `read_paths` | The read access localSIEM gives as root (`manage.py read-paths`): a missing folder means permission errors in the doctor and in the state. A change in a new version makes the web show the command for root again after **Update** (`access_changed`). |
| `module.json` `install_requirements` | The Requirements dialog of Installable (`fRequirementsBody` of `modules.js`). A wrong one (a system other than `debian` and `alpine`, an empty list or more than 20 commands, a command with a shell operator or a line break) makes the module invalid (`fCheckInstallRequirements` of the core): it is neither installed nor loaded. |
| `module.json` `setup_option` | Nothing: the core ignores it (no module has one since apache2 1.3.0 and privesc 1.1.0). |
| Folders `mod-<name>/` with a `module.json` at the top of the repository | What the catalog of the web lists, as the module `<name>`: Installable shows the ones not installed yet (one that needs a newer core as «Needs localSIEM X or newer», an invalid one as «The module of the repository is not valid»), and a `version` higher than the installed one makes Installed offer **Update**. |
| `module.json` `settings` | The form, the validation and the defaults. A new default applies to servers that never saved that key. Saved values are not migrated: a renamed key loses its value and an old value with a new type reaches the module as it was saved. |
| `locales/*.json` | Only the texts of the web; a missing text falls back to en-US, then to the key. |
| `parsers.py` (record dict) | Correlation (`correlation`, `fields.client_ip`, `fields.path`), the request card, the full-text index (`search`, `raw`), the unparsed-lines health and privacy. |
| `logformat.py` `dKnownFormats` | Parsing of every access log; `localsiem_combined` stays for the servers that already write it (versions 1.2.0 and earlier of the module added it): do not change its definition. |
| `correlate.py` | One event per request; the core calls `mAdd`, `mDue(pNow, pForce, pWatermark)` and `mPendingCount`, and feeds back the records still pending after a restart. Without `UNIQUE_ID` it pairs records by their `client_ip`, `method`, `uri`, `status` and `path` fields: a parser that writes them differently breaks the pairing. The wait for the audit record (`mWaitsForAudit`) needs the `modsecurity` field of the error.log lines and the records of the source `audit`. |
| `modsec.py` (categories, labels, ranges) | Alert rule names (SOC statistics group by them: keep them stable), grouping keys, `category:` searches. |
| `ApacheModule.mBuildEvent` (event dict) | Columns of the events table, the fields read by the YAML rules (`action`, `status`, `method`, `path`, `crs_matched`, `db_error`...), searches and the CSV export. |
| `ApacheModule.mAssess` | What reaches the SOC and its severity; the `GenericAlert` limits of the core (rule 300, description 10 000 characters). |
| `severity.yaml` | Severity of every ModSecurity detection; severity is part of the grouping key, so a change starts new groups. |
| `rules/*.yaml` | The `id` is the key of the overrides (`rules.<id>`) and of the searches (`rule:localsiem:<id>`): keep it stable. The fields must exist in the events; `{function: ...}` needs `mRuleFunctions`. |
| `discovery.py` | Which logs are read; `fSourceKey` is the key of the saved positions (a new key makes the file a new source, without its saved position); DocumentRoots of the web shell rule; the doctor. |
| `doctor.py` | The doctor of the web and of `manage.py` and the hints shown to the client. Only the checks about what is not a log (ModSecurity, the CRS, `SecRuleEngine`, `mod_unique_id`, permissions) may carry a `fix`; the checks about the logs only describe them. |
| `mRequirements` / `fRequirementChecks` | Whether the module can be turned on, the state «Off» after a first installation without Apache or ModSecurity, the requirements the web shows and **Reconfigure**. They run in the web and in `manage.py` without storage and parse the Apache configuration on every call: keep them away from the storage and from anything slow, and keep the ids `apache_config` and `modsecurity` stable. |
| privesc: event columns and fields (`mBuildEvent`, `mAnalyzeCommand`) | The YAML rules match them by name (`recon_burst`, `suid_escape`, `root_without_door`, `sensitive_group`, `writer_allowed`, `ptrace_attach`, `parent_interpreter`, `account_type`, `real_uid`, `argc_zero`...): a renamed field silently disables the rules that use it. `vhost` is the user: the grouping key of the alerts and the searches `vhost:` depend on it. |
| privesc: `fReconToken` | What counts as reconnaissance and how distinct commands are told apart: changing a token changes how fast a session reaches the thresholds. |
| privesc: `SessionTracker` and the doors (`sDoors`) | `root_without_door`: a door missing from the list makes legitimate root sessions critical; an extra one hides kernel exploits. `mExport`/`mImport` is the format of `privesc.sessions`. |
| privesc: `parsers.py` | The fields of the records (`args`, `command`, `kind`, `uid`/`euid` of snoopy), the masking of passwords and the raw text of the audit records; the formats of snoopy it reads (the module never changes `snoopy.ini`). |
| privesc: classification of the audit records (`lSensitivePaths`, `dSyscallTables`, `sChangeSyscalls`, `dOpenFlagArgument`, `dChmodModeArgument`, `sDeniedSyscalls`, `dKeyHints`) | What becomes `file`, `chmod`, `kmod`, `ptrace` and `denied`, and so the rules sensitive-file, persistence-file, monitoring-changed, suid-set, kernel-module, ptrace, denied-burst and sensitive-denied; a wrong syscall number misclassifies the records of that architecture. |
| privesc: `surface.py` | The cost of the scan (thread, limits) and what the doctor and `mSurfaceResult` report; `privesc.surface` is its reference. |
| privesc: `mRequirements` / `fRequirementChecks` | Whether the module can be turned on (any readable source), the state «Off» after a first installation whose logs `localsiem` cannot read yet, and **Reconfigure**; called without storage by the web and `manage.py`: keep it fast and without root. Keep the ids `command_source`, `audit_log` and `syslog`. |
| Core interface (`backend/core/module.py`, `registry.py` of localSIEM) | Every module: a changed hook signature, a new required manifest key or a new contract of records and events breaks them; raise `core` in their `module.json` when they need the new localSIEM. |

<a id="extensions"></a>
## 7. Extension points

### How to write a new module

1. **Folder**: create `mod-<name>/` at the root of this project; `<name>`, the name of the module, matches `[a-z][a-z0-9_]{1,31}`. The `mod-` prefix is only for the folder: `module.json`, the class, the options and the texts use `<name>`. No `__init__.py`.
2. **`module.json`**, for example:

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

3. **Texts**: `locales/<language>.json` for each of the 15 languages of localSIEM with `name`, `summary` and the label and help of every setting. The notes about the requirements go in `install_requirements` (`note`, for every system, and `debian` and `alpine`), shown in the Requirements dialog.
4. **Code**: `module.py` with a subclass of `Module` whose `vName` is the id. It must implement `mParse`, `mCreateCorrelator` and `mBuildEvent`, and usually `mDiscover`; the other hooks are optional (section 1). Import its own files relatively and the core as `backend.core...`. The two modules of this repository are complete examples ([mod-apache2/module.py](../mod-apache2/module.py), [mod-privesc/module.py](../mod-privesc/module.py)); a minimal sketch:

   ```python
   from backend.core.module import Module


   class OneEventCorrelator:
     # Each record is an event of its own, without waiting.

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

5. **Action taken**: decide what «already resolved» means for the service (for example, an IP already banned) and set `action` to `blocked` for it; add a detection only to events without an action taken.
6. **Rules**: YAML files in `mod-<name>/rules/`, returned by `mRulesPath`, and the functions they call in `mRuleFunctions`.
7. **Requirements**: if the module needs software on the server (as apache2 needs Apache and ModSecurity 2), return one check per requirement from `mRequirements()` (the format of `fCheck`: `status` `ok` or `error`, and in `fix` the command that installs it) and never install that software from the module: without its requirements the module is installed turned off. It runs without storage, also in the web and in `manage.py`. Declare also, in `install_requirements` of `module.json`, the commands that install that software on Debian and on Alpine (one command per line, without shell operators): the web shows them in Modules › Installable › Requirements, as they are and with `sudo` in front, before the module is installed.
8. **Install**: publish it in this repository (branch `main`); it appears in Modules › Installable of the localSIEM web while it is not installed, and **Install** copies the folder `mod-<name>/` to `/opt/localsiem/modules/<name>/` and restarts the collector. Read access to its `read_paths` needs root: the web shows the command (`manage.py setup-modules`). A module has no setup option: it never installs anything nor changes anything outside `/opt/localsiem`, and never writes in, rotates or deletes the logs of the client nor changes their format; if a server writes its logs in its own way, the module adapts to it, and what the server lacks is a requirement. To publish a new version, raise `version`: Modules › Installed shows the notice and **Update**, which keeps the settings and the on/off of the module and shows the command for root again only if `read_paths` changed.
9. **Documentation**: update the README, this CODE and the MANUAL in the 15 languages.

### How to add a rule to the apache2 module

Create a YAML file in [mod-apache2/rules/](../mod-apache2/rules/) (every key and operator is described at the top of [backend/core/rules.py](../../localSIEM/backend/core/rules.py)): `id`, `name`, `category`, `type`, `severity`, `kind` (`match`, `threshold` or `sequence`), the conditions (`when`, or `first`/`first_threshold`/`then`), `by`, `window`, `threshold`, `lists`, `description` and `search`. Fields are looked up in the event columns first and then in `fields`. It appears in the rules table of the module page and is loaded by the collector once the new version of the module is installed: raise `version` in `module.json`, publish it and press **Update** in Modules › Installed.

### How to add a setting to the apache2 module

Add it to `settings` of [mod-apache2/module.json](../mod-apache2/module.json) with its type and default, add its `label` and `help` to the four files of [mod-apache2/locales/](../mod-apache2/locales/), and read it with `self.mModuleSettings().get("<key>")`. The form, the validation and the reload come from the core.

### How to add a doctor check or change a severity

A check is one `fCheck(id, status, title, detail, fix)` in `fRunDoctor` ([mod-apache2/doctor.py](../mod-apache2/doctor.py)); keep the `id` stable and put in `fix` the exact snippet or command, only for requirements that are not logs: a check about the logs of the client only describes them and what localSIEM can or cannot read from them, without a `fix`. Severities of the ModSecurity detections are changed in [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) (`low`, `medium`, `high`, `critical`).

### How to add a rule to the privesc module

Create a YAML file in [mod-privesc/rules/](../mod-privesc/rules/), like the ones of Apache. Match the columns (`method`, `uri`, `path`, `vhost`, `action`) and the fields of the events (`sensitive_group`, `account_type`, `real_uid`, `recon`, `service_account`, `file`...), never the key of an audit rule; add `ignored: {not: true}` so that the ignored users never raise it, and `action: none` when only what really ran counts. If the condition needs state or logic (a sequence of the same session, a check of a file), compute a flag in `PrivescModule.mAnalyzeCommand` (every source) or in `mAuditExec`/`mAuditSyscall`/`mSyslogEvent` (one source) and match it from the rule.

### How to add a reconnaissance command, a tool or an exploit to the privesc module

- Reconnaissance: add the program to `sReconSimple`, or a branch to `fReconToken` that returns a token per kind of question ([mod-privesc/commands.py](../mod-privesc/commands.py)). A token that changes with every argument inflates the counts.
- Tools and exploits: add a regular expression to the list of [rules/known-tool.yaml](../mod-privesc/rules/known-tool.yaml) or [rules/exploit.yaml](../mod-privesc/rules/exploit.yaml) (case-insensitive, matched against the command line); the administrator can also add them from the settings (`rules.<id>.lists`).

### How to add a source or a kind of audit record to the privesc module

- A sensitive path: add it to `lSensitivePaths` of [mod-privesc/module.py](../mod-privesc/module.py) with its group (or a new group and a rule that matches `sensitive_group`). A kind of system call: add its name to the sets of `mAuditSyscall` and its number to each table of `dSyscallTables`. Never depend on the key of an audit rule (at most add it to `dKeyHints`) and never install audit rules: the server records what its administrator decides, and the doctor describes it (`dAuditKinds` of [doctor.py](../mod-privesc/doctor.py)).
- A source: return it from `fDiscoverSources` with a new `kind`, parse it in `mParse` and build its events in `mBuildEvent` with the same columns and fields as the others, so that the rules work without changes.
