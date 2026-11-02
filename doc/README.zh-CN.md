# localSIEM-modules

本 README 还提供以下语言版本：\
[de-DE](README.de-DE.md), [en-GB](README.en-GB.md), [en-US](../README.md), [es-AR](README.es-AR.md), [es-ES](README.es-ES.md), [fr-FR](README.fr-FR.md), [he-IL](README.he-IL.md), [hi-IN](README.hi-IN.md), [it-IT](README.it-IT.md), [ja-JP](README.ja-JP.md), [ko-KR](README.ko-KR.md), [pt-BR](README.pt-BR.md), [pt-PT](README.pt-PT.md), [ru-RU](README.ru-RU.md), zh-CN

## 简介

[localSIEM](https://github.com/PYMEHackers/localSIEM) 的模块。localSIEM 是一款轻量级 SIEM，运行在其所保护的同一台服务器上。每个模块教它认识服务器上的一项服务：日志在哪里、如何读取以及适用哪些规则。目前有两个模块：

- **apache2**（Apache + ModSecurity）：将每个请求的访问日志、错误日志和 ModSecurity 审计日志关联起来，并提供针对暴力破解、枚举、敏感文件、Web Shell 和数据库错误的规则。
- **privesc**（权限提升）：监控服务器上运行的内容（auditd、sudo、su、pkexec、doas、snoopy），并对提权到 root 的各个步骤发出告警。

模块从不在服务器上安装任何东西：它利用服务器上已有的内容工作。

## 截图

![localSIEM 中的 apache2 模块](https://raw.githubusercontent.com/PYMEHackers/localSIEM-modules/main/doc/screenshot.png)

## 安装

模块通过 localSIEM 的 Web 界面安装。请先以 `root` 身份安装 localSIEM：

**Debian 13**：

```bash
curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-debian.sh | bash -s -- --install --allow-from 203.0.113.10
```

**Alpine Linux 3.24**：

```bash
apk add bash curl && curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-alpine.sh | bash -s -- --install --allow-from 203.0.113.10
```

`--allow-from`：允许打开 Web 界面（`https://<server>:10443`）的 IP。

然后在 Web 界面中打开 **模块 › 可安装**，点击 **检查仓库**，查看 **前提条件**，再点击模块的 **安装**。

## 阅读文档

浏览：

- [doc/MANUAL.zh-CN.md](MANUAL.zh-CN.md)，了解如何安装、设置和使用每个模块。
- [doc/CODE.zh-CN.md](CODE.zh-CN.md)，了解模块的构建方式以及如何编写新模块（面向开发者和 AI 模型）。
