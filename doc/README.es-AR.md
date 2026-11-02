# localSIEM-modules

Este README también está disponible en:\
[de-DE](README.de-DE.md), [en-GB](README.en-GB.md), [en-US](../README.md), es-AR, [es-ES](README.es-ES.md), [fr-FR](README.fr-FR.md), [he-IL](README.he-IL.md), [hi-IN](README.hi-IN.md), [it-IT](README.it-IT.md), [ja-JP](README.ja-JP.md), [ko-KR](README.ko-KR.md), [pt-BR](README.pt-BR.md), [pt-PT](README.pt-PT.md), [ru-RU](README.ru-RU.md), [zh-CN](README.zh-CN.md)

## Qué es

Los módulos de [localSIEM](https://github.com/PYMEHackers/localSIEM), el SIEM liviano que funciona en el mismo servidor que protege. Cada módulo le enseña un servicio del servidor: dónde están sus logs, cómo leerlos y qué reglas se aplican. Hoy hay dos:

- **apache2** (Apache + ModSecurity): junta el access log, el error log y el log de auditoría de ModSecurity de cada petición, con reglas para fuerza bruta, enumeración, archivos sensibles, web shells y errores de base de datos.
- **privesc** (Escalada de privilegios): vigila lo que se ejecuta en el servidor (auditd, sudo, su, pkexec, doas, snoopy) y avisa de los pasos de una escalada a root.

Un módulo nunca instala nada en el servidor: trabaja con lo que el servidor ya tiene.

## Capturas de pantalla

![El módulo apache2 en localSIEM](https://raw.githubusercontent.com/PYMEHackers/localSIEM-modules/main/doc/screenshot.png)

## Instalación

Los módulos se instalan desde la web de localSIEM. Primero instalá localSIEM, como `root`:

**Debian 13**:

```bash
curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-debian.sh | bash -s -- --install --allow-from 203.0.113.10
```

**Alpine Linux 3.24**:

```bash
apk add bash curl && curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-alpine.sh | bash -s -- --install --allow-from 203.0.113.10
```

`--allow-from`: las IP que pueden abrir la web (`https://<servidor>:10443`).

Después, en la web, abrí **Módulos › Instalables**, apretá **Consultar el repositorio**, mirá **Requisitos** y apretá **Instalar** en el módulo.

## Leé la documentación

Explorá:

- [doc/MANUAL.es-AR.md](MANUAL.es-AR.md) para aprender a instalar, configurar y usar cada módulo.
- [doc/CODE.es-AR.md](CODE.es-AR.md) para entender cómo están hechos y cómo escribir uno nuevo (para desarrolladores y para modelos de IA).
