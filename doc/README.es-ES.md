# localSIEM-modules

Este README también está disponible en:\
[en-GB](README.en-GB.md), [en-US](../README.md), [es-AR](README.es-AR.md), es-ES

localSIEM-modules contiene los **módulos** de [localSIEM](../../localSIEM/doc/README.es-ES.md), el SIEM ligero que se ejecuta en el mismo servidor que protege. El núcleo de localSIEM guarda los eventos, busca en ellos, aplica las reglas, agrupa las alertas y las envía al SOC de PYMEHackers, pero no sabe leer ningún servicio en concreto. Cada módulo le enseña un servicio: dónde están sus logs, cómo se leen, cómo se juntan en eventos, qué cuenta como «ya resuelto», qué reglas se aplican y qué necesita el servicio para estar bien configurado.

Los módulos viven separados del núcleo para que cada uno se pueda añadir, actualizar o desactivar sin tocar el propio localSIEM.

Hoy hay dos módulos:

- **apache2** (Apache + ModSecurity): lee el `access.log` y el `error.log` de Apache y el log de auditoría de ModSecurity, y junta los tres registros de cada petición en un único evento, por su `UNIQUE_ID` o, con los logs de acceso que Apache escribe por defecto, por IP de cliente, petición, estado y hora. Lo que ModSecurity ya bloqueó antes de que la aplicación lo recibiera (fases 1-2) se queda en localSIEM, disponible para buscarlo, y no genera alerta; todo lo demás va al SOC, tenga la puntuación que tenga. Trae seis reglas (fuerza bruta, inicio de sesión correcto tras una fuerza bruta, enumeración, archivo sensible servido, posible web shell y error de base de datos tras un ataque), un doctor que comprueba los requisitos de Apache y ModSecurity, y comprobaciones de salud que avisan cuando alguien desactiva la protección.
- **privesc** (Escalada de privilegios): vigila lo que las personas y los servicios ejecutan en el servidor y avisa de los pasos de una escalada a root. Lee auditd en servidores físicos y máquinas virtuales, un hook de las shells interactivas de bash (que también ve comandos internos como `pwd`) en todas partes, contenedores incluidos (LXC, podman, systemd-nspawn), y sudo, su, pkexec, doas y snoopy a través de syslog. Un único `whoami` o `pwd` no genera nada; una ráfaga de comandos de reconocimiento distintos en una misma sesión, sí. Trae 37 reglas (ráfaga de reconocimiento, enumeración automática como linpeas, búsqueda de programas setuid, herramientas y exploits conocidos como PwnKit o DirtyPipe, shells inversas, root heredado de un programa setuid abusado, root conseguido sin sudo ni su, comandos de web shell de cuentas de servicio, puertas traseras en cuentas, sudoers, PAM, cron o SSH, bits setuid y capacidades, historial borrado, auditd desactivado...), una búsqueda de programas setuid, capacidades y archivos sensibles modificables por otros, y un doctor que dice qué necesita cada tipo de servidor.

[Manual de uso](MANUAL.es-ES.md) · [Referencia técnica](CODE.es-ES.md)

## Requisitos

- **localSIEM 2.2.0 o posterior**, en Debian 13 o Alpine Linux 3.24 o posterior con Python 3.13 o posterior (consulta el [README de localSIEM](../../localSIEM/doc/README.es-ES.md)). Los módulos se instalan desde la web de localSIEM; el comando que permite a localSIEM leer sus logs se ejecuta como root (no hace falta `sudo`).
- Para el módulo apache2: Apache con **ModSecurity 2 (mod_security2) y el OWASP Core Rule Set** ya activos. Instalar el módulo nunca instala Apache ni ModSecurity: si falta alguno de los dos, se instala **desactivado**, y cuando los instales, **Reconfigurar** en su página los detecta y te deja activarlo.
- Para el módulo privesc: **auditd** (recomendado en servidores físicos y máquinas virtuales; no se puede ejecutar dentro de un contenedor), **bash** (para su hook) o **snoopy**, al menos uno de ellos. Instalar el módulo no instala ninguno: si no hay ninguno, se instala **desactivado**. Dentro de los contenedores, un demonio de syslog que escriba `/var/log/auth.log` (o `/var/log/messages`) y snoopy le permiten ver sudo, su y los comandos de los scripts.

## Instalar o actualizar

