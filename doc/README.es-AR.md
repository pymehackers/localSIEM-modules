# localSIEM-modules

Este README también está disponible en:\
[en-GB](README.en-GB.md), [en-US](../README.md), es-AR, [es-ES](README.es-ES.md)

localSIEM-modules contiene los **módulos** de [localSIEM](../../localSIEM/doc/README.es-AR.md), el SIEM liviano que corre en el mismo servidor que protege. El núcleo de localSIEM guarda los eventos, busca en ellos, aplica las reglas, agrupa las alertas y las envía al SOC de PYMEHackers, pero no sabe leer ningún servicio en particular. Cada módulo le enseña un servicio: dónde están sus logs, cómo se leen, cómo se juntan en eventos, qué cuenta como «ya resuelto», qué reglas se aplican y qué necesita el servicio para estar bien configurado.

Los módulos viven separados del núcleo para que cada uno se pueda agregar, actualizar o desactivar sin tocar el propio localSIEM.

Hoy hay dos módulos:

- **apache2** (Apache + ModSecurity): lee el `access.log` y el `error.log` de Apache y el log de auditoría de ModSecurity, y junta los tres registros de cada petición en un único evento, por su `UNIQUE_ID` o, con los logs de acceso que Apache escribe por defecto, por IP de cliente, petición, estado y hora. Lo que ModSecurity ya bloqueó antes de que la aplicación lo recibiera (fases 1-2) queda en localSIEM, disponible para buscarlo, y no genera alerta; todo lo demás va al SOC, tenga el puntaje que tenga. Trae seis reglas (fuerza bruta, inicio de sesión correcto después de una fuerza bruta, enumeración, archivo sensible servido, posible web shell y error de base de datos después de un ataque), un doctor que verifica los requisitos de Apache y ModSecurity, y controles de salud que avisan cuando alguien desactiva la protección.
- **privesc** (Escalada de privilegios): vigila lo que las personas y los servicios ejecutan en el servidor y avisa de los pasos de una escalada a root. Lee auditd en servidores físicos y máquinas virtuales, un hook de las shells interactivas de bash (que también ve comandos internos como `pwd`) en todas partes, contenedores incluidos (LXC, podman, systemd-nspawn), y sudo, su, pkexec, doas y snoopy a través de syslog. Un `whoami` o un `pwd` sueltos no generan nada; una ráfaga de comandos de reconocimiento distintos en una misma sesión, sí. Trae 37 reglas (ráfaga de reconocimiento, enumeración automática como linpeas, búsqueda de programas setuid, herramientas y exploits conocidos como PwnKit o DirtyPipe, shells reversas, root heredado de un programa setuid abusado, root conseguido sin sudo ni su, comandos de web shell de cuentas de servicio, puertas traseras en cuentas, sudoers, PAM, cron o SSH, bits setuid y capacidades, historial borrado, auditd desactivado...), una búsqueda de programas setuid, capacidades y archivos sensibles modificables por otros, y un doctor que dice qué necesita cada tipo de servidor.

[Manual de uso](MANUAL.es-AR.md) · [Referencia técnica](CODE.es-AR.md)

## Requisitos

- **localSIEM 2.2.0 o posterior**, en Debian 13 o Alpine Linux 3.24 o posterior con Python 3.13 o posterior (mirá el [README de localSIEM](../../localSIEM/doc/README.es-AR.md)). Los módulos se instalan desde la web de localSIEM; el comando que le permite a localSIEM leer sus logs se ejecuta como root (no hace falta `sudo`).
- Para el módulo apache2: Apache con **ModSecurity 2 (mod_security2) y el OWASP Core Rule Set** ya activos. Instalar el módulo nunca instala Apache ni ModSecurity: si falta alguno de los dos, se instala **desactivado**, y cuando los instales, **Reconfigurar** en su página los detecta y te deja activarlo.
- Para el módulo privesc: **auditd** (recomendado en servidores físicos y máquinas virtuales; no puede correr dentro de un contenedor), **bash** (para su hook) o **snoopy**, al menos uno de ellos. Instalar el módulo no instala ninguno: si no hay ninguno, se instala **desactivado**. Dentro de los contenedores, un demonio de syslog que escriba `/var/log/auth.log` (o `/var/log/messages`) y snoopy le permiten ver sudo, su y los comandos de los scripts.

## Instalar o actualizar

