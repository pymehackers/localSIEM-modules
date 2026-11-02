# localSIEM-modules

Este README também está disponível em:\
[de-DE](README.de-DE.md), [en-GB](README.en-GB.md), [en-US](../README.md), [es-AR](README.es-AR.md), [es-ES](README.es-ES.md), [fr-FR](README.fr-FR.md), [he-IL](README.he-IL.md), [hi-IN](README.hi-IN.md), [it-IT](README.it-IT.md), [ja-JP](README.ja-JP.md), [ko-KR](README.ko-KR.md), pt-BR, [pt-PT](README.pt-PT.md), [ru-RU](README.ru-RU.md), [zh-CN](README.zh-CN.md)

## O que é

Os módulos do [localSIEM](https://github.com/PYMEHackers/localSIEM), o SIEM leve que funciona no mesmo servidor que protege. Cada módulo ensina a ele um serviço do servidor: onde ficam seus logs, como lê-los e quais regras se aplicam. Hoje há dois:

- **apache2** (Apache + ModSecurity): junta o access log, o error log e o log de auditoria do ModSecurity de cada requisição, com regras para força bruta, enumeração, arquivos sensíveis, web shells e erros de banco de dados.
- **privesc** (Escalonamento de privilégios): monitora o que é executado no servidor (auditd, sudo, su, pkexec, doas, snoopy) e avisa sobre os passos de uma escalada para root.

Um módulo nunca instala nada no servidor: ele trabalha com o que o servidor já tem.

## Capturas de tela

![O módulo apache2 no localSIEM](https://raw.githubusercontent.com/PYMEHackers/localSIEM-modules/main/doc/screenshot.png)

## Instalação

Os módulos são instalados pela interface web do localSIEM. Primeiro instale o localSIEM, como `root`:

**Debian 13**:

```bash
curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-debian.sh | bash -s -- --install --allow-from 203.0.113.10
```

**Alpine Linux 3.24**:

```bash
apk add bash curl && curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-alpine.sh | bash -s -- --install --allow-from 203.0.113.10
```

`--allow-from`: os IPs que podem abrir a interface web (`https://<server>:10443`).

Depois, na interface web, abra **Módulos › Instaláveis**, clique em **Consultar o repositório**, veja **Requisitos** e clique em **Instalar** no módulo.

## Leia a documentação

Explore:

- [doc/MANUAL.pt-BR.md](MANUAL.pt-BR.md) para aprender a instalar, configurar e usar cada módulo.
- [doc/CODE.pt-BR.md](CODE.pt-BR.md) para entender como eles são feitos e como escrever um novo (para desenvolvedores e para modelos de IA).
