# localSIEM-modules

This README is also available in:\
en-GB, [en-US](../README.md), [es-AR](README.es-AR.md), [es-ES](README.es-ES.md)

localSIEM-modules holds the **modules** of [localSIEM](../../localSIEM/doc/README.en-GB.md), the lightweight SIEM that runs on the same server it protects. The core of localSIEM stores the events, searches them, applies the rules, groups the alerts and sends them to the PYMEHackers SOC, but it does not know how to read any particular service. Each module teaches it one service: where its logs are, how to read them, how to join them into events, what counts as «already resolved», which rules apply and what the service needs to be configured correctly.

The modules live apart from the core so that each one can be added, updated or turned off without touching localSIEM itself.

Today there are two modules:

- **apache2** (Apache + ModSecurity): reads Apache's `access.log` and `error.log` and the ModSecurity audit log, and joins the three records of each request into one event, by its `UNIQUE_ID` or, with the access logs Apache writes by default, by client IP, request, status and time. What ModSecurity already blocked before the application received it (phases 1-2) stays in localSIEM, searchable, and raises no alert; everything else goes to the SOC, whatever its score. It comes with six rules (brute force, successful login after a brute force, enumeration, sensitive file served, possible web shell, database error after an attack), a doctor that checks the Apache and ModSecurity requirements, and health checks that warn when the protection is switched off.
- **privesc** (Privilege escalation): watches what people and services run on the server and warns about the steps of an escalation to root. It reads auditd on bare-metal servers and virtual machines, a hook of the interactive bash shells (which also sees builtins such as `pwd`) everywhere, containers included (LXC, podman, systemd-nspawn), and sudo, su, pkexec, doas and snoopy through syslog. A single `whoami` or `pwd` raises nothing; a burst of different reconnaissance commands in one session does. It comes with 37 rules (reconnaissance burst, automated enumeration such as linpeas, search for setuid programs, known tools and exploits such as PwnKit or DirtyPipe, reverse shells, root inherited from an abused setuid program, root gained without sudo or su, web shell commands of service accounts, back doors in accounts, sudoers, PAM, cron or SSH, setuid bits and capabilities, history erased, auditd turned off...), a scan of setuid programs, capabilities and sensitive files writable by others, and a doctor that says what each kind of server needs.

[User manual](MANUAL.en-GB.md) · [Code reference](CODE.en-GB.md)

## Requirements

- **localSIEM 2.2.0 or newer**, on Debian 13 or Alpine Linux 3.24 or newer with Python 3.13 or newer (see the [localSIEM README](../../localSIEM/doc/README.en-GB.md)). Modules are installed from the localSIEM web; the command that lets localSIEM read their logs runs as root (`sudo` is not needed).
- For the apache2 module: Apache with **ModSecurity 2 (mod_security2) and the OWASP Core Rule Set** already active. Installing the module never installs Apache or ModSecurity: without either of them it is installed **turned off**, and once you install them, **Reconfigure** on its page finds them and lets you turn it on.
- For the privesc module: **auditd** (recommended on bare metal and virtual machines; it cannot run inside a container), **bash** (for its hook) or **snoopy**, at least one of them. Installing the module installs none of them: without any it is installed **turned off**. Inside containers, a syslog daemon that writes `/var/log/auth.log` (or `/var/log/messages`) and snoopy let it see sudo, su and the commands of scripts.

## Install or update

