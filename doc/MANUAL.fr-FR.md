# Manuel d'utilisation de localSIEM-modules

Ce MANUAL est également disponible en :\
[de-DE](MANUAL.de-DE.md), [en-GB](MANUAL.en-GB.md), [en-US](MANUAL.md), [es-AR](MANUAL.es-AR.md), [es-ES](MANUAL.es-ES.md), fr-FR, [he-IL](MANUAL.he-IL.md), [hi-IN](MANUAL.hi-IN.md), [it-IT](MANUAL.it-IT.md), [ja-JP](MANUAL.ja-JP.md), [ko-KR](MANUAL.ko-KR.md), [pt-BR](MANUAL.pt-BR.md), [pt-PT](MANUAL.pt-PT.md), [ru-RU](MANUAL.ru-RU.md), [zh-CN](MANUAL.zh-CN.md)

[Installation](README.fr-FR.md) · [Référence du code](CODE.fr-FR.md) · [Manuel de localSIEM](../../localSIEM/doc/MANUAL.fr-FR.md)

## Sommaire

1. [Ce que sont les modules](#what)
2. [Installer et mettre à jour les modules](#installation)
3. [La page Modules](#modules-page)
4. [La page du module Apache](#apache-page)
5. [Paramètres du module Apache](#settings)
6. [Ce que le module Apache envoie au SOC](#soc)
7. [Prérequis d'Apache et de ModSecurity : le diagnostic](#doctor)
8. [Les journaux du client ne sont jamais modifiés](#client-logs)
9. [Règles du module Apache](#rules)
10. [Avertissements de santé du module Apache](#health)
11. [Le module d'élévation de privilèges](#privesc)
12. [Paramètres du module d'élévation de privilèges](#privesc-settings)
13. [Ce que le module d'élévation de privilèges envoie au SOC : ses règles](#privesc-rules)
14. [Prérequis du module d'élévation de privilèges : le diagnostic](#privesc-doctor)
15. [Serveurs mis à jour depuis la version 1.0.0 du module d'élévation de privilèges](#privesc-legacy)
16. [Surface d'attaque et avertissements de santé du module d'élévation de privilèges](#privesc-health)
17. [Ligne de commande](#cli)

<a id="what"></a>
## 1. Ce que sont les modules

localSIEM se compose d'un **cœur** et de **modules**. Le cœur conserve les événements, permet d'y effectuer des recherches, exécute les règles, regroupe les alertes, les envoie au SOC et surveille sa propre santé. Chaque module ajoute un service du serveur : il trouve ses journaux, les lit, les transforme en événements, décide de ce qui est déjà traité, apporte ses propres règles et vérifie les prérequis de ce service.

Les modules de ce projet s'installent dans `/opt/localsiem/modules/<name>/`. Il en existe aujourd'hui deux : **apache2** («Apache + ModSecurity», sections 4 à 10) et **privesc** («Élévation de privilèges», sections 11 à 16). localSIEM n'a pas de modules propres : la page Modules ne liste que les modules installés depuis ce dépôt.

<a id="installation"></a>
## 2. Installer et mettre à jour les modules

localSIEM doit être installé d'abord ; son installateur n'installe que le cœur, jamais un module. Les modules de ce projet s'installent **uniquement depuis l'interface web de localSIEM** : ce projet n'a pas d'installateur propre. L'interface web les télécharge depuis le dépôt `https://github.com/PYMEHackers/localSIEM-modules` (branche `main`). Les modules nécessitent localSIEM 2.2.0 ou une version plus récente.

**Installation.** En tant qu'administrateur, ouvrez Modules › **Installables** (section 3), cliquez sur **Consulter le dépôt**, consultez **Prérequis** (ce dont le module a besoin sur le serveur et les commandes qui l'installent, à exécuter avant de l'installer), puis cliquez sur **Installer** sur le module. Ensuite, localSIEM :

1. télécharge le dépôt et le décompresse de façon sûre (rien en dehors de son dossier, limites de taille) ;
2. copie le dossier du module (`mod-<name>/` dans le dépôt) dans `/opt/localsiem/modules/<name>/`, sans `tests/` (et sans les caches Python) ; un module installé de nouveau retrouve les paramètres qu'il avait ;
3. redémarre le collecteur, qui charge le module en quelques secondes ;
4. retire le module de la liste et ouvre la boîte de dialogue «<module> installé» avec la commande à exécuter en tant que root sur le serveur (`manage.py setup-modules`) et un bouton **Copier** : elle donne à l'utilisateur `localsiem` l'accès en lecture aux dossiers listés dans `read_paths` de son `module.json` (`/var/log/apache2` pour le module apache2, `/var/log/audit` pour le module privesc), y compris aux fichiers des rotations suivantes, et redémarre localSIEM. Cet accès en lecture est tout ce dont un module a besoin : les modules n'ont pas d'options de configuration et ne modifient jamais le serveur (sections 8 et 11). Tant qu'elle n'a pas été exécutée, le module peut afficher «Erreur» : ses journaux ne peuvent pas encore être lus. La boîte de dialogue se ferme avec «Fermer» ou avec «Voir les modules installés», qui ouvre Installés.

**Mise à jour.** À l'ouverture de Modules › **Installés**, l'interface web consulte le dépôt, et un module qui y a une version plus récente affiche un avis avec **Mettre à jour** (section 3). Après confirmation, localSIEM télécharge la nouvelle version et la met à la place de celle qui est installée (étapes 1 à 3), conserve ses paramètres et laisse le module activé ou désactivé comme il l'était. La commande pour root ne s'affiche de nouveau que si la nouvelle version lit d'autres journaux (`read_paths`) ; sinon, il n'y a rien à exécuter. Une mise à jour de localSIEM conserve les modules installés et leur accès en lecture.

**Réinstallation.** L'interface web ne réinstalle pas un module et n'en installe pas non plus une version plus ancienne : pour réinstaller un module, cliquez sur **Désinstaller** (section 3) et installez-le de nouveau depuis **Installables** ; ses paramètres sont conservés.

**Installer un module n'installe jamais le logiciel qu'il surveille.** Le module apache2 n'installe ni Apache ni ModSecurity, et le module privesc n'installe ni auditd, ni démon syslog, ni snoopy. Si, lors de sa première installation, il manque au serveur ce dont le module a besoin (Apache et ModSecurity pour apache2 ; pour privesc, une source que `localsiem` peut lire, section 14), le module est installé **désactivé** : la boîte de dialogue liste ce qui manque à la place de la commande, et le module ne peut pas être activé tant que **Reconfigurer** ne les a pas détectés (section 4). Une mise à jour laisse le module activé ou désactivé comme il l'était.

<a id="modules-page"></a>
## 3. La page Modules

Les administrateurs ouvrent **Administration › Modules**, qui comporte deux sections, chacune à sa propre adresse : **Installés** (`/admin/dashboard/modules/installed/`), qui s'ouvre par défaut (`/admin/dashboard/modules/` y mène), et **Installables** (`/admin/dashboard/modules/installable/`). Les analystes voient **Modules** dans leur tableau de bord (`/user/dashboard/modules/`) : uniquement la liste des modules installés, en lecture seule, sans sections.

**Installés** affiche une ligne par module installé, sur toute la largeur : son nom, son id, sa version, une pastille d'état, son résumé et, en dessous, les motifs de cet état. La liste s'actualise d'elle-même toutes les 10 secondes. Sans module installé, elle indique «Installez des modules depuis l'onglet Installables.» (aux analystes : «Aucun module installé. Un administrateur les installe dans Modules › Installables.»).

| État | Signification |
|---|---|
| **Activé et fonctionnel** | Activé, chargé par le collecteur et en train de lire ses sources. Les avertissements du diagnostic sont listés comme remarques mais ne changent pas l'état. |
| **Activé, avec des avertissements** | Activé, mais aucun journal à lire n'a été trouvé, une source n'existe pas encore, ou le module a été installé après le démarrage du collecteur (redémarrez le service `localsiem`). |
| **Erreur** | Le module ne se charge pas (l'erreur est affichée), son diagnostic signale une erreur, ou une source ne peut pas être lue (permissions de l'utilisateur `localsiem`). |
| **Désactivé** | Désactivé, ou installé sans ses prérequis (pour apache2 : Apache ou ModSecurity manque ; pour privesc : `localsiem` ne peut lire ni le journal d'auditd ni syslog), comme l'indique son motif. |
| **Application du changement…** | Vient d'être activé ou désactivé : le collecteur applique le changement. |
| **Inconnu** | Le collecteur (service `localsiem`) n'est pas en marche, donc rien n'est lu. |

Quand le module n'est pas désactivé, la ligne affiche aussi : **Sources en lecture** (lues / trouvées), **Lignes (1 h)**, **Dernières données**, **Événements (24 h)**, **Bloqués (24 h)** et les compteurs du **Diagnostic** («n OK · n avertissements · n erreurs»).

Les administrateurs ont aussi, sur chaque ligne :

- **L'interrupteur** de chaque module. Désactiver un module demande une confirmation : localSIEM cesse de lire ses journaux et d'envoyer ses alertes jusqu'à ce qu'il soit réactivé ; ce qui est déjà conservé est gardé. L'activer lance la lecture immédiatement. Tant qu'un prérequis du module manque, l'interrupteur est verrouillé («Désactivé : prérequis manquants») : **Reconfigurer** (section 4) le déverrouille dès qu'il les détecte.
- **Configurer**, qui ouvre la page du module, `/admin/dashboard/modules/installed/<name>/` (section 4) ; l'ancienne adresse `/admin/dashboard/modules/<name>/` y mène.
- **Désinstaller**, y compris sur un module qui ne se charge pas (et dans la page du module). Après confirmation, localSIEM supprime `/opt/localsiem/modules/<name>/` et redémarre le collecteur sans lui : il cesse de lire ses journaux et d'envoyer ses alertes. Les événements déjà conservés restent consultables, et ses paramètres sont gardés, au cas où vous le réinstalleriez. L'accès en lecture que root a donné à `localsiem` sur ses journaux n'est pas retiré.
- **Mettre à jour**, quand le dépôt propose une version plus récente du module. À chaque ouverture d'Installés, l'interface web consulte le dépôt («Recherche de versions plus récentes dans le dépôt…» ; le navigateur réutilise la réponse pendant 10 minutes), et une ligne dont le module a une version plus récente affiche «Le dépôt propose la version X (la version installée est la Y).» avec le bouton **Mettre à jour**. Après confirmation, localSIEM installe la nouvelle version (section 2), conserve ses paramètres, laisse le module activé ou désactivé comme il l'était et redémarre le collecteur ; une boîte de dialogue n'affiche la commande pour root que si la nouvelle version lit d'autres journaux. Si la nouvelle version nécessite un localSIEM plus récent, l'avis indique «Le dépôt propose la version X, mais elle nécessite localSIEM Z ou ultérieur : mettez à jour localSIEM pour l'installer.» et n'a pas de bouton.

**Installables** (administrateurs uniquement) contient la carte «Modules installables». **Consulter le dépôt** télécharge le dépôt et liste les modules qui ne sont pas encore installés sur ce serveur, chacun avec son nom, son id, sa version et son résumé, et un bouton ou une remarque :

| Bouton ou remarque | Signification |
|---|---|
| **Prérequis** | Affiche ce dont le module a besoin sur le serveur et les commandes qui l'installent, en tant que root et avec sudo (voir ci-dessous) |
| **Installer** | Installe le module (section 2) |
| «Nécessite localSIEM X ou ultérieur» | Il ne peut pas être installé : mettez d'abord localSIEM à jour |
| «Le module du dépôt n'est pas valide» | Il ne peut pas être installé |

Les modules déjà installés n'apparaissent jamais ici : ils se mettent à jour depuis Installés. Si tous les modules du dépôt sont installés, la carte indique «Tous les modules du dépôt sont déjà installés.». Après l'installation, la boîte de dialogue «<module> installé» affiche la commande à exécuter en tant que root pour que `localsiem` puisse lire les journaux du module (section 2), avec un bouton **Copier** ; tant qu'elle n'a pas été exécutée, le module peut afficher «Erreur» : ses journaux ne peuvent pas encore être lus. S'il manque au serveur ce dont le module a besoin, la boîte de dialogue liste à la place ce qui manque, avec l'indication d'ouvrir le module dans Installés (**Configurer**) et de cliquer sur **Reconfigurer** une fois que c'est en place.

**Prérequis** ouvre «<module> : prérequis» : ce dont le module a besoin sur le serveur et les commandes qui l'installent sur le système de ce serveur («Ce serveur : …»), déclarés par le module (`install_requirements` de son `module.json`), en deux versions, chacune avec **Copier** : **En tant que root** et **Avec sudo** (les mêmes commandes précédées de `sudo`). Exécutez-les sur le serveur avant d'installer le module : l'installer n'installe jamais ce logiciel, et localSIEM ne les exécute jamais. Pour le module apache2, sur Debian : `apt-get -y update`, `apt-get -y install apache2 libapache2-mod-security2 modsecurity-crs`, `a2enmod security2 unique_id`, `cp --update=none /etc/modsecurity/modsecurity.conf-recommended /etc/modsecurity/modsecurity.conf` (elle ne crée la configuration de ModSecurity, DetectionOnly, que s'il n'y en a aucune) et `systemctl restart apache2` ; sur Alpine, Apache uniquement (`apk add apache2`, puis `rc-update` et `rc-service` pour le démarrer), car Alpine n'a pas de paquet ModSecurity 2 : tant que ModSecurity n'est pas compilé depuis les sources et chargé, le module reste désactivé. Pour le module privesc : `apt-get -y install auditd rsyslog` sur Debian, et `apk add audit` avec auditd lancé au démarrage sur Alpine ; une seule source lisible suffit, et dans un conteneur auditd ne peut pas s'exécuter.

<a id="apache-page"></a>
## 4. La page du module Apache

`/admin/dashboard/modules/installed/apache2/` (administrateurs uniquement ; l'ancienne adresse `/admin/dashboard/modules/apache2/` y mène) comporte cinq parties :

1. **En-tête** : nom, id, version, le chemin d'installation (`/opt/localsiem/modules/apache2`), l'interrupteur, l'état avec ses motifs et les chiffres de la section 3. **Retour aux modules installés** revient à Installés ; **Redécouvrir et lancer le diagnostic** relit immédiatement la configuration d'Apache et actualise le diagnostic ; **Reconfigurer** recherche de nouveau Apache et ModSecurity (voir ci-dessous) ; **Désinstaller** désinstalle le module (section 3) et revient à Installés.
2. **Paramètres** : le formulaire de la section 5. **Enregistrer les paramètres** vérifie chaque valeur et, si l'une d'elles est incorrecte, indique laquelle («Valeur non valide : …»).
3. **Sources** : chaque journal en cours de lecture, avec **Type** (`access`, `error`, `audit`), **Chemin**, **Vhost**, **Lignes (1 h)**, **Non analysées (1 h)**, **Dernières données** (par exemple `2026/10/29@13:59:59.723`) et **État** (erreur s'il ne peut pas être lu, avertissement s'il n'existe pas encore). En dessous, les journaux trouvés mais non lus, avec le motif : «journal envoyé dans un pipe, non pris en charge», «couvert par un GlobalLog qui écrit tous les vhosts» ou «son format ne contient aucune donnée : chaque ligne est le même texte (un alias de LogFormat qui n'est pas défini)».
4. **Diagnostic** : les vérifications de la section 7, avec l'heure à laquelle elles ont été exécutées. Chaque prérequis manquant (ModSecurity, le CRS, `SecRuleEngine`, `mod_unique_id`, l'accès en lecture de `localsiem`) est accompagné de l'extrait ou de la commande qui le corrige et d'un bouton **Copier**. Les vérifications portant sur les journaux ne font que les décrire, ainsi que ce que localSIEM peut en lire, sans correction : les journaux du client ne sont jamais modifiés (section 8).
5. **Règles** : les règles de la section 9, chacune avec **Activée**, **Règle** (nom, id et catégorie), **Gravité**, **Seuil** et **Fenêtre (s)**, et **Enregistrer les règles**.

**Prérequis et Reconfigurer.** Tant qu'Apache ou ModSecurity manque, le module est désactivé et l'en-tête liste ce qui manque, avec la commande qui l'installe. **Reconfigurer** (même quand le module est désactivé) les recherche de nouveau avec les paramètres enregistrés ; si Apache se trouve à un emplacement non standard, renseignez d'abord **Fichier de configuration d'Apache** (section 5). Quand les deux sont trouvés, il déverrouille l'interrupteur —activer le module reste votre décision— et affiche la commande à exécuter en tant que root pour que `localsiem` puisse lire les journaux d'Apache créés après l'installation du module. Un module activé qui perd Apache ou ModSecurity reste activé : le diagnostic et les avertissements de santé (section 10) le signalent.

**Chaque changement s'applique immédiatement, sans rien redémarrer** : l'interface web l'enregistre et prévient le collecteur, qui recharge ses paramètres, redécouvre les sources et lance le diagnostic. Si le collecteur ne répond pas, l'interface web l'indique et le changement est appliqué au démarrage du collecteur.

<a id="settings"></a>
## 5. Paramètres du module Apache

| Paramètre | Par défaut | Ce qu'il fait |
|---|---|---|
| **Uniquement les sources ci-dessous** | désactivé | Ne pas découvrir les journaux à partir de la configuration d'Apache : lire uniquement les sources ajoutées manuellement. |
| **Sources ajoutées manuellement** | aucune | Journaux à lire en plus de ceux découverts (ou à leur place, avec l'option ci-dessus). Jusqu'à 50. |
| **Fichier de configuration d'Apache** | vide | Vide : détecté automatiquement (`/etc/apache2/apache2.conf` sur Debian, `/etc/apache2/httpd.conf` sur Alpine ; `/etc/httpd/conf/httpd.conf` est aussi reconnu). Avec un chemin absolu, c'est ce fichier qui est utilisé, s'il existe. |
| **Intervalle de découverte (secondes)** | 3600 | Fréquence à laquelle la configuration d'Apache est relue pour trouver de nouveaux vhosts et journaux (60 à 86400). |
| **Seuil de blocage de ModSecurity** | 0 | 0 : lu dans la configuration du CRS (`tx.inbound_anomaly_score_threshold` dans `crs-setup.conf`), 5 s'il n'y figure pas. Sert à distinguer une correspondance au-dessus du seuil de blocage d'une correspondance en dessous quand les messages de ModSecurity n'indiquent pas eux-mêmes le seuil (0 à 1000). |
| **Jours d'apprentissage pour les nouveaux fichiers PHP** | 3 | Pendant les premiers jours qui suivent le tout premier démarrage du module, un fichier PHP jamais vu auparavant n'est pas signalé comme nouveau par la règle `apache-webshell` (0 à 365). Un fichier créé ou modifié dans son DocumentRoot au cours du dernier jour compte toujours comme nouveau. |

Chaque **source ajoutée manuellement** a ces champs (* obligatoire) :

| Champ | Utilisation |
|---|---|
| **Type** * | `access.log`, `error.log` ou `Journal d'audit de ModSecurity` |
| **Chemin** * | Chemin absolu du fichier |
| **Vhost** | Vhost des lignes, pour les journaux dont les lignes ne l'indiquent pas |
| **LogFormat** | Pour les journaux d'accès : un alias (`localsiem_combined`, `combined`, `vhost_combined`, `common`, `combinedio`, ou un alias défini dans la configuration d'Apache) ou le format lui-même. Vide : les formats habituels sont essayés. |
| **Type de journal d'audit** | `Série (un seul fichier)` ou `Concurrent (un fichier par requête)` |
| **Dossier de stockage de l'audit** | Pour le type concurrent : le dossier de `SecAuditLogStorageDir` |

Un fichier n'est lu qu'une seule fois, même s'il est à la fois découvert et ajouté manuellement. Une source qui apparaît pendant que localSIEM fonctionne est lue depuis son début si elle fait 5 Mo ou moins, et depuis sa fin sinon.

Deux paramètres d'**Administration › Paramètres** de localSIEM agissent aussi sur ce module : la **fenêtre de corrélation** (5 secondes : le temps pendant lequel les trois enregistrements d'une requête sont attendus) et la **gravité sous le seuil de blocage** (`low`). Une requête signalée par ModSecurity attend aussi son enregistrement d'audit, que ModSecurity écrit à la fin de la requête, jusqu'à 2 minutes : ainsi, une requête lente n'est pas scindée en deux événements.

<a id="soc"></a>
## 6. Ce que le module Apache envoie au SOC

Pour chaque requête, le module réunit la ligne d'accès, les lignes d'erreur et l'enregistrement d'audit qui ont le même `UNIQUE_ID`. Les journaux d'accès qu'Apache écrit par défaut (`combined`, `vhost_combined`, `common`) n'ont pas d'`UNIQUE_ID` : chaque ligne d'accès est alors rattachée à l'enregistrement d'audit et aux lignes d'erreur de sa propre requête par IP du client, méthode, URI, code de statut et heure (±2 secondes), même quand la même requête se répète dans la même seconde, et l'événement est marqué «corrélation faible». Le vhost vient de `%v` ou, si le format ne le contient pas, de l'en-tête Host et du port de l'enregistrement d'audit, choisi comme Apache le choisit ; l'heure prend les microsecondes de l'enregistrement d'audit. Ensuite, il décide si quelque chose a déjà été fait à son sujet («action effectuée»), en lisant d'abord le journal d'audit (`Action: Intercepted (phase N)`), puis error.log (`Access denied with code NNN (phase N)`). Un 403 sans aucune trace de ModSecurity n'est pas considéré comme un blocage : il est marqué comme douteux.

| Situation | Part au SOC ? |
|---|---|
| Bloqué par ModSecurity en phases 1-2 (l'application ne l'a jamais reçu) | **Non.** Il reste dans localSIEM, consultable (`action:blocked`), et il est compté dans le contexte de la prochaine alerte de cette IP. |
| Bloqué en phases 3-4 (l'application l'avait déjà exécuté) | Oui |
| Correspondances de règles avec le moteur en `DetectionOnly` | Oui |
| Correspondances de règles sous le seuil de blocage | Oui |
| Signaux des règles de la section 9 | Oui |

Gravité des alertes déclenchées par les correspondances de ModSecurity (fichier `severity.yaml` du module) :

| Situation | Gravité |
|---|---|
| Correspondances non bloquées, réponse 3xx, 4xx ou 5xx | moyenne |
| Correspondances non bloquées, réponse 2xx | élevée |
| Bloqué en phases 3-4 | élevée |
| Signes de réussite : une règle sortante (950-955) s'est déclenchée et rien n'a été bloqué, ou une erreur de base de données a suivi la requête | critique |
| Sous le seuil de blocage (souvent un faux positif de l'application elle-même) | faible (la gravité sous le seuil de blocage d'Administration › Paramètres) |

Chaque alerte a un nom stable (par exemple «Apache/ModSecurity: SQL injection not blocked (CRS 942)»), une description qui se termine par la requête de recherche à coller dans la recherche de localSIEM (par exemple `ip:203.0.113.7 category:sqli`), et des détails : vhost, IP du client, méthode, URI (masquée), réponse, user agent et les données de ModSecurity (moteur, action, phase, score d'anomalie, seuil, règles et données correspondantes). À son départ, l'alerte porte aussi le contexte de l'IP : requêtes et requêtes bloquées de la dernière heure, les règles qui l'ont bloquée et la première fois qu'elle a été vue.

Les mots de passe, les cookies, les en-têtes `Authorization` et les jetons sont masqués avant tout stockage, y compris dans les corps des requêtes, et les corps des requêtes ne partent jamais au SOC. Le corps de la réponse (partie E) et le texte complet des règles exécutées (partie K) du journal d'audit ne sont jamais conservés.

<a id="doctor"></a>
## 7. Prérequis d'Apache et de ModSecurity : le diagnostic

Le diagnostic du module apache2 lit la configuration d'Apache (sans la modifier) et vérifie chaque prérequis. Il s'exécute au démarrage du collecteur, après chaque changement de paramètres, à chaque découverte, avec **Redécouvrir et lancer le diagnostic** et avec `manage.py doctor` (section 17), uniquement lorsque le module est activé : tant qu'il est désactivé parce qu'Apache ou ModSecurity manque, la page du module affiche ces prérequis à la place (section 4). Statuts : OK, avertissement (il fonctionne avec des limites), erreur (à corriger) et info (n'a d'importance que dans certaines situations).

| Vérification | Correct quand | Sinon |
|---|---|---|
| Configuration d'Apache | `apache2.conf` ou `httpd.conf` (ou le fichier configuré) est trouvé et lu | Erreur : ajoutez les sources manuellement (section 5). Les parties qui ne peuvent pas être lues sont listées comme avertissements. |
| ModSecurity | `mod_security2` (ModSecurity 2) est chargé | Erreur. Debian : `apt-get install libapache2-mod-security2 modsecurity-crs && a2enmod security2`. Alpine n'a pas de paquet : compilez mod_security2 2.9 depuis les sources. ModSecurity 3 (libmodsecurity) n'est pas pris en charge. |
| OWASP CRS | Les fichiers du CRS sont inclus (le diagnostic indique combien, ainsi que le seuil d'anomalie) | Erreur : `apt-get install modsecurity-crs`, ou incluez `crs-setup.conf` et `rules/*.conf` après ModSecurity |
| SecRuleEngine | `On` (les requêtes au-dessus du seuil sont bloquées en phase 2 et restent dans localSIEM) ou `DetectionOnly` (rien n'est bloqué : chaque correspondance part au SOC) | Erreur si `Off` ; avertissement s'il est à `Off` sauf dans certains vhosts, s'il est absent (ModSecurity prend alors `Off` par défaut) ou si certains vhosts le mettent à `Off` |
| mod_unique_id | Chargé : ModSecurity fonctionne et les trois sources d'une requête sont réunies par `UNIQUE_ID` | Erreur si ModSecurity est chargé : ModSecurity 2 n'inspecte rien sans lui (Alpine ne le charge pas) ; sinon avertissement (corrélation faible). Debian : `a2enmod unique_id` ; Alpine : `LoadModule unique_id_module modules/mod_unique_id.so` |
| Format du journal d'accès | Les journaux d'accès contiennent l'IP du client, l'heure, la ligne de requête et le code de statut, comme les formats qu'Apache écrit par défaut (OK, «Access logs in the format Apache writes») : chaque ligne est rattachée aux enregistrements de ModSecurity de sa requête par IP du client, méthode, URI, code de statut et heure. Avec les millisecondes, le vhost et l'`UNIQUE_ID` dans le format (par exemple `localsiem_combined`, sur les serveurs qui l'écrivent déjà), elles sont réunies par `UNIQUE_ID` (OK, «Access log with milliseconds, vhost, duration and UNIQUE_ID») | Info, sans correction, si un journal d'accès ne contient pas l'un des quatre : localSIEM le lit tel quel, mais ne peut pas rattacher ses lignes aux enregistrements de ModSecurity (ces requêtes sont vues dans le journal d'audit) ; info si aucun journal d'accès n'est lu (les requêtes sont vues dans le journal d'erreurs et dans le journal d'audit). Le format des journaux appartient au client (section 8) |
| mod_remoteip | Chargé avec `RemoteIPHeader` | Info, sans correction : si le site web est derrière un proxy ou un répartiteur de charge, les journaux contiennent l'IP du proxy, tout comme les alertes et les règles par IP |
| Journal d'audit | `SecAuditEngine RelevantOnly` (ou `On`) avec un `SecAuditLog` | Avertissement s'il est désactivé : localSIEM décide à partir d'error.log uniquement, et la fiche de la requête n'a ni en-têtes ni liste de règles. Quand il est activé, ses remarques ne font que le décrire : type concurrent (un fichier par transaction ; ModSecurity les crée généralement avec le mode 600, et localSIEM les lit si `localsiem` le peut), format natif (lu tel quel), partie E journalisée (elle ne part jamais au SOC), partie H absente (l'action effectuée ne peut pas être lue dans le journal d'audit ; c'est la seule remarque qui fait de la vérification un avertissement). Pas de correction : le journal d'audit est configuré par le client (section 8) |
| Masquage à la source | Une action `sanitise` existe | Info, sans correction («The audit log on disk is not masked») : le fichier écrit par ModSecurity peut contenir des mots de passe et des cookies ; localSIEM les masque avant de les conserver, et ils ne partent jamais au SOC |
| Permissions | `localsiem` peut lire chaque source | Erreur. Debian : `usermod -aG adm localsiem` ; Alpine : les commandes `setfacl` affichées. Une source qui n'existe pas encore n'est qu'une info. |
| Journaux envoyés dans un pipe | — | Avertissement : `\|/usr/bin/rotatelogs ...` et syslog ne peuvent pas être lus ; écrivez aussi le journal dans un fichier, ou ajoutez la source manuellement |
| Journal d'accès sans données | — | Avertissement : un `CustomLog` utilise un format qu'aucun `LogFormat` ne définit (ou un `LogFormat` sans aucune directive `%`), donc Apache écrit ce même texte sur chaque ligne, sans l'IP du client, l'heure ni la requête. localSIEM ne lit pas ce journal et voit les requêtes de son vhost dans son journal d'erreurs et dans le journal d'audit de ModSecurity. Le format des journaux du serveur n'est jamais modifié. |
| Moteur vu à Off | — | Erreur : les enregistrements d'audit indiquent que le moteur est désactivé |
| Version de ModSecurity | — | Info : la version lue dans le journal d'audit |

Quand la configuration a un `GlobalLog` dont le format contient `%v` (il écrit tous les vhosts), les autres journaux d'accès ne sont pas lus : ils ne feraient que répéter ses lignes. Le diagnostic ne propose jamais de modifier le format des journaux ni les paramètres du journal d'audit (section 8).

<a id="client-logs"></a>
## 8. Les journaux du client ne sont jamais modifiés

Le module apache2 ne fait que **lire** les journaux d'Apache et de ModSecurity : il n'y écrit jamais, ne les soumet jamais à une rotation, ne les tronque, ne les déplace ni ne les supprime, et il ne modifie jamais leur format ni la configuration d'Apache ou de ModSecurity qui les écrit. Si un serveur écrit ses journaux dans un format qui lui est propre (par exemple, son propre `LogFormat`, ou l'IP du client que fournit `mod_remoteip`), le module s'y adapte : il lit chaque journal d'accès avec le format qu'utilise son `CustomLog`. Le diagnostic (section 7) ne fait que décrire les journaux et ce que localSIEM peut ou ne peut pas en lire, sans proposer de les modifier ; il ne donne une correction que pour ce qui n'est pas un journal : ModSecurity, le CRS, `SecRuleEngine`, `mod_unique_id` et l'accès en lecture de l'utilisateur `localsiem`. La seule chose faite en tant que root pour ce module est cet accès en lecture (`manage.py setup-modules`, section 2).

Les versions 1.2.0 et antérieures du module avaient l'option de configuration `--configure-apache`, supprimée dans la version 1.3.0. Les serveurs où elle a été appliquée conservent le fichier qu'elle a écrit, `/etc/apache2/conf-available/localsiem.conf` (Debian) ou `/etc/apache2/conf.d/localsiem.conf` (Alpine), avec le format `localsiem_combined` et son `GlobalLog` (`localsiem_access.log`), les paramètres du journal d'audit et une `SecAction` qui masque les valeurs sensibles. Tant que ce fichier est présent, le module lit ces journaux comme n'importe quels autres. Pour annuler ce changement, supprimez ce fichier (Debian : `a2disconf localsiem`) et rechargez Apache. Sur Alpine, ce fichier chargeait aussi `mod_unique_id` et `mod_logio` : chargez `mod_unique_id` ailleurs dans la configuration d'Apache avant de le supprimer, car ModSecurity 2 n'inspecte rien sans lui (section 7). L'installateur de localSIEM supprime ce fichier avec `--uninstall` ou `--reinstall` (sur Alpine, chargez d'abord `mod_unique_id` ailleurs) et laisse les journaux (`localsiem_access.log`, `modsec_audit.log`) là où ils sont.

<a id="rules"></a>
## 9. Règles du module Apache

Les règles sont évaluées sur chaque événement. Un signal d'une règle part toujours au SOC. Dans la page du module, chaque règle peut être désactivée, et sa gravité, son seuil (1 à 100000) et sa fenêtre (1 à 86400 secondes) modifiés ; le seuil et la fenêtre ne s'appliquent qu'aux règles de seuil et de séquence. Ses événements peuvent être retrouvés avec `rule:localsiem:<id>`.

| Règle | Type | Gravité | Quand | Seuil / fenêtre |
|---|---|---|---|---|
| `apache-bruteforce` «brute force against a login page» | seuil | moyenne | Requêtes POST non bloquées depuis une IP vers une page de connexion d'un vhost (`/wp-login.php`, `/xmlrpc.php`, `/administrator/index.php`, `/user/login`, `/login`, `/admin/login`, `/login.php`, `/admin.php`, `/signin`, `/auth/login`, `/phpmyadmin/index.php`) | 20 en 300 s |
| `apache-login-after-bruteforce` «successful login after a brute force» | séquence | élevée | Au moins 10 connexions échouées (POST ayant reçu la réponse 200, 401 ou 403) vers une page de connexion, puis une ayant reçu la réponse 302 ou 303 (WordPress répond 200 à une connexion échouée et 302 à une connexion réussie) | 10, en 1800 s maximum |
| `apache-enumeration` «enumeration (burst of 404 answers)» | seuil | moyenne | Réponses 404 non bloquées envoyées à une IP par un vhost | 30 en 60 s |
| `apache-sensitive-file` «sensitive file served» | correspondance | élevée | Une réponse 2xx pour un fichier qui ne devrait pas être public : `.env`, `.git/`, `.svn/`, `.hg/`, `.htaccess`, `.htpasswd`, dumps et sauvegardes (`.sql`, `.sql.gz`, `.bak`, `.old`, `.orig`, `.swp`, `.save`, `.backup`, `.dump`, noms se terminant par `~`), `phpinfo`, `info.php`, `server-status`, `server-info`, copies de `wp-config.php` et de `config.php`/`config.inc`, `.DS_Store`, clés SSH privées, `composer.json`/`composer.lock`, `.aws/`, `backup.zip`/`.tar`/`.tar.gz`/`.tgz`/`.rar` | — |
| `apache-webshell` «possible web shell (POST to a new PHP file)» | correspondance | critique | Un POST ayant reçu une réponse 2xx vers un fichier PHP créé ou modifié dans son DocumentRoot au cours du dernier jour, ou vu pour la première fois au cours de la dernière heure (après les jours d'apprentissage) | — |
| `apache-db-error-after-attack` «database error after a suspicious request» | séquence | critique | Une requête qui a déclenché des règles du CRS et, depuis la même IP, une erreur de base de données (SQL ou PDO) dans error.log | 1, en 30 s maximum |

<a id="health"></a>
## 10. Avertissements de santé du module Apache

En plus des avertissements de santé de localSIEM lui-même, le module vérifie toutes les 5 minutes au plus, et envoie au SOC :

| Avertissement | Gravité | Que faire |
|---|---|---|
| ModSecurity n'est plus chargé | élevée | Il était chargé et ne l'est plus : les requêtes ne sont pas inspectées. Si personne ne l'a fait volontairement, quelqu'un a peut-être désactivé la protection. |
| Moteur ModSecurity passé à Off | élevée | `SecRuleEngine` est passé à `Off`, ou le journal d'audit indique que le moteur est désactivé. Vérifiez la configuration d'Apache et ses modifications récentes. |
| IP réelle du client manquante (mod_remoteip) | moyenne | Au cours de la dernière heure, au moins 90 % d'au moins 100 requêtes provenaient d'une même adresse privée ou locale : le site web est probablement derrière un proxy et Apache journalise l'IP du proxy, donc les règles par IP ne fonctionnent pas pour ces requêtes. Envoyé au plus une fois par jour. |

Ce qui a déjà été signalé est mémorisé d'un redémarrage à l'autre, de sorte qu'une mise à jour ne l'envoie pas de nouveau. Grâce à ces avertissements, un module activé n'est jamais désactivé de lui-même quand Apache ou ModSecurity disparaît.

<a id="privesc"></a>
## 11. Le module d'élévation de privilèges

Le module **privesc** («Élévation de privilèges») surveille ce que les personnes et les services exécutent sur le serveur et signale les étapes d'une élévation vers root : la reconnaissance, la recherche de programmes setuid, les outils d'énumération comme linpeas, les exploits connus, les reverse shells, root obtenu sans sudo ni su, les portes dérobées laissées en place et les tentatives d'aveugler la surveillance. Il examine aussi la surface d'attaque du serveur : programmes setuid, capabilities et fichiers sensibles modifiables par d'autres (section 16).

Il ne lit que ce dont le serveur dispose déjà : il n'installe jamais rien, ne charge jamais de règles d'audit et ne modifie jamais la configuration d'auditd, de snoopy ni des shells. Il lit jusqu'à deux sources :

| Source | Ce qu'il voit | Où il fonctionne |
|---|---|---|
| **auditd** (`/var/log/audit/audit.log`) | sudo, su, pkexec et les connexions SSH (PAM), et tout ce qu'enregistrent les règles d'audit du serveur (voir ci-dessous) | Serveurs physiques et machines virtuelles, tant qu'auditd tourne. **Pas dans un conteneur** (LXC, podman, systemd-nspawn, Docker) : l'audit du noyau n'est pas isolé par namespace, donc auditd ne tourne que sur l'hôte. |
| **syslog** (`/var/log/auth.log`, `/var/log/secure` ou `/var/log/messages`) | sudo, su, pkexec, doas, les connexions SSH et, si **snoopy** est installé, chaque programme exécuté | Partout, conteneurs compris. Lu quand auditd ne tourne pas, que son journal ne peut pas être lu ou que snoopy est installé (paramètre **Lire syslog**). Il faut un démon syslog qui écrit dans un fichier : le journal de systemd seul n'est pas lu. |

Ce que montre auditd dépend des règles d'audit que charge le serveur, qui relèvent de la décision de son administrateur ; le module les utilise telles qu'elles sont, quelles que soient leurs clés, et classe chaque enregistrement selon son type, son appel système et ses fichiers :

| Le module voit | Quand les règles d'audit du serveur enregistrent |
|---|---|
| Chaque programme exécuté (y compris depuis des scripts, des web shells et des exploits), les programmes setuid, le root qui en est hérité, les capabilities obtenues | `execve` |
| Les modifications des comptes, de sudoers, de PAM, de preload, de SSH, de cron, des services et de `/etc/audit` | Des surveillances (`-w ... -p wa`) sur ces fichiers ou les appels système qui les modifient |
| Les bits setuid ou setgid positionnés | `chmod`, `fchmod`, `fchmodat` |
| Les modules du noyau chargés ou retirés | `init_module`, `finit_module`, `delete_module` |
| Les processus attachés avec ptrace | `ptrace` |
| Les fichiers refusés à une personne | `open`, `openat`, `execve`... qui échouent avec `EACCES` ou `EPERM` |
| Les règles d'audit supprimées, l'audit désactivé, auditd arrêté, les programmes qui plantent | Toujours (le noyau et auditd les signalent) |

Sur un serveur physique ou une machine virtuelle, auditd est la source à laquelle un utilisateur ne peut pas échapper ; le diagnostic indique ce que les règles d'audit du serveur ont enregistré jusqu'ici (section 14). Dans un conteneur, snoopy est le seul moyen de voir chaque programme exécuté.

Les commandes internes du shell (`pwd`, `cd`, `unset HISTFILE`, `history -c`) n'exécutent jamais de programme, donc aucune source ne les voit, sauf à l'intérieur d'une ligne de commande comme `bash -c '...'`. Un seul `whoami` n'est jamais une alerte : le module compte les commandes de reconnaissance **distinctes** de chaque session dans une fenêtre, et seule une rafale de ces commandes en est une (section 13).

Ce que contient chaque événement du module, et comment le rechercher :

| Colonne | Contient | Exemple de recherche |
|---|---|---|
| `vhost` | La personne : l'utilisateur de connexion (il reste le même à travers sudo et su) | `module:privesc vhost:alice` |
| `method` | Type d'événement : `exec` (programme exécuté, auditd ou snoopy), `sudo`, `su`, `pkexec`, `doas`, `login`, `pam`, `file` (fichier sensible modifié), `chmod` (bit setuid), `kmod`, `ptrace`, `denied` (fichier refusé), `audit_config`, `auditd`, `crash`, `syscall` (un autre appel système enregistré par les règles d'audit du serveur) | `module:privesc method:sudo` |
| `uri` | La ligne de commande (mots de passe masqués) | `module:privesc uri:*linpeas*` |
| `path` | Le programme exécuté, ou le fichier modifié | `module:privesc path:/tmp/*` |
| `ip` | L'adresse SSH de la session, quand elle est connue | `module:privesc ip:203.0.113.7` |
| `score` | Commandes de reconnaissance distinctes de la session dans la fenêtre | `module:privesc score:>=8` |
| `action` | `blocked` quand le système lui-même l'a arrêté : un programme qui n'a pas pu s'exécuter, sudo ou su refusé, un fichier refusé | `module:privesc action:blocked` |
| `source` | `audit` ou `syslog` | `module:privesc source:syslog` |

Les règles portant sur des tentatives (échecs de sudo répétés, nombreux fichiers refusés) comptent quand même les événements bloqués ; les autres ne regardent que ce qui s'est réellement exécuté.

La page du module, `/admin/dashboard/modules/installed/privesc/`, comporte les mêmes parties que la page du module Apache (section 4) : en-tête (avec **Redécouvrir et lancer le diagnostic**, **Reconfigurer** et **Désinstaller**), paramètres (section 12), sources (`audit`, `syslog` ; et celles qui ne sont pas lues, avec le motif), diagnostic (section 14) et règles (section 13).

<a id="privesc-settings"></a>
## 12. Paramètres du module d'élévation de privilèges

| Paramètre | Par défaut | Ce qu'il fait |
|---|---|---|
| **Journal d'audit** | vide | Vide : `log_file` de `/etc/audit/auditd.conf`, ou `/var/log/audit/audit.log`. |
| **Lire syslog** | Automatique | Automatique : uniquement quand auditd ne tourne pas, que son journal ne peut pas être lu ou que snoopy est installé. Toujours, ou Jamais. |
| **Fichier syslog** | vide | Vide : `/var/log/auth.log`, `/var/log/secure` ou `/var/log/messages`, le premier qui existe. |
| **Utilisateurs ignorés** | vide | Séparés par des virgules. Leurs commandes sont conservées et consultables, mais ne déclenchent jamais d'alerte : comptes d'automatisation (ansible, sauvegardes). L'utilisateur `localsiem` est toujours ignoré. |
| **Groupes d'administrateurs** | `sudo,wheel,admin` | Séparés par des virgules. Leurs membres (et root) bénéficient du seuil de reconnaissance le plus élevé et peuvent lister leurs droits sudo sans alerte. |
| **Fenêtre de reconnaissance (secondes)** | 120 | Fenêtre dans laquelle les commandes de reconnaissance distinctes d'une session sont comptées (10 à 3600). |
| **Seuil de reconnaissance** | 8 | Nombre de commandes de reconnaissance distinctes dans la fenêtre qui constitue une rafale, pour les utilisateurs et les comptes de service (2 à 500). |
| **Seuil de reconnaissance pour les administrateurs** | 20 | Idem pour root et les administrateurs, qui les exécutent dans le cadre de leur travail (2 à 500). |
| **Seuil d'énumération automatisée** | 40 | Nombre de commandes de reconnaissance distinctes dans la fenêtre que seul un script exécute (de type linpeas), pour tout le monde (5 à 1000). |
| **Jours d'apprentissage des comptes de service** | 3 | Pendant les premiers jours qui suivent le tout premier démarrage du module, les programmes qu'exécute chaque compte de service (`www-data` exécutant `sh -c sendmail`) sont appris sans alerte (0 à 365). |
| **Heures entre les analyses des programmes setuid** | 24 | Fréquence de recherche des programmes setuid et setgid et des capabilities de fichiers (section 16). 0 : jamais (0 à 168). |
| **Dossiers analysés** | `/usr,/bin,/sbin,/lib,/lib64,/opt,/home,/srv,/tmp,/var/tmp,/dev/shm,/var/www,/etc` | Séparés par des virgules ; chacun est parcouru sans sortir de son système de fichiers. Les dossiers des conteneurs ainsi que `/proc` et `/sys` sont toujours ignorés. |
| **Intervalle de découverte (secondes)** | 300 | Fréquence à laquelle le journal d'audit, syslog et l'état d'auditd sont recherchés (60 à 86400). L'intervalle le plus court des modules activés s'applique à tous. |

Ce qui compte comme reconnaissance : `whoami`, `id`, `groups`, `uname`, `hostname`, `w`, `who`, `last`, `ps`, `ss`, `netstat`, `ip`, `ifconfig`, `env`, `pwd`, `history`, `getcap`, `lsmod`, `dmesg`, `mount` et similaires ; `sudo -l`, `crontab -l`, `systemctl list-*`, les listes de paquets ; `which`, `locate`, `command -v` ; `docker ps` et similaires ; chaque `find` différent ; la lecture de `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`, `/etc/*-release`, `/proc/version`, `/root/...`, des historiques, des clés SSH et des fichiers `.env` ; le listage de `/root`, `/home`, `/opt`, `/tmp`, des dossiers de cron... ; `grep -r password` ; et `<program> --version`. Chaque commande différente d'une session compte une seule fois dans la fenêtre.

<a id="privesc-rules"></a>
## 13. Ce que le module d'élévation de privilèges envoie au SOC : ses règles

Chaque alerte du module provient de l'une de ses règles (elles fonctionnent de la même façon quelle que soit la source qui a vu la commande), à l'exception de celles de la section 16. Comme pour Apache, chaque règle peut être désactivée et sa gravité, son seuil et sa fenêtre modifiés dans la page du module ; ses événements peuvent être retrouvés avec `rule:localsiem:<id>`. Aucune ne se déclenche pour les **Utilisateurs ignorés**. Les règles marquées «auditd» ont besoin des enregistrements d'audit de la section 11.

| Règle | Type | Gravité | Quand | Seuil / fenêtre |
|---|---|---|---|---|
| `privesc-recon-burst` «reconnaissance burst» | correspondance | moyenne | La session a atteint le seuil de reconnaissance (section 12) | — |
| `privesc-enumeration` «automated enumeration (linpeas-like)» | correspondance | élevée | La session a atteint le seuil d'énumération automatisée, même avec un script renommé | — |
| `privesc-suid-hunt` «search for setuid programs or capabilities» | correspondance | élevée | `find ... -perm -4000` (ou `-u=s`, `/6000`, `-2000`...), `getcap -r`, `find -writable` | — |
| `privesc-sudo-list` «sudo rights listed by a non-administrator» | correspondance | moyenne | `sudo -l` par un utilisateur ou un compte de service qui n'est pas administrateur | — |
| `privesc-known-tool` «known enumeration tool» | correspondance | élevée | linpeas, LinEnum, lse.sh, linux-exploit-suggester, les.sh, pspy, unix-privesc-check, linuxprivchecker, traitor, BeRoot, GTFONow, PEASS, deepce, CDK, sudo_killer, suid3num, mimipenguin, LaZagne, pwncat, searchsploit | — |
| `privesc-exploit` «known exploit» | correspondance | critique | PwnKit, DirtyPipe, Dirty COW, Baron Samedit (`sudoedit -s '\'`), Looney Tunables (`GLIBC_TUNABLES`), GameOver(lay), nf_tables (CVE-2024-1086), CVE-2023-22809 (`EDITOR=... -- /...`), polkit CVE-2021-3560 (`dbus-send ... CreateUser`), `LD_PRELOAD` avec sudo, un script nommé d'après une CVE, des programmes nommés `exploit`, `getroot`, `rootme` | — |
| `privesc-pwnkit` «PwnKit (pkexec run without arguments)» | correspondance | critique | `pkexec` exécuté avec zéro argument (auditd) | — |
| `privesc-pwnkit-log` «pkexec reports a PwnKit attempt» | correspondance | critique | pkexec journalise `GCONV_PATH`, «suspicious content» ou «was not found the /etc/shells» (syslog) | — |
| `privesc-suid-escape` «root inherited from a setuid program» | correspondance | critique | Un programme qui n'est pas setuid s'exécute avec l'uid effectif de root et l'uid réel d'un utilisateur : un programme setuid a été détourné (GTFOBins). Les assistants de montage, D-Bus, polkit et X sont exclus. | — |
| `privesc-root-without-door` «root without sudo, su or pkexec» | correspondance | critique | Une session d'une personne dont le début a été vu exécute des programmes en tant que root sans être passée par sudo, su, pkexec ou doas (exploits du noyau) (auditd) | — |
| `privesc-root-shell-interpreter` «root shell started by an interpreter» | correspondance | élevée | Un shell s'exécute en tant que root, lancé par python, perl, ruby, awk, gdb... qu'exécutait un utilisateur ordinaire (son enfant, ou le même processus) (auditd) | — |
| `privesc-file-capabilities` «program gained root capabilities from its file» | correspondance | élevée | Un utilisateur a exécuté un programme dont le fichier lui donne `cap_setuid`, `cap_dac_override`, `cap_sys_admin`... (auditd) | — |
| `privesc-tmp-exec` «program run from a world-writable folder» | correspondance | élevée | Un programme dans `/tmp`, `/var/tmp`, `/dev/shm` ou `/run/user/<uid>` | — |
| `privesc-compile-tmp` «program compiled in a temporary folder» | correspondance | élevée | `gcc`, `cc`, `clang`, `make`... dans un dossier temporaire ou sur des fichiers d'un dossier temporaire | — |
| `privesc-download-shell` «downloaded script run by a shell» | correspondance | élevée | `curl ... \| sh`, `bash -c "$(curl ...)"`, `bash <(wget ...)`, ou un outil de téléchargement suivi d'un shell dans le même pipeline | — |
| `privesc-reverse-shell` «reverse shell» | correspondance | élevée | `/dev/tcp/`, `nc -e`, `ncat --exec`, `socat exec:`, `mkfifo ... \| nc`, sockets python/perl/php/ruby/lua/node, `openssl s_client ... \| sh`, `awk /inet/tcp` | — |
| `privesc-tty-upgrade` «shell upgraded to a full terminal» | correspondance | élevée | `pty.spawn`, `script ... /dev/null`, `stty raw -echo`, `socat ... pty`, `expect ... spawn sh` | — |
| `privesc-service-recon` «service account ran reconnaissance commands» | correspondance | élevée | `www-data`, `mysql` et d'autres comptes de service exécutant `whoami`, `id`, `uname`... (un web shell) | — |
| `privesc-service-new-program` «service account ran a program it never ran before» | correspondance | élevée | Après les jours d'apprentissage, un compte de service exécute un shell, un interpréteur ou un outil qu'il n'avait jamais exécuté (`sh -c id` alors qu'il n'exécutait que `sh -c sendmail`) | — |
| `privesc-container-escape` «container used to reach the host as root» | correspondance | élevée | Quelqu'un qui n'est pas root exécute `docker run -v /:/...`, `--privileged`, `--pid=host`, `nsenter -t 1`, `lxc config set ... security.privileged true`, `lxc config device add ... source=/`, `debugfs /dev/...` | — |
| `privesc-auth-failures` «repeated sudo or su failures» | seuil | moyenne | Échecs de sudo, su, pkexec ou doas d'un même utilisateur | 3 en 600 s |
| `privesc-sensitive-file` «account, sudo, PAM or preload file changed» | correspondance | élevée | `/etc/passwd`, `shadow`, `group`, `gshadow`, `sudoers`, `sudoers.d`, `doas.conf`, `doas.d`, `ld.so.preload`, `ld.so.conf`, `ld.so.conf.d`, `pam.d`, `security` modifiés par un programme qui n'est pas un outil de paquets ou de comptes (auditd) | — |
| `privesc-persistence-file` «SSH, cron or service file changed» | correspondance | moyenne | `/root/.ssh`, `sshd_config`, `sshd_config.d`, fichiers de cron, `/etc/systemd/system`, `/etc/init.d`, `rc.local`, `/etc/local.d` modifiés (auditd) | — |
| `privesc-monitoring-changed` «auditd configuration changed» | correspondance | moyenne | `/etc/audit` modifié par un programme qui n'est pas un outil de paquets (auditd) | — |
| `privesc-suid-set` «setuid or setgid bit set on a file» | correspondance | élevée | `chmod u+s`/`g+s` sur un fichier (pas un dossier) en dehors du gestionnaire de paquets (auditd) | — |
| `privesc-setcap` «file capabilities set» | correspondance | élevée | `setcap ... cap_...` | — |
| `privesc-kernel-module` «kernel module loaded from a session» | correspondance | élevée | Un module chargé ou retiré depuis la session d'une personne (auditd) | — |
| `privesc-ptrace` «process attached with ptrace» | correspondance | moyenne | `PTRACE_ATTACH` ou `PTRACE_SEIZE` (auditd) | — |
| `privesc-denied-burst` «many files refused (enumeration)» | seuil | moyenne | Fichiers refusés (`EACCES`, `EPERM`) à un même utilisateur (auditd) | 30 en 60 s |
| `privesc-sensitive-denied` «attempt to read the password hashes or files of root» | correspondance | moyenne | `/etc/shadow`, `/etc/gshadow`, `/etc/sudoers`, `/etc/sudoers.d/` ou `/root` refusés à un utilisateur (auditd) | — |
| `privesc-history-tampering` «shell history erased or turned off» | correspondance | moyenne | `ln -s /dev/null ~/.bash_history`, `rm .bash_history`... ; `unset HISTFILE`, `HISTFILE=/dev/null`, `HISTSIZE=0`, `history -c`, `set +o history` uniquement dans une ligne de commande (`bash -c`), puisque les commandes internes n'exécutent aucun programme | — |
| `privesc-audit-stop-command` «command to turn auditd off» | correspondance | critique | `auditctl -e 0`, `auditctl -D`, `auditctl -a never`, `systemctl stop/disable/mask auditd`, `service auditd stop`, `pkill auditd`, l'effacement de `/var/log/audit` ou de `/etc/audit` | — |
| `privesc-audit-disabled` «auditing turned off» | correspondance | critique | Le noyau signale `audit_enabled=0` (auditd) | — |
| `privesc-auditd-stopped` «auditd stopped by a process» | correspondance | élevée | auditd arrêté à la demande d'un processus autre qu'init (un arrêt du serveur n'est pas signalé) | — |
| `privesc-crash` «setuid or temporary program crashed» | correspondance | moyenne | Un programme setuid, ou situé dans un dossier temporaire, a planté (auditd `ANOM_ABEND`) : souvent un exploit raté | — |

Chaque alerte a un nom stable, une description qui se termine par la requête de recherche à coller dans la recherche de localSIEM, et des détails : utilisateur, type de compte (`root`, `admin`, `user`, `service`), utilisateur réel et effectif, commande, programme, dossier, terminal, session, source (`auditd`, `snoopy`, `syslog`), IP du client et, lorsqu'ils s'appliquent, le programme parent, l'interpréteur, le fichier modifié et son groupe, les commandes de reconnaissance comptées, les capabilities, le mode positionné, la requête ptrace et l'erreur d'un fichier refusé. À son départ, l'alerte porte aussi le contexte de la session : si son début a été vu, si elle est passée par sudo ou su, son adresse SSH et ses **20 dernières commandes**, de sorte que l'analyste lit ce qui a mené à l'alerte sans faire de recherche.

La même commande peut être vue par plusieurs sources (auditd et snoopy) : les alertes sont regroupées par module, utilisateur, IP, catégorie et gravité, si bien qu'elle ne donne quand même qu'une seule alerte. Les mots de passe dans les lignes de commande (`mysql -p...`, `sshpass -p`, `curl -u user:pass`, `PASSWORD=...`, URL avec un mot de passe) sont masqués avant tout stockage, y compris dans l'hexadécimal des enregistrements d'audit.

<a id="privesc-doctor"></a>
## 14. Prérequis du module d'élévation de privilèges : le diagnostic

**Prérequis.** Le module a besoin d'une source que l'utilisateur `localsiem` peut lire (le fichier existe et `localsiem` peut l'ouvrir) : le journal d'**auditd** (auditd en marche, hors conteneur) ou le fichier **syslog** avec sudo, su, pkexec et doas (`/var/log/auth.log`, `/var/log/secure` ou `/var/log/messages`, ou le paramètre **Fichier syslog**, sauf si **Lire syslog** vaut Jamais), où **snoopy** écrit aussi chaque programme exécuté s'il est installé. N'importe laquelle suffit. Quand une source existe mais que `localsiem` ne peut pas la lire, le prérequis l'indique, avec la commande qui donne l'accès en lecture (pour le journal d'audit, la commande de la page Modules, `manage.py setup-modules` ; pour syslog, `setfacl -m g:localsiem:r <file>`). Sans aucune d'elles, il indique ce qu'il faut installer : auditd (Debian : `apt-get install auditd` ; Alpine : `apk add audit && rc-update add auditd && rc-service auditd start`), un démon syslog (Debian : `apt-get install rsyslog` ; Alpine : `apk add rsyslog && rc-update add rsyslog && rc-service rsyslog start`) ou snoopy. D'ici là, le module reste désactivé ; **Reconfigurer** vérifie de nouveau. Il n'installe rien de lui-même. Lors d'une première installation, les journaux appartiennent généralement à root : exécutez la commande qu'affiche l'interface web, puis cliquez sur **Reconfigurer**.

Le diagnostic s'exécute comme celui d'Apache (section 7). Il ne fait que décrire ce que le module voit avec ce dont dispose le serveur et ce qu'il ne peut pas voir ; ses corrections se limitent aux paquets à installer et à l'accès en lecture de `localsiem`. Il ne propose jamais de modifier les règles d'audit, `auditd.conf` (sauf `log_group`, voir ci-dessous), `snoopy.ini`, les shells ni aucune autre configuration :

| Vérification | Correct quand | Sinon |
|---|---|---|
| auditd | auditd est en marche | Avertissement s'il n'est pas installé (Debian : `apt-get install auditd` ; Alpine : `apk add audit && rc-update add auditd && rc-service auditd start`) ; avertissement, sans correction, s'il est installé mais arrêté (le fait qu'il tourne relève de la décision de l'administrateur). Info dans un conteneur : auditd ne peut pas y tourner. |
| Journal d'audit | `localsiem` peut le lire | Erreur, avec la commande de la page Modules ; avertissement si auditd tourne et que son journal n'est pas là où le module le cherche (paramètre **Journal d'audit**) |
| Groupe du journal d'audit | Le journal d'audit n'appartient pas au groupe `root` | Avertissement s'il lui appartient (`log_group = root` dans `auditd.conf`) : chaque journal qu'auditd crée lors d'une rotation a le mode 600, n'est lisible que par root et localSIEM cesse de lire. La correction est la ligne `log_group = adm` pour `/etc/audit/auditd.conf` (puis redémarrez auditd) : les nouveaux journaux sont créés avec le mode 640. |
| Enregistrements des règles d'audit | Des programmes exécutés (`EXECVE`) ont été lus | Avertissement si auditd écrit mais qu'aucun de ses enregistrements n'est un programme exécuté : les règles d'audit du serveur n'enregistrent pas `execve`, donc les commandes des scripts, des web shells et des exploits ne sont pas vues via auditd. Info avec ce que les règles ont enregistré d'autre jusqu'ici (modifications de fichiers sensibles, bits setuid, modules du noyau, ptrace, fichiers refusés) et ce qu'elles n'ont pas encore enregistré |
| syslog | Le fichier syslog est lu | Erreur s'il ne peut pas être lu (`setfacl -m g:localsiem:r <file>`) ; avertissement s'il n'y a ni journal d'audit utilisable ni fichier syslog (Debian : `apt-get install rsyslog` ; Alpine : `apk add rsyslog && rc-update add rsyslog && rc-service rsyslog start`) |
| snoopy | Installé, et ses lignes sont lues | Avertissement sans auditd : les commandes des scripts et des web shells ne sont pas vues (Debian : `apt-get install snoopy` ; Alpine n'a pas de paquet : il se compile depuis les sources). Avertissement s'il est installé mais que syslog n'est pas lu. Info si ses lignes n'ont pas d'uid effectif (`message_format` de `snoopy.ini`) : le root hérité d'un programme setuid n'est pas vu via snoopy |
| Ce que voit le module | — | Info : auditd (et ce qu'enregistrent ses règles), snoopy (chaque programme exécuté) ou, en tant qu'avertissement, seulement sudo, su, pkexec et doas (syslog sans snoopy : la plupart des règles ne peuvent pas se déclencher) ; erreur s'il ne peut rien lire. Il rappelle aussi que les commandes internes du shell ne sont jamais vues |
| Fichiers de la version 1.0.0 | — | Info, sans correction, si les fichiers qu'a laissés `--configure-privesc` sont trouvés (section 15) |
| Programmes setuid et capabilities | — | Info : la dernière analyse (section 16). Avertissement, sans correction, avec les programmes setuid qui donnent un shell root (GTFOBins) et avec les programmes dont les capabilities équivalent en pratique à root |
| Fichiers sensibles | Aucun n'est modifiable par quelqu'un d'autre que root | Erreur, sans correction, pour chacun d'eux (`/etc/passwd`, `sudoers`, cron, `/etc/profile.d`, les dossiers du `PATH` de root, `docker.sock`...) |
| Groupes privilégiés | — | Avertissement, sans correction, avec les membres de `docker`, `lxd`, `incus-admin`, `disk` et `libvirt` : ils sont root en pratique |

<a id="privesc-legacy"></a>
## 15. Serveurs mis à jour depuis la version 1.0.0 du module d'élévation de privilèges

La version 1.0.0 du module avait l'option de configuration `--configure-privesc` et un hook bash ; la version 1.1.0 a supprimé les deux, car un module n'installe ni ne modifie jamais rien en dehors de `/opt/localsiem`. Les serveurs où elle a été appliquée conservent ce qu'elle a écrit, et localSIEM ne l'utilise ni ne le supprime :

- `/etc/audit/rules.d/90-localsiem-privesc.rules` : ses règles d'audit (clés `lsiem_*`). Tant qu'elles sont chargées, le module lit leurs enregistrements comme ceux de n'importe quelle autre règle du serveur.
- `/etc/localsiem-privesc/` (le hook), `/etc/profile.d/localsiem-privesc.sh` et la ligne qui suit «localSIEM privesc: command hook» dans `/etc/bash.bashrc` (Debian) ou `/etc/bash/bashrc` (Alpine) : tant qu'ils sont présents, chaque bash interactif continue d'écrire ses commandes dans `/var/log/localsiem-privesc/`, que personne ne lit.
- `/var/log/localsiem-privesc/` : les fichiers de commandes de chaque utilisateur.
- `log_group = adm` dans `/etc/audit/auditd.conf`, `/root/.ssh` (créé vide) et le `message_format` de `/etc/snoopy.ini` : ils peuvent rester (`log_group = adm` garde lisibles les journaux d'audit après rotation, section 14, et le module lit ce format de snoopy aussi bien que ses formats par défaut).

Le diagnostic liste ceux qu'il peut voir (vérification «Files of version 1.0.0 of the module»). Pour les retirer, en tant que root : supprimez le fichier de règles et rechargez les règles (`augenrules --load`) ; supprimez `/etc/profile.d/localsiem-privesc.sh`, `/etc/localsiem-privesc/` et la ligne du bashrc ; et supprimez `/var/log/localsiem-privesc/` si vous ne voulez pas garder les commandes qu'il contient.

<a id="privesc-health"></a>
## 16. Surface d'attaque et avertissements de santé du module d'élévation de privilèges

En plus de ses règles, le module examine le serveur lui-même et envoie au SOC :

| Avertissement | Gravité | Quand |
|---|---|---|
| Nouveau programme setuid ou setgid | élevée | Une analyse trouve un programme setuid ou setgid que l'analyse précédente n'avait pas (la première analyse sert uniquement de référence). Un attaquant devenu root laisse souvent un shell setuid derrière lui ; une mise à jour de paquet peut aussi en ajouter un. |
| Nouveau programme setuid dans un dossier modifiable | critique | Idem, dans `/tmp`, `/var/tmp`, `/dev/shm`, `/home`, `/srv` ou `/var/www` |
| Nouveau programme setuid de GTFOBins | critique | Idem, pour un programme qui donne un shell root lorsqu'il est setuid (`bash`, `find`, `python`, `vim`, `less`, `cp`...) |
| Nouvelles capabilities | élevée | Un programme a obtenu des capabilities qui équivalent en pratique à root (`cap_setuid`, `cap_dac_override`, `cap_sys_admin`...) |
| Fichier sensible modifiable par quelqu'un d'autre que root | critique | Vérifié toutes les heures : `/etc/passwd`, `/etc/shadow` (également lisible par tout le monde), `sudoers`, cron, `/etc/profile.d`, PAM, services, `ld.so.preload`, les dossiers du `PATH` de root, `docker.sock`... Signalé une fois par fichier et par problème. |
| auditd arrêté (santé de localSIEM) | élevée | auditd tournait et ne tourne plus (hors conteneurs) |

L'analyse s'exécute en arrière-plan, au plus une fois par intervalle de **Heures entre les analyses des programmes setuid** (la première cinq minutes après le démarrage du collecteur), à travers les **Dossiers analysés**, en tant qu'utilisateur `localsiem` (ce qu'il ne peut pas lire est ignoré), et s'arrête après 3 millions de fichiers ou 15 minutes. Son résultat, avec les GTFOBins et les capabilities trouvés, est affiché dans le diagnostic. Les gravités de ces avertissements se trouvent dans `severity.yaml` du module. Ce qui a déjà été signalé est mémorisé d'un redémarrage à l'autre.

<a id="cli"></a>
## 17. Ligne de commande

En tant que root, `/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py <command>` :

| Commande | Utilisation |
|---|---|
| `modules` | Modules installés : id, version, activé, désactivé ou non chargé, et dossier, avec les prérequis qui lui manquent, le cas échéant ; et les modules qui n'ont pas pu être chargés, avec l'erreur |
| `doctor` | Pour chaque module activé : chaque vérification (`✓`, `!`, `✗`, `·`) avec l'extrait qui la corrige, et les sources trouvées ; pour un module désactivé parce qu'un prérequis manque, ses prérequis. `--json` donne la même chose en JSON. |
| `read-paths` | Dossiers que lisent les modules, auxquels localSIEM donne l'accès en lecture en tant que root |
| `setup-modules [--no-restart]` | En tant que root : la commande qu'affiche l'interface web ; l'accès en lecture aux dossiers des modules (`read_paths`) et un redémarrage de localSIEM (`--no-restart` : sans redémarrage). Les modules n'ont pas d'options de configuration |

Exécutez le diagnostic en tant qu'utilisateur `localsiem` pour voir ses permissions réelles :

```bash
runuser -u localsiem -- /opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor   # Debian
su -s /bin/sh localsiem -c "/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor"   # Alpine
```
