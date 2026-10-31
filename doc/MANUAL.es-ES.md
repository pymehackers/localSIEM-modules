# Manual de uso de localSIEM-modules

Este MANUAL también está disponible en:\
[en-GB](MANUAL.en-GB.md), [en-US](MANUAL.md), [es-AR](MANUAL.es-AR.md), es-ES

[Instalación](README.es-ES.md) · [Referencia técnica](CODE.es-ES.md) · [Manual de localSIEM](../../localSIEM/doc/MANUAL.es-ES.md)

## Contenido

1. [Qué son los módulos](#what)
2. [Instalar y actualizar los módulos](#installation)
3. [La página de Módulos](#modules-page)
4. [La página del módulo Apache](#apache-page)
5. [Ajustes del módulo Apache](#settings)
6. [Qué envía al SOC el módulo Apache](#soc)
7. [Requisitos de Apache y ModSecurity: el doctor](#doctor)
8. [Aplicar los requisitos: --configure-apache](#configure-apache)
9. [Reglas del módulo Apache](#rules)
10. [Avisos de salud del módulo Apache](#health)
11. [El módulo de escalada de privilegios](#privesc)
12. [Ajustes del módulo de escalada de privilegios](#privesc-settings)
13. [Qué envía al SOC el módulo de escalada de privilegios: sus reglas](#privesc-rules)
14. [Requisitos del módulo de escalada de privilegios: el doctor](#privesc-doctor)
15. [Aplicar los requisitos: --configure-privesc](#configure-privesc)
16. [Superficie de ataque y avisos de salud del módulo de escalada de privilegios](#privesc-health)
17. [Línea de comandos](#cli)

<a id="what"></a>
## 1. Qué son los módulos

localSIEM se compone de un **núcleo** y de **módulos**. El núcleo guarda los eventos, busca en ellos, ejecuta las reglas, agrupa las alertas, las envía al SOC y vigila su propia salud. Cada módulo añade un servicio del servidor: encuentra sus logs, los lee, los convierte en eventos, decide qué está ya resuelto, aporta sus propias reglas y comprueba los requisitos de ese servicio.

Los módulos de este proyecto se instalan en `/opt/localsiem/modules/<nombre>/`. Hoy hay dos: **apache2** («Apache + ModSecurity», secciones 4 a 10) y **privesc** («Escalada de privilegios», secciones 11 a 16). localSIEM no tiene módulos propios: la página de Módulos sólo muestra los módulos instalados desde este repositorio.

<a id="installation"></a>
## 2. Instalar y actualizar los módulos

Primero hay que instalar localSIEM; su instalador instala sólo el núcleo, nunca un módulo. Los módulos de este proyecto se instalan **únicamente desde la web de localSIEM**: este proyecto no tiene instalador propio. La web los descarga del repositorio `https://github.com/PYMEHackers/localSIEM-modules` (rama `main`).

**Instalar.** Como administrador, abre Módulos › **Instalables** (sección 3), pulsa **Consultar el repositorio** y después **Instalar** en el módulo. localSIEM entonces:

1. descarga el repositorio y lo descomprime de forma segura (nada fuera de su carpeta, con límites de tamaño);
2. copia la carpeta del módulo (`mod-<nombre>/` en el repositorio) a `/opt/localsiem/modules/<nombre>/`, sin `tests/` (ni cachés de Python); un módulo que se vuelve a instalar recupera los ajustes que tenía;
3. reinicia el colector, que carga el módulo en unos segundos;
4. quita el módulo de la lista y abre el cuadro de diálogo «<módulo> instalado» con el comando que hay que ejecutar como root en el servidor (`manage.py setup-modules`) y un botón **Copiar**: da al usuario `localsiem` permiso de lectura sobre las carpetas de `read_paths` de su `module.json` (`/var/log/apache2` para el módulo apache2, `/var/log/audit` para el módulo privesc), también sobre los archivos de las próximas rotaciones, y, si le añades la opción de configuración del módulo, también aplica los requisitos del módulo: `--configure-apache` (sección 8) o `--configure-privesc` (sección 15). Hasta que se ejecute, el módulo puede mostrar «Error»: todavía no puede leer sus logs. El cuadro de diálogo se cierra con «Cerrar» o con «Ver los módulos instalados», que abre Instalados.

**Actualizar.** Al abrir Módulos › **Instalados**, la web consulta el repositorio, y un módulo que tiene allí una versión más reciente muestra un aviso con **Actualizar** (sección 3). Tras confirmarlo, localSIEM descarga la versión nueva y la pone en lugar de la instalada (pasos 1 a 3), conserva sus ajustes y deja el módulo activado o desactivado como estaba. El comando para root sólo se vuelve a mostrar si la versión nueva lee otros logs (`read_paths`) o tiene otra opción de configuración; si no, no hay nada que ejecutar. Una actualización de localSIEM conserva los módulos instalados y su acceso de lectura.

**Reinstalar.** La web no reinstala un módulo ni instala una versión anterior: para reinstalar un módulo, pulsa **Desinstalar** (sección 3) y vuelve a instalarlo desde **Instalables**; sus ajustes se conservan.

**Instalar un módulo nunca instala el software que vigila.** El módulo apache2 no instala Apache ni ModSecurity, y el módulo privesc no instala auditd, ni bash, ni snoopy. Si en su primera instalación al servidor le falta lo que el módulo necesita (Apache y ModSecurity para apache2; al menos uno de auditd, bash y snoopy para privesc), el módulo se instala **desactivado**: el cuadro de diálogo muestra lo que falta en lugar del comando, y el módulo no se puede activar hasta que **Reconfigurar** los detecte (sección 4). Una actualización deja el módulo activado o desactivado como estaba.

<a id="modules-page"></a>
## 3. La página de Módulos

Los administradores abren **Administración › Módulos**, que tiene dos secciones, cada una con su propia dirección: **Instalados** (`/admin/dashboard/modules/installed/`), que se abre por defecto (`/admin/dashboard/modules/` lleva ahí), e **Instalables** (`/admin/dashboard/modules/installable/`). Los analistas ven **Módulos** en su panel (`/user/dashboard/modules/`): sólo la lista de los módulos instalados, en modo de lectura, sin secciones.

**Instalados** muestra una fila por módulo instalado, a todo lo ancho: su nombre, su id, su versión, una etiqueta de estado, su resumen y, debajo, los motivos de ese estado. La lista se actualiza sola cada 10 segundos. Si no hay ningún módulo instalado, muestra «Instala módulos desde la pestaña Instalables.» (a los analistas: «No hay módulos instalados. Los instala un administrador en Módulos › Instalables.»).

| Estado | Significado |
|---|---|
| **Activado y funcionando** | Activado, cargado por el colector y leyendo sus fuentes. Los avisos del doctor se muestran como notas, pero no cambian el estado. |
| **Activado, con avisos** | Activado, pero no se ha encontrado ningún log que leer, una fuente todavía no existe, o el módulo se instaló después de que arrancara el colector (reinicia el servicio `localsiem`). |
| **Error** | El módulo no se carga (se muestra el error), su doctor informa de un error, o una fuente no se puede leer (permisos del usuario `localsiem`). |
| **Desactivado** | Está desactivado, o se instaló sin sus requisitos (para apache2: falta Apache o ModSecurity; para privesc: no hay auditd, ni bash, ni snoopy), como indica su motivo. |
| **Aplicando el cambio…** | Se acaba de activar o desactivar: el colector lo está aplicando. |
| **Desconocido** | El colector (servicio `localsiem`) no está en marcha, así que no se está leyendo nada. |

Cuando el módulo no está desactivado, la fila muestra también: **Fuentes en lectura** (leídas / encontradas), **Líneas (1 h)**, **Último dato**, **Eventos (24 h)**, **Bloqueados (24 h)** y los recuentos del **Doctor** («n correctos · n avisos · n errores»).

Los administradores tienen además, en cada fila:

- **El interruptor** de cada módulo. Desactivar un módulo pide confirmación: localSIEM deja de leer sus logs y de enviar sus alertas hasta que se vuelva a activar; lo que ya está guardado se conserva. Al activarlo empieza a leer al momento. Mientras falte un requisito del módulo, el interruptor está bloqueado («Desactivado: faltan requisitos»): **Reconfigurar** (sección 4) lo desbloquea cuando los detecta.
- **Configurar**, que abre la página del módulo, `/admin/dashboard/modules/installed/<nombre>/` (sección 4); la dirección anterior, `/admin/dashboard/modules/<nombre>/`, lleva ahí.
- **Desinstalar**, también en un módulo que no se carga (y en la página del módulo). Tras confirmarlo, localSIEM borra `/opt/localsiem/modules/<nombre>/` y reinicia el colector sin él: deja de leer sus logs y de enviar sus alertas. En los eventos ya guardados se puede seguir buscando, y sus ajustes se conservan por si lo vuelves a instalar. El permiso de lectura que root dio a `localsiem` sobre sus logs no se retira.
- **Actualizar**, cuando el repositorio tiene una versión más reciente del módulo. Cada vez que se abre Instalados, la web consulta el repositorio («Consultando el repositorio en busca de versiones más nuevas…»; el navegador reutiliza la respuesta durante 10 minutos), y la fila de un módulo con una versión más reciente muestra «El repositorio tiene la versión X (la instalada es la Y).» con el botón **Actualizar**. Tras confirmarlo, localSIEM instala la versión nueva (sección 2), conserva sus ajustes, deja el módulo activado o desactivado como estaba y reinicia el colector; un cuadro de diálogo muestra el comando para root sólo si la versión nueva lee otros logs o tiene otra opción de configuración. Si la versión nueva necesita un localSIEM más reciente, el aviso dice «El repositorio tiene la versión X, pero necesita localSIEM Z o posterior: actualiza localSIEM para poder instalarla.» y no tiene botón.

**Instalables** (sólo para administradores) tiene la tarjeta «Módulos instalables». **Consultar el repositorio** descarga el repositorio y lista los módulos que todavía no están instalados en este servidor, cada uno con su nombre, id, versión y resumen y un botón o una nota:

| Botón o nota | Significado |
|---|---|
| **Instalar** | Instala el módulo (sección 2) |
| «Necesita localSIEM X o posterior» | No se puede instalar: actualiza antes localSIEM |
| «El módulo del repositorio no es válido» | No se puede instalar |

Los módulos ya instalados nunca aparecen aquí: se actualizan desde Instalados. Si todos los módulos del repositorio están instalados, la tarjeta muestra «Todos los módulos del repositorio ya están instalados.». Tras instalar, el cuadro de diálogo «<módulo> instalado» muestra el comando que hay que ejecutar como root para que `localsiem` pueda leer los logs del módulo (sección 2), con un botón **Copiar** y la indicación de añadir la opción de configuración del módulo (`--configure-apache` para apache2, `--configure-privesc` para privesc); hasta que se ejecute, el módulo puede mostrar «Error»: todavía no se pueden leer sus logs. Si al servidor le falta lo que necesita el módulo, el cuadro de diálogo muestra en su lugar lo que falta, con la indicación de abrir el módulo en Instalados (**Configurar**) y pulsar **Reconfigurar** cuando el servidor ya lo tenga.

<a id="apache-page"></a>
## 4. La página del módulo Apache

`/admin/dashboard/modules/installed/apache2/` (únicamente para administradores; la dirección anterior, `/admin/dashboard/modules/apache2/`, lleva ahí) tiene cinco partes:

1. **Cabecera**: nombre, id, versión, la ruta de instalación (`/opt/localsiem/modules/apache2`), el interruptor, el estado con sus motivos y las cifras de la sección 3. **Volver a los módulos instalados** regresa a Instalados; **Descubrir de nuevo y pasar el doctor** vuelve a leer al momento la configuración de Apache y actualiza el doctor; **Reconfigurar** vuelve a buscar Apache y ModSecurity (más abajo); **Desinstalar** desinstala el módulo (sección 3) y regresa a Instalados.
2. **Ajustes**: el formulario de la sección 5. **Guardar los ajustes** comprueba cada valor y, si alguno es incorrecto, dice cuál («Valor no válido: …»).
3. **Fuentes**: cada log que se está leyendo, con **Tipo** (`access`, `error`, `audit`), **Ruta**, **Vhost**, **Líneas (1 h)**, **Sin analizar (1 h)**, **Últimos datos** (por ejemplo, `2026/10/29@13:59:59.723`) y **Estado** (error si no se puede leer, aviso si todavía no existe). Debajo, los logs encontrados pero no leídos, con el motivo: «log por tubería, no admitido», «cubierto por el GlobalLog localsiem_combined» o «su formato no tiene datos: cada línea es el mismo texto (un nombre de LogFormat que no está definido)».
4. **Doctor**: las comprobaciones de la sección 7, con la hora en que se ejecutaron. Cada requisito que falta trae el fragmento que lo corrige y un botón **Copiar**. Encima, el comando para root que aplica los requisitos por ti (`manage.py setup-modules --configure-apache`, sección 8), también con un botón **Copiar**.
5. **Reglas**: las reglas de la sección 9, cada una con **Activa**, **Regla** (nombre, id y categoría), **Severidad**, **Umbral** y **Ventana (s)**, y **Guardar las reglas**.

**Requisitos y Reconfigurar.** Mientras falte Apache o ModSecurity, el módulo está desactivado y la cabecera muestra lo que falta, con el comando que lo instala. **Reconfigurar** (también con el módulo desactivado) los vuelve a buscar con los ajustes guardados; si Apache está en un sitio no estándar, rellena antes **Archivo de configuración de Apache** (sección 5). Cuando encuentra los dos, desbloquea el interruptor —activar el módulo es decisión tuya— y muestra el comando que hay que ejecutar como root para que `localsiem` pueda leer los logs de Apache creados después de instalar el módulo; añade `--configure-apache` para aplicar también los requisitos de la sección 8. Un módulo activado que pierde Apache o ModSecurity sigue activado: el doctor y los avisos de salud (sección 10) lo notifican.

**Cada cambio se aplica al momento, sin reiniciar nada**: la web lo guarda y se lo comunica al colector, que recarga sus ajustes, vuelve a descubrir las fuentes y ejecuta el doctor. Si el colector no responde, la web lo indica y el cambio se aplica cuando el colector arranque.

<a id="settings"></a>
## 5. Ajustes del módulo Apache

| Ajuste | Por defecto | Qué hace |
|---|---|---|
| **Sólo las fuentes de abajo** | desactivado | No descubrir los logs a partir de la configuración de Apache: leer únicamente las fuentes añadidas a mano. |
| **Fuentes añadidas a mano** | ninguna | Logs que se leen además de los descubiertos (o en su lugar, con la opción anterior). Hasta 50. |
| **Archivo de configuración de Apache** | vacío | Vacío: se localiza solo (`/etc/apache2/apache2.conf` en Debian, `/etc/apache2/httpd.conf` en Alpine; también se reconoce `/etc/httpd/conf/httpd.conf`). Una ruta absoluta hace que se use ese archivo, si existe. |
| **Intervalo de descubrimiento (segundos)** | 3600 | Cada cuánto se vuelve a leer la configuración de Apache para encontrar vhosts y logs nuevos (de 60 a 86400). |
| **Umbral de bloqueo de ModSecurity** | 0 | 0: se lee de la configuración del CRS (`tx.inbound_anomaly_score_threshold` en `crs-setup.conf`); 5 si no está. Sirve para distinguir una coincidencia por encima del umbral de bloqueo de otra por debajo cuando los mensajes de ModSecurity no indican el umbral (de 0 a 1000). |
| **Días de aprendizaje de archivos PHP nuevos** | 3 | Durante los primeros días tras el primer arranque del módulo, la regla `apache-webshell` no notifica como nuevo un archivo PHP nunca visto (de 0 a 365). Un archivo creado o modificado en su DocumentRoot en el último día cuenta siempre como nuevo. |

Cada **fuente añadida a mano** tiene estos campos (* obligatorio):

| Campo | Uso |
|---|---|
| **Tipo** * | `access.log`, `error.log` o `Registro de auditoría de ModSecurity` |
| **Ruta** * | Ruta absoluta del archivo |
| **Vhost** | Vhost de las líneas, para logs cuyas líneas no lo indican |
| **LogFormat** | Para logs de acceso: un alias (`localsiem_combined`, `combined`, `vhost_combined`, `common`, `combinedio`, o uno definido en la configuración de Apache) o el propio formato. Vacío: se prueban los formatos habituales. |
| **Tipo de registro de auditoría** | `Serie (un único archivo)` o `Concurrente (un archivo por petición)` |
| **Carpeta de la auditoría** | Para el tipo concurrente: la carpeta de `SecAuditLogStorageDir` |

Un archivo se lee una única vez, aunque se descubra y además se añada a mano. Una fuente que aparece con localSIEM en marcha se lee desde su principio si ocupa 5 MB o menos, y desde su final en caso contrario.

Dos ajustes de **Administración › Ajustes** de localSIEM también actúan sobre este módulo: la **ventana de correlación** (5 segundos: cuánto se esperan los tres registros de una petición) y la **severidad por debajo del umbral** (`low`).

<a id="soc"></a>
## 6. Qué envía al SOC el módulo Apache

Para cada petición, el módulo junta la línea de acceso, las líneas de error y el registro de auditoría con el mismo `UNIQUE_ID`. Los logs de acceso que Apache escribe por defecto (`combined`, `vhost_combined`, `common`) no tienen `UNIQUE_ID`: entonces cada línea de acceso se junta con el registro de auditoría y las líneas de error de su propia petición por IP de cliente, método, URI, estado y hora (±2 segundos), aunque la misma petición se repita en el mismo segundo, y el evento se marca como «correlación débil». El vhost sale de `%v` o, si el formato no lo tiene, de la cabecera Host y el puerto del registro de auditoría, elegido como lo elige Apache; la hora toma los microsegundos del registro de auditoría. Después decide si ya se ha hecho algo al respecto («acción tomada»), leyendo primero el log de auditoría (`Action: Intercepted (phase N)`) y después el error.log (`Access denied with code NNN (phase N)`). Un 403 sin ningún rastro de ModSecurity no se toma como bloqueo: se marca como dudoso.

| Situación | ¿Va al SOC? |
|---|---|
| Bloqueada por ModSecurity en las fases 1-2 (la aplicación nunca la recibió) | **No.** Se queda en localSIEM, disponible para buscarla (`action:blocked`), y se cuenta en el contexto de la siguiente alerta de esa IP. |
| Bloqueada en las fases 3-4 (la aplicación ya la había ejecutado) | Sí |
| Coincidencias de reglas con el motor en `DetectionOnly` | Sí |
| Coincidencias de reglas por debajo del umbral de bloqueo | Sí |
| Señales de las reglas de la sección 9 | Sí |

Severidad de las alertas que generan las coincidencias de ModSecurity (archivo `severity.yaml` del módulo):

| Situación | Severidad |
|---|---|
| Coincidencias no bloqueadas, respuesta 3xx, 4xx o 5xx | media |
| Coincidencias no bloqueadas, respuesta 2xx | alta |
| Bloqueada en las fases 3-4 | alta |
| Indicios de éxito: coincidió una regla de salida (950-955) y no se bloqueó nada, o un error de base de datos siguió a la petición | crítica |
| Por debajo del umbral de bloqueo (a menudo un falso positivo de la propia aplicación) | baja (la severidad por debajo del umbral de Administración › Ajustes) |

Cada alerta tiene un nombre estable (por ejemplo, «Apache/ModSecurity: SQL injection not blocked (CRS 942)»), una descripción que termina con la consulta que hay que pegar en la búsqueda de localSIEM (por ejemplo, `ip:203.0.113.7 category:sqli`) y unos detalles: vhost, IP del cliente, método, URI (enmascarada), respuesta, user agent y los datos de ModSecurity (motor, acción, fase, puntuación de anomalía, umbral, reglas y datos coincidentes). Cuando sale, la alerta lleva además el contexto de la IP: peticiones y peticiones bloqueadas de la última hora, las reglas que la bloquearon y la primera vez que se vio.

Las contraseñas, las cookies, las cabeceras `Authorization` y los tokens se enmascaran antes de guardar nada, también dentro de los cuerpos de las peticiones, y los cuerpos de las peticiones nunca viajan al SOC. El cuerpo de la respuesta (parte E) y el texto completo de las reglas ejecutadas (parte K) del log de auditoría no se guardan nunca.

<a id="doctor"></a>
## 7. Requisitos de Apache y ModSecurity: el doctor

El doctor del módulo apache2 lee la configuración de Apache (sin cambiarla) y comprueba cada requisito. Se ejecuta al arrancar el colector, después de cada cambio de ajustes, en cada descubrimiento, con **Descubrir de nuevo y pasar el doctor** y con `manage.py doctor` (sección 17), sólo con el módulo activado: mientras esté desactivado porque falta Apache o ModSecurity, la página del módulo muestra esos requisitos en su lugar (sección 4). Estados: correcto, aviso (funciona con limitaciones), error (hay que corregirlo) e información (sólo importa en algunas situaciones).

| Comprobación | Correcta cuando | Si no |
|---|---|---|
| Configuración de Apache | Se encuentra y se lee `apache2.conf` o `httpd.conf` (o el archivo configurado) | Error: añade las fuentes a mano (sección 5). Las partes que no se pueden leer se listan como avisos. |
| ModSecurity | Está cargado `mod_security2` (ModSecurity 2) | Error. Debian: `apt-get install libapache2-mod-security2 modsecurity-crs && a2enmod security2`. Alpine no tiene paquete: compila mod_security2 2.9 desde el código fuente. ModSecurity 3 (libmodsecurity) no está admitido. |
| OWASP CRS | Los archivos del CRS están incluidos (el doctor muestra cuántos y el umbral de anomalía) | Error: `apt-get install modsecurity-crs`, o incluye `crs-setup.conf` y `rules/*.conf` después de ModSecurity |
| SecRuleEngine | `On` (las peticiones por encima del umbral se bloquean en la fase 2 y se quedan en localSIEM) o `DetectionOnly` (no se bloquea nada: cada coincidencia va al SOC) | Error si es `Off`; aviso si es `Off` salvo en algunos vhosts, si falta (ModSecurity toma entonces `Off` por defecto) o si algunos vhosts lo ponen en `Off` |
| mod_unique_id | Cargado: ModSecurity funciona y las tres fuentes de una petición se juntan por `UNIQUE_ID` | Error si ModSecurity está cargado: ModSecurity 2 no inspecciona nada sin él (Alpine no lo carga); si no, aviso (correlación débil). Debian: `a2enmod unique_id`; Alpine: `LoadModule unique_id_module modules/mod_unique_id.so` |
| Formato del log de acceso | Los logs de acceso tienen IP del cliente, hora, línea de petición y estado, como los formatos que Apache escribe por defecto (OK, «Access logs in the format Apache writes»); con milisegundos, vhost, duración y `UNIQUE_ID` (`localsiem_combined`) se unen por `UNIQUE_ID` | Aviso si a un formato le falta alguno de los cuatro, con el formato `localsiem_combined` y su `GlobalLog` |
| mod_remoteip | Cargado con `RemoteIPHeader` | Información: sólo hace falta detrás de un proxy o de un balanceador de carga; sin él, todas las peticiones parecen venir del proxy y las reglas por IP no funcionan |
| Log de auditoría | `SecAuditEngine RelevantOnly` (u `On`) con un `SecAuditLog` | Aviso si está desactivado. Notas: tipo concurrente (funciona, pero sus archivos suelen tener modo 600 y no se pueden leer: se recomienda Serial), formato nativo (se recomienda JSON), parte E registrada (voluminosa y sensible), falta la parte H (la acción tomada no se puede leer del log de auditoría) |
| Enmascaramiento en origen | Existe una acción `sanitise` | Aviso, con el `SecAction` que enmascara contraseñas, tokens y cookies en el log de auditoría en disco |
| Permisos | `localsiem` puede leer todas las fuentes | Error. Debian: `usermod -aG adm localsiem`; Alpine: los comandos `setfacl` que se muestran. Una fuente que todavía no existe es sólo información. |
| Logs por tubería | — | Aviso: `\|/usr/bin/rotatelogs ...` y syslog no se pueden leer; escribe el log también en un archivo, o añade la fuente a mano |
| Log de acceso sin datos | — | Aviso: un `CustomLog` usa un formato que ningún `LogFormat` define (o un `LogFormat` sin ninguna directiva `%`), así que Apache escribe ese mismo texto en cada línea, sin la IP del cliente, la hora ni la petición. localSIEM no lee ese log y ve las peticiones de su vhost en su log de errores y en el log de auditoría de ModSecurity. El formato de los logs del servidor nunca se cambia. |
| Motor visto en Off | — | Error: los registros de auditoría informan de que el motor está desactivado |
| Versión de ModSecurity | — | Información: la versión leída del log de auditoría |

El log de acceso opcional, para tener milisegundos, duración y la unión por `UNIQUE_ID` (`GlobalLog` lo escribe para todos los vhosts sin tocar sus propios logs):

```apache
LogFormat "%a %l %u [%{%d/%b/%Y:%H:%M:%S}t.%{msec_frac}t %{%z}t] \"%r\" %>s %O \"%{Referer}i\" \"%{User-Agent}i\" %v %D %{UNIQUE_ID}e" localsiem_combined
GlobalLog ${APACHE_LOG_DIR}/localsiem_access.log localsiem_combined
```

Cuando existe un `GlobalLog` cuyo formato tiene `%v`, los demás logs de acceso no se leen (sólo repetirían sus líneas). El log de auditoría recomendado:

```apache
SecAuditEngine RelevantOnly
SecAuditLogRelevantStatus "^(?:5|4(?!04))"
SecAuditLogType Serial
SecAuditLogFormat JSON
SecAuditLogParts ABIJFHKZ
SecAuditLog /var/log/apache2/modsec_audit.log
```

<a id="configure-apache"></a>
## 8. Aplicar los requisitos: --configure-apache

El módulo nunca cambia por su cuenta la configuración de Apache. `--configure-apache` le pide que aplique los requisitos, como root: con el comando que muestra la web después de instalar el módulo (sección 2) o con `manage.py apply-setup -- --configure-apache` (sección 17):

1. Escribe un archivo propio: `/etc/apache2/conf-available/localsiem.conf` (Debian, habilitado con `a2enconf localsiem`) o `/etc/apache2/conf.d/localsiem.conf` (Alpine). Contiene el formato `localsiem_combined` con su `GlobalLog`, los ajustes del log de auditoría anteriores y el `SecAction` que enmascara los valores sensibles (id 77001).
2. Habilita `mod_unique_id` (Debian: `a2enmod unique_id`; Alpine: un `LoadModule` dentro del archivo). En Alpine el archivo carga además `mod_logio`, que necesita el `%O` del formato y que Alpine no carga por defecto (Debian lo trae integrado).
3. Crea `localsiem_access.log` y `modsec_audit.log` en `/var/log/apache2` si todavía no existen (con el grupo `adm` en Debian), antes de que Apache los cree con su propio modo, para que el permiso de lectura que da localSIEM los cubra.
4. Ejecuta `apache2ctl configtest` (Debian) o `httpd -t` (Alpine). Si pasa, recarga Apache (`systemctl reload apache2` o `rc-service apache2 reload`); nunca lo reinicia. Si este ModSecurity no acepta `SecAuditLogFormat JSON`, lo vuelve a intentar con el formato nativo. Si falla, **lo deshace todo** y Apache conserva su configuración anterior.

No instala ModSecurity ni el CRS, y no cambia `SecRuleEngine`: eso sigue siendo decisión del cliente. Para ver el archivo antes de aplicarlo: `manage.py configure-apache` (sección 17). Para deshacerlo más adelante, borra ese archivo (Debian: `a2disconf localsiem`) y recarga Apache.

<a id="rules"></a>
## 9. Reglas del módulo Apache

Las reglas se evalúan sobre cada evento. Una señal de una regla va siempre al SOC. En la página del módulo, cada regla se puede desactivar y se pueden cambiar su severidad, su umbral (de 1 a 100000) y su ventana (de 1 a 86400 segundos); el umbral y la ventana sólo se aplican a las reglas de umbral y de secuencia. Sus eventos se encuentran con `rule:localsiem:<id>`.

| Regla | Tipo | Severidad | Cuándo | Umbral / ventana |
|---|---|---|---|---|
| `apache-bruteforce` «fuerza bruta contra una página de inicio de sesión» | umbral | media | Peticiones POST no bloqueadas desde una IP a una página de inicio de sesión de un vhost (`/wp-login.php`, `/xmlrpc.php`, `/administrator/index.php`, `/user/login`, `/login`, `/admin/login`, `/login.php`, `/admin.php`, `/signin`, `/auth/login`, `/phpmyadmin/index.php`) | 20 en 300 s |
| `apache-login-after-bruteforce` «inicio de sesión correcto tras una fuerza bruta» | secuencia | alta | Al menos 10 inicios de sesión fallidos (POST respondidos con 200, 401 o 403) a una página de inicio de sesión y después uno respondido con 302 o 303 (WordPress responde 200 a un inicio de sesión fallido y 302 a uno correcto) | 10, en 1800 s |
| `apache-enumeration` «enumeración (ráfaga de respuestas 404)» | umbral | media | Respuestas 404 no bloqueadas a una IP desde un vhost | 30 en 60 s |
| `apache-sensitive-file` «archivo sensible servido» | coincidencia | alta | Una respuesta 2xx a un archivo que no debería ser público: `.env`, `.git/`, `.svn/`, `.hg/`, `.htaccess`, `.htpasswd`, volcados y copias de seguridad (`.sql`, `.sql.gz`, `.bak`, `.old`, `.orig`, `.swp`, `.save`, `.backup`, `.dump`, nombres que terminan en `~`), `phpinfo`, `info.php`, `server-status`, `server-info`, copias de `wp-config.php` y de `config.php`/`config.inc`, `.DS_Store`, claves SSH privadas, `composer.json`/`composer.lock`, `.aws/`, `backup.zip`/`.tar`/`.tar.gz`/`.tgz`/`.rar` | — |
| `apache-webshell` «posible web shell (POST a un archivo PHP nuevo)» | coincidencia | crítica | Un POST respondido con 2xx a un archivo PHP creado o modificado en su DocumentRoot en el último día, o visto por primera vez en la última hora (pasados los días de aprendizaje) | — |
| `apache-db-error-after-attack` «error de base de datos tras una petición sospechosa» | secuencia | crítica | Una petición que coincidió con reglas del CRS y, desde la misma IP, un error de base de datos (SQL o PDO) en el error.log | 1, en 30 s |

<a id="health"></a>
## 10. Avisos de salud del módulo Apache

Además de los avisos de salud del propio localSIEM, el módulo comprueba como mucho cada 5 minutos, y envía al SOC:

| Aviso | Severidad | Qué hacer |
|---|---|---|
| ModSecurity ya no está cargado | alta | Estaba cargado y ya no lo está: las peticiones no se inspeccionan. Si nadie lo hizo a propósito, puede que alguien haya desactivado la protección. |
| Motor de ModSecurity pasado a Off | alta | `SecRuleEngine` ha cambiado a `Off`, o el log de auditoría informa de que el motor está desactivado. Revisa la configuración de Apache y sus cambios recientes. |
| Falta la IP real del cliente (mod_remoteip) | media | En la última hora, al menos el 90 % de al menos 100 peticiones vinieron de una única dirección privada o local: probablemente la web está detrás de un proxy. Configura `mod_remoteip`. Se envía como mucho una vez al día. |

Lo que ya se notificó se recuerda entre reinicios, así que una actualización no lo vuelve a enviar. Por estos avisos, un módulo activado nunca se desactiva solo cuando desaparecen Apache o ModSecurity.

<a id="privesc"></a>
## 11. El módulo de escalada de privilegios

El módulo **privesc** («Escalada de privilegios») vigila lo que las personas y los servicios ejecutan en el servidor y notifica los pasos de una escalada a root: el reconocimiento, la búsqueda de programas setuid, las herramientas de enumeración como linpeas, los exploits conocidos, las shells inversas, el root conseguido sin sudo ni su, las puertas traseras que quedan atrás y los intentos de cegar la vigilancia. También revisa la superficie de ataque del servidor: programas setuid, capacidades y archivos sensibles modificables por otros (sección 16).

Lee hasta tres fuentes, según lo que tenga el servidor:

| Fuente | Qué ve | Dónde funciona |
|---|---|---|
| **auditd** (`/var/log/audit/audit.log`) | Cada programa que ejecuta una persona (también desde scripts y exploits), los programas setuid, las shells y las herramientas que ejecutan las cuentas de servicio (una web shell), sudo, su, pkexec y los inicios de sesión SSH, los cambios de archivos sensibles, los bits setuid que se ponen, los módulos del kernel, ptrace, los accesos a archivos denegados y la desactivación de la auditoría | Servidores físicos y máquinas virtuales. **No dentro de un contenedor** (LXC, podman, systemd-nspawn, Docker): la auditoría del kernel no está separada por espacios de nombres, así que auditd sólo funciona en el anfitrión. |
| **Hook de bash** (`/var/log/localsiem-privesc/<uid>.log`) | Cada comando que se escribe en una bash interactiva, comandos internos incluidos (`pwd`, `cd`, `unset HISTFILE`, `trap`), con su carpeta, su terminal y su dirección SSH | En todas partes, contenedores incluidos. Un usuario lo puede eludir (`bash --norc`, `trap - DEBUG`), y hacerlo se notifica. No ve las shells de busybox (`ash`, la shell por defecto de Alpine) ni los scripts. |
| **syslog** (`/var/log/auth.log`, `/var/log/secure` o `/var/log/messages`) | sudo, su, pkexec, doas, los inicios de sesión SSH y, si **snoopy** está instalado, cada programa que se ejecuta | Se lee cuando auditd no está en marcha (contenedores) o snoopy está instalado (ajuste **Leer syslog**). Necesita un demonio de syslog que escriba en un archivo: el journal de systemd por sí solo no se lee. |

En un servidor físico o en una máquina virtual, instala **auditd**: es la fuente que un usuario no puede eludir. En un contenedor, ejecuta auditd con estas reglas en el anfitrión y, dentro, apóyate en el hook y en snoopy.

Una nota sobre `pwd`, `cd` y los demás comandos internos de la shell: nunca ejecutan un programa, así que auditd y snoopy no los ven; sólo los ve el hook. Un único `whoami` o `pwd` nunca es una alerta: el módulo cuenta los comandos de reconocimiento **distintos** de cada sesión dentro de una ventana, y sólo una ráfaga de ellos lo es (sección 13).

Qué contiene cada evento del módulo y cómo buscarlo:

| Columna | Contiene | Búsqueda de ejemplo |
|---|---|---|
| `vhost` | La persona: el usuario con el que inició sesión (se mantiene a través de sudo y su); para el hook, el propietario del archivo | `module:privesc vhost:alice` |
| `method` | Tipo de evento: `exec` (programa ejecutado, auditd o snoopy), `command` (hook), `shell` (arranca una bash interactiva), `sudo`, `su`, `pkexec`, `doas`, `login`, `pam`, `file` (archivo sensible cambiado), `chmod` (bit setuid), `kmod`, `ptrace`, `denied` (acceso a un archivo denegado), `audit_config`, `auditd`, `crash` | `module:privesc method:sudo` |
| `uri` | La línea de comandos (con las contraseñas enmascaradas) | `module:privesc uri:*linpeas*` |
| `path` | El programa ejecutado, o el archivo cambiado | `module:privesc path:/tmp/*` |
| `ip` | La dirección SSH de la sesión, cuando se conoce | `module:privesc ip:203.0.113.7` |
| `score` | Comandos de reconocimiento distintos de la sesión en la ventana | `module:privesc score:>=8` |
| `action` | `blocked` cuando el propio sistema lo detuvo: un programa que no se pudo ejecutar, sudo o su rechazados, un acceso a un archivo denegado | `module:privesc action:blocked` |
| `source` | `audit`, `hook` o `syslog` | `module:privesc source:hook` |

Las reglas sobre intentos (fallos repetidos de sudo, muchos accesos a archivos denegados) cuentan igualmente los eventos bloqueados; las demás sólo miran lo que de verdad se ejecutó.

La página del módulo, `/admin/dashboard/modules/installed/privesc/`, tiene las mismas partes que la página del módulo Apache (sección 4): cabecera (con **Descubrir de nuevo y pasar el doctor**, **Reconfigurar** y **Desinstalar**), ajustes (sección 12), fuentes (`audit`, `hook` con un archivo por usuario, `syslog`; y las que no se leen, con el motivo), doctor (sección 14) y reglas (sección 13).

<a id="privesc-settings"></a>
## 12. Ajustes del módulo de escalada de privilegios

| Ajuste | Por defecto | Qué hace |
|---|---|---|
| **Registro de auditoría** | vacío | Vacío: `log_file` de `/etc/audit/auditd.conf`, o `/var/log/audit/audit.log`. |
| **Leer syslog** | Automático | Automático: sólo cuando auditd no está en marcha o snoopy está instalado. Siempre, o Nunca. |
| **Archivo de syslog** | vacío | Vacío: `/var/log/auth.log`, `/var/log/secure` o `/var/log/messages`, el primero que exista. |
| **Usuarios ignorados** | vacío | Separados por comas. Sus comandos se guardan y se pueden buscar, pero nunca generan una alerta: cuentas de automatización (ansible, copias de seguridad). El usuario `localsiem` siempre se ignora. |
| **Grupos de administradores** | `sudo,wheel,admin` | Separados por comas. Sus miembros (y root) tienen el umbral de reconocimiento más alto y pueden listar sus permisos de sudo sin generar una alerta. |
| **Ventana de reconocimiento (segundos)** | 120 | Ventana en la que se cuentan los comandos de reconocimiento distintos de una sesión (de 10 a 3600). |
| **Umbral de reconocimiento** | 8 | Comandos de reconocimiento distintos en la ventana que forman una ráfaga, para usuarios y cuentas de servicio (de 2 a 500). |
| **Umbral de reconocimiento de los administradores** | 20 | Lo mismo para root y los administradores, que los ejecutan como parte de su trabajo (de 2 a 500). |
| **Umbral de enumeración automática** | 40 | Comandos de reconocimiento distintos en la ventana que sólo ejecuta un script (tipo linpeas), para todo el mundo (de 5 a 1000). |
| **Días de aprendizaje de las cuentas de servicio** | 3 | Durante los primeros días tras el primer arranque del módulo, se aprenden sin alertas los programas que ejecuta cada cuenta de servicio (`www-data` ejecutando `sh -c sendmail`) (de 0 a 365). |
| **Horas entre búsquedas de programas setuid** | 24 | Cada cuánto se buscan los programas setuid y setgid y las capacidades de archivo (sección 16). 0: nunca (de 0 a 168). |
| **Carpetas revisadas** | `/usr,/bin,/sbin,/lib,/lib64,/opt,/home,/srv,/tmp,/var/tmp,/dev/shm,/var/www,/etc` | Separadas por comas; cada una se recorre sin salir de su sistema de archivos. Las carpetas de los contenedores y las de `/proc` y `/sys` se omiten siempre. |
| **Intervalo de descubrimiento (segundos)** | 300 | Cada cuánto se buscan los archivos del hook de usuarios nuevos, syslog y el estado de auditd (de 60 a 86400). El intervalo más corto de los módulos activados se aplica a todos ellos. |

Qué cuenta como reconocimiento: `whoami`, `id`, `groups`, `uname`, `hostname`, `w`, `who`, `last`, `ps`, `ss`, `netstat`, `ip`, `ifconfig`, `env`, `pwd`, `history`, `getcap`, `lsmod`, `dmesg`, `mount` y similares; `sudo -l`, `crontab -l`, `systemctl list-*`, las listas de paquetes; `which`, `locate`, `command -v`; `docker ps` y similares; cada `find` distinto; leer `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`, `/etc/*-release`, `/proc/version`, `/root/...`, los historiales, las claves SSH y los archivos `.env`; listar `/root`, `/home`, `/opt`, `/tmp`, las carpetas de cron...; `grep -r password`; y `<programa> --version`. Cada comando distinto de una sesión cuenta una vez dentro de la ventana.

<a id="privesc-rules"></a>
## 13. Qué envía al SOC el módulo de escalada de privilegios: sus reglas

Cada alerta del módulo sale de una de sus reglas (funcionan igual sea cual sea la fuente que vio el comando), salvo las de la sección 16. Como en Apache, en la página del módulo cada regla se puede desactivar y se pueden cambiar su severidad, su umbral y su ventana; sus eventos se encuentran con `rule:localsiem:<id>`. Ninguna salta para los **Usuarios ignorados**.

| Regla | Tipo | Severidad | Cuándo | Umbral / ventana |
|---|---|---|---|---|
| `privesc-recon-burst` «ráfaga de reconocimiento» | coincidencia | media | La sesión alcanzó el umbral de reconocimiento (sección 12) | — |
| `privesc-enumeration` «enumeración automática (tipo linpeas)» | coincidencia | alta | La sesión alcanzó el umbral de enumeración automática, incluso con un script renombrado | — |
| `privesc-suid-hunt` «búsqueda de programas setuid o de capacidades» | coincidencia | alta | `find ... -perm -4000` (o `-u=s`, `/6000`, `-2000`...), `getcap -r`, `find -writable` | — |
| `privesc-sudo-list` «permisos de sudo listados por alguien que no es administrador» | coincidencia | media | `sudo -l` ejecutado por un usuario o una cuenta de servicio que no es administrador | — |
| `privesc-known-tool` «herramienta de enumeración conocida» | coincidencia | alta | linpeas, LinEnum, lse.sh, linux-exploit-suggester, les.sh, pspy, unix-privesc-check, linuxprivchecker, traitor, BeRoot, GTFONow, PEASS, deepce, CDK, sudo_killer, suid3num, mimipenguin, LaZagne, pwncat, searchsploit | — |
| `privesc-exploit` «exploit conocido» | coincidencia | crítica | PwnKit, DirtyPipe, Dirty COW, Baron Samedit (`sudoedit -s '\'`), Looney Tunables (`GLIBC_TUNABLES`), GameOver(lay), nf_tables (CVE-2024-1086), CVE-2023-22809 (`EDITOR=... -- /...`), polkit CVE-2021-3560 (`dbus-send ... CreateUser`), `LD_PRELOAD` con sudo, un script con el nombre de un CVE, programas llamados `exploit`, `getroot`, `rootme` | — |
| `privesc-pwnkit` «PwnKit (pkexec ejecutado sin argumentos)» | coincidencia | crítica | `pkexec` ejecutado con cero argumentos (auditd) | — |
| `privesc-pwnkit-log` «pkexec informa de un intento de PwnKit» | coincidencia | crítica | pkexec registra `GCONV_PATH`, «suspicious content» o «was not found the /etc/shells» (syslog) | — |
| `privesc-suid-escape` «root heredado de un programa setuid» | coincidencia | crítica | Un programa que no es setuid se ejecuta con el uid efectivo de root y el uid real de un usuario: se ha abusado de un programa setuid (GTFOBins). Se exceptúan los asistentes de montaje, D-Bus, polkit y X. | — |
| `privesc-root-without-door` «root sin sudo, su ni pkexec» | coincidencia | crítica | auditd: una sesión de una persona cuyo inicio se vio ejecuta programas como root sin haber pasado por sudo, su, pkexec ni doas (exploits del kernel). Hook: una bash de root arrancada por un programa de un usuario normal que no es su, sudo, sshd, login... | — |
| `privesc-root-shell-interpreter` «shell de root arrancada por un intérprete» | coincidencia | alta | Hook: una bash de root cuyo padre es python, perl, ruby, awk, gdb... | — |
| `privesc-file-capabilities` «programa que obtuvo capacidades de root de su archivo» | coincidencia | alta | Un usuario ejecutó un programa cuyo archivo le da `cap_setuid`, `cap_dac_override`, `cap_sys_admin`... (auditd) | — |
| `privesc-tmp-exec` «programa ejecutado desde una carpeta en la que todos pueden escribir» | coincidencia | alta | Un programa en `/tmp`, `/var/tmp`, `/dev/shm` o `/run/user/<uid>` | — |
| `privesc-compile-tmp` «programa compilado en una carpeta temporal» | coincidencia | alta | `gcc`, `cc`, `clang`, `make`... en una carpeta temporal o sobre archivos de una carpeta temporal | — |
| `privesc-download-shell` «script descargado ejecutado por una shell» | coincidencia | alta | `curl ... \| sh`, `bash -c "$(curl ...)"`, `bash <(wget ...)`, o un programa de descarga seguido de una shell en la misma tubería | — |
| `privesc-reverse-shell` «shell inversa» | coincidencia | alta | `/dev/tcp/`, `nc -e`, `ncat --exec`, `socat exec:`, `mkfifo ... \| nc`, sockets de python/perl/php/ruby/lua/node, `openssl s_client ... \| sh`, `awk /inet/tcp` | — |
| `privesc-tty-upgrade` «shell mejorada a un terminal completo» | coincidencia | alta | `pty.spawn`, `script ... /dev/null`, `stty raw -echo`, `socat ... pty`, `expect ... spawn sh` | — |
| `privesc-service-recon` «una cuenta de servicio ejecutó comandos de reconocimiento» | coincidencia | alta | `www-data`, `mysql` y otras cuentas de servicio ejecutando `whoami`, `id`, `uname`... (una web shell) | — |
| `privesc-service-new-program` «una cuenta de servicio ejecutó un programa que nunca había ejecutado» | coincidencia | alta | Pasados los días de aprendizaje, una cuenta de servicio ejecuta una shell, un intérprete o una herramienta que nunca había ejecutado (`sh -c id` donde sólo ejecutaba `sh -c sendmail`) | — |
| `privesc-container-escape` «contenedor usado para llegar como root al anfitrión» | coincidencia | alta | Alguien que no es root ejecuta `docker run -v /:/...`, `--privileged`, `--pid=host`, `nsenter -t 1`, `lxc config set ... security.privileged true`, `lxc config device add ... source=/`, `debugfs /dev/...` | — |
| `privesc-auth-failures` «fallos repetidos de sudo o su» | umbral | media | sudo, su, pkexec o doas fallidos de un mismo usuario | 3 en 600 s |
| `privesc-sensitive-file` «archivo de cuentas, sudo, PAM o preload cambiado» | coincidencia | alta | `/etc/passwd`, `shadow`, `group`, `gshadow`, `sudoers`, `sudoers.d`, `doas.conf`, `ld.so.preload`, `ld.so.conf`, `pam.d`, `security` cambiados por un programa que no es una herramienta de paquetes ni de cuentas (auditd) | — |
| `privesc-persistence-file` «archivo de SSH, cron o servicios cambiado» | coincidencia | media | `/root/.ssh`, `sshd_config`, archivos de cron, `/etc/systemd/system`, `/etc/init.d`, `rc.local`, `/etc/local.d` cambiados (auditd) | — |
| `privesc-monitoring-changed` «configuración de auditd o hook de comandos cambiados» | coincidencia | media | `/etc/audit`, el hook o el bashrc cambiados (es lo esperado mientras se ejecuta `--configure-privesc`) | — |
| `privesc-suid-set` «bit setuid o setgid puesto en un archivo» | coincidencia | alta | `chmod u+s`/`g+s` fuera del gestor de paquetes (auditd) | — |
| `privesc-setcap` «capacidades de archivo puestas» | coincidencia | alta | `setcap ... cap_...` | — |
| `privesc-kernel-module` «módulo del kernel cargado desde una sesión» | coincidencia | alta | Un módulo cargado o quitado desde la sesión de una persona (auditd) | — |
| `privesc-ptrace` «proceso enganchado con ptrace» | coincidencia | media | `PTRACE_ATTACH` o `PTRACE_SEIZE` por parte de una persona (auditd) | — |
| `privesc-denied-burst` «muchos accesos a archivos denegados (enumeración)» | umbral | media | Accesos a archivos denegados (`EACCES`, `EPERM`) a un mismo usuario (auditd) | 30 en 60 s |
| `privesc-sensitive-denied` «intento de leer los hashes de las contraseñas o los archivos de root» | coincidencia | media | Acceso denegado a un usuario a `/etc/shadow`, `/etc/gshadow`, `/etc/sudoers`, `/etc/sudoers.d/` o `/root` (auditd) | — |
| `privesc-history-tampering` «historial de la shell borrado o desactivado» | coincidencia | media | `unset HISTFILE`, `HISTFILE=/dev/null`, `HISTSIZE=0`, `history -c`, `set +o history`, `ln -s /dev/null ~/.bash_history`, `rm .bash_history`... | — |
| `privesc-hook-disabled` «hook de comandos de localSIEM eludido» | coincidencia | alta | `trap - DEBUG`, `unset ...LocalsiemPrivesc...`, `bash --norc`/`--noprofile`, `env -i bash` | — |
| `privesc-hook-forged` «línea falsificada en el archivo de comandos de un usuario» | coincidencia | media | Una línea de un archivo del hook dice tener un uid distinto del del propietario del archivo | — |
| `privesc-audit-stop-command` «comando para desactivar auditd» | coincidencia | crítica | `auditctl -e 0`, `auditctl -D`, `auditctl -a never`, `systemctl stop/disable/mask auditd`, `service auditd stop`, `pkill auditd`, borrar `/var/log/audit` o `/etc/audit` | — |
| `privesc-audit-disabled` «auditoría desactivada» | coincidencia | crítica | El kernel informa de `audit_enabled=0` (auditd) | — |
| `privesc-auditd-stopped` «auditd detenido por un proceso» | coincidencia | alta | auditd detenido a petición de un proceso distinto de init (el apagado del servidor no se notifica) | — |
| `privesc-crash` «caída de un programa setuid o temporal» | coincidencia | media | Un programa setuid, o uno de una carpeta temporal, se ha caído (`ANOM_ABEND` de auditd): a menudo, un exploit fallido | — |

Cada alerta tiene un nombre estable, una descripción que termina con la consulta que hay que pegar en la búsqueda de localSIEM y unos detalles: usuario, tipo de cuenta (`root`, `admin`, `user`, `service`), usuario real y efectivo, comando, programa, carpeta, terminal, sesión, fuente (`auditd`, `hook`, `snoopy`, `syslog`), IP del cliente y, cuando corresponden, el programa padre, el archivo cambiado, los comandos de reconocimiento contados, las capacidades y el modo puesto. Cuando sale, la alerta lleva además el contexto de la sesión: si se vio su inicio, si pasó por sudo o su, su dirección SSH y sus **últimos 20 comandos**, para que el analista lea lo que llevó a la alerta sin tener que buscar.

El mismo comando lo puede ver más de una fuente (el hook y auditd): las alertas se agrupan por módulo, usuario, IP, categoría y severidad, así que sigue siendo una única alerta. Las contraseñas de las líneas de comandos (`mysql -p...`, `sshpass -p`, `curl -u user:pass`, `PASSWORD=...`, URL con contraseña) se enmascaran antes de guardar nada, también en el hexadecimal de los registros de auditoría.

<a id="privesc-doctor"></a>
## 14. Requisitos del módulo de escalada de privilegios: el doctor

**Requisitos.** El módulo necesita una forma de ver los comandos: **auditd** (fuera de un contenedor), **bash** (para su hook) o **snoopy**. Si no hay ninguno, se instala desactivado, con el comando que instala uno de ellos; **Reconfigurar** lo vuelve a comprobar. No instala ninguno por su cuenta.

El doctor funciona como el de Apache (sección 7):

| Comprobación | Correcta cuando | Si no |
|---|---|---|
| auditd | auditd está en marcha | Aviso si no está instalado (Debian: `apt-get install auditd`; Alpine: `apk add audit && rc-update add auditd && rc-service auditd start`); error si está instalado pero detenido (`systemctl enable --now auditd`). Información dentro de un contenedor: auditd no está disponible, ejecútalo en el anfitrión. |
| Reglas de auditoría | Está instalado el `/etc/audit/rules.d/90-localsiem-privesc.rules` de esta versión | Aviso, con el comando de la sección 15 |
| Registros de las reglas | Se están leyendo registros con una clave `lsiem_*` (la hora del último) | Aviso si auditd escribe pero ninguno lleva una clave de localSIEM: las reglas no están cargadas |
| Log de auditoría | `localsiem` lo puede leer | Error, con el comando de la sección 15 |
| Grupo del log de auditoría | auditd crea sus logs con el grupo `adm` | Aviso: tras una rotación, puede que el log nuevo no se pueda leer; `--configure-privesc` pone `log_group = adm` |
| bash | — | Información si bash no está instalado: el hook sólo funciona en bash |
| Hook de bash | Instalado e igual que el de esta versión del módulo | Aviso si falta o está desactualizado (vuelve a aplicar la sección 15 después de actualizar el módulo) |
| Carpeta del hook | `/var/log/localsiem-privesc` es `root:localsiem` con modo `3753` | Error, con el comando de la sección 15 |
| Archivos del hook | Cada `<uid>.log` pertenece a su usuario y se puede leer | Error si uno pertenece a otro usuario (alguien se lo ha apropiado); aviso si su usuario lo ha hecho ilegible |
| syslog | Se lee el archivo de syslog | Error si no se puede leer (`setfacl -m g:localsiem:r <archivo>`); aviso si no hay ni auditd ni un archivo de syslog (Debian: `apt-get install rsyslog`; Alpine: `rc-update add syslog boot && rc-service syslog start`) |
| snoopy | Instalado | Aviso sin auditd: no se ven los comandos de los scripts ni de las web shells (Debian: `apt-get install snoopy`; Alpine: compílalo desde el código fuente) |
| Programas setuid y capacidades | — | Información: la última búsqueda (sección 16). Aviso con los programas setuid que dan una shell de root (GTFOBins) y con los programas cuyas capacidades son, en la práctica, de root |
| Archivos sensibles | Ninguno es modificable por alguien distinto de root | Error por cada uno (`/etc/passwd`, `sudoers`, cron, `/etc/profile.d`, las carpetas del `PATH` de root, `docker.sock`...), con el `chown`/`chmod` que lo corrige |
| Grupos privilegiados | — | Aviso con los miembros de `docker`, `lxd`, `incus-admin`, `disk` y `libvirt`: en la práctica son root |

<a id="configure-privesc"></a>
## 15. Aplicar los requisitos: --configure-privesc

El módulo nunca cambia el sistema por su cuenta. `--configure-privesc` aplica sus requisitos, como root: con el comando que muestra la web después de instalar el módulo o después de **Reconfigurar** (sección 2), o con `manage.py apply-setup -- --configure-privesc` (sección 17). No instala ningún software, y volver a ejecutarlo es seguro:

1. **auditd** (si está instalado, y no en un contenedor): escribe `/etc/audit/rules.d/90-localsiem-privesc.rules` y lo carga con `augenrules --load`. Las reglas auditan cada programa que ejecuta una persona (uid de inicio de sesión 1000 o superior) y los programas que otros ejecutan con el uid efectivo de root; las shells, los intérpretes y las herramientas (`sh`, `bash`, `python3`, `perl`, `php`, `curl`, `wget`, `nc`, `id`, `whoami`...) que ejecutan las cuentas de servicio; `chmod` con el bit setuid o setgid; los módulos del kernel; `ptrace`; los accesos a archivos denegados a personas; y los cambios de cuentas, sudoers, PAM, preload, SSH, cron, servicios, `/etc/audit` y el hook. En x86 de 64 bits cubren también los programas de 32 bits (si el kernel rechaza esas reglas, se cargan sin ellas). Si auditd no acepta las reglas, vuelve el archivo anterior. Si las reglas son inmutables (`-e 2`), se cargan en el siguiente reinicio. También pone `log_group = adm` en `auditd.conf`, para que los logs que crea auditd al rotarlos sigan siendo legibles por `localsiem` (y, en Alpine, añade `localsiem` a `adm`), y crea `/root/.ssh` (vacío, 700) para que se vea una clave que se añada más adelante.
2. **Hook de bash**: copia `/etc/localsiem-privesc/hook.bash`, escribe `/etc/profile.d/localsiem-privesc.sh` y añade una línea a `/etc/bash.bashrc` (Debian) o a `/etc/bash/bashrc` (Alpine). Crea `/var/log/localsiem-privesc` (`root:localsiem`, modo `3753`: cada usuario puede crear allí su propio archivo, y nadie puede listar la carpeta ni borrar los archivos de los demás) y un archivo `<uid>.log` (modo 640) para root y para cada persona. Un archivo que pertenece al usuario equivocado se aparta (`<uid>.log.wrong-owner-<fecha>`) y se crea uno correcto. El hook escribe como mucho 30 comandos por segundo por shell y nunca ejecuta un programa por cada comando.
3. **snoopy** (si está instalado): pone `message_format` en `/etc/snoopy.ini` para que cada línea lleve el login, el uid y el uid efectivo, el pid y el padre.

Para ver las reglas antes de aplicarlas: `manage.py doctor` lista lo que falta; una vez aplicadas, las reglas están en `/etc/audit/rules.d/90-localsiem-privesc.rules`. Para deshacerlo: borra ese archivo y ejecuta `augenrules --load`; borra `/etc/profile.d/localsiem-privesc.sh`, `/etc/localsiem-privesc/` y la línea del bashrc que sigue a «localSIEM privesc: command hook»; y borra `/var/log/localsiem-privesc` si no quieres conservar los comandos.

<a id="privesc-health"></a>
## 16. Superficie de ataque y avisos de salud del módulo de escalada de privilegios

Además de sus reglas, el módulo examina el propio servidor y envía al SOC:

| Aviso | Severidad | Cuándo |
|---|---|---|
| Programa setuid o setgid nuevo | alta | Una búsqueda encuentra un programa setuid o setgid que la búsqueda anterior no tenía (la primera búsqueda sólo sirve de referencia). Un atacante que ha llegado a root suele dejar atrás una shell setuid; una actualización de paquetes también puede añadir uno. |
| Programa setuid nuevo en una carpeta modificable | crítica | Lo mismo, en `/tmp`, `/var/tmp`, `/dev/shm`, `/home`, `/srv` o `/var/www` |
| Programa setuid nuevo de GTFOBins | crítica | Lo mismo, para un programa que da una shell de root cuando es setuid (`bash`, `find`, `python`, `vim`, `less`, `cp`...) |
| Capacidades nuevas | alta | Un programa obtuvo capacidades que, en la práctica, son de root (`cap_setuid`, `cap_dac_override`, `cap_sys_admin`...) |
| Archivo sensible modificable por alguien distinto de root | crítica | Se comprueba cada hora: `/etc/passwd`, `/etc/shadow` (también si lo puede leer cualquiera), `sudoers`, cron, `/etc/profile.d`, PAM, servicios, `ld.so.preload`, las carpetas del `PATH` de root, `docker.sock`... Se notifica una vez por archivo y problema. |
| Otro usuario se ha apropiado del archivo de comandos de un usuario | alta | Un `<uid>.log` del hook pertenece a otro usuario o no es un archivo |
| auditd detenido (salud de localSIEM) | alta | auditd estaba en marcha y ya no lo está (fuera de los contenedores) |

La búsqueda se ejecuta en segundo plano, como mucho con la frecuencia que indica **Horas entre búsquedas de programas setuid** (la primera, cinco minutos después de que arranque el colector), por las **Carpetas revisadas**, como el usuario `localsiem` (lo que no puede leer se omite), y se detiene tras 3 millones de archivos o 15 minutos. Su resultado, con los programas de GTFOBins y las capacidades encontrados, se muestra en el doctor. Las severidades de estos avisos están en el `severity.yaml` del módulo. Lo que ya se notificó se recuerda entre reinicios.

<a id="cli"></a>
## 17. Línea de comandos

Como root, `/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py <comando>`:

| Comando | Uso |
|---|---|
| `modules` | Módulos instalados: id, versión, activado, desactivado o no cargado, y carpeta, con los requisitos que le faltan, si es el caso; y los módulos que no se han podido cargar, con el error |
| `doctor` | Para cada módulo activado: cada comprobación (`[ OK ]`, `[WARN]`, `[FAIL]`, `[INFO]`) con el fragmento que la corrige, y las fuentes encontradas; para un módulo desactivado porque le falta un requisito, sus requisitos. `--json` da lo mismo en JSON. |
| `configure-apache` | Muestra el archivo que escribiría `--configure-apache` |
| `read-paths` | Carpetas que leen los módulos, a las que localSIEM da permiso de lectura como root |
| `apply-setup -- OPCIÓN` | Como root: aplica la opción de configuración de un módulo instalado (`--configure-apache`, sección 8; `--configure-privesc`, sección 15) |
| `setup-modules [OPCIÓN...]` | Como root: el comando que muestra la web; el permiso de lectura sobre las carpetas de los módulos, las opciones de configuración añadidas (por ejemplo, `--configure-privesc`) y un reinicio de localSIEM |

Ejecuta el doctor como el usuario `localsiem` para ver sus permisos reales:

```bash
runuser -u localsiem -- /opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor   # Debian
su -s /bin/sh localsiem -c "/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor"   # Alpine
```
