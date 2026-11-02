# Référence du code de localSIEM-modules

Ce CODE est également disponible en :\
[de-DE](CODE.de-DE.md), [en-GB](CODE.en-GB.md), [en-US](CODE.md), [es-AR](CODE.es-AR.md), [es-ES](CODE.es-ES.md), fr-FR, [he-IL](CODE.he-IL.md), [hi-IN](CODE.hi-IN.md), [it-IT](CODE.it-IT.md), [ja-JP](CODE.ja-JP.md), [ko-KR](CODE.ko-KR.md), [pt-BR](CODE.pt-BR.md), [pt-PT](CODE.pt-PT.md), [ru-RU](CODE.ru-RU.md), [zh-CN](CODE.zh-CN.md)

## Index

1. [Architecture et décisions de conception](#architecture)
2. [Carte des modules](#modules)
3. [Symboles clés](#symbols)
4. [Principaux chemins d'appel](#flows)
5. [Points d'entrée](#routes)
6. [Analyse d'impact](#impact)
7. [Points d'extension](#extensions)

[Installation](README.fr-FR.md) · [Manuel d'utilisation](MANUAL.fr-FR.md) · [Référence du code de localSIEM](../../localSIEM/doc/CODE.fr-FR.md)

<a id="architecture"></a>
## 1. Architecture et décisions de conception

Ce projet contient les modules installables de localSIEM (projet voisin `../localSIEM`). Il n'a ni service ni installateur propre : les modules s'installent uniquement depuis l'interface web de localSIEM, dans Modules › Installables (ils se mettent à jour et se désinstallent dans Modules › Installés), qui télécharge ce dépôt (branche `main`) et copie chaque dossier de module, `mod-<name>/`, dans `/opt/localsiem/modules/<name>/` ; l'installateur de localSIEM n'installe que le cœur, jamais un module, et localSIEM n'a pas de modules propres. Les processus de localSIEM (collecteur, interface web, `manage.py`) le chargent. Le préfixe `mod-` n'appartient qu'au nom du dossier dans ce dépôt : le module lui-même (l'`id` de son `module.json`, ses options, ses paramètres et son dossier installé) garde son nom sans lui. Il existe aujourd'hui deux modules : `apache2` (dossier `mod-apache2/`) et `privesc` (dossier `mod-privesc/`).

### Pourquoi les modules vivent en dehors du cœur

Le cœur de localSIEM ([backend/core/](../../localSIEM/backend/core/)) est générique : le stockage, la recherche, le moteur de règles, le regroupement, la file d'attente du SOC, le signal de vie et la santé ne savent rien d'Apache. Ce que signifie un service (où sont ses journaux, comment ils sont découpés et analysés, comment des enregistrements deviennent un événement, ce qui compte comme déjà traité, ses règles et ses prérequis) vit dans un module. Garder les modules dans leur propre projet signifie que :

- un module a une version (`version`), déclare la version minimale de localSIEM dont il a besoin (`core`) et se met à jour, s'ajoute ou se désactive sans nouvelle version de localSIEM ;
- le cœur n'importe aucun module par son nom et n'a pas de module propre : le registre ([backend/core/registry.py](../../localSIEM/backend/core/registry.py)) parcourt uniquement `/opt/localsiem/modules/` (`LOCALSIEM_MODULES_PATH` dans les copies de développement), où l'interface web installe les modules de ce dépôt ;
- un module qui ne se charge pas n'arrête jamais les autres : son erreur est listée dans l'interface web (état «Erreur») et par `manage.py modules` ;
- un module ne modifie jamais le cœur : `backend/core/module.py` et `backend/core/registry.py` constituent tout le contrat.

### Le contrat : module.json, les locales et une sous-classe de Module

**`module.json`** (vérifié par `fReadManifest`) :

| Clé | Par défaut | Signification | apache2 | privesc |
|---|---|---|---|---|
| `id` | obligatoire | Nom du dossier du module sans le préfixe `mod-` (le nom du dossier installé), `[a-z][a-z0-9_]{1,31}` ; c'est aussi le `vName` de la classe | `apache2` | `privesc` |
| `version` | `"0"` | Version du module, affichée dans l'interface web et par `manage.py modules` | `1.3.2` | `1.1.2` |
| `core` | `"0"` | Version minimale de localSIEM dont il a besoin ; une version supérieure au `cVersion` du localSIEM installé signifie que le module n'est pas chargé | `2.2.0` | `2.2.0` |
| `entry` | obligatoire | `"file:Class"` : `file` sans `.py` (`[a-z][a-z0-9_]{0,63}`), `Class` une sous-classe de `Module` | `module:ApacheModule` | `module:PrivescModule` |
| `default_enabled` | `true` | S'il s'exécute tant que l'administrateur n'a pas décidé (`modules.<id>.enabled`) | `true` | `true` |
| `read_paths` | `[]` | Dossiers absolus que localSIEM, en tant que root, permet à l'utilisateur `localsiem` de lire (la commande qu'affiche l'interface web après l'installation, après **Reconfigurer** et après une mise à jour qui les modifie) | `["/var/log/apache2"]` | `["/var/log/audit"]` |
| `install_requirements` | `{}` | Commandes qui installent sur le serveur, en tant que root, le logiciel dont le module a besoin, pour chaque système (`debian`, `alpine`) : une commande par ligne, sans opérateurs du shell, car l'interface web les affiche aussi précédées de `sudo` (`fCheckInstallRequirements` du cœur). Affichées dans Modules › Installables › Prérequis, jamais exécutées | Debian : Apache, ModSecurity 2, le CRS, `a2enmod`, la configuration recommandée de ModSecurity s'il n'y en a aucune, redémarrage ; Alpine : Apache | Debian : auditd et rsyslog ; Alpine : auditd |
| `setup_option` | — | Utilisée par aucun module : le cœur l'ignore (le registre la supprime), car un module ne modifie jamais le serveur ; des fichiers `module.json` d'anciennes versions peuvent encore l'avoir | non définie | non définie (`--configure-privesc` a été supprimée dans la 1.1.0) |
| `settings` | `[]` | Description de chaque paramètre : l'interface web construit son formulaire à partir d'elle | 6 paramètres | 13 paramètres |

Chaque paramètre a une `key` (`[a-z][a-z0-9_]{1,31}`), un `type`, généralement un `default`, et les attributs de son type. `fValidateSettings` / `fCleanValue` / `fCleanRecords` vérifient ce que l'administrateur enregistre :

| Type | Attributs | Contrôle web | Valeurs acceptées |
|---|---|---|---|
| `boolean` | — | case à cocher | `true` / `false` |
| `integer` | `min`, `max` | champ numérique | un entier compris entre `min` et `max` |
| `string` | `max_length` (500) | champ de texte | texte sans caractères de contrôle, sans espaces aux extrémités, jusqu'à `max_length` |
| `path` | — | champ de texte à chasse fixe | vide ou absolu (commence par `/`), jusqu'à 1024 caractères |
| `choice` | `choices` (obligatoire), `required` | liste (avec «—» quand il n'est pas obligatoire) | l'un des `choices`, ou vide |
| `records` | `fields` (obligatoire : paramètres des autres types), `max_items` (50) | un bloc par enregistrement avec Ajouter et Retirer | une liste d'au plus `max_items` enregistrements ; chaque champ est vérifié, les champs `required` ne peuvent pas être vides et les champs vides sont supprimés |

**`locales/<language>.json`** (de-DE, en-GB, en-US, es-AR, es-ES, fr-FR, he-IL, hi-IN, it-IT, ja-JP, ko-KR, pt-BR, pt-PT, ru-RU, zh-CN), lu par `fReadTexts` et affiché par l'interface web (`modules.js fModuleText`, qui se rabat sur en-US puis sur la clé) :

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

Un fichier de locale absent ou cassé ne fait perdre que sa langue.

**La sous-classe de `Module`** ([backend/core/module.py](../../localSIEM/backend/core/module.py)). Le registre la crée sous la forme `Class(pSettings, pMasker, pStorage, pManifest)`. Ses hooks :

| Hook | Appelé par | Par défaut | `ApacheModule` | `PrivescModule` |
|---|---|---|---|---|
| `mStart()` | collecteur, une fois, avec le stockage prêt | rien | enregistre `apache.first_start` (début des jours d'apprentissage) | enregistre `privesc.first_start` ; charge `privesc.sessions`, `privesc.surface` et `privesc.health` |
| `mEnabled()`, `mModuleSettings()`, `mReload()` | collecteur, interface web | depuis `modules.<id>` par-dessus les valeurs par défaut de `module.json` | hérité | hérité ; `mReload` vide aussi le cache de `mSettings` |
| `mDiscoveryInterval()` | collecteur (le plus court des modules activés, au moins 60 s) | `discovery_interval_seconds` ou 3600 | hérité | hérité (300 par défaut) |
| `mDiscover()` | collecteur (démarrage, intervalle, rechargement, demande de diagnostic), `manage.py doctor` | `[]` | sources `{key, path, kind, format, vhost, audit_type, storage_dir}` issues de la configuration d'Apache et des sources manuelles | `fDiscoverSources` : le journal d'audit et syslog |
| `mCreateFramer(pSource)` | collecteur, par source | `LineFramer` | `AuditFramer` pour le journal d'audit natif en série | hérité (`LineFramer`) |
| `mParse(pSource, pUnit, pReceived)` | collecteur, par unité | obligatoire | enregistrement `access`, `error` ou `audit` | enregistrement `audit` ou `syslog` |
| `mCreateCorrelator()` | collecteur, au démarrage | obligatoire | `Correlator` (fenêtre et corrélation faible issues des paramètres du cœur) | `Correlator` : enregistrements d'audit par numéro de série (EOE ou 2 s) ; lignes syslog immédiatement |
| `mBuildEvent(pTransaction)` | collecteur, par transaction échue | obligatoire | événement avec `action` et `detections` | événement avec les indicateurs que testent les règles ; pas de détections propres |
| `mRulesPath()` / `mRuleFunctions()` | collecteur, au chargement des règles | `None` / `{}` | `rules/` de son dossier / `{"apache2.new_php": mIsNewPhp}` | `rules/` de son dossier / `{}` hérité |
| `mDetectionFromSignal(pEvent, pSignal)` | collecteur, par signal de règle (facultatif : recherché avec `hasattr`) | détection générique | détection avec les détails de la requête et `{rule: {id, count}}` | détection avec utilisateur, commande, programme, session, parent, fichier... |
| `mEnrich(pDetection)` | collecteur, avec le groupe, avant de construire l'alerte | `{}` | contexte de l'IP sur la dernière heure | contexte de la session : début vu, porte, adresse SSH, 20 dernières commandes |
| `mDoctor()` | collecteur (état `<id>.doctor`), `manage.py doctor` | `[]` | `fRunDoctor` | `fRunDoctor` (auditd et ce qu'ont enregistré ses règles, syslog, snoopy, ce que voit le module, fichiers de la version 1.0.0, surface d'attaque) |
| `mHealth(pNow)` | collecteur, toutes les 60 s, modules activés uniquement | `[]` | ModSecurity déchargé ou à Off, IP réelle du client manquante (au plus toutes les 300 s) | enregistre les sessions ; résultats de l'analyse ; toutes les 300 s : auditd arrêté, fichiers sensibles modifiables (toutes les heures), lance l'analyse des programmes setuid |
| `mSkipped()` | état du collecteur, `manage.py doctor` | `[]` | journaux envoyés dans un pipe, journaux couverts par le `GlobalLog`, journaux d'accès sans données (`format_without_data`) | syslog non lu (auditd en marche, `syslog_mode` à never), journal d'audit absent |
| `mSetLowDisk(pLowDisk)` | collecteur, niveau du disque | rien | cesse de conserver les en-têtes et les corps de l'audit | hérité |
| `mDisplayRecord(pRecord)` | interface web, fiche de la requête | `{}` | en-têtes et corps de l'enregistrement d'audit conservé (`fAuditDisplay`) | hérité |
| `mRequirements()` | cœur, localSIEM 2.2.0 ou ultérieur : première installation, démarrage et rechargement du collecteur, **Reconfigurer** dans l'interface web, `manage.py modules` et `doctor` | `[]` (aucun prérequis) | `apache_config` et `modsecurity` (`fRequirementChecks`) | `command_source` : toute source que `localsiem` peut lire, le journal d'audit (auditd en marche, pas dans un conteneur) ou syslog (avec snoopy, s'il est installé) ; `audit_log` / `syslog` quand une source existe mais ne peut pas être lue |

Le cœur n'a plus ni `mSetupSnippet` ni `mApplySetup` : les modules n'ont pas d'options de configuration et ne modifient jamais le serveur.

Les enregistrements sont des dicts avec `time`, `received`, `module` (l'id : le collecteur choisit le corrélateur en fonction de lui), `source`, `source_key`, `correlation`, `parse_status` (`ok`, `partial`, `unparsed`), `fields` et `raw` (masqué), plus éventuellement `search` (le texte indexé pour la recherche en texte intégral). Les événements ont les colonnes de la table des événements (`lEventColumns` dans `storage_sqlite.py`) plus `record_ids`, `rule_hits` et `detections`. Une détection a `module`, `vhost`, `ip`, `category`, `severity`, `rule`, `type`, `description`, `search`, `details`, `time` et `uid`.

### Prérequis : un module n'installe jamais ce qu'il surveille

Installer un module n'installe jamais le logiciel qu'il surveille : le module apache2 n'installe ni Apache ni ModSecurity, et le module privesc n'installe ni auditd, ni démon syslog, ni snoopy (son prérequis, `command_source`, est toute source que l'utilisateur `localsiem` peut lire : le journal d'audit avec auditd en marche hors conteneur, ou syslog ; `fRequirementChecks` de `mod-privesc/doctor.py`). Le module lui-même définit ce dont il a besoin avant de pouvoir être activé, dans `mRequirements()` (localSIEM 2.2.0 ou ultérieur) : une liste de vérifications au format du diagnostic, remplie quand aucune n'a le statut `error`. Le module apache2 renvoie `apache_config` (une configuration d'Apache est trouvée : `apache2.conf`, `httpd.conf` ou le fichier du paramètre `config_file`) et `modsecurity` (`mod_security2` est chargé ; ModSecurity 3 ne compte pas), que `fRequirementChecks` tire des premières vérifications du diagnostic ; sans Apache, les deux sont des erreurs. Ce qui installe ce logiciel est déclaré dans `install_requirements` de `module.json` : l'interface web l'affiche avant d'installer le module (Modules › Installables › Prérequis), pour le système du serveur, et ne l'exécute jamais. Le cœur :

- installe le module désactivé (`modules.<id>.enabled = false`) quand un prérequis manque lors de sa première installation et que l'administrateur n'a jamais décidé ; une mise à jour ne modifie jamais `enabled` ;
- ne permet pas de l'activer tant qu'un prérequis manque : l'interrupteur est verrouillé et l'interface web affiche les prérequis avec leur `fix` ;
- ne désactive jamais de lui-même un module activé qui perd un prérequis : son diagnostic et ses avertissements de santé (`mHealth` : «ModSecurity is no longer loaded») le signalent, et le désactiver les ferait taire ;
- vérifie de nouveau les prérequis quand le collecteur démarre ou se recharge, et avec **Reconfigurer** dans la page du module (même quand il est désactivé) : s'ils sont remplis, il déverrouille l'interrupteur, l'administrateur active le module, et l'interface web affiche la commande à exécuter en tant que root qui permet à `localsiem` de lire les journaux créés après l'installation (`read_paths`).

### Chargé comme namespace package

Il n'y a de `__init__.py` nulle part (namespace packages implicites de Python 3.13). `fRegisterPackage` crée le package `localsiem_modules` avec le dossier des modules comme `__path__`, et `fLoadClass` importe `localsiem_modules.<id>.<file>`, vérifie que la classe est un `Module` et que son `vName` est égal à l'`id`. Conséquences pour le code d'un module :

- ses propres fichiers sont importés **relativement** (`from .parsers import AccessParser`) ;
- le cœur est importé sous la forme **`backend.core...`** (`from backend.core.module import Module`) : les processus de localSIEM placent le dossier de localSIEM dans `sys.path` ;
- seules la bibliothèque standard et les dépendances de localSIEM (son environnement virtuel `/opt/localsiem/venv/`, par exemple PyYAML) sont disponibles : localSIEM n'installe rien pour un module.

### Formulaire de paramètres construit à partir du manifeste

Un module n'a pas de HTML propre. L'interface web lit `settings` de `module.json` et les textes de `locales/`, construit le formulaire (`modules.js fBuildSettings`, `fRecordsEditor`), valide ce qui est enregistré avec `fValidateSettings` et ne conserve dans `settings.json`, sous `modules.<id>`, que les valeurs que l'administrateur a enregistrées ; `enabled` s'y trouve aussi. Le module lit `mModuleSettings()` : les valeurs par défaut de `module.json` avec, par-dessus, les valeurs enregistrées. Ajouter un paramètre ne nécessite donc aucune modification de l'interface web ni du cœur.

Paramètres du cœur que le module apache2 lit aussi depuis `self.dSettings` : `host`, `correlation_window_seconds` (5), `weak_correlation_seconds` (2), `below_threshold_severity` (`low`) et `health.single_ip_percent` / `health.single_ip_minimum_requests` (90 / 100). `mModuleSettings()` transmet aussi les clés enregistrées sous `modules.apache2` que `module.json` ne déclare pas : c'est ainsi que `mDiscover` lit `document_roots` (`{vhost: folder}`, par-dessus les DocumentRoots découverts) ; il ne peut être défini qu'en modifiant `settings.json`.

### Le principe de l'«action effectuée»

Seul ce que personne n'a encore traité part au SOC. Dans le module apache2, l'action effectuée est lue depuis la source la plus fiable : le journal d'audit (`Action: Intercepted (phase N)` au format natif, `audit_data.action.intercepted/phase` en JSON), puis error.log (`Access denied with code NNN (phase N)`). Un 403 sans aucune trace de ModSecurity n'est pas un blocage (`fields.doubtful_block`).

| Situation | `action` | Détection (vers le SOC) |
|---|---|---|
| Interceptée en phases 1-2 (l'application ne l'a jamais reçue) | `blocked` | aucune : `mAssess` renvoie `None` ; comptée dans le contexte des alertes ultérieures |
| Interceptée en phases 3-4 | `none` | oui, `blocked_late` (élevée), ou `success_indicator` avec une erreur de base de données |
| Correspondances avec le moteur en `DetectionOnly` | `none` | oui |
| Correspondances sous le seuil d'anomalie | `none` | oui, `below_threshold` (faible) |
| Signaux des règles YAML | `none` | oui |

Les gravités proviennent de `severity.yaml` (`fLoadSeverityTable` ; un fichier absent ou une valeur non valide conserve la valeur par défaut intégrée) : `crs_not_blocked_2xx` élevée, `crs_not_blocked_other` moyenne, `blocked_late` élevée, `success_indicator` critique (règle sortante 950-955 non bloquée, ou erreur de base de données dans la même requête), `below_threshold` faible (le paramètre du cœur `below_threshold_severity` a la priorité). «Au-dessus du seuil» signifie qu'une règle 949xxx s'est déclenchée ou que le score indiqué par ModSecurity a atteint le seuil ; un score calculé à partir des gravités des règles n'est qu'une estimation et ne décide pas. Le seuil est celui des messages, sinon `anomaly_threshold`, sinon celui de `crs-setup.conf`, sinon 5.

### Fonctionnement du module apache2

1. **Découverte** (`discovery.py`) : `ApacheConfig` lit directement la configuration (`Include`, `IncludeOptional`, `Define`, `${VARS}` de l'`envvars` de Debian, `<VirtualHost>`, `<IfModule>` comparé aux modules chargés), en tant qu'utilisateur `localsiem` et sans `apache2ctl`. `fDiscoverSources` transforme `CustomLog`/`GlobalLog`/`TransferLog`, `ErrorLog` et `SecAuditLog` en sources avec la clé stable `apache:<kind>:<real path>`. Un `GlobalLog` dont le format contient `%v` couvre tous les vhosts (les autres journaux d'accès sont ignorés) ; les journaux envoyés dans un pipe et syslog sont ignorés, de même que les journaux d'accès dont le format n'a aucune directive `%` (Apache écrit tel quel un alias qu'aucun `LogFormat` ne définit : `format_without_data`, sauf si un autre `CustomLog` avec des données écrit dans le même fichier ; le diagnostic l'indique, sans correction, puisque le format des journaux n'est jamais modifié) ; les sources manuelles passent en premier et un fichier n'est lu qu'une fois.
2. **Découpage et analyse** (`parsers.py`, `logformat.py`, `modsec.py`) : les lignes d'accès sont analysées avec une expression régulière générée à partir de leur `LogFormat` (le dernier format qui a fonctionné est essayé en premier) ; les lignes d'erreur sont classées (`modsecurity`, `database`, `php`, `crash`, `apache`) ; les enregistrements d'audit sont lus en JSON (une ligne, coupée avant `matched_rules`), en série natif (`AuditFramer` réunit `--id-A--` à `--id-Z--`) ou en concurrent (la ligne d'index pointe vers un fichier sous `SecAuditLogStorageDir`). Tout est masqué ; ce qui ne correspond pas est conservé comme `unparsed`.
3. **Corrélation** (`correlate.py`) : les enregistrements ayant le même `UNIQUE_ID` forment une transaction, qui attend la fenêtre de corrélation et le filigrane (watermark) des sources en train de rattraper leur retard ; une ligne d'accès sans `UNIQUE_ID` (les formats qu'Apache écrit par défaut) est appariée par `mPair`, quand elle ou les enregistrements de sa requête arrivent à échéance, avec les enregistrements de ModSecurity qui n'ont pas de ligne d'accès : même IP du client, heure à ±2 s (la ligne a des secondes entières) et mêmes méthode, URI, code de statut et chemin quand les deux côtés les connaissent ; le candidat qui concorde sur le plus grand nombre d'entre eux l'emporte, puis le plus proche, puis le plus ancien, et l'événement est marqué comme faible. Les lignes d'error.log sans `UNIQUE_ID` rejoignent immédiatement la transaction la plus proche de leur IP. Une transaction avec un `UNIQUE_ID` et une ligne ModSecurity d'error.log, alors que des enregistrements d'audit arrivent (`vAuditSeen`), attend aussi son propre enregistrement d'audit (`mWaitsForAudit`), au plus `cAuditWaitSeconds` (120 s) à partir de son premier enregistrement : ModSecurity écrit les lignes de ses règles pendant que la requête s'exécute et l'enregistrement d'audit à sa fin, de sorte qu'une requête lente deviendrait sinon deux événements ; une fois l'enregistrement d'audit arrivé, la ligne d'accès dispose de `cAfterAuditSeconds` (2 s) supplémentaires.
4. **Événement** (`ApacheModule.mBuildEvent`) : champs pris dans access, puis audit, puis error ; le vhost depuis `%v` ou, à défaut, depuis l'en-tête Host et le port local de l'enregistrement d'audit (`mVhostName`) ; avec une ligne d'accès à secondes entières, l'heure de l'enregistrement d'audit ; `fSummarize` donne les règles, les catégories, le score, le seuil et l'interception ; l'action effectuée et `mAssess` décident de la détection.
5. **Règles, enrichissement, diagnostic et santé** : les règles YAML de `rules/` s'exécutent sur chaque événement (moteur du cœur) ; `mEnrich` ajoute le contexte de l'IP ; `fRunDoctor` vérifie les prérequis et décrit les journaux, sans rien modifier ; `mHealth` surveille ModSecurity et l'IP réelle du client. Le module n'a pas d'option de configuration : en tant que root, localSIEM donne seulement à `localsiem` l'accès en lecture à `/var/log/apache2`.

### Décisions de conception à connaître

- **Pas d'installateur propre** : les modules sont installés (Modules › Installables), mis à jour (**Mettre à jour**, dans Modules › Installés) et désinstallés (**Désinstaller**) uniquement depuis l'interface web de localSIEM, qui télécharge ce dépôt et les installe avec `backend/core/catalog.py` (décompression sûre, une installation à la fois, remplacement atomique du dossier). Ce qui nécessite root (l'accès en lecture aux `read_paths`) est fait par localSIEM : après l'installation (et après une mise à jour qui modifie `read_paths`), l'interface web affiche la commande à exécuter en tant que root.
- **Les journaux du client sont seulement lus** : un module n'écrit jamais dans les journaux des services qu'il surveille, ne les soumet jamais à une rotation, ne les tronque, ne les déplace ni ne les supprime, et ne modifie jamais leur format ; le module apache2 ne modifie pas non plus la configuration d'Apache ou de ModSecurity (il n'a pas de `setup_option`). Si un serveur écrit ses journaux dans un format qui lui est propre (son propre `LogFormat`, l'IP du client de `mod_remoteip`), le module s'adapte : `AccessFormat` construit l'analyseur de chaque journal d'accès à partir de son `LogFormat`, et `fCanPair` / `Correlator.mPair` réunissent les lignes sans `UNIQUE_ID`. Le diagnostic ne fait que décrire les journaux et ce que localSIEM peut ou ne peut pas en lire : les vérifications `log_format`, `log_format_without_data`, `remoteip`, `audit_log` et `sanitise` n'ont pas de `fix` ; seul ce qui n'est pas un journal (ModSecurity, le CRS, `SecRuleEngine`, `mod_unique_id`, les permissions de lecture de `localsiem`) en a un. `--configure-apache` a été supprimée dans la version 1.3.0 ; `localsiem_combined` reste dans `dKnownFormats` pour les serveurs qui l'écrivent déjà, et l'installateur de localSIEM supprime le `localsiem.conf` qu'écrivaient les anciennes versions (`--uninstall`, `--reinstall`).
- La **partie K** (`matched_rules`) et la **partie E** (corps de la réponse) du journal d'audit ne sont jamais conservées. Les en-têtes et le corps restent uniquement dans l'enregistrement brut masqué ; la fiche de la requête les reconstruit (`fAuditDisplay`). L'index en texte intégral reçoit un texte réduit (`search` : ligne de requête, hôte, user agent et l'id, le message et les données de chaque règle).
- **Le texte brut est reconstruit à partir des parties masquées** : l'enregistrement d'audit d'origine peut contenir des mots de passe et des cookies.
- **L'interface web et les outils créent le module sans stockage** (`pStorage` vaut `None` dans `WebContext.mModule` et `manage.py`) : le constructeur et les hooks qu'ils appellent ne doivent pas utiliser le stockage.
- **État dans la base de données des événements** : `apache.first_start` (jours d'apprentissage), `apache.health` (ce qui a déjà été signalé, pour qu'un redémarrage ne le répète pas) et `apache2.doctor` (écrit par le collecteur). Les deux premiers, comme les clés de source `apache:<kind>:<real path>`, gardent le nom qu'avait le module avant de s'appeler apache2 : un serveur qui avait le module `apache` conserve ses jours d'apprentissage, sa mémoire de santé et ses positions de lecture (avec une nouvelle clé de source, chaque journal de moins de 5 Mio serait relu depuis le début). Les heures de la mémoire de santé sont au format natif du projet (`2026-10-29@13-59-59.723`, UTC) ; un état enregistré par une ancienne version, avec des secondes epoch, est converti au chargement.
- **Sécurité des chemins** : `mIsNewPhp` refuse `..` et reste à l'intérieur du DocumentRoot ; `fReadConcurrentEntry` reste à l'intérieur de `SecAuditLogStorageDir` et lit au plus 8 Mio ; le corrélateur garde au plus 50 000 transactions en attente.

### Fonctionnement du module privesc

La question n'est pas «quelqu'un a-t-il exécuté `whoami` ?» (les administrateurs le font tous les jours) mais «cette session suit-elle le chemin d'une élévation, et y est-elle parvenue ?». Le module transforme deux sources en événements ayant une seule signification (`vhost` la personne, `method` le type, `uri` la commande, `path` le programme ou le fichier, `ip` l'adresse SSH, `score` la reconnaissance distincte de la session), calcule des indicateurs sur eux, et laisse les règles YAML décider de ce qui part au SOC.

1. **Découverte** (`discovery.py`) : `fDiscoverSources` renvoie le journal d'audit (`fAuditLogPath` : paramètre, `log_file` d'`auditd.conf`, `/var/log/audit/audit.log` ; y compris quand auditd tourne et que `localsiem` ne peut pas encore le lire, afin que le cœur le signale) et syslog (`fSyslogPath`) quand `syslog_mode` le prévoit (`auto` : auditd ne tourne pas, son journal n'est pas lisible, ou snoopy est installé). Il rassemble aussi ce dont le diagnostic a besoin : conteneur (`fContainer`, lisible sans root : `/run/systemd/container`, `/run/.containerenv`, `/.dockerenv`, `/proc/self/cgroup`, `systemd-detect-virt`), binaire et pid d'auditd, snoopy, si chaque journal peut être lu (`fReadState` : `readable`, `unreadable` ou `missing`) et les fichiers qu'a laissés la version 1.0.0 (`fLegacyLeftovers`). `Accounts` relit `/etc/passwd`, `/etc/group` et `UID_MIN` quand ils changent, et classe un uid comme `root`, `admin` (membre de `admin_groups`), `user` ou `service`.
2. **Analyse** (`parsers.py`) : `fParseAuditLine` lit `type=... msg=audit(<time>:<serial>): k=v ...`, la partie espace utilisateur `msg='...'`, la partie enrichie après `\x1d`, réunit les arguments d'`EXECVE` (y compris ceux découpés en morceaux `aN[i]`), décode les valeurs hexadécimales (`proctitle`, `cmd`, `cwd`, `name`, `exe`, `aN`...) et **reconstruit le texte brut à partir des valeurs décodées et masquées** (l'hexadécimal d'un mot de passe le conserverait) ; `search` reçoit la commande décodée. `fParseSyslogLine` lit les horodatages ISO et classiques (avec ou sans le `facility.priority` de busybox) et `fParseSyslogMessage` comprend snoopy (ses formats par défaut de 2.4 et 2.5, `uid:alice(1000)/root(0)` compris, et celui que définissait la version 1.0.0), sudo, su (util-linux et busybox), pkexec, doas, `pam_unix` et sshd. `fMaskCommand` masque les mots de passe dans les lignes de commande avant le masqueur du cœur.
3. **Corrélation** (`correlate.py`) : les enregistrements d'audit ayant le même numéro de série forment une transaction, échue à `EOE`, immédiatement pour les types espace utilisateur à un seul enregistrement (`USER_*`, `CRED_*`, `DAEMON_*`...), ou après 2 s sans enregistrements ; au plus 50 000 en attente. Les lignes syslog sont échues immédiatement.
4. **Événement** (`PrivescModule.mBuildEvent`) : `mAuditEvent` répartit par type : `EXECVE` → `mAuditExec` (bit setuid du programme à partir de l'enregistrement `PATH` ou de `stat`, `suid_escape` quand l'euid vaut 0, que l'uid réel ne vaut pas 0 et que le programme n'est pas setuid, capabilities obtenues depuis `BPRM_FCAPS`, `root_without_door`, `parent_interpreter` quand un shell s'exécute en tant que root lancé par un interpréteur d'un utilisateur autre que root, le parent depuis la mémoire des processus) ; `USER_*`/`LOGIN` → `mAuditUser` (session démarrée, adresse SSH, portes : `USER_START`/`USER_CMD` de sudo, su, pkexec, doas, run0, systemd ; échecs) ; `CONFIG_CHANGE` (`audit_disabled`, `audit_rule_removed` pour toute règle supprimée), `DAEMON_*` (`auditd_stopped_manually` quand l'émetteur n'est pas le pid 1), `ANOM_ABEND` (`crash_suspicious`) ; tout autre `SYSCALL` → `mAuditSyscall`, qui le classe selon son appel système (`fSyscallName` : le nom du format enrichi, ou le numéro dans la table de son architecture), ses arguments et ses enregistrements `PATH`, jamais selon la clé de la règle : `denied` (open, exec ou truncate échoué avec `EACCES`/`EPERM` pour une personne), `kmod`, `ptrace` (`ptrace_attach` pour `PTRACE_ATTACH`/`PTRACE_SEIZE`), `chmod` (mode avec le bit setuid ou setgid, pas sur un dossier, avec `writer_allowed`) et `file` (une modification d'un chemin de `lSensitivePaths`, avec `sensitive_group` et `writer_allowed` ; la clé, via `dKeyHints`, uniquement quand aucun chemin ne peut être résolu). `mSyslogEvent` traite snoopy comme `exec` (`suid_escape` à partir de `stat` ; sans `filename`, le programme à partir du premier mot de la commande) ainsi que sudo, su, pkexec, doas, login et pam. Chaque commande passe par `mAnalyzeCommand` : jeton de reconnaissance (`fReconToken`) et jetons distincts de la session dans la fenêtre (`recon_burst`, `recon_massive`, `score`), téléchargements exécutés par un shell (`cDownloadOnelinerRegex`, ou un outil de téléchargement suivi d'un shell ayant le même parent), `compile_in_tmp`, les dernières commandes de la session et, pour les comptes de service, le programme (`fProgramKey`) comparé à son historique (`mPathFirstSeen` du cœur, après `learning_days` : `new_program`). `ignored` marque les utilisateurs ignorés.
5. **Règles, enrichissement, diagnostic et santé** : les 35 règles YAML de `rules/` décident de chaque détection (`mDetectionFromSignal`) ; `mEnrich` ajoute le contexte de la session ; `fRunDoctor` décrit auditd et ce qu'ont enregistré ses règles, syslog, snoopy, ce que le module voit et ce qu'il ne voit pas, les fichiers de la version 1.0.0 et la surface d'attaque ; `mHealth` signale auditd arrêté, les fichiers sensibles modifiables et le résultat de l'analyse des programmes setuid (`SurfaceScanner`, un thread). Le module n'a pas d'option de configuration et ne modifie rien sur le serveur.

### Décisions de conception du module privesc

- **Deux sources, une seule signification.** Un utilisateur ne peut pas échapper à auditd, mais auditd ne tourne pas dans les conteneurs (l'audit du noyau n'est pas isolé par namespace) ; snoopy voit chaque programme dans les conteneurs mais a besoin de syslog ; syslog seul ne fournit que sudo, su, pkexec et doas. Aucune source ne voit les commandes internes du shell. Les règles testent des colonnes et des indicateurs, jamais la source, de sorte qu'une source peut être ajoutée sans les toucher. La même commande vue deux fois donne une seule alerte : le cœur regroupe les détections par module, utilisateur, IP, catégorie et gravité.
- **Des rafales, pas des commandes.** La reconnaissance est un jeton par type de question (`whoami`, `read:/etc/passwd`, `find:-perm:`...), et seul le nombre de jetons distincts d'une session dans une fenêtre déclenche une alerte, avec un seuil plus élevé pour les administrateurs et un troisième pour les scripts. Les seuils sont des paramètres, pas des seuils de règle : la règle ne teste que `recon_burst` / `recon_massive`.
- **La réussite est ce qui compte le plus.** `suid_escape` (un programme qui n'est pas setuid s'exécutant avec l'euid 0 et un uid réel différent de 0) et `root_without_door` (root dans une session dont le début a été vu et qui n'est jamais passée par sudo, su, pkexec ou doas) sont les deux signes critiques qu'une élévation a réussi, presque sans faux positifs. Une session dont le début n'a pas été vu (sessions ouvertes avant le module, sessions oubliées après une journée d'inactivité) n'est jamais signalée.
- **Les sessions survivent aux redémarrages.** `SessionTracker` conserve le début, l'adresse SSH et la porte de chaque session dans l'état `privesc.sessions` (enregistré au plus une fois par minute) ; les jetons de reconnaissance et les dernières commandes restent en mémoire. Les sessions inactives depuis une journée sont abandonnées.
- **Uniquement ce dont le serveur dispose déjà.** Le module n'installe jamais rien et ne modifie jamais rien en dehors de `/opt/localsiem` : il ne charge aucune règle d'audit, ne touche ni à `auditd.conf` ni à `snoopy.ini` et n'installe aucun hook. La version 1.0.0 le faisait (`--configure-privesc` : règles d'audit avec les clés `lsiem_*`, `log_group = adm`, un hook bash, le format de snoopy) ; la version 1.1.0 l'a supprimé. Les enregistrements d'audit sont donc classés selon leur type, leur appel système et leurs chemins, de sorte que n'importe quelles règles d'audit fonctionnent (celles du serveur, les règles d'exemple STIG, ou les règles `lsiem_*` qu'a laissées la 1.0.0) ; la clé est conservée dans `fields.key` pour les recherches et n'est qu'une indication (`dKeyHints`). Les numéros des appels système sont lus par architecture (`dSyscallTables` : x86_64, i386 et la table générique d'aarch64, riscv64 et loongarch64) quand le journal n'a pas de noms enrichis. Le diagnostic décrit ce que les règles du serveur enregistrent et ce qu'elles n'enregistrent pas ; son `fix` n'est qu'un paquet à installer ou l'accès en lecture de `localsiem`.
- **Lisible signifie lisible.** Le prérequis est rempli par une source qui existe et que `localsiem` peut ouvrir (`fReadState`), pas par un programme installé : lors d'une première installation, les journaux appartiennent généralement à root, donc le module reste désactivé jusqu'à la commande pour root (`manage.py setup-modules`) et **Reconfigurer**.
- **Les gestionnaires de paquets ne sont pas des attaquants.** Les modifications de fichiers sensibles et de bits setuid faites par les outils de comptes et de paquets (`sAllowedWriters`), ou par des programmes dont les ancêtres connus sont des gestionnaires de paquets, positionnent `writer_allowed`, et les règles les ignorent.
- **L'analyse ne bloque jamais le collecteur.** `SurfaceScanner` parcourt les `scan_paths` dans un thread qui lui est propre, sans sortir du système de fichiers de chacun, en ignorant `/proc`, `/sys` et les dossiers des conteneurs, jusqu'à 3 millions de fichiers ou 15 minutes ; `mHealth` récupère le résultat quand il est prêt. La première analyse sert de référence ; les suivantes signalent ce qui est nouveau.
- **L'interface web et les outils créent le module sans stockage** : `mDiscover`, `mDoctor` et `mRequirements` ne l'utilisent jamais, et `mAnalyzeCommand` n'appelle `mPathFirstSeen` que lorsqu'il existe.
- **État dans la base de données des événements** : `privesc.first_start` (jours d'apprentissage), `privesc.sessions`, `privesc.surface` (la référence de l'analyse et le diagnostic), `privesc.health` (ce qui a déjà été signalé, si auditd tournait) et `privesc.doctor` (écrit par le collecteur). Les programmes vus des comptes de service sont des lignes de `seen_paths` avec le vhost `privesc:<account>`. Les heures de `privesc.health` (la mémoire de santé) et de `privesc.sessions` (`last` de chaque session) sont au format natif du projet (`2026-10-29@13-59-59.723`, UTC) ; un état enregistré par une ancienne version, avec des secondes epoch, est converti au chargement.

<a id="modules"></a>
## 2. Carte des modules

| Module | Chemin | Responsabilité | Dépend de | Utilisé par |
|---|---|---|---|---|
| Manifeste | [mod-apache2/module.json](../mod-apache2/module.json) | id, version, cœur minimal, point d'entrée, chemins lus, paramètres (pas d'option de configuration) | — | registre, interface web, `manage.py` |
| Module Apache | [mod-apache2/module.py](../mod-apache2/module.py) | `ApacheModule` : hooks, action effectuée, gravité, détections, fonction de règle, enrichissement, santé | correlate, discovery, doctor, modsec, parsers ; cœur `masking`, `module`, `query`, `timeutil`, `health` ; PyYAML | collecteur, interface web, `manage.py` |
| Découverte | [mod-apache2/discovery.py](../mod-apache2/discovery.py) | `ApacheConfig` (analyseur de la configuration), sources et journaux ignorés, DocumentRoots | logformat (`dKnownFormats`) | module, doctor |
| Diagnostic | [mod-apache2/doctor.py](../mod-apache2/doctor.py) | Vérifications des prérequis ; décrit les journaux (format, journal d'audit, masquage) sans proposer de les modifier | discovery | module |
| Formats d'accès | [mod-apache2/logformat.py](../mod-apache2/logformat.py) | `LogFormat` vers expression régulière, heures en UTC, ligne de requête | cœur `timeutil` | parsers, discovery |
| Analyseurs | [mod-apache2/parsers.py](../mod-apache2/parsers.py) | access, error, audit (JSON, natif, concurrent), `AuditFramer`, `fAuditDisplay` | logformat, modsec ; cœur `masking`, `timeutil` | module |
| ModSecurity | [mod-apache2/modsec.py](../mod-apache2/modsec.py) | Messages, catégories, plages du CRS, scores, interception | — | parsers, module |
| Corrélation | [mod-apache2/correlate.py](../mod-apache2/correlate.py) | `UNIQUE_ID`, appariement sans lui (`mPair`), fenêtre, filigrane | cœur `timeutil` | module (collecteur) |
| Table des gravités | [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) | Gravités des détections de ModSecurity | — | module (`fLoadSeverityTable`) |
| Règles | [mod-apache2/rules/](../mod-apache2/rules/) | Six règles YAML | moteur de règles du cœur, `mIsNewPhp` | collecteur (`RulesEngine`), interface web (`fRules`) |
| Textes | [mod-apache2/locales/](../mod-apache2/locales/) | Nom, résumé, libellés et aide des paramètres, choix | — | interface web |
| privesc : manifeste | [mod-privesc/module.json](../mod-privesc/module.json) | id, version, cœur minimal, point d'entrée, chemins lus, 13 paramètres (pas d'option de configuration) | — | registre, interface web, `manage.py` |
| privesc : module | [mod-privesc/module.py](../mod-privesc/module.py) | `PrivescModule` : hooks, événements des deux sources, classement des enregistrements d'audit (chemins sensibles, appels système par architecture), indicateurs, détections des règles, enrichissement, santé, résultats de l'analyse | commands, correlate, discovery, doctor, parsers, surface ; cœur `masking`, `module`, `query`, `timeutil`, `health` ; PyYAML | collecteur, interface web, `manage.py` |
| privesc : découverte | [mod-privesc/discovery.py](../mod-privesc/discovery.py) | Sources, conteneur, auditd, snoopy, syslog, si chaque journal peut être lu, fichiers laissés par la version 1.0.0, `Accounts` (utilisateurs, groupes, type de compte) | — | module, doctor |
| privesc : analyseurs | [mod-privesc/parsers.py](../mod-privesc/parsers.py) | Enregistrements d'audit (hexadécimal, `msg='...'`, enrichis), lignes syslog (snoopy dans ses formats habituels, sudo, su, pkexec, doas, pam, sshd), masquage des lignes de commande | cœur `masking`, `timeutil` | module |
| privesc : corrélation | [mod-privesc/correlate.py](../mod-privesc/correlate.py) | Enregistrements d'audit par numéro de série (EOE, enregistrements espace utilisateur, 2 s) ; lignes syslog immédiatement | — | module (collecteur) |
| privesc : commandes | [mod-privesc/commands.py](../mod-privesc/commands.py) | Jetons de reconnaissance, programme d'un compte de service, shells, interpréteurs, outils de téléchargement, portes, compilateurs ; `SessionTracker` | cœur `timeutil` | module |
| privesc : surface d'attaque | [mod-privesc/surface.py](../mod-privesc/surface.py) | `SurfaceScanner` (setuid, setgid, capabilities), GTFOBins, fichiers sensibles modifiables, groupes privilégiés | — | module, doctor |
| privesc : diagnostic | [mod-privesc/doctor.py](../mod-privesc/doctor.py) | Décrit auditd, son journal et ce qu'ont enregistré ses règles, syslog, snoopy, ce que voit le module, les fichiers de la version 1.0.0 et la surface (corrections : uniquement des paquets et l'accès en lecture) ; prérequis `command_source` (toute source lisible) | discovery, surface ; cœur `timeutil` | module |
| privesc : règles | [mod-privesc/rules/](../mod-privesc/rules/) | 35 règles YAML | moteur de règles du cœur | collecteur (`RulesEngine`), interface web (`fRules`) |
| privesc : table des gravités | [mod-privesc/severity.yaml](../mod-privesc/severity.yaml) | Gravités des détections construites par le module (analyse, fichiers sensibles) | — | module (`fLoadSeverityTable`) |
| privesc : textes | [mod-privesc/locales/](../mod-privesc/locales/) | Nom, résumé, libellés et aide des paramètres, choix | — | interface web |
| Cœur : interface | [backend/core/module.py](../../localSIEM/backend/core/module.py) | `Module`, `LineFramer` | registry | modules |
| Cœur : registre | [backend/core/registry.py](../../localSIEM/backend/core/registry.py) | Trouver, vérifier et charger les modules ; valeurs par défaut et validation des paramètres | `config` | collecteur, interface web, `manage.py`, `backend/core/catalog.py` |
| Cœur : interface web | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) | Pages Modules (Installés, Installables, la page d'un module) et API | registry, catalog, rules | navigateurs |
| Cœur : catalogue | [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) | Téléchargement et décompression sûre du dépôt, liste avec l'action de chaque module (`install`, `update`, `incompatible`, `invalid`...) et `newer`, installation ou mise à jour atomique (`previous`, `access_changed`), désinstallation, commande pour root : Modules › Installables et **Mettre à jour** / **Désinstaller** de Modules › Installés, seul moyen d'installer des modules | registry | interface web |

<a id="symbols"></a>
## 3. Symboles clés

| Symbole | Fichier:ligne | Ce qu'il fait |
|---|---|---|
| `ApacheModule` | [mod-apache2/module.py:68](../mod-apache2/module.py#L68) | Le module apache2 (`vName = "apache2"`) |
| `fLoadSeverityTable` | [mod-apache2/module.py:54](../mod-apache2/module.py#L54) | `severity.yaml` par-dessus les valeurs par défaut intégrées |
| `ApacheModule.mDiscover` | [mod-apache2/module.py:95](../mod-apache2/module.py#L95) | Analyse la configuration ; sources, journaux ignorés, DocumentRoots |
| `ApacheModule.mThreshold` | [mod-apache2/module.py:105](../mod-apache2/module.py#L105) | Seuil d'anomalie : paramètre, CRS, ou 5 |
| `ApacheModule.mParse` | [mod-apache2/module.py:136](../mod-apache2/module.py#L136) | Unité vers enregistrement selon le type de source |
| `ApacheModule.mBuildEvent` | [mod-apache2/module.py:176](../mod-apache2/module.py#L176) | Transaction vers événement : champs, action effectuée, scores, détection |
| `ApacheModule.mVhostName` | [mod-apache2/module.py:311](../mod-apache2/module.py#L311) | En-tête Host ou hostname de ModSecurity vers le vhost qu'Apache a choisi (ce que journalise `%v`) |
| `ApacheModule.mAssess` | [mod-apache2/module.py:323](../mod-apache2/module.py#L323) | Gravité, nom de règle, description et détails de ce qui part au SOC |
| `ApacheModule.mDetectionFromSignal` | [mod-apache2/module.py:385](../mod-apache2/module.py#L385) | Signal d'une règle YAML vers détection |
| `ApacheModule.mIsNewPhp` | [mod-apache2/module.py:414](../mod-apache2/module.py#L414) | Fonction de règle `apache2.new_php` |
| `ApacheModule.mEnrich` | [mod-apache2/module.py:442](../mod-apache2/module.py#L442) | Contexte de l'IP (dernière heure) pour l'alerte |
| `ApacheModule.mHealth` | [mod-apache2/module.py:461](../mod-apache2/module.py#L461) | ModSecurity déchargé ou à Off ; IP réelle du client manquante |
| `ApacheModule.mDisplayRecord` | [mod-apache2/module.py:538](../mod-apache2/module.py#L538) | En-têtes et corps pour la fiche de la requête |
| `ApacheModule.mRequirements` | [mod-apache2/module.py:545](../mod-apache2/module.py#L545) | Apache et ModSecurity 2 : ce dont le module a besoin avant de pouvoir être activé |
| `ApacheConfig` | [mod-apache2/discovery.py:105](../mod-apache2/discovery.py#L105) | Analyseur de la configuration d'Apache |
| `ApacheConfig.mDirective` | [mod-apache2/discovery.py:228](../mod-apache2/discovery.py#L228) | Directives lues (journaux, vhosts, modules, ModSecurity) |
| `ApacheConfig.mVhostName` | [mod-apache2/discovery.py:358](../mod-apache2/discovery.py#L358) | Vhost d'une requête à partir de son en-tête Host et de l'adresse et du port locaux, tel qu'Apache le choisit |
| `fSourceKey` / `fDiscoverSources` | [mod-apache2/discovery.py:403](../mod-apache2/discovery.py#L403) / [:408](../mod-apache2/discovery.py#L408) | Clé de source stable ; sources à lire et sources ignorées |
| `fRunDoctor` | [mod-apache2/doctor.py:46](../mod-apache2/doctor.py#L46) | Vérifications des prérequis `{id, status, title, detail, fix}` |
| `fCanPair` | [mod-apache2/doctor.py:26](../mod-apache2/doctor.py#L26) | Si un format d'accès peut être rattaché sans `UNIQUE_ID` (IP du client, heure, ligne de requête, code de statut) |
| `fRequirementChecks` | [mod-apache2/doctor.py:174](../mod-apache2/doctor.py#L174) | Les vérifications `apache_config` et `modsecurity` du diagnostic ou, sans Apache, les deux en erreur, avec la commande qui les installe |
| `AccessFormat` / `dKnownFormats` | [mod-apache2/logformat.py:60](../mod-apache2/logformat.py#L60) / [:15](../mod-apache2/logformat.py#L15) | `LogFormat` vers expression régulière ; alias connus |
| `AccessParser` | [mod-apache2/parsers.py:59](../mod-apache2/parsers.py#L59) | Ligne d'access.log vers enregistrement |
| `fParseErrorLine` | [mod-apache2/parsers.py:147](../mod-apache2/parsers.py#L147) | Ligne d'error.log : ModSecurity, base de données, PHP, crash |
| `AuditFramer` | [mod-apache2/parsers.py:233](../mod-apache2/parsers.py#L233) | Enregistrements natifs sur plusieurs lignes ; position de commit sûre |
| `fParseAuditRecord` / `fFinishAudit` | [mod-apache2/parsers.py:277](../mod-apache2/parsers.py#L277) / [:426](../mod-apache2/parsers.py#L426) | Enregistrement d'audit JSON ou natif ; masquage, texte brut et texte indexé |
| `fAuditDisplay` / `fReadConcurrentEntry` | [mod-apache2/parsers.py:495](../mod-apache2/parsers.py#L495) / [:577](../mod-apache2/parsers.py#L577) | Fiche d'un enregistrement conservé ; fichier d'une entrée concurrente |
| `fParseMessage` / `fSummarize` | [mod-apache2/modsec.py:52](../mod-apache2/modsec.py#L52) / [:152](../mod-apache2/modsec.py#L152) | Un message de ModSecurity ; règles, catégories, score, seuil, interception |
| `Correlator` | [mod-apache2/correlate.py:57](../mod-apache2/correlate.py#L57) | `mAdd` ([:148](../mod-apache2/correlate.py#L148)), `mPair` ([:207](../mod-apache2/correlate.py#L207)), `mDue` ([:248](../mod-apache2/correlate.py#L248)), `mWaitsForAudit` ([:271](../mod-apache2/correlate.py#L271)), `mPendingCount` |
| `PrivescModule` | [mod-privesc/module.py:226](../mod-privesc/module.py#L226) | Le module privesc (`vName = "privesc"`) |
| `PrivescModule.mBuildEvent` | [mod-privesc/module.py:341](../mod-privesc/module.py#L341) | Transaction vers événement, par source ; `ignored` ; champs vides supprimés (`fCleanFields` conserve 0) |
| `PrivescModule.mAnalyzeCommand` | [mod-privesc/module.py:366](../mod-privesc/module.py#L366) | Reconnaissance de la session, téléchargement exécuté par un shell, compilation dans `/tmp`, commandes récentes, nouveau programme d'un compte de service |
| `PrivescModule.mAuditEvent` / `mAuditExec` / `mAuditUser` | [mod-privesc/module.py:427](../mod-privesc/module.py#L427) / [:587](../mod-privesc/module.py#L587) / [:661](../mod-privesc/module.py#L661) | Transaction d'audit par type ; programmes exécutés (`suid_escape`, `root_without_door`, `parent_interpreter`, capabilities) ; connexions, portes et échecs |
| `PrivescModule.mAuditSyscall` | [mod-privesc/module.py:509](../mod-privesc/module.py#L509) | Tout autre appel système selon son nom, ses arguments et ses chemins : `denied`, `kmod`, `ptrace`, `chmod`, `file` (`sensitive_group`) ou `syscall` |
| `fSyscallName` / `fSensitiveGroup` | [mod-privesc/module.py:184](../mod-privesc/module.py#L184) / [:210](../mod-privesc/module.py#L210) | Nom d'un appel système (nom enrichi, ou numéro par architecture) ; groupe d'un chemin sensible (`lSensitivePaths`) |
| `PrivescModule.mSyslogEvent` | [mod-privesc/module.py:702](../mod-privesc/module.py#L702) | snoopy, sudo, su, pkexec, doas, connexions |
| `PrivescModule.mWriterAllowed` | [mod-privesc/module.py:412](../mod-privesc/module.py#L412) | L'auteur de la modification d'un fichier sensible, ou un ancêtre connu, est un outil de comptes ou de paquets |
| `PrivescModule.mDetectionFromSignal` / `mEnrich` | [mod-privesc/module.py:781](../mod-privesc/module.py#L781) / [:818](../mod-privesc/module.py#L818) | Signal d'une règle vers détection ; contexte de la session pour l'alerte |
| `PrivescModule.mHealth` / `mSurfaceResult` | [mod-privesc/module.py:851](../mod-privesc/module.py#L851) / [:903](../mod-privesc/module.py#L903) | Sessions enregistrées, auditd arrêté, fichiers sensibles, analyse lancée ; nouveaux programmes setuid et capabilities |
| `fDiscoverSources` / `fReadState` / `fLegacyLeftovers` | [mod-privesc/discovery.py:291](../mod-privesc/discovery.py#L291) / [:160](../mod-privesc/discovery.py#L160) / [:175](../mod-privesc/discovery.py#L175) | Sources, sources ignorées et informations pour le diagnostic ; si un journal peut être lu ; fichiers laissés par la version 1.0.0 |
| `fContainer` / `fAuditdPid` | [mod-privesc/discovery.py:54](../mod-privesc/discovery.py#L54) / [:96](../mod-privesc/discovery.py#L96) | Type de conteneur (sans root) ; pid d'un auditd en marche |
| `Accounts` | [mod-privesc/discovery.py:190](../mod-privesc/discovery.py#L190) | Noms des uids, groupes, `UID_MIN`, type de compte (`mAccountType`) |
| `fParseAuditLine` / `fParseSyslogLine` | [mod-privesc/parsers.py:83](../mod-privesc/parsers.py#L83) / [:316](../mod-privesc/parsers.py#L316) | Enregistrements des deux sources |
| `fMaskCommand` | [mod-privesc/parsers.py:45](../mod-privesc/parsers.py#L45) | Mots de passe des lignes de commande, puis le masqueur du cœur |
| `Correlator` (privesc) | [mod-privesc/correlate.py:20](../mod-privesc/correlate.py#L20) | Enregistrements d'audit par numéro de série ; les autres immédiatement |
| `fReconToken` / `fProgramKey` / `fCommandArgs` | [mod-privesc/commands.py:115](../mod-privesc/commands.py#L115) / [:180](../mod-privesc/commands.py#L180) / [:91](../mod-privesc/commands.py#L91) | Jeton de reconnaissance d'une commande ; programme d'un compte de service ; mots d'une commande saisie |
| `SessionTracker` | [mod-privesc/commands.py:202](../mod-privesc/commands.py#L202) | Sessions (début, IP, porte, reconnaissance, dernières commandes), processus, téléchargements ; `mExport`/`mImport` |
| `SurfaceScanner` / `fCheckSensitiveFiles` | [mod-privesc/surface.py:167](../mod-privesc/surface.py#L167) / [:133](../mod-privesc/surface.py#L133) | Analyse des setuid, setgid et capabilities dans un thread ; fichiers sensibles modifiables par d'autres |
| `fRunDoctor` / `fRequirementChecks` (privesc) | [mod-privesc/doctor.py:275](../mod-privesc/doctor.py#L275) / [:282](../mod-privesc/doctor.py#L282) | Vérifications du diagnostic (descriptions ; corrections uniquement pour les paquets et l'accès en lecture) ; prérequis `command_source` : toute source lisible |
| `Module` / `LineFramer` | [backend/core/module.py:59](../../localSIEM/backend/core/module.py#L59) / [:48](../../localSIEM/backend/core/module.py#L48) | Interface d'un module ; une ligne par unité |
| `fReadManifest` | [backend/core/registry.py:133](../../localSIEM/backend/core/registry.py#L133) | Vérifie `module.json`, lit les textes |
| `fListManifests` / `fCreateModules` | [backend/core/registry.py:165](../../localSIEM/backend/core/registry.py#L165) / [:229](../../localSIEM/backend/core/registry.py#L229) | Les modules installés (`/opt/localsiem/modules/*`) ; instances et erreurs |
| `fRegisterPackage` / `fLoadClass` | [backend/core/registry.py:185](../../localSIEM/backend/core/registry.py#L185) / [:197](../../localSIEM/backend/core/registry.py#L197) | Namespace package `localsiem_modules` ; import et vérifications du point d'entrée |
| `fModuleSettings` / `fValidateSettings` | [backend/core/registry.py:250](../../localSIEM/backend/core/registry.py#L250) / [:317](../../localSIEM/backend/core/registry.py#L317) | Valeurs par défaut sous les valeurs enregistrées ; validation de ce qui est enregistré |
| `fSaveModule` | [backend/web/api_modules.py:290](../../localSIEM/backend/web/api_modules.py#L290) | `POST /api/admin/modules/{name}` |
| `fGetCatalog` / `fInstallFromCatalog` / `fUninstallModule` | [backend/web/api_modules.py:384](../../localSIEM/backend/web/api_modules.py#L384) / [:395](../../localSIEM/backend/web/api_modules.py#L395) / [:422](../../localSIEM/backend/web/api_modules.py#L422) | `GET /api/admin/module-catalog` ; `POST /api/admin/module-catalog/{name}` (installation ou mise à jour ; une première installation sans ses prérequis est désactivée : `fFirstInstallation`) ; `DELETE /api/admin/modules/{name}` |
| `fInstall` / `fCatalog` | [backend/core/catalog.py:235](../../localSIEM/backend/core/catalog.py#L235) / [:171](../../localSIEM/backend/core/catalog.py#L171) | Installe ou met à jour un module à côté de la copie installée et les échange par un renommage (`previous`, `access_changed`) ; les modules du dépôt avec `installed`, `newer` et leur action |
| `fRemove` / `fRootCommand` | [backend/core/catalog.py:302](../../localSIEM/backend/core/catalog.py#L302) / [:372](../../localSIEM/backend/core/catalog.py#L372) | Désinstalle un module (renommage et suppression) ; la commande pour root (`manage.py setup-modules`) |
| `fCatalogPanel` / `fUpdateNotice` / `fUpdate` | [frontend/assets/modules.js:218](../../localSIEM/frontend/assets/modules.js#L218) / [:417](../../localSIEM/frontend/assets/modules.js#L417) / [:452](../../localSIEM/frontend/assets/modules.js#L452) | Section Installables (uniquement les modules non installés, **Installer** et sa boîte de dialogue) ; avis d'une version plus récente sur une ligne d'Installés ; **Mettre à jour** (confirmation, le même `POST`, une boîte de dialogue uniquement avec `access_changed` ou quand le collecteur n'a pas répondu) |

<a id="flows"></a>
## 4. Principaux chemins d'appel

**Démarrage du collecteur → registre → ApacheModule**

`Collector.mSetup` → `fCreateModules` → `fListManifests` (`/opt/localsiem/modules/*`) → `fReadManifest` (id = dossier, point d'entrée, paramètres, `core` ≤ `cVersion`, `fReadTexts`) → `fCreateModule` → `fLoadClass` (`fRegisterPackage`, `import localsiem_modules.apache2.module`, sous-classe de `Module`, `vName == id`) → `ApacheModule(dSettings, vMasker, vStorage, dManifest)` → `mStart` → `mCreateCorrelator` → `Collector.mLoadRules` (`mRulesPath`, `mRuleFunctions`, surcharges `rules.<id>` → `RulesEngine.mLoad`) → `Collector.mDiscover` (`mEnabled` → `mDiscover` → `ApacheConfig.mParse` → `fDiscoverSources` ; un `FileTailer` et `mCreateFramer` par source) → enregistrements en attente remis dans le corrélateur → `mPublishDoctor` (`mDoctor` → `fRunDoctor` → état `apache2.doctor`).

**Une ligne lue → détections**

1. `Collector.mReadSources` → `FileTailer.mPoll` → framer `mFeed` (`LineFramer`, ou `AuditFramer` dont `mSafeCommit` conserve la position avant un enregistrement inachevé) → `ApacheModule.mParse` (`AccessParser.mParse`, `fParseErrorLine`, ou `fReadConcurrentEntry` + `fParseAuditRecord` et `mObserveAudit`) → enregistrements et positions conservés dans une seule transaction → `Correlator.mAdd`.
2. `Collector.mProcessDue` → `Correlator.mDue(pWatermark=...)` → `ApacheModule.mBuildEvent` (`fSummarize`, action effectuée, `mAssess`, `mPathFirstSeen` pour les `.php` en 2xx) → `RulesEngine.mEvaluate` (règles YAML ; `{function: apache2.new_php}` → `mIsNewPhp`) → `mSaveEvents` → `mDetect` pour chaque détection et `mDetectionFromSignal` pour chaque signal → `Grouper.mAdd`.
3. `Collector.mProcessGroups` → `ApacheModule.mEnrich` (`mGetIpContext`) → `fBuildAlert` → file d'attente du SOC.

**L'administrateur enregistre les paramètres → rechargement du collecteur**

`modules.js fBuildSettings` (envoi) → `POST /api/admin/modules/apache2` `{settings}` → `fSaveModule` → `fValidateSettings` (422 `invalid_setting:<key>` ou `<key>.<field>`) → `fSaveSettings` (`settings.json`, `modules.apache2`) → `WebContext.mApplySettings` → socket du collecteur `{"command": "reload"}` → `Collector.mHandleIpc` → `Collector.mCycle` → `mReloadSettings` (`ApacheModule.mReload`, `mLoadRules`, `mDiscover`, `mPublishDoctor`, `mPublishState`). L'interrupteur envoie `{enabled}` de la même façon (pour l'activer : 422 `requirements_missing` tant qu'un prérequis du module manque) et la table des règles envoie `{rules}` (`fCleanRules` → `rules.<id>` : `enabled`, `severity`, `threshold` ou `first_threshold`, `window`). Si le socket ne répond pas, le collecteur remarque quand même le nouveau `settings.json` à son cycle suivant.

**Installer un module depuis l'interface web** (le seul moyen d'installer des modules)

`modules.js fCatalogPanel` (Modules › Installables) → **Consulter le dépôt** → `GET /api/admin/module-catalog` (`fGetCatalog` → `fFetchCatalog` → `fDownload` → `fCatalog` : chaque dossier `mod-<name>/` du dépôt, avec `installed`, `newer` et `action`) → seuls les éléments dont `installed` est null sont listés → **Prérequis** (`fShowRequirements` → `fRequirementsBody` : les `install_requirements` du module pour le système du serveur, `system` de la réponse, en tant que root et avec `sudo`, et les remarques `install_requirements.*` de ses locales ; rien n'est exécuté) → **Installer** → `POST /api/admin/module-catalog/{name}` (`fInstallFromCatalog` → `fFetchAndInstall` → `InstallLock` → `fDownload` → `fInstall` : `mod-apache2/` → `/opt/localsiem/modules/apache2/`, `previous` null, `access_changed` true) → `WebContext.mReloadModules` → `fFirstInstallation` (un prérequis manque et `modules.<name>.enabled` n'a jamais été enregistré : `enabled = false`) → `restart` du collecteur → `fCreateModules` charge le module → la boîte de dialogue «<module> installé» affiche la commande pour root (`fRootCommand` : `manage.py setup-modules`, accès en lecture aux `read_paths`) ou, si un prérequis manque, les vérifications non remplies.

**Mettre à jour un module depuis l'interface web**

Ouverture de Modules › Installés → `fCheckRepository` → `fFetchCatalog(false)` de `modules.js` (la dernière réponse de `GET /api/admin/module-catalog`, réutilisée pendant 600 s ; installer, mettre à jour ou désinstaller un module l'oublie) → éléments avec `newer` et `action` à `update` ou `incompatible` → `fUpdateNotice` sur la ligne (uniquement tant que la version installée est celle qui a été comparée) → **Mettre à jour** → `fUpdate` → confirmation → `POST /api/admin/module-catalog/{name}` (le même `fInstallFromCatalog` → `fInstall` : la nouvelle copie remplace celle qui est installée, `previous` est l'ancienne version, `access_changed` indique si `read_paths` a changé ; pas de `fFirstInstallation`, donc `enabled` et les paramètres restent) → `restart` du collecteur → une boîte de dialogue uniquement si `access_changed` (la commande pour root) ou si le collecteur n'a pas répondu.

**Désinstaller un module depuis l'interface web**

**Désinstaller** (ligne de Modules › Installés ou page du module) → `fUninstallButton` → confirmation → `DELETE /api/admin/modules/{name}` (`fUninstallModule` → `fRemove` → `InstallLock` → renommage de `/opt/localsiem/modules/<name>/` vers un dossier de transit, où il est supprimé) → `WebContext.mReloadModules` → `restart` du collecteur. `modules.<name>` et les surcharges de ses règles restent dans `settings.json`, et l'accès en lecture donné par root reste aussi.

**Première installation sans Apache ni ModSecurity → Reconfigurer** (localSIEM 2.2.0 ou ultérieur)

Installation dans l'interface web → `fInstall` (première installation) → le module créé à partir de la copie installée (stockage `None`) → `ApacheModule.mRequirements` → `ApacheConfig.mParse` → `fRequirementChecks` (avec Apache : `fRunDoctor` → `apache_config`, `modsecurity` ; sans lui, les deux en erreur) → une erreur et `modules.apache2.enabled` jamais enregistré → `modules.apache2.enabled = false` («Désactivé», interrupteur verrouillé, prérequis dans la page). Plus tard, avec Apache et ModSecurity installés : **Reconfigurer** → `POST /api/admin/modules/apache2/reconfigure` → `mRequirements` → remplis → interrupteur déverrouillé et commande pour root (accès en lecture aux `read_paths` ; apache2 n'a pas de `setup_option`) → l'administrateur active le module → rechargement du collecteur → `mDiscover` → `mPublishDoctor`.

**Fiche de la requête et diagnostic depuis l'interface web**

`GET /api/events/{id}` → `fEvent` → `WebContext.mModule("apache2")` → `mDisplayRecord` → `fAuditDisplay`. **Redécouvrir et lancer le diagnostic** → `POST /api/admin/modules/apache2/doctor` → collecteur `{"command": "doctor"}` → `mDiscover` + `mPublishDoctor`.

**Santé**

`Collector.mCycle` (toutes les 60 s) → `mCheckHealth` → `ApacheModule.mHealth` (au plus toutes les 300 s ; `ApacheConfig.mParse`, `mCountRecentEvents`) → `fHealthDetection` → `mDetect`.

**privesc : une commande exécutée → détections**

1. auditd écrit `SYSCALL`, `EXECVE`, `CWD`, `PATH`, `PROCTITLE`, `EOE` avec un même numéro de série → `FileTailer.mPoll` → `LineFramer` → `PrivescModule.mParse` → `fParseAuditLine` (hexadécimal décodé, `fMaskCommand`, texte brut reconstruit) → `Correlator.mAdd` (clé `audit:<time>:<serial>`, échue à `EOE`).
2. `Correlator.mDue` → `PrivescModule.mBuildEvent` → `mAuditEvent` → `mAuditExec` (`suid_escape`, `BPRM_FCAPS`, `root_without_door` depuis `SessionTracker.mGet`, `mRememberProcess`) → `mAnalyzeCommand` (`fReconToken` → `SessionTracker.mRecon` → `recon_burst`/`recon_massive` ; `cDownloadOnelinerRegex`, `mDownload`/`mRecentDownload` ; `fCompileInTemporary` ; `mCommand` ; compte de service : `fProgramKey` → `mPathFirstSeen` → `new_program`) → `fCleanFields`.
3. `RulesEngine.mEvaluate` (règles de `mod-privesc/rules/`) → `PrivescModule.mDetectionFromSignal` → `Grouper.mAdd` → `Collector.mProcessGroups` → `PrivescModule.mEnrich` (session : 20 dernières commandes) → `fBuildAlert` → file d'attente du SOC.

Avec snoopy, la même commande arrive aussi sous forme de ligne syslog : `fParseSyslogLine` → `fParseSyslogMessage` → `mSyslogEvent` → `mAnalyzeCommand` (session `snoopy:<uid>:<sid>`).

**privesc : sessions et portes**

`LOGIN` (auid et ses attribués) ou `USER_LOGIN`/`USER_START` de sshd ou de login → `mAuditUser` → `SessionTracker.mStart` (utilisateur, adresse SSH). `USER_START`/`USER_CMD` avec le résultat success de sudo, su, pkexec, doas, run0 ou systemd → `SessionTracker.mDoor`. Un `EXECVE` ultérieur de cette session avec uid et euid à 0 → `root_without_door` uniquement si le début a été vu et qu'il n'y a pas eu de porte. `mHealth` enregistre `SessionTracker.mExport` dans `privesc.sessions` au plus une fois par minute ; `mStart` le charge (`mImport`).

**privesc : un appel système enregistré par les règles d'audit du serveur**

auditd écrit `SYSCALL` (avec `arch`, `syscall`, `a0`-`a3`, `success`, `exit` et la clé de la règle qui l'a enregistré, quelle qu'elle soit), `CWD`, `PATH`... → `fParseAuditLine` → `Correlator` → `mAuditEvent` → `mAuditSyscall` : `fSyscallName` → open/exec/truncate échoué avec `EACCES`/`EPERM` et un uid de connexion → `denied` ; `init_module`/`finit_module`/`delete_module` → `kmod` ; `ptrace` → `ptrace` ; `chmod`/`fchmod`/`fchmodat`/`fchmodat2` avec `S_ISUID`/`S_ISGID` dans le mode, pas sur un dossier → `chmod` (`mWriterAllowed`) ; une modification (un appel de `sChangeSyscalls`, une ouverture avec des drapeaux d'écriture, un `PATH` avec `CREATE`/`DELETE`) d'un chemin de `lSensitivePaths` → `file` avec `sensitive_group` (`dKeyHints` uniquement sans chemin résolvable) et `mWriterAllowed` ; tout le reste → `syscall`. `mBuildEvent` mémorise l'heure de chaque type (`dRuntime["audit_kinds"]`) pour le diagnostic.

**privesc : analyse de la surface d'attaque**

`mHealth` (toutes les 300 s, cinq minutes après le démarrage, toutes les `surface_scan_hours`) → `SurfaceScanner.mStart` (thread : `os.walk` de `scan_paths`, `os.lstat`, `os.getxattr("security.capability")` → `fCapabilities`) → `mHealth` suivant → `mSurfaceResult` (`SurfaceScanner.mTake`, comparé à `privesc.surface` : nouveaux setuid/setgid → `new_setuid*`, nouvelles capabilities → `new_capabilities`) → `mModuleDetection` → `mDetect` ; le résultat est enregistré dans `privesc.surface` et affiché par `fSurfaceChecks`. Toutes les heures, `fCheckSensitiveFiles` → `sensitive_file_writable`.

**privesc : prérequis et Reconfigurer**

`fInstall` (première installation) ou **Reconfigurer** → `PrivescModule.mRequirements` → `fRequirementChecks(mModuleSettings())` (`fContainer`, `fAuditdPid`, `fAuditLogPath` → `fReadState` ; `fSyslogPath` → `fReadState` sauf si `syslog_mode` vaut `never` ; `fSnoopyInstalled`) → une source lisible : `command_source` ok (celles qui ne sont pas lisibles en avertissement) ; une source qui existe mais ne peut pas être lue : erreur `audit_log` ou `syslog` avec l'accès en lecture (`manage.py setup-modules` ou `setfacl`) ; rien : erreur `command_source` avec le paquet à installer. Le module reste désactivé tant qu'il y a une erreur.

<a id="routes"></a>
## 5. Points d'entrée

| Point d'entrée | Gestionnaire | Fichier |
|---|---|---|
| `"entry": "module:ApacheModule"` de `module.json` | `ApacheModule` | [mod-apache2/module.py](../mod-apache2/module.py) |
| `mod-apache2/rules/*.yaml` | `RulesEngine` (cœur) | [mod-apache2/rules/](../mod-apache2/rules/) |
| Fonction de règle `apache2.new_php` | `ApacheModule.mIsNewPhp` | [mod-apache2/module.py](../mod-apache2/module.py) |
| Interface web : Modules › Installables, le seul moyen d'installer des modules (`GET /api/admin/module-catalog`, `POST /api/admin/module-catalog/{name}`) | `fGetCatalog`, `fInstallFromCatalog` ; vue `fCatalogPanel` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| Interface web : **Mettre à jour** sur une ligne de Modules › Installés (le même `GET`, réutilisé pendant 10 minutes par le navigateur, et le même `POST`) | `fCheckRepository`, `fUpdateNotice`, `fUpdate` → `fInstallFromCatalog` | [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js), [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| Interface web : **Désinstaller** (`DELETE /api/admin/modules/{name}`) | `fUninstallModule` → `fRemove` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `read_paths` de `module.json` | `manage.py read-paths` : les dossiers que localSIEM, en tant que root, permet à `localsiem` de lire (la commande de `fRootCommand`) | [backend/manage.py](../../localSIEM/backend/manage.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `manage.py modules` | `fMain` (`fModules`) | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py doctor [--json]` | `mDiscover`, `mSkipped`, `mDoctor` | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py read-paths` | `read_paths` de chaque manifeste | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `/user/dashboard/modules/` ; `/admin/dashboard/modules/` (302 vers `installed/`), `/admin/dashboard/modules/installed/`, `/admin/dashboard/modules/installable/` | `fUserTab` / `fAdminTab` / `fAdminModulesSection` ; vue `LocalsiemViews.modules` | [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| `/admin/dashboard/modules/installed/apache2/` (l'ancienne `/admin/dashboard/modules/apache2/` y renvoie par un 301) | `fAdminModule` (le 301 : `fAdminModulesSection`) ; vue `LocalsiemViews.module` | mêmes fichiers |
| `GET /api/modules` | `fModules` (état pour toute personne connectée) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `GET /api/admin/modules/apache2` | `fModule` (paramètres, valeurs, sources, diagnostic, règles) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2` | `fSaveModule` (`enabled`, `settings`, `rules`) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/doctor` | `fRunDoctor` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/reconfigure` (**Reconfigurer**, localSIEM 2.2.0 ou ultérieur) | `mRequirements` → `fRequirementChecks` | [mod-apache2/module.py](../mod-apache2/module.py), [mod-apache2/doctor.py](../mod-apache2/doctor.py) |
| `GET /api/events/{id}` | `fEvent` → `mDisplayRecord` | [backend/web/api_search.py](../../localSIEM/backend/web/api_search.py) |
| `"entry": "module:PrivescModule"` de `mod-privesc/module.json` | `PrivescModule` | [mod-privesc/module.py](../mod-privesc/module.py) |
| `mod-privesc/rules/*.yaml` | `RulesEngine` (cœur) | [mod-privesc/rules/](../mod-privesc/rules/) |
| `/admin/dashboard/modules/installed/privesc/`, `GET`/`POST /api/admin/modules/privesc`, `.../privesc/doctor`, `.../privesc/reconfigure` | `fAdminModule`, `fModule`, `fSaveModule`, `fRunDoctor`, `mRequirements` → `fRequirementChecks` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [mod-privesc/doctor.py](../mod-privesc/doctor.py) |
| Enregistrements d'audit des règles du serveur (toute clé) | `mAuditEvent` → `mAuditExec`, `mAuditUser`, `mAuditSyscall` | [mod-privesc/module.py](../mod-privesc/module.py) |

<a id="impact"></a>
## 6. Analyse d'impact

| Composant | Ce qui est affecté s'il change |
|---|---|
| `module.json` `id` | Doit être égal au nom du dossier sans `mod-` (le nom du dossier installé) et à `vName`. C'est la clé des paramètres (`modules.<id>`), de l'état (`<id>.doctor`) et le `module` de chaque événement : un renommage perd les paramètres enregistrés et scinde l'historique. |
| `module.json` `core` | Le relever au-dessus du localSIEM installé empêche le module de se charger (état «Erreur») ; dans le dépôt, Installables affiche «Nécessite localSIEM X ou ultérieur» et Installés affiche la version plus récente sans **Mettre à jour**. |
| `module.json` `entry` | Doit pointer vers une sous-classe de `Module` ; une valeur erronée est une erreur de chargement. |
| `module.json` `default_enabled` | Activé ou désactivé sur les serveurs où l'administrateur n'a jamais décidé (désactivé si ses prérequis manquent lors de la première installation). |
| `module.json` `read_paths` | L'accès en lecture que localSIEM donne en tant que root (`manage.py read-paths`) : un dossier manquant entraîne des erreurs de permissions dans le diagnostic et dans l'état. Une modification dans une nouvelle version fait que l'interface web affiche de nouveau la commande pour root après **Mettre à jour** (`access_changed`). |
| `module.json` `install_requirements` | La boîte de dialogue Prérequis d'Installables (`fRequirementsBody` de `modules.js`). Une valeur erronée (un système autre que `debian` et `alpine`, une liste vide ou plus de 20 commandes, une commande avec un opérateur du shell ou un saut de ligne) rend le module non valide (`fCheckInstallRequirements` du cœur) : il n'est ni installé ni chargé. |
| `module.json` `setup_option` | Rien : le cœur l'ignore (aucun module n'en a depuis apache2 1.3.0 et privesc 1.1.0). |
| Dossiers `mod-<name>/` avec un `module.json` à la racine du dépôt | Ce que liste le catalogue de l'interface web, en tant que module `<name>` : Installables affiche ceux qui ne sont pas encore installés (celui qui nécessite un cœur plus récent sous la forme «Nécessite localSIEM X ou ultérieur», un module non valide sous la forme «Le module du dépôt n'est pas valide»), et une `version` supérieure à celle qui est installée fait qu'Installés propose **Mettre à jour**. |
| `module.json` `settings` | Le formulaire, la validation et les valeurs par défaut. Une nouvelle valeur par défaut s'applique aux serveurs qui n'ont jamais enregistré cette clé. Les valeurs enregistrées ne sont pas migrées : une clé renommée perd sa valeur et une ancienne valeur avec un nouveau type parvient au module telle qu'elle a été enregistrée. |
| `locales/*.json` | Uniquement les textes de l'interface web ; un texte manquant se rabat sur en-US, puis sur la clé. |
| `parsers.py` (dict de l'enregistrement) | La corrélation (`correlation`, `fields.client_ip`, `fields.path`), la fiche de la requête, l'index en texte intégral (`search`, `raw`), la santé des lignes non analysées et la confidentialité. |
| `logformat.py` `dKnownFormats` | L'analyse de chaque journal d'accès ; `localsiem_combined` reste pour les serveurs qui l'écrivent déjà (les versions 1.2.0 et antérieures du module l'ajoutaient) : ne modifiez pas sa définition. |
| `correlate.py` | Un événement par requête ; le cœur appelle `mAdd`, `mDue(pNow, pForce, pWatermark)` et `mPendingCount`, et réinjecte les enregistrements encore en attente après un redémarrage. Sans `UNIQUE_ID`, il apparie les enregistrements par leurs champs `client_ip`, `method`, `uri`, `status` et `path` : un analyseur qui les écrit différemment casse l'appariement. L'attente de l'enregistrement d'audit (`mWaitsForAudit`) nécessite le champ `modsecurity` des lignes d'error.log et les enregistrements de la source `audit`. |
| `modsec.py` (catégories, libellés, plages) | Noms de règle des alertes (les statistiques du SOC sont regroupées selon eux : gardez-les stables), clés de regroupement, recherches `category:`. |
| `ApacheModule.mBuildEvent` (dict de l'événement) | Colonnes de la table des événements, champs lus par les règles YAML (`action`, `status`, `method`, `path`, `crs_matched`, `db_error`...), recherches et export CSV. |
| `ApacheModule.mAssess` | Ce qui parvient au SOC et sa gravité ; les limites de `GenericAlert` du cœur (règle 300, description 10 000 caractères). |
| `severity.yaml` | Gravité de chaque détection de ModSecurity ; la gravité fait partie de la clé de regroupement, donc une modification démarre de nouveaux groupes. |
| `rules/*.yaml` | L'`id` est la clé des surcharges (`rules.<id>`) et des recherches (`rule:localsiem:<id>`) : gardez-le stable. Les champs doivent exister dans les événements ; `{function: ...}` nécessite `mRuleFunctions`. |
| `discovery.py` | Quels journaux sont lus ; `fSourceKey` est la clé des positions enregistrées (une nouvelle clé fait du fichier une nouvelle source, sans sa position enregistrée) ; DocumentRoots de la règle web shell ; le diagnostic. |
| `doctor.py` | Le diagnostic de l'interface web et de `manage.py` et les indications montrées au client. Seules les vérifications portant sur ce qui n'est pas un journal (ModSecurity, le CRS, `SecRuleEngine`, `mod_unique_id`, permissions) peuvent porter un `fix` ; les vérifications portant sur les journaux ne font que les décrire. |
| `mRequirements` / `fRequirementChecks` | Si le module peut être activé, l'état «Désactivé» après une première installation sans Apache ni ModSecurity, les prérequis qu'affiche l'interface web et **Reconfigurer**. Ils s'exécutent dans l'interface web et dans `manage.py` sans stockage et analysent la configuration d'Apache à chaque appel : tenez-les à l'écart du stockage et de tout ce qui est lent, et gardez stables les ids `apache_config` et `modsecurity`. |
| privesc : colonnes et champs des événements (`mBuildEvent`, `mAnalyzeCommand`) | Les règles YAML les testent par leur nom (`recon_burst`, `suid_escape`, `root_without_door`, `sensitive_group`, `writer_allowed`, `ptrace_attach`, `parent_interpreter`, `account_type`, `real_uid`, `argc_zero`...) : un champ renommé désactive silencieusement les règles qui l'utilisent. `vhost` est l'utilisateur : la clé de regroupement des alertes et les recherches `vhost:` en dépendent. |
| privesc : `fReconToken` | Ce qui compte comme reconnaissance et comment les commandes distinctes sont différenciées : modifier un jeton change la vitesse à laquelle une session atteint les seuils. |
| privesc : `SessionTracker` et les portes (`sDoors`) | `root_without_door` : une porte absente de la liste rend critiques des sessions root légitimes ; une porte en trop masque des exploits du noyau. `mExport`/`mImport` est le format de `privesc.sessions`. |
| privesc : `parsers.py` | Les champs des enregistrements (`args`, `command`, `kind`, `uid`/`euid` de snoopy), le masquage des mots de passe et le texte brut des enregistrements d'audit ; les formats de snoopy qu'il lit (le module ne modifie jamais `snoopy.ini`). |
| privesc : classement des enregistrements d'audit (`lSensitivePaths`, `dSyscallTables`, `sChangeSyscalls`, `dOpenFlagArgument`, `dChmodModeArgument`, `sDeniedSyscalls`, `dKeyHints`) | Ce qui devient `file`, `chmod`, `kmod`, `ptrace` et `denied`, et donc les règles sensitive-file, persistence-file, monitoring-changed, suid-set, kernel-module, ptrace, denied-burst et sensitive-denied ; un numéro d'appel système erroné classe mal les enregistrements de cette architecture. |
| privesc : `surface.py` | Le coût de l'analyse (thread, limites) et ce que signalent le diagnostic et `mSurfaceResult` ; `privesc.surface` est sa référence. |
| privesc : `mRequirements` / `fRequirementChecks` | Si le module peut être activé (toute source lisible), l'état «Désactivé» après une première installation dont `localsiem` ne peut pas encore lire les journaux, et **Reconfigurer** ; appelés sans stockage par l'interface web et `manage.py` : gardez-les rapides et sans root. Gardez les ids `command_source`, `audit_log` et `syslog`. |
| Interface du cœur (`backend/core/module.py`, `registry.py` de localSIEM) | Tous les modules : une signature de hook modifiée, une nouvelle clé de manifeste obligatoire ou un nouveau contrat d'enregistrements et d'événements les casse ; relevez `core` dans leur `module.json` quand ils ont besoin du nouveau localSIEM. |

<a id="extensions"></a>
## 7. Points d'extension

### Comment écrire un nouveau module

1. **Dossier** : créez `mod-<name>/` à la racine de ce projet ; `<name>`, le nom du module, respecte `[a-z][a-z0-9_]{1,31}`. Le préfixe `mod-` ne concerne que le dossier : `module.json`, la classe, les options et les textes utilisent `<name>`. Pas de `__init__.py`.
2. **`module.json`**, par exemple :

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

3. **Textes** : `locales/<language>.json` pour chacune des 15 langues de localSIEM avec `name`, `summary` et le libellé et l'aide de chaque paramètre. Les remarques sur les prérequis vont dans `install_requirements` (`note`, pour tous les systèmes, ainsi que `debian` et `alpine`), affichées dans la boîte de dialogue Prérequis.
4. **Code** : `module.py` avec une sous-classe de `Module` dont le `vName` est l'id. Elle doit implémenter `mParse`, `mCreateCorrelator` et `mBuildEvent`, et généralement `mDiscover` ; les autres hooks sont facultatifs (section 1). Importez ses propres fichiers de façon relative et le cœur sous la forme `backend.core...`. Les deux modules de ce dépôt sont des exemples complets ([mod-apache2/module.py](../mod-apache2/module.py), [mod-privesc/module.py](../mod-privesc/module.py)) ; une ébauche minimale :

   ```python
   from backend.core.module import Module


   class OneEventCorrelator:
     # Chaque enregistrement est un événement à part entière, sans attente.

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

5. **Action effectuée** : décidez de ce que signifie «déjà traité» pour le service (par exemple, une IP déjà bannie) et mettez `action` à `blocked` dans ce cas ; n'ajoutez une détection qu'aux événements sans action effectuée.
6. **Règles** : des fichiers YAML dans `mod-<name>/rules/`, renvoyés par `mRulesPath`, et les fonctions qu'ils appellent dans `mRuleFunctions`.
7. **Prérequis** : si le module a besoin d'un logiciel sur le serveur (comme apache2 a besoin d'Apache et de ModSecurity 2), renvoyez une vérification par prérequis depuis `mRequirements()` (le format de `fCheck` : `status` `ok` ou `error`, et dans `fix` la commande qui l'installe) et n'installez jamais ce logiciel depuis le module : sans ses prérequis, le module est installé désactivé. Il s'exécute sans stockage, y compris dans l'interface web et dans `manage.py`. Déclarez aussi, dans `install_requirements` de `module.json`, les commandes qui installent ce logiciel sur Debian et sur Alpine (une commande par ligne, sans opérateurs du shell) : l'interface web les affiche dans Modules › Installables › Prérequis, telles quelles et précédées de `sudo`, avant que le module soit installé.
8. **Installation** : publiez-le dans ce dépôt (branche `main`) ; il apparaît dans Modules › Installables de l'interface web de localSIEM tant qu'il n'est pas installé, et **Installer** copie le dossier `mod-<name>/` dans `/opt/localsiem/modules/<name>/` et redémarre le collecteur. L'accès en lecture à ses `read_paths` nécessite root : l'interface web affiche la commande (`manage.py setup-modules`). Un module n'a pas d'option de configuration : il n'installe jamais rien et ne modifie jamais rien en dehors de `/opt/localsiem`, et il n'écrit jamais dans les journaux du client, ne les soumet jamais à une rotation, ne les supprime jamais et ne modifie jamais leur format ; si un serveur écrit ses journaux à sa manière, le module s'y adapte, et ce qui manque au serveur est un prérequis. Pour publier une nouvelle version, augmentez `version` : Modules › Installés affiche l'avis et **Mettre à jour**, qui conserve les paramètres et l'état activé ou désactivé du module et n'affiche de nouveau la commande pour root que si `read_paths` a changé.
9. **Documentation** : mettez à jour le README, ce CODE et le MANUAL dans les 15 langues.

### Comment ajouter une règle au module apache2

Créez un fichier YAML dans [mod-apache2/rules/](../mod-apache2/rules/) (chaque clé et chaque opérateur sont décrits en tête de [backend/core/rules.py](../../localSIEM/backend/core/rules.py)) : `id`, `name`, `category`, `type`, `severity`, `kind` (`match`, `threshold` ou `sequence`), les conditions (`when`, ou `first`/`first_threshold`/`then`), `by`, `window`, `threshold`, `lists`, `description` et `search`. Les champs sont recherchés d'abord dans les colonnes de l'événement, puis dans `fields`. Elle apparaît dans la table des règles de la page du module et est chargée par le collecteur une fois la nouvelle version du module installée : augmentez `version` dans `module.json`, publiez-la et cliquez sur **Mettre à jour** dans Modules › Installés.

### Comment ajouter un paramètre au module apache2

Ajoutez-le à `settings` de [mod-apache2/module.json](../mod-apache2/module.json) avec son type et sa valeur par défaut, ajoutez son `label` et son `help` aux quatre fichiers de [mod-apache2/locales/](../mod-apache2/locales/), et lisez-le avec `self.mModuleSettings().get("<key>")`. Le formulaire, la validation et le rechargement viennent du cœur.

### Comment ajouter une vérification au diagnostic ou modifier une gravité

Une vérification est un `fCheck(id, status, title, detail, fix)` dans `fRunDoctor` ([mod-apache2/doctor.py](../mod-apache2/doctor.py)) ; gardez l'`id` stable et mettez dans `fix` l'extrait ou la commande exacts, uniquement pour les prérequis qui ne sont pas des journaux : une vérification portant sur les journaux du client ne fait que les décrire, ainsi que ce que localSIEM peut ou ne peut pas en lire, sans `fix`. Les gravités des détections de ModSecurity se modifient dans [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) (`low`, `medium`, `high`, `critical`).

### Comment ajouter une règle au module privesc

Créez un fichier YAML dans [mod-privesc/rules/](../mod-privesc/rules/), comme ceux d'Apache. Testez les colonnes (`method`, `uri`, `path`, `vhost`, `action`) et les champs des événements (`sensitive_group`, `account_type`, `real_uid`, `recon`, `service_account`, `file`...), jamais la clé d'une règle d'audit ; ajoutez `ignored: {not: true}` pour que les utilisateurs ignorés ne la déclenchent jamais, et `action: none` quand seul compte ce qui s'est réellement exécuté. Si la condition nécessite un état ou une logique (une séquence de la même session, une vérification d'un fichier), calculez un indicateur dans `PrivescModule.mAnalyzeCommand` (toutes les sources) ou dans `mAuditExec`/`mAuditSyscall`/`mSyslogEvent` (une seule source) et testez-le depuis la règle.

### Comment ajouter une commande de reconnaissance, un outil ou un exploit au module privesc

- Reconnaissance : ajoutez le programme à `sReconSimple`, ou une branche à `fReconToken` qui renvoie un jeton par type de question ([mod-privesc/commands.py](../mod-privesc/commands.py)). Un jeton qui change à chaque argument gonfle les comptages.
- Outils et exploits : ajoutez une expression régulière à la liste de [rules/known-tool.yaml](../mod-privesc/rules/known-tool.yaml) ou de [rules/exploit.yaml](../mod-privesc/rules/exploit.yaml) (insensible à la casse, testée sur la ligne de commande) ; l'administrateur peut aussi les ajouter depuis les paramètres (`rules.<id>.lists`).

### Comment ajouter une source ou un type d'enregistrement d'audit au module privesc

- Un chemin sensible : ajoutez-le à `lSensitivePaths` de [mod-privesc/module.py](../mod-privesc/module.py) avec son groupe (ou un nouveau groupe et une règle qui teste `sensitive_group`). Un type d'appel système : ajoutez son nom aux ensembles de `mAuditSyscall` et son numéro à chaque table de `dSyscallTables`. Ne dépendez jamais de la clé d'une règle d'audit (ajoutez-la tout au plus à `dKeyHints`) et n'installez jamais de règles d'audit : le serveur enregistre ce que décide son administrateur, et le diagnostic le décrit (`dAuditKinds` de [doctor.py](../mod-privesc/doctor.py)).
- Une source : renvoyez-la depuis `fDiscoverSources` avec un nouveau `kind`, analysez-la dans `mParse` et construisez ses événements dans `mBuildEvent` avec les mêmes colonnes et les mêmes champs que les autres, afin que les règles fonctionnent sans modification.