localSIEM must be installed first: its installer installs the core only and leaves it ready for the modules (see the [localSIEM README](https://github.com/PYMEHackers/localSIEM)). The modules are installed **only from the localSIEM web**: this project has no installer of its own, and the web downloads them from this repository (`https://github.com/PYMEHackers/localSIEM-modules`, branch `main`).

1. As an administrator, open **Administration › Modules › Installable** (`/admin/dashboard/modules/installable/`).
2. Press **Check the repository**: it lists the modules of this repository that are not installed yet, with the version of each one. If every one is already installed, it says «Every module of the repository is already installed.».
3. Press **Install** on the module. localSIEM copies it to `/opt/localsiem/modules/<name>/` (without its `tests/` folder) and loads it within a few seconds; the module leaves the list and a dialogue says what comes next.
4. Reading the logs of a module needs root, so the dialogue shows the command to run as root on the server (`manage.py setup-modules`), with a **Copy** button. It gives the `localsiem` user read access to the folders the module declares (`/var/log/apache2` for the apache2 module, `/var/log/audit` for the privesc module) and, if you add the setup option of the module to it, it also applies that option:
   - `--configure-apache` (apache2): the module writes one file of its own, runs `configtest`, undoes everything if it fails and reloads Apache (never restarts it) if it works.
   - `--configure-privesc` (privesc): the module loads its auditd rules (restoring the previous ones if auditd refuses them), sets `log_group = adm` in `auditd.conf`, installs the bash hook and the folder of the command files, and sets the format of snoopy if it is installed. Run it again after updating the module.

   If the server lacks what the module needs, the dialogue lists what is missing instead: the module is installed turned off (see below).

**Update.** When **Administration › Modules › Installed** (`/admin/dashboard/modules/installed/`) opens, the web checks the repository. A module with a newer version there shows «The repository has version X (the installed one is Y).» and an **Update** button: after you confirm, localSIEM installs the new version over the installed one, keeps its settings, leaves the module on or off as it was and restarts the collector. The command for root is shown again only if the new version reads other logs or has another setup option. If the new version needs a newer localSIEM, the notice says so and has no button.

The web has no reinstall button: to reinstall a module, press **Uninstall** on its row in **Installed** and install it again from **Installable**; its settings are kept.

## Turn on and configure the Apache module

If the server has Apache and ModSecurity, the apache2 module is **on** after the installation and already reading the Apache logs. If either is missing, it is installed **turned off** and cannot be turned on yet: install them, press **Reconfigure** on the page of the module and, once it finds them, turn it on with its switch. To check it, turn it on or off or configure it:

1. Open the localSIEM web (`https://<server>:10443/`) and sign in as an administrator.
2. Go to **Administration › Modules › Installed** (`/admin/dashboard/modules/installed/`; `/admin/dashboard/modules/` opens it). Each module shows its state («On and working», «On, with warnings», «Error», «Off», «Applying the change…» or «Unknown»), why, and a switch to turn it on or off.
3. Click **Configure** to open `/admin/dashboard/modules/installed/apache2/`: its state and figures, its settings (manual sources, Apache configuration file, discovery interval, blocking threshold, learning days), the sources it reads, the doctor with the snippet that fixes each missing requirement, and its rules (on or off, severity, threshold and window).

Changes apply at once, without restarting anything. Analysts see the state of the modules, read-only, in `/user/dashboard/modules/`.

From the command line, as root:

```bash
/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py modules            # installed modules and their state
/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor             # requirements and sources
/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py configure-apache   # file that --configure-apache would write
```

## Turn on and configure the privilege escalation module

If the server has auditd, bash or snoopy, the privesc module is **on** after the installation. Then run, as root, the command the web shows, adding `--configure-privesc`:

```bash
/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py setup-modules --configure-privesc
```

What it watches depends on the server:

- **Bare metal or a virtual machine**: install auditd first (`apt-get install auditd` on Debian; `apk add audit && rc-update add auditd && rc-service auditd start` on Alpine), then run the command above. auditd sees every program run, also from scripts and exploits, and cannot be avoided by a user.
- **Container** (LXC, podman, systemd-nspawn): auditd cannot run inside it. The module reads the bash hook and syslog; install a syslog daemon and snoopy (`apt-get install rsyslog snoopy` on Debian) to also see sudo, su and the commands of scripts and web shells, and run auditd with the rules of this module on the host.

Its page, `/admin/dashboard/modules/installed/privesc/`, shows the sources it reads (the audit log, one command file per user, syslog), the doctor (what each kind of server is missing, the setuid programs that give a root shell, the sensitive files writable by others and the members of groups such as `docker` that are root in practice) and the rules. The settings let you ignore automation accounts, name the administrator groups and tune the reconnaissance thresholds.

## Contents of this project

| Path | Content |
|---|---|
| `mod-apache2/` | The apache2 module (the folder of each module is `mod-<name>/`; the module keeps its name): `module.json`, code, `severity.yaml`, rules (`rules/`), texts of the web (`locales/`) and tests (`tests/`) |
| `mod-privesc/` | The privesc module: `module.json`, code, `severity.yaml`, rules (`rules/`), texts of the web (`locales/`) and the bash hook (`hook/`) |
| `doc/` | User manual, code reference and the translations of this README |

The [user manual](MANUAL.en-GB.md) explains the Modules page and, for each module, every setting, what goes to the SOC, the requirements the doctor checks, the rules and the health warnings. The [code reference](CODE.en-GB.md) explains the contract with the core and how to write a new module.