Primero hay que instalar localSIEM: su instalador instala únicamente el núcleo y lo deja listo para los módulos (mirá el [README de localSIEM](https://github.com/PYMEHackers/localSIEM)). Los módulos se instalan **exclusivamente desde la web de localSIEM**: este proyecto no tiene instalador propio, y la web los descarga de este repositorio (`https://github.com/PYMEHackers/localSIEM-modules`, rama `main`).

1. Como administrador, abrí **Administración › Módulos › Instalables** (`/admin/dashboard/modules/installable/`).
2. Hacé clic en **Consultar el repositorio**: lista los módulos de este repositorio que todavía no están instalados, con la versión de cada uno. Si ya están todos instalados, lo dice: «Todos los módulos del repositorio ya están instalados.».
3. Hacé clic en **Instalar** en el módulo. localSIEM lo copia a `/opt/localsiem/modules/<nombre>/` (sin su carpeta `tests/`) y lo carga en unos segundos; el módulo sale de la lista y un cuadro de diálogo te dice qué sigue.
4. Leer los logs de un módulo necesita root, así que el cuadro de diálogo muestra el comando que tenés que ejecutar como root en el servidor (`manage.py setup-modules`), con un botón **Copiar**. Le da al usuario `localsiem` permiso de lectura sobre las carpetas que declara el módulo (`/var/log/apache2` para el módulo apache2, `/var/log/audit` para el módulo privesc) y, si le agregás la opción de configuración del módulo, también aplica esa opción:
   - `--configure-apache` (apache2): el módulo escribe un archivo propio, ejecuta `configtest`, deshace todo si falla y recarga Apache (nunca lo reinicia) si funciona.
   - `--configure-privesc` (privesc): el módulo carga sus reglas de auditd (restaura las anteriores si auditd las rechaza), pone `log_group = adm` en `auditd.conf`, instala el hook de bash y la carpeta de los archivos de comandos, y configura el formato de snoopy si está instalado. Volvé a ejecutarlo después de actualizar el módulo.

   Si al servidor le falta lo que necesita el módulo, el cuadro de diálogo muestra en su lugar lo que falta: el módulo se instala desactivado (más abajo).

**Actualizar.** Cuando abrís **Administración › Módulos › Instalados** (`/admin/dashboard/modules/installed/`), la web consulta el repositorio. Un módulo que tiene ahí una versión más nueva muestra «El repositorio tiene la versión X (la instalada es la Y).» y un botón **Actualizar**: después de que confirmás, localSIEM instala la versión nueva sobre la instalada, conserva sus ajustes, deja el módulo activado o desactivado como estaba y reinicia el colector. El comando para root se vuelve a mostrar únicamente si la versión nueva lee otros logs o tiene otra opción de configuración. Si la versión nueva necesita un localSIEM más nuevo, el aviso lo dice y no tiene botón.

La web no tiene un botón para reinstalar: para reinstalar un módulo, hacé clic en **Desinstalar** en su fila de **Instalados** y volvé a instalarlo desde **Instalables**; sus ajustes se conservan.

## Activar y configurar el módulo Apache

Si el servidor tiene Apache y ModSecurity, el módulo apache2 queda **activado** después de la instalación y ya está leyendo los logs de Apache. Si falta alguno de los dos, se instala **desactivado** y todavía no se puede activar: instalalos, hacé clic en **Reconfigurar** en la página del módulo y, cuando los detecte, activalo con su interruptor. Para revisarlo, activarlo, desactivarlo o configurarlo:

1. Abrí la web de localSIEM (`https://<servidor>:10443/`) e iniciá sesión como administrador.
2. Andá a **Administración › Módulos › Instalados** (`/admin/dashboard/modules/installed/`; `/admin/dashboard/modules/` lleva ahí). Cada módulo muestra su estado («Activado y funcionando», «Activado, con avisos», «Error», «Desactivado», «Aplicando el cambio…» o «Desconocido»), el motivo y un interruptor para activarlo o desactivarlo.
3. Hacé clic en **Configurar** para abrir `/admin/dashboard/modules/installed/apache2/`: su estado y sus cifras, sus ajustes (fuentes manuales, archivo de configuración de Apache, intervalo de descubrimiento, umbral de bloqueo, días de aprendizaje), las fuentes que lee, el doctor con el fragmento que corrige cada requisito que falta, y sus reglas (activas o no, severidad, umbral y ventana).

Los cambios se aplican en el momento, sin reiniciar nada. Los analistas ven el estado de los módulos, en modo de lectura, en `/user/dashboard/modules/`.

Desde la línea de comandos, como root:

```bash
/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py modules            # módulos instalados y su estado
/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor             # requisitos y fuentes
/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py configure-apache   # archivo que escribiría --configure-apache
```

## Activar y configurar el módulo de escalada de privilegios

Si el servidor tiene auditd, bash o snoopy, el módulo privesc queda **activado** después de la instalación. Después ejecutá, como root, el comando que muestra la web, agregándole `--configure-privesc`:

```bash
/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py setup-modules --configure-privesc
```

Lo que vigila depende del servidor:

- **Servidor físico o máquina virtual**: instalá primero auditd (`apt-get install auditd` en Debian; `apk add audit && rc-update add auditd && rc-service auditd start` en Alpine) y después ejecutá el comando de arriba. auditd ve cada programa que se ejecuta, también desde scripts y exploits, y ningún usuario puede esquivarlo.
- **Contenedor** (LXC, podman, systemd-nspawn): auditd no puede correr adentro. El módulo lee el hook de bash y syslog; instalá un demonio de syslog y snoopy (`apt-get install rsyslog snoopy` en Debian) para ver también sudo, su y los comandos de los scripts y de las web shells, y corré auditd con las reglas de este módulo en el host.

Su página, `/admin/dashboard/modules/installed/privesc/`, muestra las fuentes que lee (el log de auditoría, un archivo de comandos por usuario, syslog), el doctor (lo que le falta a cada tipo de servidor, los programas setuid que dan una shell de root, los archivos sensibles modificables por otros y los miembros de grupos como `docker` que en la práctica son root) y las reglas. Los ajustes te permiten ignorar cuentas de automatización, indicar los grupos de administradores y ajustar los umbrales de reconocimiento.

## Contenido de este proyecto

| Ruta | Contenido |
|---|---|
| `mod-apache2/` | El módulo apache2 (la carpeta de cada módulo es `mod-<nombre>/`; el módulo conserva su nombre): `module.json`, código, `severity.yaml`, reglas (`rules/`), textos de la web (`locales/`) y tests (`tests/`) |
| `mod-privesc/` | El módulo privesc: `module.json`, código, `severity.yaml`, reglas (`rules/`), textos de la web (`locales/`) y el hook de bash (`hook/`) |
| `doc/` | Manual de uso, referencia técnica y las traducciones de este README |

El [manual de uso](MANUAL.es-AR.md) explica la página de Módulos y, para cada módulo, cada ajuste, qué va al SOC, los requisitos que verifica el doctor, las reglas y los avisos de salud. La [referencia técnica](CODE.es-AR.md) explica el contrato con el núcleo y cómo escribir un módulo nuevo.
