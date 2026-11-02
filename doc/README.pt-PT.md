# localSIEM-modules

Este README também está disponível em:\
[de-DE](README.de-DE.md), [en-GB](README.en-GB.md), [en-US](../README.md), [es-AR](README.es-AR.md), [es-ES](README.es-ES.md), [fr-FR](README.fr-FR.md), [he-IL](README.he-IL.md), [hi-IN](README.hi-IN.md), [it-IT](README.it-IT.md), [ja-JP](README.ja-JP.md), [ko-KR](README.ko-KR.md), [pt-BR](README.pt-BR.md), pt-PT, [ru-RU](README.ru-RU.md), [zh-CN](README.zh-CN.md)

## O que é

Os módulos do [localSIEM](https://github.com/PYMEHackers/localSIEM), o SIEM leve que funciona no mesmo servidor que protege. Cada módulo ensina-lhe um serviço do servidor: onde estão os seus registos, como lê-los e que regras se aplicam. Hoje existem dois:

- **apache2** (Apache + ModSecurity): junta o registo de acessos, o registo de erros e o registo de auditoria do ModSecurity de cada pedido, com regras para força bruta, enumeração, ficheiros sensíveis, web shells e erros de base de dados.
- **privesc** (Escalada de privilégios): vigia o que é executado no servidor (auditd, sudo, su, pkexec, doas, snoopy) e avisa sobre os passos de uma escalada para root.

Um módulo nunca instala nada no servidor: trabalha com o que o servidor já tem.

## Capturas de ecrã

![O módulo apache2 no localSIEM](https://raw.githubusercontent.com/PYMEHackers/localSIEM-modules/main/doc/screenshot.png)

## Instalação

Os módulos instalam-se a partir da interface web do localSIEM. Instale primeiro o localSIEM, como `root`:

**Debian 13**:

```bash
curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-debian.sh | bash -s -- --install --allow-from 203.0.113.10
```

**Alpine Linux 3.24**:

```bash
apk add bash curl && curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-alpine.sh | bash -s -- --install --allow-from 203.0.113.10
```

`--allow-from`: os IPs autorizados a abrir a interface web (`https://<server>:10443`).

Depois, na interface web, abra **Módulos › Instaláveis**, clique em **Consultar o repositório**, consulte **Requisitos** e clique em **Instalar** no módulo.

## Consultar a documentação

Explore:

- [doc/MANUAL.pt-PT.md](MANUAL.pt-PT.md) para aprender a instalar, configurar e utilizar cada módulo.
- [doc/CODE.pt-PT.md](CODE.pt-PT.md) para perceber como estão construídos e como escrever um novo (para programadores e para modelos de IA).
