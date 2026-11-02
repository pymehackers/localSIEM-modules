# localSIEM-modules

Этот README также доступен на языках:\
[de-DE](README.de-DE.md), [en-GB](README.en-GB.md), [en-US](../README.md), [es-AR](README.es-AR.md), [es-ES](README.es-ES.md), [fr-FR](README.fr-FR.md), [he-IL](README.he-IL.md), [hi-IN](README.hi-IN.md), [it-IT](README.it-IT.md), [ja-JP](README.ja-JP.md), [ko-KR](README.ko-KR.md), [pt-BR](README.pt-BR.md), [pt-PT](README.pt-PT.md), ru-RU, [zh-CN](README.zh-CN.md)

## Что это

Модули [localSIEM](https://github.com/PYMEHackers/localSIEM) — лёгкого SIEM, который работает на том же сервере, который защищает. Каждый модуль учит его одной службе сервера: где лежат её журналы, как их читать и какие правила применять. Сейчас модулей два:

- **apache2** (Apache + ModSecurity): объединяет журнал доступа, журнал ошибок и журнал аудита ModSecurity каждого запроса, с правилами для перебора паролей, перечисления, чувствительных файлов, веб-шеллов и ошибок базы данных.
- **privesc** (Повышение привилегий): следит за тем, что запускается на сервере (auditd, sudo, su, pkexec, doas, snoopy), и предупреждает о шагах повышения привилегий до root.

Модуль никогда ничего не устанавливает на сервер: он работает с тем, что на сервере уже есть.

## Снимки экрана

![Модуль apache2 в localSIEM](https://raw.githubusercontent.com/PYMEHackers/localSIEM-modules/main/doc/screenshot.png)

## Установка

Модули устанавливаются из веб-интерфейса localSIEM. Сначала установите localSIEM от имени `root`:

**Debian 13**:

```bash
curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-debian.sh | bash -s -- --install --allow-from 203.0.113.10
```

**Alpine Linux 3.24**:

```bash
apk add bash curl && curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-alpine.sh | bash -s -- --install --allow-from 203.0.113.10
```

`--allow-from`: IP, с которых разрешено открывать веб-интерфейс (`https://<server>:10443`).

Затем в веб-интерфейсе откройте **Модули › Устанавливаемые**, нажмите **Проверить репозиторий**, посмотрите **Требования** и нажмите **Установить** у модуля.

## Документация

Изучите:

- [doc/MANUAL.ru-RU.md](MANUAL.ru-RU.md), чтобы узнать, как установить, настроить и использовать каждый модуль.
- [doc/CODE.ru-RU.md](CODE.ru-RU.md), чтобы понять, как они устроены и как написать новый (для разработчиков и моделей ИИ).
