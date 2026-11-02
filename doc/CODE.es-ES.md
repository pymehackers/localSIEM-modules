# Referencia técnica de localSIEM-modules

Este CODE también está disponible en:\
[de-DE](CODE.de-DE.md), [en-GB](CODE.en-GB.md), [en-US](CODE.md), [es-AR](CODE.es-AR.md), es-ES, [fr-FR](CODE.fr-FR.md), [he-IL](CODE.he-IL.md), [hi-IN](CODE.hi-IN.md), [it-IT](CODE.it-IT.md), [ja-JP](CODE.ja-JP.md), [ko-KR](CODE.ko-KR.md), [pt-BR](CODE.pt-BR.md), [pt-PT](CODE.pt-PT.md), [ru-RU](CODE.ru-RU.md), [zh-CN](CODE.zh-CN.md)

## Índice

1. [Arquitectura y decisiones de diseño](#architecture)
2. [Mapa de módulos](#modules)
3. [Símbolos clave](#symbols)
4. [Flujos principales de llamadas](#flows)
5. [Puntos de entrada](#routes)
6. [Análisis de impacto](#impact)
7. [Puntos de extensión](#extensions)

[Instalación](README.es-ES.md) · [Manual de uso](MANUAL.es-ES.md) · [Referencia técnica de localSIEM](../../localSIEM/doc/CODE.es-ES.md)

<a id="architecture"></a>
## 1. Arquitectura y decisiones de diseño

Este proyecto contiene los módulos instalables de localSIEM (proyecto hermano `../localSIEM`). No tiene servicio ni instalador propios: los módulos se instalan únicamente desde la web de localSIEM, en Módulos › Instalables (se actualizan y se desinstalan en Módulos › Instalados), que descarga este repositorio (rama `main`) y copia la carpeta de cada módulo, `mod-<nombre>/`, a `/opt/localsiem/modules/<nombre>/`; el instalador de localSIEM instala sólo el núcleo, nunca un módulo, y localSIEM no tiene módulos propios. Los procesos de localSIEM (colector, web, `manage.py`) lo cargan. El prefijo `mod-` es exclusivo del nombre de la carpeta en este repositorio: el módulo en sí (el `id` de su `module.json`, sus opciones, sus ajustes y su carpeta instalada) conserva su nombre sin él. Hoy hay dos módulos: `apache2` (carpeta `mod-apache2/`) y `privesc` (carpeta `mod-privesc/`).

### Por qué los módulos viven fuera del núcleo

El núcleo de localSIEM ([backend/core/](../../localSIEM/backend/core/)) es genérico: el almacenamiento, la búsqueda, el motor de reglas, la agrupación, la cola del SOC, el latido y la salud no saben nada de Apache. Lo que significa un servicio (dónde están sus logs, cómo se trocean y se analizan, cómo los registros se convierten en un evento, qué cuenta como ya resuelto, sus reglas y sus requisitos) vive en un módulo. Tener los módulos en su propio proyecto significa que:

- un módulo tiene versión (`version`), declara la versión mínima de localSIEM que necesita (`core`) y se actualiza, se añade o se desactiva sin una nueva versión de localSIEM;
- el núcleo no importa ningún módulo por su nombre ni tiene módulos propios: el registro de módulos ([backend/core/registry.py](../../localSIEM/backend/core/registry.py)) sólo recorre `/opt/localsiem/modules/` (`LOCALSIEM_MODULES_PATH` en las copias de desarrollo), donde la web instala los módulos de este repositorio;
- un módulo que no se carga nunca detiene a los demás: su error aparece en la web (estado «Error») y en `manage.py modules`;
- un módulo nunca modifica el núcleo: `backend/core/module.py` y `backend/core/registry.py` son todo el contrato.

### El contrato: module.json, locales y una subclase de Module

**`module.json`** (lo comprueba `fReadManifest`):

| Clave | Por defecto | Significado | apache2 | privesc |
|---|---|---|---|---|
| `id` | obligatoria | Nombre de la carpeta del módulo sin el prefijo `mod-` (el nombre de la carpeta instalada), `[a-z][a-z0-9_]{1,31}`; también el `vName` de la clase | `apache2` | `privesc` |
| `version` | `"0"` | Versión del módulo, que muestran la web y `manage.py modules` | `1.3.2` | `1.1.2` |
| `core` | `"0"` | Versión mínima de localSIEM que necesita; si es mayor que la `cVersion` del localSIEM instalado, el módulo no se carga | `2.2.0` | `2.2.0` |
| `entry` | obligatoria | `"archivo:Clase"`: `archivo` sin `.py` (`[a-z][a-z0-9_]{0,63}`), `Clase` una subclase de `Module` | `module:ApacheModule` | `module:PrivescModule` |
| `default_enabled` | `true` | Si funciona hasta que el administrador decida (`modules.<id>.enabled`) | `true` | `true` |
| `read_paths` | `[]` | Carpetas absolutas que localSIEM, como root, permite leer al usuario `localsiem` (el comando que muestra la web después de instalar, después de **Reconfigurar** y después de una actualización que las cambie) | `["/var/log/apache2"]` | `["/var/log/audit"]` |
| `install_requirements` | `{}` | Comandos que instalan en el servidor, como root, el software que necesita el módulo, para cada sistema (`debian`, `alpine`): un comando por línea, sin operadores de la shell, porque la web también los muestra con `sudo` delante (`fCheckInstallRequirements` del núcleo). Se muestran en Módulos › Instalables › Requisitos y nunca se ejecutan | Debian: Apache, ModSecurity 2, el CRS, `a2enmod`, la configuración recomendada de ModSecurity si no hay ninguna, reinicio; Alpine: Apache | Debian: auditd y rsyslog; Alpine: auditd |
| `setup_option` | — | No la usa ningún módulo: el núcleo la ignora (el registro la descarta), porque un módulo nunca cambia el servidor; los `module.json` de versiones anteriores todavía pueden tenerla | no la tiene | no la tiene (`--configure-privesc` se eliminó en la 1.1.0) |
| `settings` | `[]` | Descripción de cada ajuste: la web construye su formulario a partir de ella | 6 ajustes | 13 ajustes |

Cada ajuste tiene una `key` (`[a-z][a-z0-9_]{1,31}`), un `type`, normalmente un `default`, y los atributos de su tipo. `fValidateSettings` / `fCleanValue` / `fCleanRecords` comprueban lo que guarda el administrador:

| Tipo | Atributos | Control en la web | Valores aceptados |
|---|---|---|---|
| `boolean` | — | casilla | `true` / `false` |
| `integer` | `min`, `max` | campo numérico | un entero entre `min` y `max` |
| `string` | `max_length` (500) | campo de texto | texto sin caracteres de control, sin espacios en los extremos, de hasta `max_length` |
| `path` | — | campo de texto monoespaciado | vacío o absoluto (empieza por `/`), de hasta 1024 caracteres |
| `choice` | `choices` (obligatorio), `required` | lista (con «—» cuando no es obligatorio) | uno de `choices`, o vacío |
| `records` | `fields` (obligatorio: ajustes de los otros tipos), `max_items` (50) | un bloque por registro, con Añadir y Quitar | una lista de hasta `max_items` registros; se comprueba cada campo, los campos `required` no pueden quedar vacíos y los campos vacíos se descartan |

**`locales/<idioma>.json`** (de-DE, en-GB, en-US, es-AR, es-ES, fr-FR, he-IL, hi-IN, it-IT, ja-JP, ko-KR, pt-BR, pt-PT, ru-RU, zh-CN), que lee `fReadTexts` y muestra la web (`modules.js fModuleText`, que recurre a en-US y después a la clave):

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

Un archivo de idioma que falte o esté roto sólo pierde su idioma.

**La subclase de `Module`** ([backend/core/module.py](../../localSIEM/backend/core/module.py)). El registro la crea como `Clase(pSettings, pMasker, pStorage, pManifest)`. Sus métodos de enganche:

| Método | Lo llama | Por defecto | `ApacheModule` | `PrivescModule` |
|---|---|---|---|---|
| `mStart()` | el colector, una vez, con el almacenamiento listo | nada | guarda `apache.first_start` (inicio de los días de aprendizaje) | guarda `privesc.first_start`; carga `privesc.sessions`, `privesc.surface` y `privesc.health` |
| `mEnabled()`, `mModuleSettings()`, `mReload()` | el colector, la web | de `modules.<id>` sobre los valores por defecto de `module.json` | heredados | heredados; `mReload` además vacía la caché de `mSettings` |
| `mDiscoveryInterval()` | el colector (el menor de los módulos activados, como mínimo 60 s) | `discovery_interval_seconds` o 3600 | heredado | heredado (300 por defecto) |
| `mDiscover()` | el colector (arranque, intervalo, recarga, petición de doctor), `manage.py doctor` | `[]` | fuentes `{key, path, kind, format, vhost, audit_type, storage_dir}` a partir de la configuración de Apache y de las fuentes manuales | `fDiscoverSources`: el log de auditoría y syslog |
| `mCreateFramer(pSource)` | el colector, por fuente | `LineFramer` | `AuditFramer` para el log de auditoría nativo en serie | heredado (`LineFramer`) |
| `mParse(pSource, pUnit, pReceived)` | el colector, por unidad | obligatorio | registro de `access`, `error` o `audit` | registro de `audit` o `syslog` |
| `mCreateCorrelator()` | el colector, al arrancar | obligatorio | `Correlator` (ventana y correlación débil de los ajustes del núcleo) | `Correlator`: los registros de auditoría por número de serie (EOE o 2 s); las líneas de syslog, en el acto |
| `mBuildEvent(pTransaction)` | el colector, por transacción vencida | obligatorio | evento con `action` y `detections` | evento con los indicadores que comprueban las reglas; sin detecciones propias |
| `mRulesPath()` / `mRuleFunctions()` | el colector, al cargar las reglas | `None` / `{}` | `rules/` de su carpeta / `{"apache2.new_php": mIsNewPhp}` | `rules/` de su carpeta / `{}` heredado |
| `mDetectionFromSignal(pEvent, pSignal)` | el colector, por señal de regla (opcional: se busca con `hasattr`) | detección genérica | detección con los detalles de la petición y `{rule: {id, count}}` | detección con usuario, comando, programa, sesión, padre, archivo... |
| `mEnrich(pDetection)` | el colector, con el grupo, antes de construir la alerta | `{}` | contexto de la IP en la última hora | contexto de la sesión: inicio visto, puerta, dirección SSH, últimos 20 comandos |
| `mDoctor()` | el colector (estado `<id>.doctor`), `manage.py doctor` | `[]` | `fRunDoctor` | `fRunDoctor` (auditd y lo que han registrado sus reglas, syslog, snoopy, lo que ve el módulo, archivos de la versión 1.0.0, superficie de ataque) |
| `mHealth(pNow)` | el colector, cada 60 s, sólo módulos activados | `[]` | ModSecurity descargado o en Off, falta la IP real del cliente (como mucho cada 300 s) | guarda las sesiones; resultados de la búsqueda; cada 300 s: auditd detenido, archivos sensibles modificables (cada hora), arranca la búsqueda de programas setuid |
| `mSkipped()` | estado del colector, `manage.py doctor` | `[]` | logs por tubería, logs cubiertos por el `GlobalLog`, logs de acceso sin datos (`format_without_data`) | syslog no leído (auditd en marcha, `syslog_mode` en never), falta el log de auditoría |
| `mSetLowDisk(pLowDisk)` | el colector, nivel de disco | nada | deja de guardar cabeceras y cuerpos de auditoría | heredado |
| `mDisplayRecord(pRecord)` | la web, ficha de la petición | `{}` | cabeceras y cuerpo del registro de auditoría guardado (`fAuditDisplay`) | heredado |
| `mRequirements()` | el núcleo, localSIEM 2.2.0 o posterior: primera instalación, arranque y recarga del colector, **Reconfigurar** en la web, `manage.py modules` y `doctor` | `[]` (sin requisitos) | `apache_config` y `modsecurity` (`fRequirementChecks`) | `command_source`: cualquier fuente que `localsiem` pueda leer, el log de auditoría (con auditd en marcha, no en un contenedor) o syslog (con snoopy, si está instalado); `audit_log` / `syslog` cuando una fuente existe pero no se puede leer |

El núcleo ya no tiene `mSetupSnippet` ni `mApplySetup`: los módulos no tienen opciones de configuración y nunca cambian el servidor.

Los registros son diccionarios con `time`, `received`, `module` (el id: el colector elige el correlador por él), `source`, `source_key`, `correlation`, `parse_status` (`ok`, `partial`, `unparsed`), `fields` y `raw` (enmascarado), y opcionalmente `search` (el texto que se indexa para la búsqueda de texto completo). Los eventos tienen las columnas de la tabla de eventos (`lEventColumns` en `storage_sqlite.py`) más `record_ids`, `rule_hits` y `detections`. Una detección tiene `module`, `vhost`, `ip`, `category`, `severity`, `rule`, `type`, `description`, `search`, `details`, `time` y `uid`.

### Requisitos: un módulo nunca instala lo que vigila

Instalar un módulo nunca instala el software que vigila: el módulo apache2 no instala Apache ni ModSecurity, y el módulo privesc no instala auditd, ni un demonio de syslog, ni snoopy (su requisito, `command_source`, es cualquier fuente que pueda leer el usuario `localsiem`: el log de auditoría con auditd en marcha fuera de un contenedor, o syslog; `fRequirementChecks` de `mod-privesc/doctor.py`). Lo que necesita el módulo para poder activarse lo define el propio módulo en `mRequirements()` (localSIEM 2.2.0 o posterior): una lista de comprobaciones con el formato del doctor, que se cumple cuando ninguna tiene el estado `error`. El módulo apache2 devuelve `apache_config` (se encuentra una configuración de Apache: `apache2.conf`, `httpd.conf` o el archivo del ajuste `config_file`) y `modsecurity` (`mod_security2` está cargado; ModSecurity 3 no cuenta), que `fRequirementChecks` toma de las primeras comprobaciones del doctor; sin Apache, las dos son errores. Lo que instala ese software se declara en `install_requirements` de `module.json`: la web lo muestra antes de instalar el módulo (Módulos › Instalables › Requisitos), para el sistema del servidor, y nunca lo ejecuta. El núcleo:

- instala el módulo desactivado (`modules.<id>.enabled = false`) cuando en su primera instalación falta un requisito y el administrador nunca decidió; una actualización nunca cambia `enabled`;
- no deja activarlo mientras falte un requisito: el interruptor queda bloqueado y la web muestra los requisitos con su `fix`;
- nunca desactiva por su cuenta un módulo activado que pierde un requisito: su doctor y sus avisos de salud (`mHealth`: «ModSecurity is no longer loaded») lo notifican, y desactivarlo los silenciaría;
- vuelve a comprobar los requisitos al arrancar o recargar el colector, y con **Reconfigurar** en la página del módulo (también desactivado): si se cumplen, desbloquea el interruptor, el administrador activa el módulo y la web muestra el comando que hay que ejecutar como root para que `localsiem` pueda leer los logs creados después de la instalación (`read_paths`).

### Cargado como paquete de espacio de nombres

No hay ningún `__init__.py` (paquetes de espacio de nombres implícitos de Python 3.13). `fRegisterPackage` crea el paquete `localsiem_modules` con la carpeta de los módulos como su `__path__`, y `fLoadClass` importa `localsiem_modules.<id>.<archivo>`, comprueba que la clase sea un `Module` y que su `vName` coincida con el `id`. Consecuencias para el código de un módulo:

- sus propios archivos se importan de forma **relativa** (`from .parsers import AccessParser`);
- el núcleo se importa como **`backend.core...`** (`from backend.core.module import Module`): los procesos de localSIEM ponen la carpeta de localSIEM en `sys.path`;
- sólo están disponibles la biblioteca estándar y las dependencias de localSIEM (su entorno virtual `/opt/localsiem/venv/`, por ejemplo PyYAML): localSIEM no instala nada para un módulo.

### Formulario de ajustes construido a partir del manifiesto

Un módulo no tiene HTML propio. La web lee `settings` de `module.json` y los textos de `locales/`, construye el formulario (`modules.js fBuildSettings`, `fRecordsEditor`), valida lo que se guarda con `fValidateSettings` y guarda únicamente los valores que guardó el administrador en `settings.json`, dentro de `modules.<id>`; `enabled` también vive ahí. El módulo lee `mModuleSettings()`: los valores por defecto de `module.json` con los valores guardados por encima. Por eso, añadir un ajuste no exige ningún cambio ni en la web ni en el núcleo.

Ajustes del núcleo que el módulo apache2 también lee de `self.dSettings`: `host`, `correlation_window_seconds` (5), `weak_correlation_seconds` (2), `below_threshold_severity` (`low`) y `health.single_ip_percent` / `health.single_ip_minimum_requests` (90 / 100). `mModuleSettings()` también pasa las claves guardadas en `modules.apache2` que `module.json` no declara: así lee `mDiscover` `document_roots` (`{vhost: carpeta}`, por encima de los DocumentRoot descubiertos); sólo se puede fijar editando `settings.json`.

### El principio de la «acción tomada»

Al SOC sólo llega lo que todavía nadie ha resuelto. En el módulo apache2, la acción tomada se lee de la fuente más fiable: el log de auditoría (`Action: Intercepted (phase N)` en formato nativo, `audit_data.action.intercepted/phase` en JSON) y, después, el error.log (`Access denied with code NNN (phase N)`). Un 403 sin ningún rastro de ModSecurity no es un bloqueo (`fields.doubtful_block`).

| Situación | `action` | Detección (al SOC) |
|---|---|---|
| Interceptada en las fases 1-2 (la aplicación nunca la recibió) | `blocked` | ninguna: `mAssess` devuelve `None`; se cuenta en el contexto de las alertas posteriores |
| Interceptada en las fases 3-4 | `none` | sí, `blocked_late` (alta), o `success_indicator` con un error de base de datos |
| Coincidencias con el motor en `DetectionOnly` | `none` | sí |
| Coincidencias por debajo del umbral de anomalía | `none` | sí, `below_threshold` (baja) |
| Señales de las reglas YAML | `none` | sí |

Las severidades vienen de `severity.yaml` (`fLoadSeverityTable`; si falta el archivo o un valor no es válido, se mantiene el valor integrado): `crs_not_blocked_2xx` alta, `crs_not_blocked_other` media, `blocked_late` alta, `success_indicator` crítica (regla de salida 950-955 no bloqueada, o un error de base de datos en la misma petición), `below_threshold` baja (el ajuste del núcleo `below_threshold_severity` tiene prioridad). «Por encima del umbral» significa que coincidió una regla 949xxx o que la puntuación indicada por ModSecurity alcanzó el umbral; una puntuación calculada a partir de las severidades de las reglas es sólo una estimación y no decide. El umbral es el de los mensajes; si no, `anomaly_threshold`; si no, el de `crs-setup.conf`; si no, 5.

### Cómo funciona el módulo apache2

1. **Descubrimiento** (`discovery.py`): `ApacheConfig` lee la configuración directamente (`Include`, `IncludeOptional`, `Define`, `${VARS}` del `envvars` de Debian, `<VirtualHost>`, `<IfModule>` frente a los módulos cargados), como el usuario `localsiem` y sin `apache2ctl`. `fDiscoverSources` convierte `CustomLog`/`GlobalLog`/`TransferLog`, `ErrorLog` y `SecAuditLog` en fuentes con la clave estable `apache:<tipo>:<ruta real>`. Un `GlobalLog` cuyo formato tiene `%v` cubre todos los vhosts (los demás logs de acceso se omiten); los logs por tubería y syslog se omiten, y también los logs de acceso cuyo formato no tiene ninguna directiva `%` (Apache escribe tal cual un nombre que ningún `LogFormat` define: `format_without_data`, salvo que otro `CustomLog` con datos escriba en el mismo archivo; el doctor lo indica, sin solución, porque el formato de los logs nunca se cambia); las fuentes manuales van primero y un archivo se lee una única vez.
2. **Troceado y análisis** (`parsers.py`, `logformat.py`, `modsec.py`): las líneas de acceso se analizan con una expresión regular generada a partir de su `LogFormat` (se prueba primero el último formato que funcionó); las líneas de error se clasifican (`modsecurity`, `database`, `php`, `crash`, `apache`); los registros de auditoría se leen como JSON (una línea, cortada antes de `matched_rules`), nativo en serie (`AuditFramer` junta de `--id-A--` a `--id-Z--`) o concurrente (la línea del índice apunta a un archivo dentro de `SecAuditLogStorageDir`). Todo se enmascara; lo que no encaja se conserva como `unparsed`.
3. **Correlación** (`correlate.py`): los registros con el mismo `UNIQUE_ID` forman una transacción, que espera la ventana de correlación y la marca de agua de las fuentes que se están poniendo al día; una línea de acceso sin `UNIQUE_ID` (los formatos que Apache escribe por defecto) se empareja en `mPair`, cuando vence ella o los registros de su petición, con los registros de ModSecurity que no tienen línea de acceso: misma IP de cliente, hora a ±2 s (la línea tiene segundos enteros) y el mismo método, URI, estado y ruta cuando los dos lados los conocen; gana el candidato que coincide en más datos, después el más cercano y después el más antiguo, y el evento se marca como débil. Las líneas de error.log sin `UNIQUE_ID` se juntan en el acto con la transacción más cercana de su IP. Una transacción con `UNIQUE_ID` y una línea de ModSecurity del error.log, mientras llegan registros de auditoría (`vAuditSeen`), espera además a su propio registro de auditoría (`mWaitsForAudit`), como mucho `cAuditWaitSeconds` (120 s) desde su primer registro: ModSecurity escribe las líneas de sus reglas mientras la petición se ejecuta y el registro de auditoría cuando termina, así que, si no, una petición lenta se convertiría en dos eventos; cuando llega el registro de auditoría, la línea del access log tiene `cAfterAuditSeconds` (2 s) más.
4. **Evento** (`ApacheModule.mBuildEvent`): campos tomados del acceso, después de la auditoría y después del error; el vhost de `%v` o, sin él, de la cabecera Host y el puerto local del registro de auditoría (`mVhostName`); con una línea de acceso de segundos enteros, la hora del registro de auditoría; `fSummarize` da las reglas, las categorías, la puntuación, el umbral y la interceptación; la acción tomada y `mAssess` deciden la detección.
5. **Reglas, enriquecimiento, doctor y salud**: las reglas YAML de `rules/` se ejecutan sobre cada evento (motor del núcleo); `mEnrich` añade el contexto de la IP; `fRunDoctor` comprueba los requisitos y describe los logs, sin cambiar nada; `mHealth` vigila ModSecurity y la IP real del cliente. El módulo no tiene opción de configuración: como root, localSIEM sólo da a `localsiem` permiso de lectura sobre `/var/log/apache2`.

### Decisiones de diseño que conviene conocer

- **Sin instalador propio**: los módulos se instalan (Módulos › Instalables), se actualizan (**Actualizar**, en Módulos › Instalados) y se desinstalan (**Desinstalar**) únicamente desde la web de localSIEM, que descarga este repositorio y los instala con `backend/core/catalog.py` (descompresión segura, una instalación cada vez, cambio atómico de la carpeta). Lo que requiere root (el permiso de lectura sobre los `read_paths`) lo hace localSIEM: después de instalar (y después de una actualización que cambie `read_paths`), la web muestra el comando que hay que ejecutar como root.
- **Los logs del cliente sólo se leen**: un módulo nunca escribe en los logs de los servicios que vigila, ni los rota, trunca, mueve o borra, y nunca cambia su formato; el módulo apache2 tampoco cambia nunca la configuración de Apache ni la de ModSecurity (no tiene `setup_option`). Si un servidor escribe sus logs en un formato propio (un `LogFormat` propio, la IP del cliente de `mod_remoteip`), el que se adapta es el módulo: `AccessFormat` construye el analizador de cada log de acceso a partir de su `LogFormat`, y `fCanPair` / `Correlator.mPair` unen las líneas sin `UNIQUE_ID`. El doctor sólo describe los logs y lo que localSIEM puede o no puede leer de ellos: las comprobaciones `log_format`, `log_format_without_data`, `remoteip`, `audit_log` y `sanitise` no tienen `fix`; sólo lo que no es un log (ModSecurity, el CRS, `SecRuleEngine`, `mod_unique_id`, los permisos de lectura de `localsiem`) trae uno. `--configure-apache` se eliminó en la versión 1.3.0; `localsiem_combined` sigue en `dKnownFormats` para los servidores que ya lo escriben, y el instalador de localSIEM borra el `localsiem.conf` que escribieron las versiones anteriores (`--uninstall`, `--reinstall`).
- **La parte K** (`matched_rules`) y **la parte E** (cuerpo de la respuesta) del log de auditoría no se guardan nunca. Las cabeceras y el cuerpo se quedan únicamente en el registro en bruto enmascarado; la ficha de la petición los reconstruye (`fAuditDisplay`). El índice de texto completo recibe un texto reducido (`search`: línea de la petición, host, user agent y el id, el mensaje y los datos de cada regla).
- **El texto en bruto se reconstruye a partir de las partes enmascaradas**: el registro de auditoría original puede contener contraseñas y cookies.
- **La web y las herramientas crean el módulo sin almacenamiento** (`pStorage` es `None` en `WebContext.mModule` y `manage.py`): el constructor y los métodos que ellas llaman no deben usar el almacenamiento.
- **Estado en la base de datos de eventos**: `apache.first_start` (días de aprendizaje), `apache.health` (lo que ya se notificó, para que un reinicio no lo repita) y `apache2.doctor` (lo escribe el colector). Las dos primeras, como las claves de fuente `apache:<tipo>:<ruta real>`, conservan el nombre que tenía el módulo antes de llamarse apache2: un servidor que tenía el módulo `apache` conserva sus días de aprendizaje, su memoria de salud y sus posiciones de lectura (con una clave de fuente nueva, todo log de menos de 5 MiB se volvería a leer desde el principio). Las horas de la memoria de salud están en el formato nativo del proyecto (`2026-10-29@13-59-59.723`, UTC); un estado guardado por una versión anterior, con segundos epoch, se convierte al cargarlo.
- **Seguridad de las rutas**: `mIsNewPhp` rechaza `..` y no sale del DocumentRoot; `fReadConcurrentEntry` no sale de `SecAuditLogStorageDir` y lee como mucho 8 MiB; el correlador guarda como mucho 50 000 transacciones pendientes.

### Cómo funciona el módulo privesc

La pregunta no es «¿alguien ha ejecutado `whoami`?» (los administradores lo hacen a diario), sino «¿esta sesión está recorriendo el camino de una escalada, y ha llegado al final?». El módulo convierte dos fuentes en eventos con un único significado (`vhost` la persona, `method` el tipo, `uri` el comando, `path` el programa o el archivo, `ip` la dirección SSH, `score` el reconocimiento distinto de la sesión), calcula indicadores sobre ellos y deja que las reglas YAML decidan qué va al SOC.

1. **Descubrimiento** (`discovery.py`): `fDiscoverSources` devuelve el log de auditoría (`fAuditLogPath`: el ajuste, el `log_file` de `auditd.conf` o `/var/log/audit/audit.log`; también cuando auditd está en marcha y `localsiem` todavía no lo puede leer, para que lo notifique el núcleo) y syslog (`fSyslogPath`) cuando lo indica `syslog_mode` (`auto`: auditd no está en marcha, su log no se puede leer, o snoopy está instalado). También reúne lo que necesita el doctor: contenedor (`fContainer`, legible sin root: `/run/systemd/container`, `/run/.containerenv`, `/.dockerenv`, `/proc/self/cgroup`, `systemd-detect-virt`), binario y pid de auditd, snoopy, si cada log se puede leer (`fReadState`: `readable`, `unreadable` o `missing`) y los archivos que dejó la versión 1.0.0 (`fLegacyLeftovers`). `Accounts` vuelve a leer `/etc/passwd`, `/etc/group` y `UID_MIN` cuando cambian, y clasifica un uid como `root`, `admin` (miembro de `admin_groups`), `user` o `service`.
2. **Análisis** (`parsers.py`): `fParseAuditLine` lee `type=... msg=audit(<time>:<serial>): k=v ...`, la parte de espacio de usuario `msg='...'` y la parte enriquecida tras `\x1d`, junta los argumentos de `EXECVE` (también los partidos en trozos `aN[i]`), decodifica los valores hexadecimales (`proctitle`, `cmd`, `cwd`, `name`, `exe`, `aN`...) y **reconstruye el texto en bruto a partir de los valores decodificados y enmascarados** (el hexadecimal de una contraseña la conservaría); `search` recibe el comando decodificado. `fParseSyslogLine` lee marcas de tiempo ISO y clásicas (con o sin el `facility.priority` de busybox) y `fParseSyslogMessage` entiende snoopy (sus formatos por defecto de la 2.4 y la 2.5, `uid:alice(1000)/root(0)` incluido, y el que puso la versión 1.0.0), sudo, su (util-linux y busybox), pkexec, doas, `pam_unix` y sshd. `fMaskCommand` enmascara las contraseñas de las líneas de comandos antes del enmascarador del núcleo.
3. **Correlación** (`correlate.py`): los registros de auditoría con el mismo número de serie forman una transacción, que vence con `EOE`, en el acto para los tipos de espacio de usuario de un solo registro (`USER_*`, `CRED_*`, `DAEMON_*`...), o tras 2 s sin registros; como mucho 50 000 pendientes. Las líneas de syslog vencen en el acto.
4. **Evento** (`PrivescModule.mBuildEvent`): `mAuditEvent` reparte según el tipo: `EXECVE` → `mAuditExec` (bit setuid del programa a partir del registro `PATH` o de `stat`, `suid_escape` cuando el euid es 0, el uid real no lo es y el programa no es setuid, capacidades obtenidas de `BPRM_FCAPS`, `root_without_door`, `parent_interpreter` cuando una shell se ejecuta como root arrancada por un intérprete de un usuario distinto de root, el padre a partir de la memoria de procesos); `USER_*`/`LOGIN` → `mAuditUser` (sesión iniciada, dirección SSH, puertas: `USER_START`/`USER_CMD` de sudo, su, pkexec, doas, run0, systemd; fallos); `CONFIG_CHANGE` (`audit_disabled`, `audit_rule_removed` para cualquier regla que se quite), `DAEMON_*` (`auditd_stopped_manually` cuando el remitente no es el pid 1), `ANOM_ABEND` (`crash_suspicious`); cualquier otro `SYSCALL` → `mAuditSyscall`, que lo clasifica por su llamada al sistema (`fSyscallName`: el nombre del formato enriquecido, o el número en la tabla de su arquitectura), sus argumentos y sus registros `PATH`, nunca por la clave de la regla: `denied` (open, exec o truncate fallidos con `EACCES`/`EPERM` para una persona), `kmod`, `ptrace` (`ptrace_attach` para `PTRACE_ATTACH`/`PTRACE_SEIZE`), `chmod` (modo con el bit setuid o setgid, no sobre una carpeta, con `writer_allowed`) y `file` (un cambio de una ruta de `lSensitivePaths`, con `sensitive_group` y `writer_allowed`; la clave, a través de `dKeyHints`, sólo cuando no se puede resolver ninguna ruta). `mSyslogEvent` trata snoopy como `exec` (`suid_escape` a partir de `stat`; sin `filename`, el programa a partir de la primera palabra del comando) y sudo, su, pkexec, doas, login y pam. Cada comando pasa por `mAnalyzeCommand`: token de reconocimiento (`fReconToken`) y tokens distintos de la sesión en la ventana (`recon_burst`, `recon_massive`, `score`), descargas ejecutadas por una shell (`cDownloadOnelinerRegex`, o un programa de descarga seguido de una shell con el mismo padre), `compile_in_tmp`, los últimos comandos de la sesión y, para las cuentas de servicio, el programa (`fProgramKey`) frente a su historial (`mPathFirstSeen` del núcleo, pasados los `learning_days`: `new_program`). `ignored` marca los usuarios ignorados.
5. **Reglas, enriquecimiento, doctor y salud**: las 35 reglas YAML de `rules/` deciden cada detección (`mDetectionFromSignal`); `mEnrich` añade el contexto de la sesión; `fRunDoctor` describe auditd y lo que han registrado sus reglas, syslog, snoopy, lo que ve el módulo y lo que no puede ver, los archivos de la versión 1.0.0 y la superficie de ataque; `mHealth` notifica auditd detenido, los archivos sensibles modificables y el resultado de la búsqueda de programas setuid (`SurfaceScanner`, un hilo). El módulo no tiene opción de configuración y no cambia nada en el servidor.

### Decisiones de diseño del módulo privesc

- **Dos fuentes, un único significado.** Un usuario no puede eludir auditd, pero auditd no funciona dentro de los contenedores (la auditoría del kernel no está separada por espacios de nombres); snoopy ve todos los programas en los contenedores, pero necesita syslog; syslog por sí solo sólo da sudo, su, pkexec y doas. Ninguna fuente ve los comandos internos de la shell. Las reglas comprueban columnas e indicadores, nunca la fuente, así que se puede añadir una fuente sin tocarlas. El mismo comando visto dos veces da una única alerta: el núcleo agrupa las detecciones por módulo, usuario, IP, categoría y severidad.
- **Ráfagas, no comandos.** El reconocimiento es un token por tipo de pregunta (`whoami`, `read:/etc/passwd`, `find:-perm:`...), y sólo el número de tokens distintos de una sesión en una ventana genera una alerta, con un umbral más alto para los administradores y un tercero para los scripts. Los umbrales son ajustes, no umbrales de regla: la regla sólo comprueba `recon_burst` / `recon_massive`.
- **Lo que más importa es el éxito.** `suid_escape` (un programa que no es setuid ejecutándose con euid 0 y un uid real que no es 0) y `root_without_door` (root en una sesión cuyo inicio se vio y que nunca pasó por sudo, su, pkexec ni doas) son las dos señales críticas de que una escalada ha funcionado, casi sin falsos positivos. Una sesión cuyo inicio no se vio (sesiones abiertas antes que el módulo, sesiones olvidadas tras un día de inactividad) nunca se marca.
- **Las sesiones sobreviven a los reinicios.** `SessionTracker` guarda el inicio, la dirección SSH y la puerta de cada sesión en el estado `privesc.sessions` (como mucho una vez por minuto); los tokens de reconocimiento y los últimos comandos se quedan en memoria. Las sesiones inactivas durante un día se descartan.
- **Sólo lo que el servidor ya tiene.** El módulo nunca instala nada ni cambia nada fuera de `/opt/localsiem`: no carga reglas de auditoría, no toca `auditd.conf` ni `snoopy.ini` y no instala ningún hook. La versión 1.0.0 sí lo hacía (`--configure-privesc`: reglas de auditoría con las claves `lsiem_*`, `log_group = adm`, un hook de bash, el formato de snoopy); la versión 1.1.0 lo eliminó. Por eso los registros de auditoría se clasifican por su tipo, su llamada al sistema y sus rutas, de modo que sirve cualquier conjunto de reglas de auditoría (las del servidor, las reglas de ejemplo STIG o las reglas `lsiem_*` que dejó la 1.0.0); la clave se guarda en `fields.key` para las búsquedas y es sólo una pista (`dKeyHints`). Los números de las llamadas al sistema se leen por arquitectura (`dSyscallTables`: x86_64, i386 y la tabla genérica de aarch64, riscv64 y loongarch64) cuando el log no tiene los nombres del formato enriquecido. El doctor describe lo que registran las reglas del servidor y lo que no; su `fix` es sólo un paquete que instalar o el permiso de lectura de `localsiem`.
- **Legible quiere decir legible.** El requisito lo cumple una fuente que existe y que `localsiem` puede abrir (`fReadState`), no un programa instalado: en una primera instalación los logs suelen pertenecer a root, así que el módulo sigue desactivado hasta el comando para root (`manage.py setup-modules`) y **Reconfigurar**.
- **Los gestores de paquetes no son atacantes.** Los cambios de archivos sensibles y de bits setuid que hacen las herramientas de cuentas y de paquetes (`sAllowedWriters`), o los programas cuyos antepasados conocidos son gestores de paquetes, ponen `writer_allowed`, y las reglas los omiten.
- **La búsqueda nunca bloquea el colector.** `SurfaceScanner` recorre los `scan_paths` en un hilo propio, sin salir del sistema de archivos de cada uno, omitiendo `/proc`, `/sys` y las carpetas de los contenedores, hasta 3 millones de archivos o 15 minutos; `mHealth` recoge el resultado cuando está listo. La primera búsqueda es la referencia; las siguientes notifican lo nuevo.
- **La web y las herramientas crean el módulo sin almacenamiento**: `mDiscover`, `mDoctor` y `mRequirements` nunca lo usan, y `mAnalyzeCommand` sólo llama a `mPathFirstSeen` cuando existe.
- **Estado en la base de datos de eventos**: `privesc.first_start` (días de aprendizaje), `privesc.sessions`, `privesc.surface` (la referencia de la búsqueda y del doctor), `privesc.health` (lo que ya se notificó y si auditd estaba en marcha) y `privesc.doctor` (lo escribe el colector). Los programas vistos de las cuentas de servicio son filas de `seen_paths` con el vhost `privesc:<cuenta>`. Las horas de `privesc.health` (la memoria de salud) y de `privesc.sessions` (`last` de cada sesión) están en el formato nativo del proyecto (`2026-10-29@13-59-59.723`, UTC); un estado guardado por una versión anterior, con segundos epoch, se convierte al cargarlo.

<a id="modules"></a>
## 2. Mapa de módulos

| Módulo | Ruta | Responsabilidad | Depende de | Usado por |
|---|---|---|---|---|
| Manifiesto | [mod-apache2/module.json](../mod-apache2/module.json) | id, versión, núcleo mínimo, entrada, rutas de lectura, ajustes (sin opción de configuración) | — | registro, web, `manage.py` |
| Módulo Apache | [mod-apache2/module.py](../mod-apache2/module.py) | `ApacheModule`: métodos de enganche, acción tomada, severidad, detecciones, función de regla, enriquecimiento, salud | correlate, discovery, doctor, modsec, parsers; del núcleo `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | colector, web, `manage.py` |
| Descubrimiento | [mod-apache2/discovery.py](../mod-apache2/discovery.py) | `ApacheConfig` (analizador de la configuración), fuentes y logs omitidos, DocumentRoot | logformat (`dKnownFormats`) | módulo, doctor |
| Doctor | [mod-apache2/doctor.py](../mod-apache2/doctor.py) | Comprobación de requisitos; describe los logs (formato, log de auditoría, enmascaramiento) sin proponer cambiarlos | discovery | módulo |
| Formatos de acceso | [mod-apache2/logformat.py](../mod-apache2/logformat.py) | `LogFormat` a expresión regular, horas a UTC, línea de la petición | `timeutil` del núcleo | parsers, discovery |
| Analizadores | [mod-apache2/parsers.py](../mod-apache2/parsers.py) | access, error, audit (JSON, nativo, concurrente), `AuditFramer`, `fAuditDisplay` | logformat, modsec; del núcleo `masking`, `timeutil` | módulo |
| ModSecurity | [mod-apache2/modsec.py](../mod-apache2/modsec.py) | Mensajes, categorías, rangos del CRS, puntuaciones, interceptación | — | parsers, módulo |
| Correlación | [mod-apache2/correlate.py](../mod-apache2/correlate.py) | `UNIQUE_ID`, emparejamiento sin él (`mPair`), ventana, marca de agua | `timeutil` del núcleo | módulo (colector) |
| Tabla de severidades | [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) | Severidades de las detecciones de ModSecurity | — | módulo (`fLoadSeverityTable`) |
| Reglas | [mod-apache2/rules/](../mod-apache2/rules/) | Seis reglas YAML | motor de reglas del núcleo, `mIsNewPhp` | colector (`RulesEngine`), web (`fRules`) |
| Textos | [mod-apache2/locales/](../mod-apache2/locales/) | Nombre, resumen, etiquetas y ayudas de los ajustes, opciones | — | web |
| privesc: manifiesto | [mod-privesc/module.json](../mod-privesc/module.json) | id, versión, núcleo mínimo, entrada, rutas de lectura, 13 ajustes (sin opción de configuración) | — | registro, web, `manage.py` |
| privesc: módulo | [mod-privesc/module.py](../mod-privesc/module.py) | `PrivescModule`: métodos de enganche, eventos de las dos fuentes, clasificación de los registros de auditoría (rutas sensibles, llamadas al sistema por arquitectura), indicadores, detecciones de las reglas, enriquecimiento, salud, resultados de la búsqueda | commands, correlate, discovery, doctor, parsers, surface; del núcleo `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | colector, web, `manage.py` |
| privesc: descubrimiento | [mod-privesc/discovery.py](../mod-privesc/discovery.py) | Fuentes, contenedor, auditd, snoopy, syslog, si cada log se puede leer, archivos que dejó la versión 1.0.0, `Accounts` (usuarios, grupos, tipo de cuenta) | — | módulo, doctor |
| privesc: analizadores | [mod-privesc/parsers.py](../mod-privesc/parsers.py) | Registros de auditoría (hexadecimal, `msg='...'`, enriquecidos), líneas de syslog (snoopy en sus formatos habituales, sudo, su, pkexec, doas, pam, sshd), enmascaramiento de las líneas de comandos | del núcleo `masking`, `timeutil` | módulo |
| privesc: correlación | [mod-privesc/correlate.py](../mod-privesc/correlate.py) | Registros de auditoría por número de serie (EOE, registros de espacio de usuario, 2 s); líneas de syslog en el acto | — | módulo (colector) |
| privesc: comandos | [mod-privesc/commands.py](../mod-privesc/commands.py) | Tokens de reconocimiento, programa de una cuenta de servicio, shells, intérpretes, programas de descarga, puertas, compiladores; `SessionTracker` | `timeutil` del núcleo | módulo |
| privesc: superficie de ataque | [mod-privesc/surface.py](../mod-privesc/surface.py) | `SurfaceScanner` (setuid, setgid, capacidades), GTFOBins, archivos sensibles modificables, grupos privilegiados | — | módulo, doctor |
| privesc: doctor | [mod-privesc/doctor.py](../mod-privesc/doctor.py) | Describe auditd, su log y lo que han registrado sus reglas, syslog, snoopy, lo que ve el módulo, los archivos de la versión 1.0.0 y la superficie (correcciones: sólo paquetes y permiso de lectura); requisito `command_source` (cualquier fuente legible) | discovery, surface; `timeutil` del núcleo | módulo |
| privesc: reglas | [mod-privesc/rules/](../mod-privesc/rules/) | 35 reglas YAML | motor de reglas del núcleo | colector (`RulesEngine`), web (`fRules`) |
| privesc: tabla de severidades | [mod-privesc/severity.yaml](../mod-privesc/severity.yaml) | Severidades de las detecciones que construye el propio módulo (búsqueda, archivos sensibles) | — | módulo (`fLoadSeverityTable`) |
| privesc: textos | [mod-privesc/locales/](../mod-privesc/locales/) | Nombre, resumen, etiquetas y ayudas de los ajustes, opciones | — | web |
| Núcleo: interfaz | [backend/core/module.py](../../localSIEM/backend/core/module.py) | `Module`, `LineFramer` | registro | módulos |
| Núcleo: registro | [backend/core/registry.py](../../localSIEM/backend/core/registry.py) | Encontrar, comprobar y cargar módulos; valores por defecto y validación de los ajustes | `config` | colector, web, `manage.py`, `backend/core/catalog.py` |
| Núcleo: web | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) | Páginas de los módulos (Instalados, Instalables, la página de un módulo) y API | registro, catálogo, reglas | navegadores |
| Núcleo: catálogo | [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) | Descarga y descompresión segura del repositorio, lista con la acción de cada módulo (`install`, `update`, `incompatible`, `invalid`...) y `newer`, instalación o actualización atómica (`previous`, `access_changed`), desinstalación, comando para root: Módulos › Instalables y **Actualizar** / **Desinstalar** de Módulos › Instalados, la única forma de instalar módulos | registro | web |

<a id="symbols"></a>
## 3. Símbolos clave

| Símbolo | Archivo:línea | Qué hace |
|---|---|---|
| `ApacheModule` | [mod-apache2/module.py:68](../mod-apache2/module.py#L68) | El módulo apache2 (`vName = "apache2"`) |
| `fLoadSeverityTable` | [mod-apache2/module.py:54](../mod-apache2/module.py#L54) | `severity.yaml` por encima de los valores integrados |
| `ApacheModule.mDiscover` | [mod-apache2/module.py:95](../mod-apache2/module.py#L95) | Analiza la configuración: fuentes, logs omitidos, DocumentRoot |
| `ApacheModule.mThreshold` | [mod-apache2/module.py:105](../mod-apache2/module.py#L105) | Umbral de anomalía: ajuste, CRS o 5 |
| `ApacheModule.mParse` | [mod-apache2/module.py:136](../mod-apache2/module.py#L136) | Unidad a registro según el tipo de fuente |
| `ApacheModule.mBuildEvent` | [mod-apache2/module.py:176](../mod-apache2/module.py#L176) | Transacción a evento: campos, acción tomada, puntuaciones, detección |
| `ApacheModule.mVhostName` | [mod-apache2/module.py:311](../mod-apache2/module.py#L311) | Cabecera Host o hostname de ModSecurity al vhost que eligió Apache (lo que registra `%v`) |
| `ApacheModule.mAssess` | [mod-apache2/module.py:323](../mod-apache2/module.py#L323) | Severidad, nombre de regla, descripción y detalles de lo que va al SOC |
| `ApacheModule.mDetectionFromSignal` | [mod-apache2/module.py:385](../mod-apache2/module.py#L385) | Señal de una regla YAML a detección |
| `ApacheModule.mIsNewPhp` | [mod-apache2/module.py:414](../mod-apache2/module.py#L414) | Función de regla `apache2.new_php` |
| `ApacheModule.mEnrich` | [mod-apache2/module.py:442](../mod-apache2/module.py#L442) | Contexto de la IP (última hora) para la alerta |
| `ApacheModule.mHealth` | [mod-apache2/module.py:461](../mod-apache2/module.py#L461) | ModSecurity descargado o en Off; falta la IP real del cliente |
| `ApacheModule.mDisplayRecord` | [mod-apache2/module.py:538](../mod-apache2/module.py#L538) | Cabeceras y cuerpo para la ficha de la petición |
| `ApacheModule.mRequirements` | [mod-apache2/module.py:545](../mod-apache2/module.py#L545) | Apache y ModSecurity 2: lo que necesita el módulo para poder activarse |
| `ApacheConfig` | [mod-apache2/discovery.py:105](../mod-apache2/discovery.py#L105) | Analizador de la configuración de Apache |
| `ApacheConfig.mDirective` | [mod-apache2/discovery.py:228](../mod-apache2/discovery.py#L228) | Directivas leídas (logs, vhosts, módulos, ModSecurity) |
| `ApacheConfig.mVhostName` | [mod-apache2/discovery.py:358](../mod-apache2/discovery.py#L358) | Vhost de una petición a partir de su cabecera Host y de la dirección y el puerto locales, como lo elige Apache |
| `fSourceKey` / `fDiscoverSources` | [mod-apache2/discovery.py:403](../mod-apache2/discovery.py#L403) / [:408](../mod-apache2/discovery.py#L408) | Clave estable de una fuente; fuentes que leer y omitidas |
| `fRunDoctor` | [mod-apache2/doctor.py:46](../mod-apache2/doctor.py#L46) | Comprobación de requisitos `{id, status, title, detail, fix}` |
| `fCanPair` | [mod-apache2/doctor.py:26](../mod-apache2/doctor.py#L26) | Si un formato de acceso se puede unir sin `UNIQUE_ID` (IP del cliente, hora, línea de petición, estado) |
| `fRequirementChecks` | [mod-apache2/doctor.py:174](../mod-apache2/doctor.py#L174) | Las comprobaciones `apache_config` y `modsecurity` del doctor o, sin Apache, las dos como error, con el comando que los instala |
| `AccessFormat` / `dKnownFormats` | [mod-apache2/logformat.py:60](../mod-apache2/logformat.py#L60) / [:15](../mod-apache2/logformat.py#L15) | `LogFormat` a expresión regular; alias conocidos |
| `AccessParser` | [mod-apache2/parsers.py:59](../mod-apache2/parsers.py#L59) | Línea de access.log a registro |
| `fParseErrorLine` | [mod-apache2/parsers.py:147](../mod-apache2/parsers.py#L147) | Línea de error.log: ModSecurity, base de datos, PHP, caída |
| `AuditFramer` | [mod-apache2/parsers.py:233](../mod-apache2/parsers.py#L233) | Registros nativos de varias líneas; posición segura para confirmar |
| `fParseAuditRecord` / `fFinishAudit` | [mod-apache2/parsers.py:277](../mod-apache2/parsers.py#L277) / [:426](../mod-apache2/parsers.py#L426) | Registro de auditoría JSON o nativo; enmascaramiento, texto en bruto e indexado |
| `fAuditDisplay` / `fReadConcurrentEntry` | [mod-apache2/parsers.py:495](../mod-apache2/parsers.py#L495) / [:577](../mod-apache2/parsers.py#L577) | Ficha de un registro guardado; archivo de una entrada concurrente |
| `fParseMessage` / `fSummarize` | [mod-apache2/modsec.py:52](../mod-apache2/modsec.py#L52) / [:152](../mod-apache2/modsec.py#L152) | Un mensaje de ModSecurity; reglas, categorías, puntuación, umbral, interceptación |
| `Correlator` | [mod-apache2/correlate.py:57](../mod-apache2/correlate.py#L57) | `mAdd` ([:148](../mod-apache2/correlate.py#L148)), `mPair` ([:207](../mod-apache2/correlate.py#L207)), `mDue` ([:248](../mod-apache2/correlate.py#L248)), `mWaitsForAudit` ([:271](../mod-apache2/correlate.py#L271)), `mPendingCount` |
| `PrivescModule` | [mod-privesc/module.py:226](../mod-privesc/module.py#L226) | El módulo privesc (`vName = "privesc"`) |
| `PrivescModule.mBuildEvent` | [mod-privesc/module.py:341](../mod-privesc/module.py#L341) | Transacción a evento, según la fuente; `ignored`; se descartan los campos vacíos (`fCleanFields` conserva el 0) |
| `PrivescModule.mAnalyzeCommand` | [mod-privesc/module.py:366](../mod-privesc/module.py#L366) | Reconocimiento de la sesión, descarga ejecutada por una shell, compilación en `/tmp`, comandos recientes, programa nuevo de una cuenta de servicio |
| `PrivescModule.mAuditEvent` / `mAuditExec` / `mAuditUser` | [mod-privesc/module.py:427](../mod-privesc/module.py#L427) / [:587](../mod-privesc/module.py#L587) / [:661](../mod-privesc/module.py#L661) | Transacción de auditoría según el tipo; programas ejecutados (`suid_escape`, `root_without_door`, `parent_interpreter`, capacidades); inicios de sesión, puertas y fallos |
| `PrivescModule.mAuditSyscall` | [mod-privesc/module.py:509](../mod-privesc/module.py#L509) | Cualquier otra llamada al sistema según su nombre, sus argumentos y sus rutas: `denied`, `kmod`, `ptrace`, `chmod`, `file` (`sensitive_group`) o `syscall` |
| `fSyscallName` / `fSensitiveGroup` | [mod-privesc/module.py:184](../mod-privesc/module.py#L184) / [:210](../mod-privesc/module.py#L210) | Nombre de una llamada al sistema (nombre enriquecido, o número según la arquitectura); grupo de una ruta sensible (`lSensitivePaths`) |
| `PrivescModule.mSyslogEvent` | [mod-privesc/module.py:702](../mod-privesc/module.py#L702) | snoopy, sudo, su, pkexec, doas, inicios de sesión |
| `PrivescModule.mWriterAllowed` | [mod-privesc/module.py:412](../mod-privesc/module.py#L412) | Quien escribe un archivo sensible, o un antepasado conocido suyo, es una herramienta de cuentas o de paquetes |
| `PrivescModule.mDetectionFromSignal` / `mEnrich` | [mod-privesc/module.py:781](../mod-privesc/module.py#L781) / [:818](../mod-privesc/module.py#L818) | Señal de una regla a detección; contexto de la sesión para la alerta |
| `PrivescModule.mHealth` / `mSurfaceResult` | [mod-privesc/module.py:851](../mod-privesc/module.py#L851) / [:903](../mod-privesc/module.py#L903) | Sesiones guardadas, auditd detenido, archivos sensibles, búsqueda arrancada; programas setuid y capacidades nuevos |
| `fDiscoverSources` / `fReadState` / `fLegacyLeftovers` | [mod-privesc/discovery.py:291](../mod-privesc/discovery.py#L291) / [:160](../mod-privesc/discovery.py#L160) / [:175](../mod-privesc/discovery.py#L175) | Fuentes, fuentes omitidas e información para el doctor; si un log se puede leer; archivos que dejó la versión 1.0.0 |
| `fContainer` / `fAuditdPid` | [mod-privesc/discovery.py:54](../mod-privesc/discovery.py#L54) / [:96](../mod-privesc/discovery.py#L96) | Tipo de contenedor (sin root); pid de un auditd en marcha |
| `Accounts` | [mod-privesc/discovery.py:190](../mod-privesc/discovery.py#L190) | Nombres de los uid, grupos, `UID_MIN`, tipo de cuenta (`mAccountType`) |
| `fParseAuditLine` / `fParseSyslogLine` | [mod-privesc/parsers.py:83](../mod-privesc/parsers.py#L83) / [:316](../mod-privesc/parsers.py#L316) | Registros de las dos fuentes |
| `fMaskCommand` | [mod-privesc/parsers.py:45](../mod-privesc/parsers.py#L45) | Contraseñas de las líneas de comandos y, después, el enmascarador del núcleo |
| `Correlator` (privesc) | [mod-privesc/correlate.py:20](../mod-privesc/correlate.py#L20) | Registros de auditoría por número de serie; los demás, en el acto |
| `fReconToken` / `fProgramKey` / `fCommandArgs` | [mod-privesc/commands.py:115](../mod-privesc/commands.py#L115) / [:180](../mod-privesc/commands.py#L180) / [:91](../mod-privesc/commands.py#L91) | Token de reconocimiento de un comando; programa de una cuenta de servicio; palabras de un comando escrito |
| `SessionTracker` | [mod-privesc/commands.py:202](../mod-privesc/commands.py#L202) | Sesiones (inicio, IP, puerta, reconocimiento, últimos comandos), procesos, descargas; `mExport`/`mImport` |
| `SurfaceScanner` / `fCheckSensitiveFiles` | [mod-privesc/surface.py:167](../mod-privesc/surface.py#L167) / [:133](../mod-privesc/surface.py#L133) | Búsqueda de setuid, setgid y capacidades en un hilo; archivos sensibles modificables por otros |
| `fRunDoctor` / `fRequirementChecks` (privesc) | [mod-privesc/doctor.py:275](../mod-privesc/doctor.py#L275) / [:282](../mod-privesc/doctor.py#L282) | Comprobaciones del doctor (descripciones; correcciones sólo para paquetes y permiso de lectura); requisito `command_source`: cualquier fuente legible |
| `Module` / `LineFramer` | [backend/core/module.py:59](../../localSIEM/backend/core/module.py#L59) / [:48](../../localSIEM/backend/core/module.py#L48) | Interfaz de un módulo; una línea por unidad |
| `fReadManifest` | [backend/core/registry.py:133](../../localSIEM/backend/core/registry.py#L133) | Comprueba `module.json` y lee los textos |
| `fListManifests` / `fCreateModules` | [backend/core/registry.py:165](../../localSIEM/backend/core/registry.py#L165) / [:229](../../localSIEM/backend/core/registry.py#L229) | Los módulos instalados (`/opt/localsiem/modules/*`); instancias y errores |
| `fRegisterPackage` / `fLoadClass` | [backend/core/registry.py:185](../../localSIEM/backend/core/registry.py#L185) / [:197](../../localSIEM/backend/core/registry.py#L197) | Paquete de espacio de nombres `localsiem_modules`; importación y comprobaciones de la entrada |
| `fModuleSettings` / `fValidateSettings` | [backend/core/registry.py:250](../../localSIEM/backend/core/registry.py#L250) / [:317](../../localSIEM/backend/core/registry.py#L317) | Valores por defecto bajo los guardados; validación de lo que se guarda |
| `fSaveModule` | [backend/web/api_modules.py:290](../../localSIEM/backend/web/api_modules.py#L290) | `POST /api/admin/modules/{name}` |
| `fGetCatalog` / `fInstallFromCatalog` / `fUninstallModule` | [backend/web/api_modules.py:384](../../localSIEM/backend/web/api_modules.py#L384) / [:395](../../localSIEM/backend/web/api_modules.py#L395) / [:422](../../localSIEM/backend/web/api_modules.py#L422) | `GET /api/admin/module-catalog`; `POST /api/admin/module-catalog/{name}` (instala o actualiza; una primera instalación sin sus requisitos queda desactivada: `fFirstInstallation`); `DELETE /api/admin/modules/{name}` |
| `fInstall` / `fCatalog` | [backend/core/catalog.py:235](../../localSIEM/backend/core/catalog.py#L235) / [:171](../../localSIEM/backend/core/catalog.py#L171) | Instala o actualiza un módulo junto a la copia instalada y las intercambia con un renombrado (`previous`, `access_changed`); los módulos del repositorio con `installed`, `newer` y su acción |
| `fRemove` / `fRootCommand` | [backend/core/catalog.py:302](../../localSIEM/backend/core/catalog.py#L302) / [:372](../../localSIEM/backend/core/catalog.py#L372) | Desinstala un módulo (renombrado y borrado); el comando para root (`manage.py setup-modules`) |
| `fCatalogPanel` / `fUpdateNotice` / `fUpdate` | [frontend/assets/modules.js:218](../../localSIEM/frontend/assets/modules.js#L218) / [:417](../../localSIEM/frontend/assets/modules.js#L417) / [:452](../../localSIEM/frontend/assets/modules.js#L452) | Sección Instalables (sólo los módulos no instalados, **Instalar** y su cuadro de diálogo); aviso de una versión más reciente en una fila de Instalados; **Actualizar** (confirmación, el mismo `POST`, un cuadro de diálogo sólo con `access_changed` o cuando el colector no responde) |

<a id="flows"></a>
## 4. Flujos principales de llamadas

**Arranque del colector → registro → ApacheModule**

`Collector.mSetup` → `fCreateModules` → `fListManifests` (`/opt/localsiem/modules/*`) → `fReadManifest` (id = carpeta, entrada, ajustes, `core` ≤ `cVersion`, `fReadTexts`) → `fCreateModule` → `fLoadClass` (`fRegisterPackage`, `import localsiem_modules.apache2.module`, subclase de `Module`, `vName == id`) → `ApacheModule(dSettings, vMasker, vStorage, dManifest)` → `mStart` → `mCreateCorrelator` → `Collector.mLoadRules` (`mRulesPath`, `mRuleFunctions`, ajustes `rules.<id>` → `RulesEngine.mLoad`) → `Collector.mDiscover` (`mEnabled` → `mDiscover` → `ApacheConfig.mParse` → `fDiscoverSources`; un `FileTailer` y `mCreateFramer` por fuente) → los registros pendientes vuelven al correlador → `mPublishDoctor` (`mDoctor` → `fRunDoctor` → estado `apache2.doctor`).

**Una línea leída → detecciones**

1. `Collector.mReadSources` → `FileTailer.mPoll` → troceador `mFeed` (`LineFramer`, o `AuditFramer`, cuyo `mSafeCommit` deja la posición antes de un registro sin terminar) → `ApacheModule.mParse` (`AccessParser.mParse`, `fParseErrorLine`, o `fReadConcurrentEntry` + `fParseAuditRecord` y `mObserveAudit`) → registros y posiciones guardados en una sola transacción → `Correlator.mAdd`.
2. `Collector.mProcessDue` → `Correlator.mDue(pWatermark=...)` → `ApacheModule.mBuildEvent` (`fSummarize`, acción tomada, `mAssess`, `mPathFirstSeen` para `.php` con 2xx) → `RulesEngine.mEvaluate` (reglas YAML; `{function: apache2.new_php}` → `mIsNewPhp`) → `mSaveEvents` → `mDetect` por cada detección y `mDetectionFromSignal` por cada señal → `Grouper.mAdd`.
3. `Collector.mProcessGroups` → `ApacheModule.mEnrich` (`mGetIpContext`) → `fBuildAlert` → cola del SOC.

**El administrador guarda los ajustes → recarga del colector**

`modules.js fBuildSettings` (envío) → `POST /api/admin/modules/apache2` `{settings}` → `fSaveModule` → `fValidateSettings` (422 `invalid_setting:<key>` o `<key>.<field>`) → `fSaveSettings` (`settings.json`, `modules.apache2`) → `WebContext.mApplySettings` → socket del colector `{"command": "reload"}` → `Collector.mHandleIpc` → `Collector.mCycle` → `mReloadSettings` (`ApacheModule.mReload`, `mLoadRules`, `mDiscover`, `mPublishDoctor`, `mPublishState`). El interruptor envía `{enabled}` por el mismo camino (al activarlo: 422 `requirements_missing` mientras falte un requisito del módulo) y la tabla de reglas envía `{rules}` (`fCleanRules` → `rules.<id>`: `enabled`, `severity`, `threshold` o `first_threshold`, `window`). Si el socket no responde, el colector detecta igualmente el nuevo `settings.json` en su siguiente ciclo.

**Instalar un módulo desde la web** (la única forma de instalar módulos)

`modules.js fCatalogPanel` (Módulos › Instalables) → **Consultar el repositorio** → `GET /api/admin/module-catalog` (`fGetCatalog` → `fFetchCatalog` → `fDownload` → `fCatalog`: cada carpeta `mod-<nombre>/` del repositorio, con `installed`, `newer` y `action`) → sólo se listan los elementos con `installed` nulo → **Requisitos** (`fShowRequirements` → `fRequirementsBody`: el `install_requirements` del módulo para el sistema del servidor, `system` de la respuesta, como root y con `sudo`, y las notas `install_requirements.*` de sus textos; no se ejecuta nada) → **Instalar** → `POST /api/admin/module-catalog/{name}` (`fInstallFromCatalog` → `fFetchAndInstall` → `InstallLock` → `fDownload` → `fInstall`: `mod-apache2/` → `/opt/localsiem/modules/apache2/`, `previous` nulo, `access_changed` verdadero) → `WebContext.mReloadModules` → `fFirstInstallation` (falta un requisito y `modules.<nombre>.enabled` nunca se guardó: `enabled = false`) → `restart` del colector → `fCreateModules` carga el módulo → el cuadro de diálogo «<módulo> instalado» muestra el comando para root (`fRootCommand`: `manage.py setup-modules`, permiso de lectura sobre los `read_paths`) o, si falta un requisito, las comprobaciones que no se cumplen.

**Actualizar un módulo desde la web**

Se abre Módulos › Instalados → `fCheckRepository` → `fFetchCatalog(false)` de `modules.js` (la última respuesta de `GET /api/admin/module-catalog`, reutilizada durante 600 s; instalar, actualizar o desinstalar un módulo la olvida) → elementos con `newer` y `action` `update` o `incompatible` → `fUpdateNotice` en la fila (sólo mientras la versión instalada sea la comparada) → **Actualizar** → `fUpdate` → confirmación → `POST /api/admin/module-catalog/{name}` (el mismo `fInstallFromCatalog` → `fInstall`: la copia nueva sustituye a la instalada, `previous` es la versión anterior y `access_changed` indica si cambiaron los `read_paths`; sin `fFirstInstallation`, así que `enabled` y los ajustes se mantienen) → `restart` del colector → un cuadro de diálogo sólo si `access_changed` (el comando para root) o si el colector no respondió.

**Desinstalar un módulo desde la web**

**Desinstalar** (fila de Módulos › Instalados o página del módulo) → `fUninstallButton` → confirmación → `DELETE /api/admin/modules/{name}` (`fUninstallModule` → `fRemove` → `InstallLock` → renombrado de `/opt/localsiem/modules/<nombre>/` a una carpeta temporal, donde se borra) → `WebContext.mReloadModules` → `restart` del colector. `modules.<nombre>` y los ajustes de sus reglas se quedan en `settings.json`, y el permiso de lectura que dio root se mantiene.

**Primera instalación sin Apache o sin ModSecurity → Reconfigurar** (localSIEM 2.2.0 o posterior)

Instalar en la web → `fInstall` (primera instalación) → el módulo creado desde la copia instalada (almacenamiento `None`) → `ApacheModule.mRequirements` → `ApacheConfig.mParse` → `fRequirementChecks` (con Apache: `fRunDoctor` → `apache_config`, `modsecurity`; sin él, las dos como error) → un error y `modules.apache2.enabled` nunca guardado → `modules.apache2.enabled = false` («Desactivado», interruptor bloqueado, requisitos en la página). Más tarde, con Apache y ModSecurity instalados: **Reconfigurar** → `POST /api/admin/modules/apache2/reconfigure` → `mRequirements` → se cumplen → interruptor desbloqueado y el comando de root (acceso de lectura a los `read_paths`; apache2 no tiene `setup_option`) → el administrador activa el módulo → recarga del colector → `mDiscover` → `mPublishDoctor`.

**Ficha de la petición y doctor desde la web**

`GET /api/events/{id}` → `fEvent` → `WebContext.mModule("apache2")` → `mDisplayRecord` → `fAuditDisplay`. **Descubrir de nuevo y pasar el doctor** → `POST /api/admin/modules/apache2/doctor` → colector `{"command": "doctor"}` → `mDiscover` + `mPublishDoctor`.

**Salud**

`Collector.mCycle` (cada 60 s) → `mCheckHealth` → `ApacheModule.mHealth` (como mucho cada 300 s; `ApacheConfig.mParse`, `mCountRecentEvents`) → `fHealthDetection` → `mDetect`.

**privesc: un comando ejecutado → detecciones**

1. auditd escribe `SYSCALL`, `EXECVE`, `CWD`, `PATH`, `PROCTITLE` y `EOE` con un mismo número de serie → `FileTailer.mPoll` → `LineFramer` → `PrivescModule.mParse` → `fParseAuditLine` (hexadecimal decodificado, `fMaskCommand`, texto en bruto reconstruido) → `Correlator.mAdd` (clave `audit:<time>:<serial>`, vence con `EOE`).
2. `Correlator.mDue` → `PrivescModule.mBuildEvent` → `mAuditEvent` → `mAuditExec` (`suid_escape`, `BPRM_FCAPS`, `root_without_door` a partir de `SessionTracker.mGet`, `mRememberProcess`) → `mAnalyzeCommand` (`fReconToken` → `SessionTracker.mRecon` → `recon_burst`/`recon_massive`; `cDownloadOnelinerRegex`, `mDownload`/`mRecentDownload`; `fCompileInTemporary`; `mCommand`; cuenta de servicio: `fProgramKey` → `mPathFirstSeen` → `new_program`) → `fCleanFields`.
3. `RulesEngine.mEvaluate` (reglas de `mod-privesc/rules/`) → `PrivescModule.mDetectionFromSignal` → `Grouper.mAdd` → `Collector.mProcessGroups` → `PrivescModule.mEnrich` (sesión: últimos 20 comandos) → `fBuildAlert` → cola del SOC.

Con snoopy, el mismo comando llega también como línea de syslog: `fParseSyslogLine` → `fParseSyslogMessage` → `mSyslogEvent` → `mAnalyzeCommand` (sesión `snoopy:<uid>:<sid>`).

**privesc: sesiones y puertas**

`LOGIN` (auid y ses asignados) o `USER_LOGIN`/`USER_START` de sshd o de login → `mAuditUser` → `SessionTracker.mStart` (usuario, dirección SSH). `USER_START`/`USER_CMD` con resultado success de sudo, su, pkexec, doas, run0 o systemd → `SessionTracker.mDoor`. Un `EXECVE` posterior de esa sesión con uid y euid 0 → `root_without_door` sólo si se vio el inicio y no hubo puerta. `mHealth` guarda `SessionTracker.mExport` en `privesc.sessions` como mucho una vez por minuto; `mStart` lo carga (`mImport`).

**privesc: una llamada al sistema registrada por las reglas de auditoría del servidor**

auditd escribe `SYSCALL` (con `arch`, `syscall`, `a0`-`a3`, `success`, `exit` y la clave de la regla que lo registró, sea cual sea), `CWD`, `PATH`... → `fParseAuditLine` → `Correlator` → `mAuditEvent` → `mAuditSyscall`: `fSyscallName` → open/exec/truncate fallidos con `EACCES`/`EPERM` y un uid de inicio de sesión → `denied`; `init_module`/`finit_module`/`delete_module` → `kmod`; `ptrace` → `ptrace`; `chmod`/`fchmod`/`fchmodat`/`fchmodat2` con `S_ISUID`/`S_ISGID` en el modo, no sobre una carpeta → `chmod` (`mWriterAllowed`); un cambio (una llamada de `sChangeSyscalls`, un open con indicadores de escritura, un `PATH` con `CREATE`/`DELETE`) de una ruta de `lSensitivePaths` → `file` con `sensitive_group` (`dKeyHints` sólo sin una ruta que se pueda resolver) y `mWriterAllowed`; cualquier otra cosa → `syscall`. `mBuildEvent` recuerda la hora de cada tipo (`dRuntime["audit_kinds"]`) para el doctor.

**privesc: búsqueda en la superficie de ataque**

`mHealth` (cada 300 s, cinco minutos después del arranque, cada `surface_scan_hours`) → `SurfaceScanner.mStart` (hilo: `os.walk` de `scan_paths`, `os.lstat`, `os.getxattr("security.capability")` → `fCapabilities`) → siguiente `mHealth` → `mSurfaceResult` (`SurfaceScanner.mTake`, frente a `privesc.surface`: setuid/setgid nuevos → `new_setuid*`, capacidades nuevas → `new_capabilities`) → `mModuleDetection` → `mDetect`; el resultado se guarda en `privesc.surface` y lo muestra `fSurfaceChecks`. Cada hora, `fCheckSensitiveFiles` → `sensitive_file_writable`.

**privesc: requisitos y Reconfigurar**

`fInstall` (primera instalación) o **Reconfigurar** → `PrivescModule.mRequirements` → `fRequirementChecks(mModuleSettings())` (`fContainer`, `fAuditdPid`, `fAuditLogPath` → `fReadState`; `fSyslogPath` → `fReadState` salvo que `syslog_mode` sea `never`; `fSnoopyInstalled`) → una fuente legible: `command_source` correcto (las que no se pueden leer, como avisos); una fuente que existe pero no se puede leer: error en `audit_log` o `syslog` con el permiso de lectura (`manage.py setup-modules` o `setfacl`); nada: error en `command_source` con el paquete que hay que instalar. El módulo sigue desactivado mientras haya un error.

<a id="routes"></a>
## 5. Puntos de entrada

| Punto de entrada | Manejador | Archivo |
|---|---|---|
| `"entry": "module:ApacheModule"` de `module.json` | `ApacheModule` | [mod-apache2/module.py](../mod-apache2/module.py) |
| `mod-apache2/rules/*.yaml` | `RulesEngine` (núcleo) | [mod-apache2/rules/](../mod-apache2/rules/) |
| Función de regla `apache2.new_php` | `ApacheModule.mIsNewPhp` | [mod-apache2/module.py](../mod-apache2/module.py) |
| Web: Módulos › Instalables, la única forma de instalar módulos (`GET /api/admin/module-catalog`, `POST /api/admin/module-catalog/{name}`) | `fGetCatalog`, `fInstallFromCatalog`; vista `fCatalogPanel` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| Web: **Actualizar** en una fila de Módulos › Instalados (el mismo `GET`, que el navegador reutiliza durante 10 minutos, y el mismo `POST`) | `fCheckRepository`, `fUpdateNotice`, `fUpdate` → `fInstallFromCatalog` | [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js), [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| Web: **Desinstalar** (`DELETE /api/admin/modules/{name}`) | `fUninstallModule` → `fRemove` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `read_paths` de `module.json` | `manage.py read-paths`: las carpetas que localSIEM permite leer a `localsiem`, como root (el comando de `fRootCommand`) | [backend/manage.py](../../localSIEM/backend/manage.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `manage.py modules` | `fMain` (`fModules`) | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py doctor [--json]` | `mDiscover`, `mSkipped`, `mDoctor` | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py read-paths` | `read_paths` de cada manifiesto | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `/user/dashboard/modules/`; `/admin/dashboard/modules/` (302 a `installed/`), `/admin/dashboard/modules/installed/`, `/admin/dashboard/modules/installable/` | `fUserTab` / `fAdminTab` / `fAdminModulesSection`; vista `LocalsiemViews.modules` | [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| `/admin/dashboard/modules/installed/apache2/` (la anterior, `/admin/dashboard/modules/apache2/`, responde con un 301 hacia ella) | `fAdminModule` (el 301: `fAdminModulesSection`); vista `LocalsiemViews.module` | los mismos archivos |
| `GET /api/modules` | `fModules` (estado para cualquier usuario con sesión iniciada) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `GET /api/admin/modules/apache2` | `fModule` (ajustes, valores, fuentes, doctor, reglas) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2` | `fSaveModule` (`enabled`, `settings`, `rules`) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/doctor` | `fRunDoctor` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/reconfigure` (**Reconfigurar**, localSIEM 2.2.0 o posterior) | `mRequirements` → `fRequirementChecks` | [mod-apache2/module.py](../mod-apache2/module.py), [mod-apache2/doctor.py](../mod-apache2/doctor.py) |
| `GET /api/events/{id}` | `fEvent` → `mDisplayRecord` | [backend/web/api_search.py](../../localSIEM/backend/web/api_search.py) |
| `"entry": "module:PrivescModule"` de `mod-privesc/module.json` | `PrivescModule` | [mod-privesc/module.py](../mod-privesc/module.py) |
| `mod-privesc/rules/*.yaml` | `RulesEngine` (núcleo) | [mod-privesc/rules/](../mod-privesc/rules/) |
| `/admin/dashboard/modules/installed/privesc/`, `GET`/`POST /api/admin/modules/privesc`, `.../privesc/doctor`, `.../privesc/reconfigure` | `fAdminModule`, `fModule`, `fSaveModule`, `fRunDoctor`, `mRequirements` → `fRequirementChecks` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [mod-privesc/doctor.py](../mod-privesc/doctor.py) |
| Registros de auditoría de las reglas del servidor (cualquier clave) | `mAuditEvent` → `mAuditExec`, `mAuditUser`, `mAuditSyscall` | [mod-privesc/module.py](../mod-privesc/module.py) |

<a id="impact"></a>
## 6. Análisis de impacto

| Componente | Qué se ve afectado si cambia |
|---|---|
| `id` de `module.json` | Debe coincidir con el nombre de la carpeta sin `mod-` (el nombre de la carpeta instalada) y con `vName`. Es la clave de los ajustes (`modules.<id>`), del estado (`<id>.doctor`) y el `module` de cada evento: renombrarlo pierde los ajustes guardados y parte el histórico en dos. |
| `core` de `module.json` | Subirlo por encima del localSIEM instalado impide que el módulo se cargue (estado «Error»); en el repositorio, Instalables muestra «Necesita localSIEM X o posterior» e Instalados muestra la versión más reciente sin **Actualizar**. |
| `entry` de `module.json` | Debe apuntar a una subclase de `Module`; un valor incorrecto es un error de carga. |
| `default_enabled` de `module.json` | Activación en los servidores donde el administrador nunca decidió (si en la primera instalación faltan sus requisitos, desactivado). |
| `read_paths` de `module.json` | El permiso de lectura que da localSIEM como root (`manage.py read-paths`): una carpeta que falte significa errores de permisos en el doctor y en el estado. Un cambio en una versión nueva hace que la web vuelva a mostrar el comando para root después de **Actualizar** (`access_changed`). |
| `install_requirements` de `module.json` | El diálogo Requisitos de Instalables (`fRequirementsBody` de `modules.js`). Uno incorrecto (un sistema que no sea `debian` ni `alpine`, una lista vacía o de más de 20 comandos, un comando con un operador de la shell o un salto de línea) hace que el módulo no sea válido (`fCheckInstallRequirements` del núcleo): ni se instala ni se carga. |
| `setup_option` de `module.json` | Nada: el núcleo la ignora (ningún módulo la tiene desde apache2 1.3.0 y privesc 1.1.0). |
| Carpetas `mod-<nombre>/` con un `module.json` en la raíz del repositorio | Lo que lista el catálogo de la web, como el módulo `<nombre>`: Instalables muestra los que todavía no están instalados (uno que necesita un núcleo más reciente, como «Necesita localSIEM X o posterior»; uno no válido, como «El módulo del repositorio no es válido»), y una `version` mayor que la instalada hace que Instalados ofrezca **Actualizar**. |
| `settings` de `module.json` | El formulario, la validación y los valores por defecto. Un nuevo valor por defecto se aplica en los servidores que nunca guardaron esa clave. Los valores guardados no se migran: una clave renombrada pierde su valor, y un valor antiguo con un tipo nuevo llega al módulo tal como se guardó. |
| `locales/*.json` | Sólo los textos de la web; un texto que falte recurre a en-US y después a la clave. |
| `parsers.py` (diccionario de registro) | La correlación (`correlation`, `fields.client_ip`, `fields.path`), la ficha de la petición, el índice de texto completo (`search`, `raw`), la salud de líneas sin analizar y la privacidad. |
| `dKnownFormats` de `logformat.py` | El análisis de todos los logs de acceso; `localsiem_combined` sigue ahí para los servidores que ya lo escriben (lo añadían las versiones 1.2.0 y anteriores del módulo): no cambies su definición. |
| `correlate.py` | Un evento por petición; el núcleo llama a `mAdd`, `mDue(pNow, pForce, pWatermark)` y `mPendingCount`, y le devuelve los registros que seguían pendientes tras un reinicio. Sin `UNIQUE_ID` empareja los registros por sus campos `client_ip`, `method`, `uri`, `status` y `path`: un parser que los escriba de otra forma rompe el emparejamiento. La espera del registro de auditoría (`mWaitsForAudit`) necesita el campo `modsecurity` de las líneas del error.log y los registros de la fuente `audit`. |
| `modsec.py` (categorías, etiquetas, rangos) | Los nombres de regla de las alertas (las estadísticas del SOC agrupan por ellos: mantenlos estables), las claves de agrupación, las búsquedas `category:`. |
| `ApacheModule.mBuildEvent` (diccionario de evento) | Las columnas de la tabla de eventos, los campos que leen las reglas YAML (`action`, `status`, `method`, `path`, `crs_matched`, `db_error`...), las búsquedas y la exportación CSV. |
| `ApacheModule.mAssess` | Lo que llega al SOC y su severidad; los límites de `GenericAlert` del núcleo (regla 300, descripción 10 000 caracteres). |
| `severity.yaml` | La severidad de cada detección de ModSecurity; la severidad forma parte de la clave de agrupación, así que un cambio empieza grupos nuevos. |
| `rules/*.yaml` | El `id` es la clave de los ajustes de la regla (`rules.<id>`) y de las búsquedas (`rule:localsiem:<id>`): mantenlo estable. Los campos deben existir en los eventos; `{function: ...}` necesita `mRuleFunctions`. |
| `discovery.py` | Qué logs se leen; `fSourceKey` es la clave de las posiciones guardadas (una clave nueva convierte el archivo en una fuente nueva, sin su posición guardada); los DocumentRoot de la regla de web shell; el doctor. |
| `doctor.py` | El doctor de la web y de `manage.py` y las indicaciones que se muestran al cliente. Sólo las comprobaciones de lo que no es un log (ModSecurity, el CRS, `SecRuleEngine`, `mod_unique_id`, los permisos) pueden llevar `fix`; las de los logs sólo los describen. |
| `mRequirements` / `fRequirementChecks` | Si el módulo se puede activar, el estado «Desactivado» después de una primera instalación sin Apache o sin ModSecurity, los requisitos que muestra la web y **Reconfigurar**. Se ejecutan en la web y en `manage.py` sin almacenamiento y leen la configuración de Apache en cada llamada: mantenlos lejos del almacenamiento y de cualquier cosa lenta, y mantén estables los ids `apache_config` y `modsecurity`. |
| privesc: columnas y campos del evento (`mBuildEvent`, `mAnalyzeCommand`) | Las reglas YAML los comprueban por su nombre (`recon_burst`, `suid_escape`, `root_without_door`, `sensitive_group`, `writer_allowed`, `ptrace_attach`, `parent_interpreter`, `account_type`, `real_uid`, `argc_zero`...): un campo renombrado desactiva en silencio las reglas que lo usan. `vhost` es el usuario: de él dependen la clave de agrupación de las alertas y las búsquedas `vhost:`. |
| privesc: `fReconToken` | Qué cuenta como reconocimiento y cómo se distinguen los comandos distintos: cambiar un token cambia lo rápido que una sesión alcanza los umbrales. |
| privesc: `SessionTracker` y las puertas (`sDoors`) | `root_without_door`: una puerta que falte en la lista convierte en críticas sesiones de root legítimas; una de más oculta exploits del kernel. `mExport`/`mImport` es el formato de `privesc.sessions`. |
| privesc: `parsers.py` | Los campos de los registros (`args`, `command`, `kind`, el `uid`/`euid` de snoopy), el enmascaramiento de las contraseñas y el texto en bruto de los registros de auditoría; los formatos de snoopy que lee (el módulo nunca cambia `snoopy.ini`). |
| privesc: clasificación de los registros de auditoría (`lSensitivePaths`, `dSyscallTables`, `sChangeSyscalls`, `dOpenFlagArgument`, `dChmodModeArgument`, `sDeniedSyscalls`, `dKeyHints`) | Lo que se convierte en `file`, `chmod`, `kmod`, `ptrace` y `denied`, y por tanto las reglas sensitive-file, persistence-file, monitoring-changed, suid-set, kernel-module, ptrace, denied-burst y sensitive-denied; un número de llamada al sistema equivocado clasifica mal los registros de esa arquitectura. |
| privesc: `surface.py` | El coste de la búsqueda (hilo, límites) y lo que notifican el doctor y `mSurfaceResult`; `privesc.surface` es su referencia. |
| privesc: `mRequirements` / `fRequirementChecks` | Si el módulo se puede activar (cualquier fuente legible), el estado «Desactivado» después de una primera instalación cuyos logs `localsiem` todavía no puede leer, y **Reconfigurar**; la web y `manage.py` los llaman sin almacenamiento: mantenlos rápidos y sin root. Mantén los ids `command_source`, `audit_log` y `syslog`. |
| Interfaz del núcleo (`backend/core/module.py`, `registry.py` de localSIEM) | Todos los módulos: una firma de método cambiada, una nueva clave obligatoria del manifiesto o un nuevo contrato de registros y eventos los rompe; sube `core` en su `module.json` cuando necesiten el nuevo localSIEM. |

<a id="extensions"></a>
## 7. Puntos de extensión

### Cómo escribir un módulo nuevo

1. **Carpeta**: crea `mod-<nombre>/` en la raíz de este proyecto; `<nombre>`, el nombre del módulo, cumple `[a-z][a-z0-9_]{1,31}`. El prefijo `mod-` es sólo de la carpeta: `module.json`, la clase, las opciones y los textos usan `<nombre>`. Sin `__init__.py`.
2. **`module.json`**, por ejemplo:

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

3. **Textos**: `locales/<idioma>.json` para cada uno de los 15 idiomas de localSIEM con `name`, `summary` y la etiqueta y la ayuda de cada ajuste. Las notas sobre los requisitos van en `install_requirements` (`note`, para todos los sistemas, y `debian` y `alpine`), que muestra el diálogo Requisitos.
4. **Código**: `module.py` con una subclase de `Module` cuyo `vName` sea el id. Debe implementar `mParse`, `mCreateCorrelator` y `mBuildEvent`, y normalmente `mDiscover`; los demás métodos son opcionales (sección 1). Importa sus propios archivos de forma relativa y el núcleo como `backend.core...`. Los dos módulos de este repositorio son ejemplos completos ([mod-apache2/module.py](../mod-apache2/module.py), [mod-privesc/module.py](../mod-privesc/module.py)); un esbozo mínimo:

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

5. **Acción tomada**: decide qué significa «ya resuelto» para el servicio (por ejemplo, una IP ya baneada) y pon `action` a `blocked` en ese caso; añade una detección únicamente a los eventos sin acción tomada.
6. **Reglas**: archivos YAML en `mod-<nombre>/rules/`, que devuelve `mRulesPath`, y las funciones a las que llaman en `mRuleFunctions`.
7. **Requisitos**: si el módulo necesita software en el servidor (como apache2 necesita Apache y ModSecurity 2), devuelve desde `mRequirements()` una comprobación por requisito (el formato de `fCheck`: `status` `ok` o `error`, y en `fix` el comando que lo instala) y nunca instales ese software desde el módulo: sin sus requisitos, el módulo se instala desactivado. Se ejecuta sin almacenamiento, también en la web y en `manage.py`. Declara también, en `install_requirements` de `module.json`, los comandos que instalan ese software en Debian y en Alpine (un comando por línea, sin operadores de la shell): la web los muestra en Módulos › Instalables › Requisitos, tal cual y con `sudo` delante, antes de instalar el módulo.
8. **Instalación**: publícalo en este repositorio (rama `main`); aparece en Módulos › Instalables de la web de localSIEM mientras no esté instalado, e **Instalar** copia la carpeta `mod-<nombre>/` a `/opt/localsiem/modules/<nombre>/` y reinicia el colector. El permiso de lectura sobre sus `read_paths` requiere root: la web muestra el comando (`manage.py setup-modules`). Un módulo no tiene opción de configuración: nunca instala nada ni cambia nada fuera de `/opt/localsiem`, y nunca escribe en los logs del cliente, ni los rota o borra, ni cambia su formato; si un servidor escribe sus logs a su manera, el que se adapta es el módulo, y lo que le falta al servidor es un requisito. Para publicar una versión nueva, sube `version`: Módulos › Instalados muestra el aviso y **Actualizar**, que conserva los ajustes y la activación del módulo y sólo vuelve a mostrar el comando para root si cambiaron los `read_paths`.
9. **Documentación**: actualiza el README, este CODE y el MANUAL en los 15 idiomas.

### Cómo añadir una regla al módulo apache2

Crea un archivo YAML en [mod-apache2/rules/](../mod-apache2/rules/) (todas las claves y operadores se describen al principio de [backend/core/rules.py](../../localSIEM/backend/core/rules.py)): `id`, `name`, `category`, `type`, `severity`, `kind` (`match`, `threshold` o `sequence`), las condiciones (`when`, o `first`/`first_threshold`/`then`), `by`, `window`, `threshold`, `lists`, `description` y `search`. Los campos se buscan primero en las columnas del evento y después en `fields`. Aparece en la tabla de reglas de la página del módulo y el colector la carga cuando se instala la versión nueva del módulo: sube `version` en `module.json`, publícalo y pulsa **Actualizar** en Módulos › Instalados.

### Cómo añadir un ajuste al módulo apache2

Añádelo a `settings` de [mod-apache2/module.json](../mod-apache2/module.json) con su tipo y su valor por defecto, añade su `label` y su `help` a los cuatro archivos de [mod-apache2/locales/](../mod-apache2/locales/) y léelo con `self.mModuleSettings().get("<key>")`. El formulario, la validación y la recarga los pone el núcleo.

### Cómo añadir una comprobación al doctor o cambiar una severidad

Una comprobación es un `fCheck(id, status, title, detail, fix)` dentro de `fRunDoctor` ([mod-apache2/doctor.py](../mod-apache2/doctor.py)); mantén estable el `id` y pon en `fix` el fragmento o el comando exactos, sólo para los requisitos que no son logs: una comprobación sobre los logs del cliente sólo los describe, junto con lo que localSIEM puede o no puede leer de ellos, sin `fix`. Las severidades de las detecciones de ModSecurity se cambian en [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) (`low`, `medium`, `high`, `critical`).

### Cómo añadir una regla al módulo privesc

Crea un archivo YAML en [mod-privesc/rules/](../mod-privesc/rules/), como los de Apache. Comprueba las columnas (`method`, `uri`, `path`, `vhost`, `action`) y los campos de los eventos (`sensitive_group`, `account_type`, `real_uid`, `recon`, `service_account`, `file`...), nunca la clave de una regla de auditoría; añade `ignored: {not: true}` para que los usuarios ignorados nunca la disparen, y `action: none` cuando sólo cuente lo que de verdad se ejecutó. Si la condición necesita estado o lógica (una secuencia de la misma sesión, una comprobación de un archivo), calcula un indicador en `PrivescModule.mAnalyzeCommand` (todas las fuentes) o en `mAuditExec`/`mAuditSyscall`/`mSyslogEvent` (una sola fuente) y compruébalo desde la regla.

### Cómo añadir un comando de reconocimiento, una herramienta o un exploit al módulo privesc

- Reconocimiento: añade el programa a `sReconSimple`, o una rama a `fReconToken` que devuelva un token por tipo de pregunta ([mod-privesc/commands.py](../mod-privesc/commands.py)). Un token que cambia con cada argumento infla los recuentos.
- Herramientas y exploits: añade una expresión regular a la lista de [rules/known-tool.yaml](../mod-privesc/rules/known-tool.yaml) o de [rules/exploit.yaml](../mod-privesc/rules/exploit.yaml) (sin distinguir mayúsculas de minúsculas, comparada con la línea de comandos); el administrador también puede añadirlas desde los ajustes (`rules.<id>.lists`).

### Cómo añadir una fuente o un tipo de registro de auditoría al módulo privesc

- Una ruta sensible: añádela a `lSensitivePaths` de [mod-privesc/module.py](../mod-privesc/module.py) con su grupo (o con un grupo nuevo y una regla que compruebe `sensitive_group`). Un tipo de llamada al sistema: añade su nombre a los conjuntos de `mAuditSyscall` y su número a cada tabla de `dSyscallTables`. Nunca dependas de la clave de una regla de auditoría (como mucho, añádela a `dKeyHints`) y nunca instales reglas de auditoría: el servidor registra lo que decide su administrador, y el doctor lo describe (`dAuditKinds` de [doctor.py](../mod-privesc/doctor.py)).
- Una fuente: devuélvela desde `fDiscoverSources` con un `kind` nuevo, analízala en `mParse` y construye sus eventos en `mBuildEvent` con las mismas columnas y campos que las demás, para que las reglas funcionen sin cambios.