Primero hay que instalar localSIEM: su instalador instala sólo el núcleo y lo deja preparado para los módulos (consulta el [README de localSIEM](https://github.com/PYMEHackers/localSIEM)). Los módulos se instalan **únicamente desde la web de localSIEM**: este proyecto no tiene instalador propio, y la web los descarga de este repositorio (`https://github.com/PYMEHackers/localSIEM-modules`, rama `main`).

1. Como administrador, abre **Administración › Módulos › Instalables** (`/admin/dashboard/modules/installable/`).
2. Pulsa **Consultar el repositorio**: lista los módulos de este repositorio que todavía no están instalados, con la versión de cada uno. Si ya están todos instalados, lo indica: «Todos los módulos del repositorio ya están instalados.».
3. Pulsa **Instalar** en el módulo. localSIEM lo copia a `/opt/localsiem/modules/<nombre>/` (sin su carpeta `tests/`) y lo carga en unos segundos; el módulo sale de la lista y un cuadro de diálogo indica qué hacer a continuación.
4. Leer los logs de un módulo requiere root, así que el cuadro de diálogo muestra el comando que hay que ejecutar como root en el servidor (`manage.py setup-modules`), con un botón **Copiar**. Da al usuario `localsiem` permiso de lectura sobre las carpetas que declara el módulo (`/var/log/apache2` para el módulo apache2, `/var/log/audit` para el módulo privesc) y, si le añades la opción de configuración del módulo, también aplica esa opción:
   - `--configure-apache` (apache2): el módulo escribe un archivo propio, ejecuta `configtest`, lo deshace todo si falla y recarga Apache (nunca lo reinicia) si funciona.
   - `--configure-privesc` (privesc): el módulo carga sus reglas de auditd (restaura las anteriores si auditd las rechaza), pone `log_group = adm` en `auditd.conf`, instala el hook de bash y la carpeta de los archivos de comandos, y configura el formato de snoopy si está instalado. Vuelve a ejecutarlo después de actualizar el módulo.

   Si al servidor le falta lo que necesita el módulo, el cuadro de diálogo muestra en su lugar lo que falta: el módulo se instala desactivado (más abajo).

**Actualizar.** Al abrir **Administración › Módulos › Instalados** (`/admin/dashboard/modules/installed/`), la web consulta el repositorio. Un módulo que tiene allí una versión más reciente muestra «El repositorio tiene la versión X (la instalada es la Y).» y un botón **Actualizar**: tras confirmarlo, localSIEM instala la versión nueva sobre la instalada, conserva sus ajustes, deja el módulo activado o desactivado como estaba y reinicia el colector. El comando para root sólo se vuelve a mostrar si la versión nueva lee otros logs o tiene otra opción de configuración. Si la versión nueva necesita un localSIEM más reciente, el aviso lo indica y no tiene botón.

La web no tiene botón para reinstalar: para reinstalar un módulo, pulsa **Desinstalar** en su fila de **Instalados** y vuelve a instalarlo desde **Instalables**; sus ajustes se conservan.

## Activar y configurar el módulo Apache

Si el servidor tiene Apache y ModSecurity, el módulo apache2 queda **activado** después de la instalación y ya está leyendo los logs de Apache. Si falta alguno de los dos, se instala **desactivado** y todavía no se puede activar: instálalos, pulsa **Reconfigurar** en la página del módulo y, cuando los detecte, actívalo con su interruptor. Para revisarlo, activarlo, desactivarlo o configurarlo:

1. Abre la web de localSIEM (`https://<servidor>:10443/`) e inicia sesión como administrador.
2. Ve a **Administración › Módulos › Instalados** (`/admin/dashboard/modules/installed/`; `/admin/dashboard/modules/` lleva ahí). Cada módulo muestra su estado («Activado y funcionando», «Activado, con avisos», «Error», «Desactivado», «Aplicando el cambio…» o «Desconocido»), el motivo y un interruptor para activarlo o desactivarlo.
3. Pulsa **Configurar** para abrir `/admin/dashboard/modules/installed/apache2/`: su estado y sus cifras, sus ajustes (fuentes manuales, archivo de configuración de Apache, intervalo de descubrimiento, umbral de bloqueo, días de aprendizaje), las fuentes que lee, el doctor con el fragmento que corrige cada requisito que falta, y sus reglas (activas o no, severidad, umbral y ventana).

Los cambios se aplican al momento, sin reiniciar nada. Los analistas ven el estado de los módulos, en modo de lectura, en `/user/dashboard/modules/`.

Desde la línea de comandos, como root:

```bash
/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py modules            # módulos instalados y su estado
/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor             # requisitos y fuentes
/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py configure-apache   # archivo que escribiría --configure-apache
```

## Activar y configurar el módulo de escalada de privilegios

Si el servidor tiene auditd, bash o snoopy, el módulo privesc queda **activado** después de la instalación. Después ejecuta, como root, el comando que muestra la web, añadiendo `--configure-privesc`:

```bash
/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py setup-modules --configure-privesc
```

Lo que vigila depende del servidor:

- **Servidor físico o máquina virtual**: instala primero auditd (`apt-get install auditd` en Debian; `apk add audit && rc-update add auditd && rc-service auditd start` en Alpine) y después ejecuta el comando anterior. auditd ve todos los programas que se ejecutan, también desde scripts y exploits, y un usuario no lo puede eludir.
- **Contenedor** (LXC, podman, systemd-nspawn): auditd no se puede ejecutar dentro. El módulo lee el hook de bash y syslog; instala un demonio de syslog y snoopy (`apt-get install rsyslog snoopy` en Debian) para ver también sudo, su y los comandos de los scripts y de las web shells, y ejecuta auditd con las reglas de este módulo en el anfitrión.

Su página, `/admin/dashboard/modules/installed/privesc/`, muestra las fuentes que lee (el log de auditoría, un archivo de comandos por usuario, syslog), el doctor (lo que le falta a cada tipo de servidor, los programas setuid que dan una shell de root, los archivos sensibles modificables por otros y los miembros de grupos como `docker`, que en la práctica son root) y las reglas. Los ajustes permiten ignorar las cuentas de automatización, indicar los grupos de administradores y ajustar los umbrales de reconocimiento.

## Contenido de este proyecto

| Ruta | Contenido |
|---|---|
| `mod-apache2/` | El módulo apache2 (la carpeta de cada módulo es `mod-<nombre>/`; el módulo conserva su nombre): `module.json`, código, `severity.yaml`, reglas (`rules/`), textos de la web (`locales/`) y tests (`tests/`) |
| `mod-privesc/` | El módulo privesc: `module.json`, código, `severity.yaml`, reglas (`rules/`), textos de la web (`locales/`) y el hook de bash (`hook/`) |
| `doc/` | Manual de uso, referencia técnica y las traducciones de este README |

El [manual de uso](MANUAL.es-ES.md) explica la página de Módulos y, para cada módulo, cada ajuste, qué va al SOC, los requisitos que comprueba el doctor, las reglas y los avisos de salud. La [referencia técnica](CODE.es-ES.md) explica el contrato con el núcleo y cómo escribir un módulo nuevo.
